"""Health endpoints — no authentication required.

Every service exposes ``/liveness`` and ``/readiness`` per
``services/README.md`` non-negotiable.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/liveness")
def liveness():
    """Is the process alive?  Always 200 if the server can respond at all."""
    return {"status": "alive"}


@router.get("/readiness")
def readiness():
    """Is the service ready to take traffic?

    In M1 the gateway has no external dependencies (no DB, no Redis yet),
    so readiness equals liveness.  When rate limiting (Redis) is added this
    probe should verify the Redis connection.
    """
    return {"status": "ready"}
