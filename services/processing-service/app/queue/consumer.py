"""Redis Streams consumer — the reliability core of the service.

Everything here exists to make one guarantee: **a job is never lost and never
silently done twice.** The mechanisms, and why each is needed:

``XREADGROUP`` with a consumer group
    Many pods read one stream, each message goes to exactly one of them, and
    Redis remembers who holds what. This is what makes `replicas: 10` under the
    HPA a scaling story rather than ten workers racing on the same documents.

Ack *after* the outcome is committed, never before
    An ack says "this message is dealt with". Acking on receipt and then
    crashing loses the document with no trace. So the ack happens after the
    terminal status is written to Postgres — and a transient failure is not
    acked at all, leaving the message pending on purpose.

``XAUTOCLAIM`` on an interval
    A pending message belonging to a pod that no longer exists is invisible to
    ``XREADGROUP`` — it was delivered, so it is nobody's "new" message, and it
    would sit there forever. Reclaiming messages idle beyond
    ``reclaim_min_idle_ms`` is what makes `kubectl delete pod` mid-job a
    self-healing demo instead of a lost document.

Redis' delivery counter as the attempt count
    Not a per-process retry loop. A pod that is OOM-killed holding a job
    consumed an attempt, and the next worker to claim it can see that. An
    in-process counter resets to zero on every crash, which is precisely the
    case it needs to survive.

Dead-letter after ``max_attempts``
    Bounded so a poison message cannot circulate through the fleet forever.

The consumer is otherwise stateless: everything it knows is in Redis and
Postgres, so any pod can take over any job, and losing a pod costs a re-probe.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import uuid
from datetime import UTC, datetime

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.config import settings
from app.errors import JobTimeoutError, ProcessingError
from app.logging_config import bind_job_context
from app.metrics import (
    JOB_DURATION,
    JOBS,
    JOBS_IN_FLIGHT,
    RECLAIMED,
    STREAM_LENGTH,
    STREAM_PENDING,
)
from app.pipeline import JobEvent, ProcessingPipeline
from app.queue import deadletter, events
from app.database import session_scope
from app.repositories.jobs import JobRepository

logger = logging.getLogger(settings.service_name)

# Poll interval used only when blocking reads are disabled (read_block_ms <= 0).
_IDLE_POLL_S = 0.05


class StreamConsumer:
    def __init__(self, *, redis: Redis, pipeline: ProcessingPipeline) -> None:
        self._redis = redis
        self._pipeline = pipeline
        self._consumer_name = settings.consumer_name()
        self._stream = settings.redis_stream_name
        self._group = settings.redis_consumer_group

        self._stopping = asyncio.Event()
        # The hard bound on concurrent jobs. _tick already reads only what it
        # has capacity for, but the reclaim path dispatches too, and without
        # this a burst of reclaimed messages becomes that many concurrent
        # pipelines in one pod, each holding a DB session and an HTTP
        # connection.
        self._slots = asyncio.Semaphore(settings.concurrency)
        self._tasks: set[asyncio.Task] = set()
        self._last_reclaim = 0.0
        self._started = False

    # -- lifecycle ---------------------------------------------------------
    @property
    def is_running(self) -> bool:
        return self._started and not self._stopping.is_set()

    async def ensure_group(self) -> None:
        """Create the consumer group, tolerating the common races.

        ``MKSTREAM`` so a worker can start before any document has ever been
        uploaded — otherwise the first deploy of a fresh environment crash-loops
        until someone uploads something.

        ``id="0"`` rather than ``"$"``: ``$`` means "only messages published
        after this moment", which would silently skip every job already waiting
        in the stream when the first worker starts.
        """
        try:
            await self._redis.xgroup_create(
                name=self._stream, groupname=self._group, id="0", mkstream=True
            )
            logger.info("consumer_group_created", extra={"group": self._group})
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
            logger.debug("consumer_group_exists", extra={"group": self._group})

    async def group_exists(self) -> bool:
        """Readiness check — the group is what the pod actually consumes from."""
        try:
            groups = await self._redis.xinfo_groups(self._stream)
        except ResponseError:
            return False
        return any(_decode(group.get("name")) == self._group for group in groups)

    async def run(self) -> None:
        """Read, dispatch, reclaim — until stopped."""
        await self.ensure_group()
        self._started = True
        logger.info(
            "consumer_started",
            extra={
                "consumer": self._consumer_name,
                "group": self._group,
                "stream": self._stream,
                "concurrency": settings.concurrency,
            },
        )

        try:
            while not self._stopping.is_set():
                try:
                    await self._tick()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    # Never let a transient Redis error kill the loop: the pod
                    # would keep passing liveness while consuming nothing.
                    # (Liveness watches the task, so a genuine death is caught
                    # — this is about not dying for a blip.)
                    logger.exception("consumer_loop_error")
                    await asyncio.sleep(1.0)
        finally:
            self._started = False
            await self._drain()

    async def stop(self) -> None:
        """Signal the loop to finish. Safe to call more than once."""
        self._stopping.set()

    # -- one iteration -----------------------------------------------------
    async def _tick(self) -> None:
        # Checked before the read, not after: a message that XREADGROUP hands
        # us is already marked pending under this consumer's name, and
        # discarding it would strand it until the reclaim threshold expires
        # minutes later. Not reading it at all leaves it in the stream, where
        # any pod can pick it up immediately.
        if self._stopping.is_set():
            return

        await self._maybe_reclaim()
        await self._refresh_depth_metrics()

        # Capacity is checked BEFORE reading, and only free slots are asked
        # for. A message XREADGROUP hands over is immediately pending under
        # this consumer's name, so fetching one there is no slot to run would
        # hide it from the pods that could run it — and from the HPA, which
        # reads queue depth to decide whether more pods are needed.
        free = min(settings.read_batch_size, settings.concurrency - len(self._tasks))
        if free <= 0:
            await asyncio.sleep(_IDLE_POLL_S)
            return

        response = await self._read(free)
        if not response:
            return

        for _stream_name, messages in response:
            for message_id, fields in messages:
                # No stopping check here on purpose. These messages are already
                # pending under our name; dispatching gives them a chance to
                # finish inside the drain window, and anything that does not
                # finish is left un-acked for another worker either way.
                await self._dispatch(_decode(message_id), _decode_fields(fields))

    async def _read(self, count: int):
        """One XREADGROUP, blocking or polling.

        ``BLOCK 0`` means *block forever* in Redis, which would leave a worker
        wedged in a read that no shutdown signal can interrupt. So a
        non-positive ``read_block_ms`` is treated as "do not block" and paired
        with a short sleep, rather than passed through to mean the opposite of
        what the number suggests.
        """
        if settings.read_block_ms > 0:
            return await self._redis.xreadgroup(
                groupname=self._group,
                consumername=self._consumer_name,
                streams={self._stream: ">"},
                count=count,
                block=settings.read_block_ms,
            )

        response = await self._redis.xreadgroup(
            groupname=self._group,
            consumername=self._consumer_name,
            streams={self._stream: ">"},
            count=count,
        )
        if not response:
            # Yield rather than spin the loop at full speed on an empty queue.
            await asyncio.sleep(_IDLE_POLL_S)
        return response

    async def _dispatch(self, message_id: str, fields: dict[str, str]) -> None:
        """Start one job, respecting the concurrency limit."""
        await self._slots.acquire()
        task = asyncio.create_task(self._run_job(message_id, fields))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        task.add_done_callback(lambda _: self._slots.release())

    # -- one job -----------------------------------------------------------
    async def _run_job(self, message_id: str, fields: dict[str, str]) -> None:
        attempt = await self._delivery_count(message_id)
        # One correlation id per job, propagated to ai-service and
        # search-service as X-Request-ID.
        request_id = fields.get("request_id") or f"job-{uuid.uuid4().hex[:16]}"
        bind_job_context(
            job_id=message_id,
            document_id=fields.get("document_id", "-"),
            request_id=request_id,
        )

        JOBS_IN_FLIGHT.inc()
        started = time.monotonic()
        try:
            await self._process(message_id, fields, attempt)
        except asyncio.CancelledError:
            raise
        except Exception:
            # _process handles the failures it knows about. This is the net
            # under a bug in the handling itself: without it the exception dies
            # inside a task nobody awaits, the message is left pending, and the
            # only trace is asyncio's "exception was never retrieved" at GC
            # time. Left un-acked deliberately — a bug here is not a reason to
            # declare the document dead.
            logger.exception("job_handler_crashed", extra={"attempt": attempt})
        finally:
            JOBS_IN_FLIGHT.dec()
            JOB_DURATION.observe(time.monotonic() - started)

    async def _process(
        self, message_id: str, fields: dict[str, str], attempt: int
    ) -> None:
        # --- parse (terminal on failure) ----------------------------------
        try:
            event = events.parse(message_id, fields, attempt=attempt)
        except ProcessingError as exc:
            logger.error(
                "job_rejected", extra={"error_code": exc.code, "error": str(exc)}
            )
            # Straight to the dead-letter stream: a malformed message will be
            # just as malformed on its third delivery.
            await deadletter.publish(
                self._redis,
                message_id=message_id,
                fields=fields,
                error_code=exc.code,
                error_message=str(exc),
                attempts=attempt,
            )
            await self._ack(message_id)
            JOBS.labels(outcome="failed").inc()
            return

        # --- claim (idempotency gate) -------------------------------------
        claimed_attempt = await asyncio.to_thread(self._claim, event)
        if claimed_attempt is None:
            logger.info("job_already_completed", extra={"attempt": attempt})
            await self._ack(message_id)
            JOBS.labels(outcome="skipped_duplicate").inc()
            return

        # The repository reconciles Redis' counter with what the row already
        # recorded; that reconciled value, not the raw counter, is what the
        # attempt budget is spent against.
        attempt = claimed_attempt
        event.attempt = attempt

        logger.info(
            "job_started",
            # 'document_filename', not 'filename': LogRecord already owns that
            # name, and logging raises KeyError rather than shadowing it.
            extra={"attempt": attempt, "document_filename": event.filename},
        )

        # --- run ----------------------------------------------------------
        try:
            result = await asyncio.wait_for(
                self._pipeline.run(event), timeout=settings.job_timeout_s
            )
        except TimeoutError as exc:
            await self._fail(
                event,
                JobTimeoutError(
                    f"Job exceeded the {settings.job_timeout_s}s limit"
                ),
                attempt,
                fields,
            )
            del exc
            return
        except ProcessingError as exc:
            await self._fail(event, exc, attempt, fields)
            return
        except asyncio.CancelledError:
            # Shutdown. Leave the message pending, un-acked, so another pod
            # reclaims it. This is the correct outcome, not an error.
            logger.info("job_cancelled_for_shutdown")
            raise
        except Exception as exc:
            logger.exception("job_unexpected_error")
            await self._fail(event, ProcessingError(str(exc)), attempt, fields)
            return

        # --- complete ------------------------------------------------------
        await asyncio.to_thread(self._complete, event, result.degraded)
        await self._ack(message_id)

        outcome = "completed_degraded" if result.degraded else "completed"
        JOBS.labels(outcome=outcome).inc()
        logger.info(
            "processing_completed",
            extra={
                "attempt": attempt,
                "degraded": result.degraded,
                "document_type": result.document_type,
                "pages": result.page_count,
                "chunks": result.chunks_indexed,
                "skipped_stages": result.skipped_stages,
            },
        )

    async def _fail(
        self,
        event: JobEvent,
        error: ProcessingError,
        attempt: int,
        fields: dict[str, str],
    ) -> None:
        """Apply the ack policy for a failed job.

        Terminal, or out of attempts → record FAILED, dead-letter, ack.
        Retryable with attempts left → record the reason, do NOT ack. The
        message stays pending and ``XAUTOCLAIM`` hands it to a worker later.
        """
        exhausted = attempt >= settings.max_attempts
        give_up = (not error.retryable) or exhausted

        if give_up:
            await asyncio.to_thread(self._mark_failed, event, error)
            await deadletter.publish(
                self._redis,
                message_id=event.job_id,
                fields=fields,
                error_code=error.code,
                error_message=str(error),
                attempts=attempt,
            )
            await self._ack(event.job_id)
            JOBS.labels(outcome="failed").inc()
            logger.error(
                "processing_failed",
                extra={
                    "error_code": error.code,
                    "error": str(error),
                    "attempt": attempt,
                    "retryable": error.retryable,
                    "terminal": True,
                },
            )
            return

        await asyncio.to_thread(self._requeue, event, error)
        logger.warning(
            "processing_deferred",
            extra={
                "error_code": error.code,
                "error": str(error),
                "attempt": attempt,
                "max_attempts": settings.max_attempts,
                "terminal": False,
            },
        )

    # -- database (sync, run off the event loop) ---------------------------
    def _claim(self, event: JobEvent) -> int | None:
        with session_scope() as session:
            return JobRepository(session).claim(
                job_id=event.job_id,
                document_id=event.document_id,
                user_id=event.user_id,
                delivered=event.attempt,
                consumer_name=self._consumer_name,
                queued_at=_parse_timestamp(event.uploaded_at),
            )

    @staticmethod
    def _complete(event: JobEvent, degraded: bool) -> None:
        with session_scope() as session:
            JobRepository(session).mark_completed(
                job_id=event.job_id, degraded=degraded
            )

    @staticmethod
    def _mark_failed(event: JobEvent, error: ProcessingError) -> None:
        with session_scope() as session:
            JobRepository(session).mark_failed(
                job_id=event.job_id,
                error_code=error.code,
                error_message=str(error),
                stage=None,
            )

    @staticmethod
    def _requeue(event: JobEvent, error: ProcessingError) -> None:
        with session_scope() as session:
            JobRepository(session).requeue(
                job_id=event.job_id,
                error_code=error.code,
                error_message=str(error),
            )

    # -- redis helpers -----------------------------------------------------
    async def _ack(self, message_id: str) -> None:
        try:
            await self._redis.xack(self._stream, self._group, message_id)
        except Exception:
            # The outcome is already committed to Postgres. A failed ack means
            # the message is redelivered later, and the idempotency gate in
            # `claim` turns that second delivery into a no-op — which is
            # exactly why the gate exists.
            logger.warning("ack_failed", extra={"message_id": message_id})

    async def _delivery_count(self, message_id: str) -> int:
        """How many times Redis has handed this message to a consumer.

        Survives pod death, unlike an in-process counter — which is the whole
        point, since pod death is the failure this budget is bounding.
        """
        try:
            pending = await self._redis.xpending_range(
                self._stream, self._group, min=message_id, max=message_id, count=1
            )
        except Exception:
            return 0
        if not pending:
            return 1
        # Absent on some broker implementations; the persisted attempt count in
        # `claim` covers that case, so 0 here means "no opinion" rather than
        # "first delivery".
        return int(pending[0].get("times_delivered") or 0)

    async def _maybe_reclaim(self) -> None:
        """Take over messages abandoned by a worker that stopped."""
        now = time.monotonic()
        if now - self._last_reclaim < settings.reclaim_interval_s:
            return
        self._last_reclaim = now

        try:
            _next_id, messages, _deleted = await self._redis.xautoclaim(
                name=self._stream,
                groupname=self._group,
                consumername=self._consumer_name,
                min_idle_time=settings.reclaim_min_idle_ms,
                start_id="0-0",
                count=settings.read_batch_size,
            )
        except ResponseError:
            logger.exception("reclaim_failed")
            return

        for message_id, fields in messages or []:
            if self._stopping.is_set():
                return
            RECLAIMED.inc()
            logger.warning(
                "job_reclaimed",
                extra={
                    "message_id": _decode(message_id),
                    "idle_ms_threshold": settings.reclaim_min_idle_ms,
                },
            )
            await self._dispatch(_decode(message_id), _decode_fields(fields))

    async def _refresh_depth_metrics(self) -> None:
        """Export queue depth — the HPA/KEDA signal and the demo's headline."""
        try:
            pending = await self._redis.xpending(self._stream, self._group)
            STREAM_PENDING.labels(stream=self._stream, group=self._group).set(
                int(pending.get("pending") or 0) if isinstance(pending, dict) else 0
            )
            STREAM_LENGTH.labels(stream=self._stream).set(
                await self._redis.xlen(self._stream)
            )
        except Exception:
            # Metrics are not worth an exception in the hot loop.
            logger.debug("depth_metrics_unavailable")

    # -- shutdown ----------------------------------------------------------
    async def _drain(self) -> None:
        """Let in-flight jobs finish, then give up on the stragglers.

        Finishing is strongly preferred — the work is nearly done and the model
        tokens are already spent. But the pod has a bounded grace period before
        the kubelet sends SIGKILL, so anything still running at the deadline is
        cancelled and left un-acked for another pod to reclaim. Nothing is lost
        either way; the deadline only decides whether the job finishes here or
        somewhere else.
        """
        if not self._tasks:
            return

        logger.info("draining_jobs", extra={"in_flight": len(self._tasks)})
        pending = list(self._tasks)
        done, still_running = await asyncio.wait(
            pending, timeout=settings.graceful_shutdown_s
        )

        if still_running:
            logger.warning(
                "drain_timeout",
                extra={
                    "abandoned": len(still_running),
                    "note": "left un-acked for reclaim by another worker",
                },
            )
            for task in still_running:
                task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.gather(*still_running, return_exceptions=True)

        logger.info("drain_complete", extra={"finished": len(done)})


# --------------------------------------------------------------------------
# redis-py returns bytes unless decode_responses=True. The client is built with
# decoding on, but these keep the consumer correct either way — including under
# fakeredis in the tests.
# --------------------------------------------------------------------------
def _decode(value) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def _decode_fields(fields: dict) -> dict[str, str]:
    return {_decode(key): _decode(value) for key, value in (fields or {}).items()}


def _parse_timestamp(value: str | None) -> datetime:
    """The producer's ``uploaded_at``, or now if it is absent or unparseable.

    ``queued_at`` is NOT NULL, and a missing timestamp is not worth failing a
    job over.
    """
    if value:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(UTC)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return datetime.now(UTC)
