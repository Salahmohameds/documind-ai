"""Redelivery must not reprocess a completed document.

At-least-once delivery is not a corner case; it is the normal behaviour of the
broker. A message is redelivered whenever an ack is lost, a pod dies between
the commit and the ack, or a job is reclaimed after a false-positive idle
timeout. Without a gate, each of those re-indexes the document, overwrites its
risk assessment and spends model tokens to arrive back where it already was.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.database import session_scope
from app.models import ProcessingJob
from app.queue.consumer import StreamConsumer
from tests.conftest import (
    DOCUMENT_ID,
    StubPipeline,
    drain_once,
    job_fields,
    publish,
)


async def test_redelivered_message_is_acked_without_reprocessing(redis, seeded_document):
    message_id = await publish(redis)
    pipeline = StubPipeline()
    consumer = StreamConsumer(redis=redis, pipeline=pipeline)
    await consumer.ensure_group()

    await drain_once(consumer)
    assert pipeline.runs == [message_id]

    # The same message arrives again — the ack was lost, or the pod died
    # between committing COMPLETED and acking.
    await consumer._dispatch(message_id, job_fields())
    import asyncio

    await asyncio.gather(*list(consumer._tasks), return_exceptions=True)

    # Ran once, not twice.
    assert pipeline.runs == [message_id]

    with session_scope() as session:
        job = session.get(ProcessingJob, message_id)
        assert job.status == "COMPLETED"
        assert job.attempt == 1


async def test_a_new_message_for_the_same_document_does_reprocess(redis, seeded_document):
    """The gate is per *job*, not per document.

    Re-uploading a document, or a deliberate replay from the dead-letter
    stream, is a new message id and must be processed.
    """
    first = await publish(redis)
    pipeline = StubPipeline()
    consumer = StreamConsumer(redis=redis, pipeline=pipeline)
    await consumer.ensure_group()
    await drain_once(consumer)

    second = await publish(redis)
    await drain_once(consumer)

    assert pipeline.runs == [first, second]
    assert first != second


async def test_a_previously_failed_job_is_retried_not_skipped(redis, seeded_document):
    """Only COMPLETED stops the pipeline. FAILED deserves the retry."""
    message_id = "1724692800000-0"
    with session_scope() as session:
        session.add(
            ProcessingJob(
                job_id=message_id,
                document_id=DOCUMENT_ID,
                status="FAILED",
                attempt=1,
                error_code="ERR_UPSTREAM_UNAVAILABLE",
                error_message="ai-service was down",
                queued_at=datetime.now(UTC),
            )
        )

    pipeline = StubPipeline()
    consumer = StreamConsumer(redis=redis, pipeline=pipeline)
    await consumer.ensure_group()
    await consumer._dispatch(message_id, job_fields())
    import asyncio

    await asyncio.gather(*list(consumer._tasks), return_exceptions=True)

    assert pipeline.runs == [message_id]
    with session_scope() as session:
        job = session.get(ProcessingJob, message_id)
        assert job.status == "COMPLETED"
        # Second attempt, counted from the row rather than the broker.
        assert job.attempt == 2
        # The previous attempt's error must not linger and be read as current.
        assert job.error_code is None


async def test_attempt_count_survives_a_broker_that_reports_nothing(redis, seeded_document):
    """A worker OOM-killed mid-job leaves the row PROCESSING.

    The next claim must count that as a spent attempt — otherwise a job that
    reliably kills its worker gets an unbounded retry budget.
    """
    message_id = "1724692800001-0"
    with session_scope() as session:
        session.add(
            ProcessingJob(
                job_id=message_id,
                document_id=DOCUMENT_ID,
                status="PROCESSING",
                attempt=2,
                consumer_name="pod-that-died",
                queued_at=datetime.now(UTC),
            )
        )

    pipeline = StubPipeline()
    consumer = StreamConsumer(redis=redis, pipeline=pipeline)
    await consumer.ensure_group()
    await consumer._dispatch(message_id, job_fields())
    import asyncio

    await asyncio.gather(*list(consumer._tasks), return_exceptions=True)

    with session_scope() as session:
        assert session.get(ProcessingJob, message_id).attempt == 3
