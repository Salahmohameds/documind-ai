"""The orchestration. One job in, one document processed.

    fetch → extract_text → classify → (extract ‖ summarize ‖ risk) → index → complete

The worker is an *orchestrator*: it decides what happens and in what order, and
delegates every judgement about a document to ai-service and every judgement
about retrieval to search-service. There is no prompt, no model, no scoring rule
and no vector arithmetic in this file, and there should never be.

Two policies are worth reading before the code:

**Failure is graded, not binary.** A document whose text is extracted and
indexed is useful even if the risk model was unreachable — it is searchable,
it answers RAG questions, and the missing assessment can be backfilled. So the
*enrichment* stages (extract, summarize, risk) are allowed to fail
individually: the failure is recorded and counted, and the job continues. The
*spine* stages (fetch, extract_text, index) are not: without them there is no
document to speak of, and the job fails so Redis can retry it.

**Concurrency is where it is free.** Classification must finish first — its
result steers the other three prompts. After that, extract/summarize/risk are
independent calls against the same text and run under one ``gather``, which
turns three sequential model round-trips into one. On the mock backend this is
noise; against a real provider at ~1.8 s per call it is the difference between
a 6-second job and a 2-second one, and under the k6 spike scenario it is the
difference between draining the queue and not.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.clients.ai import AIServiceClient, is_degraded
from app.clients.search import SearchServiceClient
from app.config import settings
from app.database import session_scope
from app.errors import ProcessingError
from app.extraction import pdf
from app.metrics import STAGE_DURATION, STAGE_FAILURES
from app.observability import stage_span
from app.repositories.jobs import JobRepository, to_document_type
from app.storage.base import DocumentReader

logger = logging.getLogger(settings.service_name)


@dataclass
class JobEvent:
    """One message off the stream, validated.

    ``job_id`` is the Redis message id rather than anything the producer chose:
    it is unique, monotonic, and identical across redeliveries of the same
    message, which is exactly the property an idempotency key needs.
    """

    job_id: str
    document_id: str
    storage_key: str
    filename: str
    attempt: int
    user_id: str | None = None
    uploaded_at: str | None = None
    raw: dict[str, str] = field(default_factory=dict)


@dataclass
class PipelineResult:
    degraded: bool = False
    page_count: int = 0
    char_count: int = 0
    chunks_indexed: int = 0
    document_type: str = "UNKNOWN"
    # Stages that failed without failing the job — surfaced in the completion
    # log so "completed" is never quietly hiding three dead calls.
    skipped_stages: list[str] = field(default_factory=list)


class ProcessingPipeline:
    def __init__(
        self,
        *,
        reader: DocumentReader,
        ai_client: AIServiceClient,
        search_client: SearchServiceClient,
    ) -> None:
        self._reader = reader
        self._ai = ai_client
        self._search = search_client

    async def run(self, event: JobEvent) -> PipelineResult:
        """Process one document. Raises ProcessingError on a spine failure."""
        result = PipelineResult()

        # --- fetch (spine) ------------------------------------------------
        with _stage("fetch"):
            self._set_stage(event.job_id, "fetch")
            # Blocking I/O — both storage backends are sync SDKs. Off-loaded to
            # a thread so a 25 MB read does not stall the other jobs sharing
            # this pod's event loop.
            data = await asyncio.to_thread(
                self._reader.read, event.storage_key, settings.max_document_bytes
            )

        # --- extract_text (spine) -----------------------------------------
        with _stage("extract_text"):
            self._set_stage(event.job_id, "extract_text")
            # CPU-bound pypdf parse — same reasoning as above.
            document = await asyncio.to_thread(pdf.extract, data)
            result.page_count = document.page_count
            result.char_count = document.char_count

        logger.info(
            "text_extracted",
            extra={
                "pages": document.page_count,
                "chars": document.char_count,
                "encrypted": document.encrypted,
            },
        )

        # --- classify (enrichment, but ordered first) ----------------------
        label = await self._classify(event, document.text, result)
        result.document_type = to_document_type(label)

        # --- extract ‖ summarize ‖ risk (enrichment, concurrent) ----------
        await asyncio.gather(
            self._extract_fields(event, document.text, label, result),
            self._summarize(event, document.text, label, result),
            self._assess_risk(event, document.text, label, result),
        )

        # --- index (spine) -------------------------------------------------
        with _stage("index"):
            self._set_stage(event.job_id, "index")
            response = await self._search.index(
                document_id=event.document_id,
                pages=document.pages,
                text=document.text,
            )
            result.chunks_indexed = int(response.get("chunks_indexed") or 0)

        logger.info("document_indexed", extra={"chunks": result.chunks_indexed})
        return result

    # -- enrichment stages -------------------------------------------------
    # Each returns quietly on failure; `_enrichment` records and counts it.

    async def _classify(
        self, event: JobEvent, text: str, result: PipelineResult
    ) -> str | None:
        response = await self._enrichment(
            "classify",
            event,
            result,
            lambda: self._ai.classify(text=text, document_id=event.document_id),
        )
        if response is None:
            return None

        label = response.get("label")
        with session_scope() as session:
            JobRepository(session).set_document_type(event.document_id, label)

        logger.info(
            "document_classified",
            extra={"label": label, "confidence": response.get("confidence")},
        )
        return label

    async def _extract_fields(
        self, event: JobEvent, text: str, label: str | None, result: PipelineResult
    ) -> None:
        response = await self._enrichment(
            "extract",
            event,
            result,
            lambda: self._ai.extract(
                text=text, document_id=event.document_id, document_type=label
            ),
        )
        if response is None:
            return

        fields = response.get("fields") or {}
        with session_scope() as session:
            JobRepository(session).save_extracted_fields(event.document_id, fields)
        logger.info("fields_extracted", extra={"field_count": len(fields)})

    async def _summarize(
        self, event: JobEvent, text: str, label: str | None, result: PipelineResult
    ) -> None:
        response = await self._enrichment(
            "summarize",
            event,
            result,
            lambda: self._ai.summarize(
                text=text, document_id=event.document_id, document_type=label
            ),
        )
        if response is None:
            return

        # ai-service reports insufficient_text when the document was too short
        # to summarise honestly. Storing its apology as a summary would be
        # worse than storing nothing.
        if response.get("insufficient_text"):
            logger.info("summary_skipped", extra={"reason": "insufficient_text"})
            result.skipped_stages.append("summarize")
            return

        summary = (response.get("summary") or "").strip()
        if not summary:
            result.skipped_stages.append("summarize")
            return

        with session_scope() as session:
            JobRepository(session).save_summary(
                event.document_id,
                summary=summary,
                key_points=response.get("key_points"),
                style=response.get("style"),
            )
        logger.info("document_summarized", extra={"chars": len(summary)})

    async def _assess_risk(
        self, event: JobEvent, text: str, label: str | None, result: PipelineResult
    ) -> None:
        response = await self._enrichment(
            "risk",
            event,
            result,
            lambda: self._ai.analyse_risk(
                text=text, document_id=event.document_id, document_type=label
            ),
        )
        if response is None:
            return

        with session_scope() as session:
            JobRepository(session).save_risk_assessment(
                event.document_id,
                score=response.get("score"),
                categories=response.get("categories"),
                findings=response.get("findings"),
            )
        logger.info(
            "risk_assessed",
            extra={"score": response.get("score"), "band": response.get("band")},
        )

    # -- shared enrichment wrapper ----------------------------------------
    async def _enrichment(
        self,
        stage: str,
        event: JobEvent,
        result: PipelineResult,
        call,
    ) -> dict[str, Any] | None:
        """Run one enrichment stage, absorbing its failure.

        Returns the response, or None if the stage failed. The job continues
        either way — see the module docstring on graded failure.
        """
        self._set_stage(event.job_id, stage)
        started = time.monotonic()
        with stage_span(stage) as span:
            try:
                response = await call()
            except ProcessingError as exc:
                STAGE_FAILURES.labels(stage=stage, error_code=exc.code).inc()
                result.skipped_stages.append(stage)
                # Recorded on the span but NOT set as a span error: the stage
                # failed, the job did not. A trace that shows this as a failure
                # would misreport a document that came out searchable.
                span.set_attribute("documind.error_code", exc.code)
                span.set_attribute("documind.absorbed_failure", True)
                logger.warning(
                    "stage_failed",
                    extra={
                        "stage": stage,
                        "error_code": exc.code,
                        "error": str(exc),
                        "job_failed": False,
                    },
                )
                return None
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                STAGE_FAILURES.labels(stage=stage, error_code="ERR_UNEXPECTED").inc()
                result.skipped_stages.append(stage)
                span.set_attribute("documind.absorbed_failure", True)
                logger.exception(
                    "stage_failed",
                    extra={"stage": stage, "error": str(exc), "job_failed": False},
                )
                return None
            finally:
                STAGE_DURATION.labels(stage=stage).observe(time.monotonic() - started)

        if is_degraded(response):
            result.degraded = True
        return response

    @staticmethod
    def _set_stage(job_id: str, stage: str) -> None:
        """Best-effort progress marker.

        A failure to write the marker must never fail the job — it exists to
        make a stuck job diagnosable, not to gate the work.
        """
        try:
            with session_scope() as session:
                JobRepository(session).mark_stage(job_id, stage)
        except Exception:
            logger.warning("stage_marker_write_failed", extra={"stage": stage})


class _stage:
    """Time a spine stage, record it, and open its trace span.

    One construct for all three so a stage cannot be added that is timed but
    not traced — the drift that makes a dashboard and a trace tell different
    stories about the same run.
    """

    def __init__(self, name: str) -> None:
        self._name = name

    def __enter__(self) -> _stage:
        self._started = time.monotonic()
        self._span_cm = stage_span(self._name)
        self._span = self._span_cm.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        STAGE_DURATION.labels(stage=self._name).observe(
            time.monotonic() - self._started
        )
        if exc_type is not None and issubclass(exc_type, ProcessingError):
            STAGE_FAILURES.labels(stage=self._name, error_code=exc.code).inc()
            self._span.set_attribute("documind.error_code", exc.code)
        # Hand the exception to the span so it is recorded and the span status
        # is set to error, then let it propagate.
        self._span_cm.__exit__(exc_type, exc, tb)
        return False
