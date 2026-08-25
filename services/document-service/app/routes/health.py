"""Health probe endpoints.

* ``GET /liveness``  — is the process alive?  Fast, no I/O.
* ``GET /readiness`` — can the service accept traffic?  Checks Postgres + Redis.

Per services/README.md:
  'Health endpoints: GET /liveness (alive) + GET /readiness (ready for traffic)
   — both must check real dependencies where relevant.'

Liveness MUST NOT depend on downstream systems (Postgres, Redis).  A liveness
probe that fails because the DB is temporarily unreachable would cause
Kubernetes to restart an otherwise healthy pod, making the outage worse.
"""

from __future__ import annotations

import logging

import redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db

logger = logging.getLogger(settings.service_name)
router = APIRouter(tags=["health"])


@router.get("/liveness")
def liveness() -> dict[str, str]:
    """Process is alive — no downstream checks."""
    return {"status": "ok", "service": settings.service_name}


@router.get("/readiness")
def readiness(db: Session = Depends(get_db)) -> dict:
    """Verify PostgreSQL and Redis are reachable."""
    checks: dict[str, str] = {}

    # --- PostgreSQL ---------------------------------------------------------
    try:
        db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        logger.warning("readiness_check_failed", extra={"dependency": "postgres"})
        checks["postgres"] = "unavailable"

    # --- Redis --------------------------------------------------------------
    try:
        r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        r.close()
        checks["redis"] = "ok"
    except Exception:
        logger.warning("readiness_check_failed", extra={"dependency": "redis"})
        checks["redis"] = "unavailable"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    from fastapi.responses import JSONResponse

    return JSONResponse(
        content={
            "status": "ready" if all_ok else "degraded",
            "service": settings.service_name,
            "checks": checks,
        },
        status_code=status_code,
    )
