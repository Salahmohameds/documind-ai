"""Graceful shutdown: a rolling update must not lose a document.

The contract on SIGTERM:

    readiness 503 → stop reading NEW messages → let in-flight jobs finish
    → cancel whatever is left at the deadline, UN-ACKED
    → another pod's XAUTOCLAIM picks it up

The last step is the one worth testing: the pod is going away either way, and
the only question is whether the work it was holding survives.
"""

from __future__ import annotations

import asyncio

from app.config import settings
from app.database import session_scope
from app.models import ProcessingJob
from app.queue.consumer import StreamConsumer
from tests.conftest import StubPipeline, pending_count, publish


class BlockingPipeline(StubPipeline):
    """Hangs until released, so shutdown can be driven mid-job."""

    def __init__(self) -> None:
        super().__init__()
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def run(self, event):
        self.runs.append(event.job_id)
        self.entered.set()
        await self.release.wait()
        return await super().run(event)


async def test_in_flight_job_is_left_unacked_when_the_drain_times_out(
    redis, seeded_document, monkeypatch
):
    """The pod dies; the document does not."""
    monkeypatch.setattr(settings, "graceful_shutdown_s", 0.05)

    message_id = await publish(redis)
    pipeline = BlockingPipeline()
    consumer = StreamConsumer(redis=redis, pipeline=pipeline)
    await consumer.ensure_group()

    loop = asyncio.create_task(consumer.run())
    await asyncio.wait_for(pipeline.entered.wait(), timeout=2)

    await consumer.stop()
    await asyncio.wait_for(loop, timeout=5)

    # Never acked — still pending, therefore reclaimable by another worker.
    assert await pending_count(redis) == 1
    with session_scope() as session:
        # Left mid-flight rather than falsely marked COMPLETED or FAILED.
        assert session.get(ProcessingJob, message_id).status == "PROCESSING"


async def test_in_flight_job_is_allowed_to_finish_within_the_grace_period(
    redis, seeded_document, monkeypatch
):
    """Finishing is preferred: the work is nearly done and the tokens are spent."""
    monkeypatch.setattr(settings, "graceful_shutdown_s", 5.0)

    message_id = await publish(redis)
    pipeline = BlockingPipeline()
    consumer = StreamConsumer(redis=redis, pipeline=pipeline)
    await consumer.ensure_group()

    loop = asyncio.create_task(consumer.run())
    await asyncio.wait_for(pipeline.entered.wait(), timeout=2)

    await consumer.stop()
    pipeline.release.set()          # the job completes during the drain
    await asyncio.wait_for(loop, timeout=5)

    assert await pending_count(redis) == 0
    with session_scope() as session:
        assert session.get(ProcessingJob, message_id).status == "COMPLETED"


async def test_no_new_messages_are_read_once_shutdown_begins(redis, seeded_document):
    """Whatever is still in the stream stays there, visible to other pods.

    Specifically it must not be *read*: a message XREADGROUP hands over is
    immediately pending under this consumer's name, and a pod that is going
    away cannot finish it — so it would be stranded until the reclaim
    threshold expires minutes later. Leaving it unread costs nothing.
    """
    await publish(redis)
    await publish(redis)

    pipeline = StubPipeline()
    consumer = StreamConsumer(redis=redis, pipeline=pipeline)
    await consumer.ensure_group()
    await consumer.stop()

    await consumer._tick()

    assert pipeline.runs == []
    # Not claimed by anyone: still available to a healthy pod right now.
    assert await pending_count(redis) == 0
    assert await redis.xlen(settings.redis_stream_name) == 2


async def test_is_running_reports_false_during_shutdown(redis):
    """Readiness reads this — the pod must leave the endpoints list first."""
    consumer = StreamConsumer(redis=redis, pipeline=StubPipeline())
    assert consumer.is_running is False   # not started yet

    loop = asyncio.create_task(consumer.run())
    await asyncio.sleep(0.05)
    assert consumer.is_running is True

    await consumer.stop()
    assert consumer.is_running is False
    await asyncio.wait_for(loop, timeout=5)
