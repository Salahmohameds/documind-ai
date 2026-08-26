"""Every database write the worker makes.

Two mappings live here and nowhere else, because getting either wrong is a
constraint violation at runtime rather than a type error at build time:

1. **Document lifecycle.** ``documents.status`` is CHECK-constrained to
   ``UPLOADED|PROCESSING|INDEXED|FAILED``. document-service already maps its
   own vocabulary onto those values
   (``services/document-service/app/repositories/documents.py``), and the
   frontend reads the result through that service. So the worker writes the
   same uppercase values — the richer ``QUEUED→PROCESSING→COMPLETED|FAILED``
   lifecycle the async pipeline actually has is recorded in ``processing_jobs``
   instead, where it can carry an attempt count, an error and a duration.

2. **ai-service casing.** The AI contract is lowercase throughout
   (``invoice``, ``low``); the database CHECKs are not
   (``INVOICE``, ``Low``). Every value crossing that boundary is normalised
   here.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Document,
    DocumentSummary,
    ExtractedFields,
    ProcessingJob,
    RiskAssessment,
)

logger = logging.getLogger(settings.service_name)

# Job lifecycle (processing_jobs.status) -> document lifecycle (documents.status)
_DOCUMENT_STATUS = {
    "QUEUED": "UPLOADED",
    "PROCESSING": "PROCESSING",
    "COMPLETED": "INDEXED",
    "FAILED": "FAILED",
}

_DOCUMENT_TYPES = {"invoice": "INVOICE", "contract": "CONTRACT", "unknown": "UNKNOWN"}
_RISK_BANDS = {"low": "Low", "medium": "Medium", "high": "High"}

# error_message is TEXT, but a provider stack trace in a status field helps
# nobody and bloats every row the frontend reads.
_MAX_ERROR_CHARS = 1000


def to_document_type(label: str | None) -> str:
    """'invoice' -> 'INVOICE'. Anything unrecognised is UNKNOWN, not an error.

    An unexpected label is a classifier problem, not a reason to fail a job
    that has perfectly good text — and the CHECK constraint would reject it.
    """
    return _DOCUMENT_TYPES.get((label or "").strip().lower(), "UNKNOWN")


def to_risk_band(band: str | None) -> str | None:
    """'high' -> 'High'. None when absent, which the column allows."""
    if band is None:
        return None
    return _RISK_BANDS.get(band.strip().lower())


class JobRepository:
    """Persistence for one job. Each method is its own transaction."""

    def __init__(self, session: Session) -> None:
        self._db = session

    # -- claim -------------------------------------------------------------
    def claim(
        self,
        *,
        job_id: str,
        document_id: str,
        user_id: str | None,
        delivered: int,
        consumer_name: str,
        queued_at: datetime,
    ) -> int | None:
        """Take ownership of a job. Returns its attempt number, or None if done.

        An ``int`` rather than the ORM row on purpose: ``session_scope`` closes
        the session on the way out, and every attribute of a returned row would
        then raise ``DetachedInstanceError`` at the call site.

        The idempotency gate. ``job_id`` is the Redis message id, so a
        redelivered message lands on the same primary key. If that row is
        already ``COMPLETED`` the caller acks and runs nothing: replaying the
        pipeline would re-index the document, overwrite its risk assessment and
        burn model tokens to reach the state it is already in.

        A previously ``FAILED`` row is *not* a stop: a failure that was
        transient deserves the retry Redis is offering.

        The attempt count is the **larger** of Redis' delivery counter and one
        past what this row already recorded. Two independent sources because
        each covers the other's gap: the Redis counter survives a pod being
        OOM-killed mid-job (where no code of ours runs to increment anything),
        and the row survives a Redis failover or a broker whose counter is
        unavailable. Taking the max means neither a lost pod nor a lost counter
        can hand a poison message an unbounded retry budget.
        """
        existing = self._db.get(ProcessingJob, job_id, with_for_update=False)

        if existing is not None and existing.status == "COMPLETED":
            return None

        if existing is None:
            attempt = max(1, delivered)
            existing = ProcessingJob(
                job_id=job_id,
                document_id=document_id,
                user_id=user_id,
                queued_at=queued_at,
            )
            self._db.add(existing)
        else:
            attempt = max(delivered, (existing.attempt or 0) + 1)

        existing.status = "PROCESSING"
        existing.attempt = attempt
        existing.consumer_name = consumer_name
        existing.started_at = datetime.now(UTC)
        existing.stage = "claim"
        # Clear the previous attempt's failure so a stale error cannot be read
        # as the current one.
        existing.error_code = None
        existing.error_message = None
        existing.degraded = False

        self._set_document_status(document_id, "PROCESSING")
        self._db.commit()
        return attempt

    def mark_stage(self, job_id: str, stage: str) -> None:
        """Record the stage in progress, so a stuck job is diagnosable."""
        job = self._db.get(ProcessingJob, job_id)
        if job is None:
            return
        job.stage = stage
        self._db.commit()

    # -- terminal states ---------------------------------------------------
    def mark_completed(self, *, job_id: str, degraded: bool) -> None:
        job = self._db.get(ProcessingJob, job_id)
        if job is None:
            return
        finished = datetime.now(UTC)
        job.status = "COMPLETED"
        job.stage = "complete"
        job.degraded = degraded
        job.finished_at = finished
        job.duration_ms = _elapsed_ms(job.started_at, finished)

        document = self._db.get(Document, job.document_id)
        if document is not None:
            document.status = _DOCUMENT_STATUS["COMPLETED"]
            document.indexed_at = finished
        self._db.commit()

    def mark_failed(
        self, *, job_id: str, error_code: str, error_message: str, stage: str | None
    ) -> None:
        job = self._db.get(ProcessingJob, job_id)
        if job is None:
            return
        finished = datetime.now(UTC)
        job.status = "FAILED"
        job.error_code = error_code
        job.error_message = error_message[:_MAX_ERROR_CHARS]
        if stage:
            job.stage = stage
        job.finished_at = finished
        job.duration_ms = _elapsed_ms(job.started_at, finished)

        self._set_document_status(job.document_id, "FAILED")
        self._db.commit()

    def requeue(self, *, job_id: str, error_code: str, error_message: str) -> None:
        """Record a transient failure without declaring the job dead.

        The message stays un-acked in Redis for another worker to reclaim, so
        the job returns to QUEUED and the *document* goes back to UPLOADED
        rather than FAILED — the frontend should show "still working", not a
        red state that will silently turn green again.
        """
        job = self._db.get(ProcessingJob, job_id)
        if job is None:
            return
        job.status = "QUEUED"
        job.error_code = error_code
        job.error_message = error_message[:_MAX_ERROR_CHARS]
        job.finished_at = None
        job.duration_ms = None

        self._set_document_status(job.document_id, "QUEUED")
        self._db.commit()

    # -- pipeline results --------------------------------------------------
    def set_document_type(self, document_id: str, label: str | None) -> None:
        document = self._db.get(Document, document_id)
        if document is None:
            return
        document.document_type = to_document_type(label)
        self._db.commit()

    def save_extracted_fields(self, document_id: str, fields: dict[str, Any]) -> None:
        """Upsert. A reprocessed document replaces its fields, never duplicates."""
        row = self._db.get(ExtractedFields, document_id)
        if row is None:
            row = ExtractedFields(document_id=document_id, fields=fields)
            self._db.add(row)
        else:
            row.fields = fields
        row.extracted_at = datetime.now(UTC)
        self._db.commit()

    def save_summary(
        self,
        document_id: str,
        *,
        summary: str,
        key_points: list[str] | None,
        style: str | None,
    ) -> None:
        row = self._db.get(DocumentSummary, document_id)
        if row is None:
            row = DocumentSummary(document_id=document_id, summary=summary)
            self._db.add(row)
        else:
            row.summary = summary
        row.key_points = key_points
        row.style = style
        row.summarized_at = datetime.now(UTC)
        self._db.commit()

    def save_risk_assessment(
        self,
        document_id: str,
        *,
        score: int | None,
        categories: dict[str, str] | None,
        findings: Any,
    ) -> None:
        categories = categories or {}
        row = self._db.get(RiskAssessment, document_id)
        if row is None:
            row = RiskAssessment(document_id=document_id)
            self._db.add(row)
        row.risk_score = score
        row.financial_risk = to_risk_band(categories.get("financial"))
        row.legal_risk = to_risk_band(categories.get("legal"))
        row.operational_risk = to_risk_band(categories.get("operational"))
        row.risk_reasons = findings
        row.assessed_at = datetime.now(UTC)
        self._db.commit()

    # -- reads -------------------------------------------------------------
    def document_exists(self, document_id: str) -> bool:
        return (
            self._db.scalar(
                select(Document.document_id).where(Document.document_id == document_id)
            )
            is not None
        )

    # -- internals ---------------------------------------------------------
    def _set_document_status(self, document_id: str, job_status: str) -> None:
        document = self._db.get(Document, document_id)
        if document is None:
            # document-service creates the row before it publishes, so this
            # means the document was deleted mid-flight. Not worth failing a
            # job over; the FK would have stopped us anyway.
            logger.warning("document_row_missing", extra={"document_id": document_id})
            return
        document.status = _DOCUMENT_STATUS[job_status]


def _elapsed_ms(started: datetime | None, finished: datetime) -> int | None:
    if started is None:
        return None
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    return int((finished - started).total_seconds() * 1000)
