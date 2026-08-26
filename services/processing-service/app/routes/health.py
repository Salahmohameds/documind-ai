"""Health, readiness and metrics endpoints.

Per services/README.md every service exposes ``/liveness`` and ``/readiness``.
A worker takes no HTTP traffic, so the distinction is sharper here than it is
for an API:

``/liveness``  — is this process still *doing its job*? For a worker that is
    not "can the HTTP server answer", because a worker whose consumer task has
    died still answers HTTP perfectly while consuming nothing. That failure is
    invisible to every other signal — the pod is Running, Ready, using no CPU,
    and the queue quietly grows. So liveness checks the consumer task itself
    and nothing downstream. Restarting is the right response; a dead task
    cannot be revived in place.

``/readiness`` — can this pod usefully take work? Postgres, Redis, storage, and
    the consumer group. It goes 503 the moment shutdown begins, which is what
    takes the pod out of the endpoints list before its jobs are drained.

Liveness deliberately does NOT check Postgres or Redis: a probe that fails
because the database blipped would have Kubernetes restart every worker at
once, turning a dependency outage into an outage plus a thundering herd.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app.config import settings
from app.database import engine

logger = logging.getLogger(settings.service_name)
router = APIRouter(tags=["health"])


@router.get("/liveness")
def liveness(request: Request) -> JSONResponse:
    """Process alive AND the consumer task still running."""
    state = request.app.state
    consumer_task = getattr(state, "consumer_task", None)
    shutting_down = getattr(state, "shutting_down", False)

    # During drain the task is finishing on purpose — reporting dead here would
    # have the kubelet SIGKILL a pod that is doing exactly what it should.
    alive = shutting_down or (consumer_task is not None and not consumer_task.done())

    if not alive:
        logger.error("liveness_failed", extra={"reason": "consumer_task_not_running"})
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": settings.service_name,
                "reason": "consumer_task_not_running",
            },
        )

    return JSONResponse(
        content={"status": "ok", "service": settings.service_name}
    )


@router.get("/readiness")
async def readiness(request: Request) -> JSONResponse:
    """Verify every dependency the worker needs to process a job."""
    state = request.app.state
    checks: dict[str, str] = {}

    if getattr(state, "shutting_down", False):
        return JSONResponse(
            status_code=503,
            content={
                "status": "draining",
                "service": settings.service_name,
                "checks": {"consumer": "draining"},
            },
        )

    # --- PostgreSQL --------------------------------------------------------
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        logger.warning("readiness_check_failed", extra={"dependency": "postgres"})
        checks["postgres"] = "unavailable"

    # --- Redis -------------------------------------------------------------
    redis = getattr(state, "redis", None)
    try:
        if redis is None:
            raise RuntimeError("redis client not initialised")
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        logger.warning("readiness_check_failed", extra={"dependency": "redis"})
        checks["redis"] = "unavailable"

    # --- Object storage ----------------------------------------------------
    reader = getattr(state, "reader", None)
    try:
        if reader is None:
            raise RuntimeError("storage reader not initialised")
        reader.health_check()
        checks["storage"] = "ok"
    except Exception:
        logger.warning("readiness_check_failed", extra={"dependency": "storage"})
        checks["storage"] = "unavailable"

    # --- Consumer ----------------------------------------------------------
    consumer = getattr(state, "consumer", None)
    try:
        if consumer is None or not consumer.is_running:
            checks["consumer"] = "not_running"
        elif await consumer.group_exists():
            checks["consumer"] = "ok"
        else:
            checks["consumer"] = "group_missing"
    except Exception:
        logger.warning("readiness_check_failed", extra={"dependency": "consumer"})
        checks["consumer"] = "unavailable"

    # ai-service and search-service are deliberately NOT checked. A worker with
    # a reachable queue and database is ready to *claim* jobs; if a downstream
    # model service is down, the circuit breaker fails those jobs fast and the
    # retry path handles them. Gating readiness on them would take the entire
    # worker fleet out of service for a dependency that only affects some
    # stages — and readiness has no traffic to gate here anyway.

    all_ok = all(value == "ok" for value in checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status": "ready" if all_ok else "degraded",
            "service": settings.service_name,
            "checks": checks,
        },
    )


@router.get("/metrics")
def metrics() -> PlainTextResponse:
    """Prometheus scrape endpoint."""
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST
    )
