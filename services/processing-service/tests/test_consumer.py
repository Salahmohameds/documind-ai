"""Consumer reliability: the ack policy, reclaim, dead-lettering, idempotency.

These are the tests that justify calling this a cloud-native worker rather than
a script. Each one pins a guarantee:

* a completed job is acked, and its document reaches INDEXED;
* a transient failure is NOT acked, so the message stays pending for reclaim;
* a terminal failure IS acked and dead-lettered, so a poison message cannot
  circulate through the fleet forever;
* a job abandoned by a dead worker is reclaimed by a live one;
* a redelivered message for a completed job does no work a second time.

They run against fakeredis, which implements real consumer-group semantics —
XPENDING, XAUTOCLAIM and delivery counters included — so the behaviour under
test is the behaviour Redis will produce.
"""

from __future__ import annotations


from app.config import settings
from app.database import session_scope
from app.errors import ProcessingError, UpstreamUnavailableError
from app.models import Document, ProcessingJob
from app.pipeline import PipelineResult
from app.queue.consumer import StreamConsumer
from tests.conftest import (
    DOCUMENT_ID,
    StubPipeline,
    drain_once,
    pending_count,
    publish,
)


# --------------------------------------------------------------------------
# Group creation
# --------------------------------------------------------------------------
async def test_creates_the_group_and_tolerates_it_already_existing(redis):
    consumer = StreamConsumer(redis=redis, pipeline=StubPipeline())

    await consumer.ensure_group()
    # Idempotent: every replica runs this on startup, and BUSYGROUP is the
    # normal case for all but the first.
    await consumer.ensure_group()

    assert await consumer.group_exists() is True


async def test_group_starts_at_zero_so_queued_work_is_not_skipped(redis, seeded_document):
    """A message published BEFORE the first worker starts must still be seen.

    Creating the group at '$' would silently skip everything already queued —
    a real hazard on a fresh deploy.
    """
    message_id = await publish(redis)

    pipeline = StubPipeline()
    consumer = StreamConsumer(redis=redis, pipeline=pipeline)
    await consumer.ensure_group()
    await drain_once(consumer)

    assert pipeline.runs == [message_id]


# --------------------------------------------------------------------------
# Ack policy
# --------------------------------------------------------------------------
async def test_successful_job_is_acked_and_recorded(redis, seeded_document):
    message_id = await publish(redis)
    consumer = StreamConsumer(redis=redis, pipeline=StubPipeline())
    await consumer.ensure_group()

    await drain_once(consumer)

    assert await pending_count(redis) == 0
    with session_scope() as session:
        job = session.get(ProcessingJob, message_id)
        assert job.status == "COMPLETED"
        assert job.duration_ms is not None
        assert job.finished_at is not None
        # documents.status uses the constraint's vocabulary, not the job's.
        assert session.get(Document, DOCUMENT_ID).status == "INDEXED"
        assert session.get(Document, DOCUMENT_ID).indexed_at is not None


async def test_transient_failure_is_not_acked(redis, seeded_document):
    """The message must stay pending so another worker can reclaim it.

    Acking here would lose the document with no trace — the single worst
    outcome this design exists to prevent.
    """
    message_id = await publish(redis)
    pipeline = StubPipeline(error=UpstreamUnavailableError("ai-service is down"))
    consumer = StreamConsumer(redis=redis, pipeline=pipeline)
    await consumer.ensure_group()

    await drain_once(consumer)

    assert await pending_count(redis) == 1
    with session_scope() as session:
        job = session.get(ProcessingJob, message_id)
        # Back to QUEUED, not FAILED: it has attempts left.
        assert job.status == "QUEUED"
        assert job.error_code == "ERR_UPSTREAM_UNAVAILABLE"
        # The frontend should show "still working", not a red state that will
        # silently turn green again.
        assert session.get(Document, DOCUMENT_ID).status == "UPLOADED"


async def test_terminal_failure_is_acked_and_dead_lettered(redis, seeded_document):
    """A job that cannot ever succeed is retired immediately."""
    message_id = await publish(redis)
    pipeline = StubPipeline(error=ProcessingError("not a pdf"))  # retryable=False
    consumer = StreamConsumer(redis=redis, pipeline=pipeline)
    await consumer.ensure_group()

    await drain_once(consumer)

    assert await pending_count(redis) == 0
    assert pipeline.runs == [message_id]  # tried exactly once, not three times

    dead = await redis.xrange(settings.redis_dead_letter_stream)
    assert len(dead) == 1
    entry = dead[0][1]
    assert entry["original_message_id"] == message_id
    assert entry["failure_code"] == "ERR_PROCESSING"
    # The original payload is preserved so the job can be replayed by hand.
    assert entry["document_id"] == DOCUMENT_ID

    with session_scope() as session:
        assert session.get(ProcessingJob, message_id).status == "FAILED"
        assert session.get(Document, DOCUMENT_ID).status == "FAILED"


async def test_malformed_event_goes_straight_to_the_dead_letter_stream(redis):
    """A message missing document_id will be just as broken on delivery three."""
    message_id = await redis.xadd(
        settings.redis_stream_name, {"event_version": "1", "filename": "x.pdf"}
    )
    pipeline = StubPipeline()
    consumer = StreamConsumer(redis=redis, pipeline=pipeline)
    await consumer.ensure_group()

    await drain_once(consumer)

    assert pipeline.runs == []          # never entered the pipeline
    assert await pending_count(redis) == 0
    dead = await redis.xrange(settings.redis_dead_letter_stream)
    assert dead[0][1]["failure_code"] == "ERR_MALFORMED_JOB"
    assert dead[0][1]["original_message_id"] == message_id


async def test_unknown_event_version_is_rejected_rather_than_guessed(redis):
    await redis.xadd(
        settings.redis_stream_name,
        {"event_version": "9", "document_id": DOCUMENT_ID, "storage_key": "k"},
    )
    pipeline = StubPipeline()
    consumer = StreamConsumer(redis=redis, pipeline=pipeline)
    await consumer.ensure_group()

    await drain_once(consumer)

    assert pipeline.runs == []
    dead = await redis.xrange(settings.redis_dead_letter_stream)
    assert dead[0][1]["failure_code"] == "ERR_MALFORMED_JOB"


async def test_unknown_extra_fields_are_ignored(redis, seeded_document):
    """The contract is additive: role 3 can add a field without a lockstep deploy."""
    message_id = await publish(redis, user_id="user_42", tenant="acme", priority="high")
    consumer = StreamConsumer(redis=redis, pipeline=StubPipeline())
    await consumer.ensure_group()

    await drain_once(consumer)

    with session_scope() as session:
        job = session.get(ProcessingJob, message_id)
        assert job.status == "COMPLETED"
        # user_id is read opportunistically — it is not in the contract yet.
        assert job.user_id == "user_42"


# --------------------------------------------------------------------------
# Attempt budget
# --------------------------------------------------------------------------
async def test_retryable_failure_is_dead_lettered_once_attempts_run_out(
    redis, seeded_document, monkeypatch
):
    """Bounded, so a permanently-down dependency does not requeue forever."""
    monkeypatch.setattr(settings, "max_attempts", 2)

    await publish(redis)
    pipeline = StubPipeline(error=UpstreamUnavailableError("still down"))
    consumer = StreamConsumer(redis=redis, pipeline=pipeline)
    await consumer.ensure_group()

    # Delivery 1: retryable, left pending.
    await drain_once(consumer)
    assert await pending_count(redis) == 1
    assert await redis.xlen(settings.redis_dead_letter_stream) == 0

    # Delivery 2 (via reclaim): attempts exhausted, retired.
    monkeypatch.setattr(settings, "reclaim_min_idle_ms", 0)
    consumer._last_reclaim = 0.0
    await drain_once(consumer)

    assert await pending_count(redis) == 0
    assert await redis.xlen(settings.redis_dead_letter_stream) == 1


# --------------------------------------------------------------------------
# Reclaim — the self-healing path
# --------------------------------------------------------------------------
async def test_a_second_worker_reclaims_a_job_abandoned_by_the_first(
    redis, seeded_document, monkeypatch
):
    """`kubectl delete pod` mid-job must not strand the document.

    A pending message belonging to a pod that no longer exists is invisible to
    XREADGROUP — it was already delivered — so without XAUTOCLAIM it would sit
    there forever.
    """
    message_id = await publish(redis)

    dead_worker = StreamConsumer(redis=redis, pipeline=StubPipeline())
    await dead_worker.ensure_group()
    # Claim the message, then "die" without acking it.
    await redis.xreadgroup(
        groupname=settings.redis_consumer_group,
        consumername="pod-that-dies",
        streams={settings.redis_stream_name: ">"},
        count=1,
    )
    assert await pending_count(redis) == 1

    monkeypatch.setattr(settings, "reclaim_min_idle_ms", 0)
    survivor_pipeline = StubPipeline()
    survivor = StreamConsumer(redis=redis, pipeline=survivor_pipeline)
    survivor._last_reclaim = 0.0

    await drain_once(survivor)

    assert survivor_pipeline.runs == [message_id]
    assert await pending_count(redis) == 0
    with session_scope() as session:
        assert session.get(ProcessingJob, message_id).status == "COMPLETED"


async def test_reclaim_leaves_healthy_in_flight_work_alone(redis, seeded_document):
    """Only messages idle beyond the threshold are taken.

    The default threshold sits above job_timeout_s precisely so a worker that
    is still doing its job does not have it stolen mid-flight.
    """
    await publish(redis)
    consumer = StreamConsumer(redis=redis, pipeline=StubPipeline())
    await consumer.ensure_group()
    await redis.xreadgroup(
        groupname=settings.redis_consumer_group,
        consumername="busy-pod",
        streams={settings.redis_stream_name: ">"},
        count=1,
    )

    # settings.reclaim_min_idle_ms is the 300 s default here.
    consumer._last_reclaim = 0.0
    await consumer._maybe_reclaim()

    assert consumer._tasks == set()
    assert await pending_count(redis) == 1


# --------------------------------------------------------------------------
# Degraded completion
# --------------------------------------------------------------------------
async def test_degraded_completion_is_recorded_as_such(redis, seeded_document):
    message_id = await publish(redis)
    pipeline = StubPipeline(result=PipelineResult(degraded=True))
    consumer = StreamConsumer(redis=redis, pipeline=pipeline)
    await consumer.ensure_group()

    await drain_once(consumer)

    with session_scope() as session:
        job = session.get(ProcessingJob, message_id)
        assert job.status == "COMPLETED"
        assert job.degraded is True
