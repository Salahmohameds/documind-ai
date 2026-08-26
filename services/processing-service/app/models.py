"""ORM mapping for the tables this worker reads and writes.

``documents`` is owned by document-service and mapped here read-mostly: the
worker only ever touches ``status``, ``document_type`` and ``indexed_at``. The
column set is kept identical to
``services/document-service/app/models.py`` so the two services cannot drift
into disagreeing about the same table.

``processing_jobs`` and ``document_summaries`` are added by
``database/migrations/002_processing_jobs.sql`` and owned here.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# SQLite (used by the test suite) has no JSONB. This keeps one model definition
# working against both without a second schema.
JSONType = JSONB().with_variant(JSON(), "sqlite")


class Document(Base):
    """The shared document row. Owned by document-service."""

    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(String, primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    # CHECK (document_type IN ('INVOICE','CONTRACT','UNKNOWN')) — uppercase.
    # ai-service returns lowercase; see repositories/jobs.py for the mapping.
    document_type: Mapped[str] = mapped_column(String, nullable=False)
    # CHECK (status IN ('UPLOADED','PROCESSING','INDEXED','FAILED'))
    status: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ProcessingJob(Base):
    """One attempt-tracked unit of async work. Keyed by the Redis message id."""

    __tablename__ = "processing_jobs"

    job_id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    consumer_name: Mapped[str | None] = mapped_column(String, nullable=True)
    stage: Mapped[str | None] = mapped_column(String, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    degraded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ExtractedFields(Base):
    """Output of ai-service /extract."""

    __tablename__ = "extracted_fields"

    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.document_id", ondelete="CASCADE"), primary_key=True
    )
    fields: Mapped[dict] = mapped_column(JSONType, nullable=False)
    extracted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class RiskAssessment(Base):
    """Output of ai-service /analysis/risk.

    The three band columns are CHECK-constrained to 'Low'|'Medium'|'High' —
    title case — while the ai-service contract uses lowercase. The mapping is
    in repositories/jobs.py and is not optional.
    """

    __tablename__ = "risk_assessments"

    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.document_id", ondelete="CASCADE"), primary_key=True
    )
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    financial_risk: Mapped[str | None] = mapped_column(String, nullable=True)
    legal_risk: Mapped[str | None] = mapped_column(String, nullable=True)
    operational_risk: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_reasons: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    assessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class DocumentSummary(Base):
    """Output of ai-service /summarize."""

    __tablename__ = "document_summaries"

    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.document_id", ondelete="CASCADE"), primary_key=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    style: Mapped[str | None] = mapped_column(String, nullable=True)
    summarized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
