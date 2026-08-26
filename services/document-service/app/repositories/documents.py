"""Persistence operations for Document Service-owned metadata."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Document


class DocumentRepository:
    """Maps application lifecycle values to the existing shared schema."""

    # These mappings avoid changing the shared schema during M1.  They must be
    # revisited with the Data/Search owner before a shared migration changes
    # the database's uppercase lifecycle constraint.
    _TO_DATABASE_STATUS = {
        "queued": "UPLOADED",
        "processing": "PROCESSING",
        "completed": "INDEXED",
        "failed": "FAILED",
    }
    _FROM_DATABASE_STATUS = {
        value: key for key, value in _TO_DATABASE_STATUS.items()
    }

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        document_id: str,
        filename: str,
        document_type: str,
        uploaded_at: datetime,
    ) -> Document:
        document = Document(
            document_id=document_id,
            filename=filename,
            document_type=document_type,
            status=self._TO_DATABASE_STATUS["queued"],
            uploaded_at=uploaded_at,
        )
        self._db.add(document)
        self._db.commit()
        self._db.refresh(document)
        return document

    def get(self, document_id: str) -> Document | None:
        return self._db.get(Document, document_id)

    def list(self, *, page: int, page_size: int) -> tuple[list[Document], int]:
        total = int(self._db.scalar(select(func.count()).select_from(Document)) or 0)
        statement = (
            select(Document)
            .order_by(Document.uploaded_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self._db.scalars(statement)), total

    def mark_failed(self, document_id: str) -> None:
        document = self.get(document_id)
        if document is None:
            return
        document.status = self._TO_DATABASE_STATUS["failed"]
        self._db.commit()

    def delete(self, document_id: str) -> bool:
        """Delete a document by ID.  Returns ``True`` if the row existed."""
        document = self.get(document_id)
        if document is None:
            return False
        self._db.delete(document)
        self._db.commit()
        return True

    def reset_to_queued(self, document_id: str) -> Document | None:
        """Reset a document's status to *queued* for reprocessing.

        Clears ``indexed_at`` so downstream consumers treat this as a fresh
        job.  Returns the updated ``Document``, or ``None`` if not found.
        """
        document = self.get(document_id)
        if document is None:
            return None
        document.status = self._TO_DATABASE_STATUS["queued"]
        document.indexed_at = None
        self._db.commit()
        self._db.refresh(document)
        return document

    @classmethod
    def api_status(cls, database_status: str) -> str:
        return cls._FROM_DATABASE_STATUS.get(database_status, "failed")
