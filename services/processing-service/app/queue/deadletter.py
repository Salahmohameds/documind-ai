"""Dead-letter path.

A job that has exhausted its attempts must go *somewhere*. Dropping it loses a
customer's document silently; leaving it pending forever means every
``XAUTOCLAIM`` picks it up again, so one poison message eventually occupies the
whole worker fleet. Neither is acceptable, so it moves to a second stream where
it can be inspected, fixed and replayed by hand.

The stream is capped with ``MAXLEN ~`` — approximate trimming is O(1) where
exact trimming is not — so a sustained failure cannot fill Redis and take the
live queue down with it.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from redis.asyncio import Redis

from app.config import settings
from app.metrics import DEAD_LETTERED

logger = logging.getLogger(settings.service_name)


async def publish(
    redis: Redis,
    *,
    message_id: str,
    fields: dict[str, str],
    error_code: str,
    error_message: str,
    attempts: int,
) -> None:
    """Copy a failed message to the dead-letter stream, with its diagnosis."""
    payload = dict(fields)
    payload.update(
        {
            # Preserved because the dead-letter entry gets its own new id, and
            # without this the trail back to the original message is gone.
            "original_message_id": message_id,
            "failure_code": error_code,
            "failure_reason": error_message[:1000],
            "attempts": str(attempts),
            "failed_at": datetime.now(UTC).isoformat(),
            "consumer": settings.consumer_name(),
        }
    )

    try:
        await redis.xadd(
            settings.redis_dead_letter_stream,
            payload,
            maxlen=settings.dead_letter_maxlen,
            approximate=True,
        )
    except Exception:
        # The job is already recorded FAILED in Postgres, which is the record
        # that matters to the frontend. Losing the dead-letter copy is bad but
        # it is not worth failing the ack and re-running a poison message.
        logger.exception(
            "dead_letter_publish_failed", extra={"message_id": message_id}
        )
        return

    DEAD_LETTERED.labels(error_code=error_code).inc()
    logger.error(
        "job_dead_lettered",
        extra={
            "message_id": message_id,
            "error_code": error_code,
            "attempts": attempts,
            "stream": settings.redis_dead_letter_stream,
        },
    )
