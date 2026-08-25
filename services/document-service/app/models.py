"""ORM mapping for the repository-owned ``documents`` table.

This intentionally maps the existing shared database schema without changing
it.  ``document_chunks`` (owned by the Search Service) has a foreign key to
``documents.document_id``; therefore this service must create the parent row
before it publishes a processing job.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


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
