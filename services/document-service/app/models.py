"""ORM mapping for the repository-owned ``documents`` table.

This intentionally maps the existing shared database schema without changing
it.  ``document_chunks`` (owned by the Search Service) has a foreign key to
``documents.document_id``; therefore this service must create the parent row
before it publishes a processing job.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Postgres holds these columns as JSONB; the tests run against SQLite, which has
# no such type. Reading is identical either way -- this service only ever
# selects from the analysis tables -- so the variant keeps the models portable
# without pretending the production column is anything other than JSONB.
_Json = JSON().with_variant(JSONB(), "postgresql")


class Document(Base):
    """Persistent representation of an uploaded document."""

    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(String, primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    document_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<Document id={self.document_id!r} "
            f"name={self.filename!r} status={self.status!r}>"
        )


class ExtractedFields(Base):
    """Structured fields written by processing-service's ``extract`` stage.

    Read-only here: this service owns the ``documents`` row, not the analysis.
    ``fields`` is the raw ai-service payload, keyed by field name — see
    ``app/repositories/analysis.py`` for the shape.
    """

    __tablename__ = "extracted_fields"

    document_id: Mapped[str] = mapped_column(String, primary_key=True)
    fields: Mapped[dict] = mapped_column(_Json, nullable=False)


class RiskAssessment(Base):
    """Risk score, per-category bands and the rules that fired.

    ``risk_reasons`` holds the findings list. Per-category risk is stored as
    Low/Medium/High rather than a number because ai-service derives it from
    which rules fired, not from a model — there is no finer-grained truth to
    read.
    """

    __tablename__ = "risk_assessments"

    document_id: Mapped[str] = mapped_column(String, primary_key=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    financial_risk: Mapped[str | None] = mapped_column(String, nullable=True)
    legal_risk: Mapped[str | None] = mapped_column(String, nullable=True)
    operational_risk: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_reasons: Mapped[list | None] = mapped_column(_Json, nullable=True)


class DocumentSummary(Base):
    """Narrative summary and key points from the ``summarize`` stage."""

    __tablename__ = "document_summaries"

    document_id: Mapped[str] = mapped_column(String, primary_key=True)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    key_points: Mapped[list | None] = mapped_column(_Json, nullable=True)
