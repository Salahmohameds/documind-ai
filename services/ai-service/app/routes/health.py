"""Health probe endpoints.

* ``GET /liveness``  - is the process alive? Fast, no I/O.
* ``GET /readiness`` - can the service accept traffic? Probes the provider.

Per services/README.md:
  'Health endpoints: GET /liveness (alive) + GET /readiness (ready for traffic)
   - both must check real dependencies where relevant.'

Liveness MUST NOT depend on the model provider. A liveness probe that fails
because OCI Generative AI is having a bad afternoon would have Kubernetes
restart every healthy pod in the deployment, turning a degraded dependency into
a self-inflicted outage.

Readiness means something here: it reflects an actual (cached) reachability
probe and the circuit breaker state, so a pod that cannot serve model-backed
traffic is pulled out of the Service endpoints instead of accepting requests it
will fail. ``return 200`` would be a lie with a health check's name on it.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.adapters import get_provider
from app.config import settings
from app.pipeline import breaker, provider_reachable

logger = logging.getLogger(settings.service_name)
router = APIRouter(tags=["health"])


@router.get("/liveness")
def liveness() -> dict[str, str]:
    """Process is alive - no downstream checks."""
    return {"status": "ok", "service": settings.service_name}


@router.get("/readiness")
def readiness() -> JSONResponse:
    """Report whether this pod can actually serve model-backed traffic."""
    provider = get_provider()
    checks: dict[str, object] = {}

    circuit = breaker.state
    checks["circuit_breaker"] = circuit

    try:
        reachable = provider_reachable()
        checks["provider"] = "ok" if reachable else "unreachable"
    except Exception as exc:
        logger.warning(
            "readiness_check_failed",
            extra={"event": "readiness_check_failed", "dependency": "provider", "error": str(exc)},
        )
        reachable = False
        checks["provider"] = "error"

    checks["backend"] = settings.ai_backend
    checks["model"] = provider.chat_model
    checks["embedding_model"] = provider.embed_model
    checks["embedding_dim"] = provider.embed_dim

    ready = reachable and circuit != "open"
    return JSONResponse(
        content={
            "status": "ready" if ready else "degraded",
            "service": settings.service_name,
            "provider": provider.name,
            "checks": checks,
        },
        status_code=200 if ready else 503,
    )
