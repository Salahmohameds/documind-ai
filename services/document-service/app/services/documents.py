"""Document Service use cases, independent of FastAPI and storage details."""

from __future__ import annotations

from datetime import UTC, datetime
from math import ceil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from redis.exceptions import RedisError

from app.errors import (
    DocumentNotFoundError,
    InvalidDocumentError,
    QueueUnavailableError,
)
from app.models import Document
from app.repositories.documents import DocumentRepository
from app.schemas import (
    BulkFailedItemSchema,
    BulkResultSchema,
    DocErrorSchema,
    DocumentDetailSchema,
    DocumentPageSchema,
    DocumentStatusSchema,
    DocumentSummarySchema,
)
from app.storage.base import DocumentStorage

_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class DocumentService:
    def __init__(self, *, repository: DocumentRepository, storage: DocumentStorage, publisher) -> None:
        self._repository = repository
        self._storage = storage
        self._publisher = publisher

    async def create(self, upload: UploadFile) -> DocumentSummarySchema:
        filename = self._safe_pdf_filename(upload.filename)
        document_id = f"doc_{uuid4().hex}"
        storage_key = f"documents/{document_id}.pdf"
        stored = await self._storage.save_pdf(upload, storage_key, _MAX_UPLOAD_BYTES)
        uploaded_at = datetime.now(UTC)

        try:
            document = self._repository.create(
                document_id=document_id,
                filename=filename,
                document_type="UNKNOWN",
                uploaded_at=uploaded_at,
            )
        except Exception:
            self._storage.delete(storage_key)
            raise

        try:
            self._publisher.publish_document(
                {
                    "event_version": "1",
                    "document_id": document_id,
                    "storage_key": stored.storage_key,
                    "filename": filename,
                    "content_type": "application/pdf",
                    "size_bytes": str(stored.size_bytes),
                    "uploaded_at": uploaded_at.isoformat(),
                }
            )
        except RedisError as exc:
            self._repository.mark_failed(document_id)
            raise QueueUnavailableError(
                "The document was saved but could not be submitted for processing."
            ) from exc

        return self._summary(document)

    def get(self, document_id: str) -> DocumentDetailSchema:
        document = self._get_or_raise(document_id)
        summary = self._summary(document)
        return DocumentDetailSchema(**summary.model_dump())

    def get_status(self, document_id: str) -> DocumentStatusSchema:
        document = self._get_or_raise(document_id)
        status = self._repository.api_status(document.status)
        error = self._queue_error() if status == "failed" else None
        return DocumentStatusSchema(
            id=document.document_id,
            status=status,
            risk=None,
            verdict="Pending",
            progress=None,
            error=error,
        )

    def list(self, *, page: int, page_size: int) -> DocumentPageSchema:
        documents, total = self._repository.list(page=page, page_size=page_size)
        return DocumentPageSchema(
            rows=[self._summary(document) for document in documents],
            total=total,
            unfilteredTotal=total,
            page=page,
            pageSize=page_size,
            pageCount=max(1, ceil(total / page_size)),
        )

    def bulk_delete(self, ids: list[str]) -> BulkResultSchema:
        """Delete documents by IDs.  Non-existent IDs are reported as failed."""
        succeeded: list[str] = []
        failed: list[BulkFailedItemSchema] = []

        for doc_id in ids:
            document = self._repository.get(doc_id)
            if document is None:
                failed.append(
                    BulkFailedItemSchema(
                        id=doc_id, name="unknown", reason="Document not found"
                    )
                )
                continue

            name = document.filename
            storage_key = f"documents/{doc_id}.pdf"
            self._repository.delete(doc_id)
            self._storage.delete(storage_key)
            succeeded.append(doc_id)

        return BulkResultSchema(
            requested=len(ids), succeeded=succeeded, failed=failed
        )

    def bulk_reprocess(self, ids: list[str]) -> BulkResultSchema:
        """Reset documents to *queued* and republish processing jobs.

        Uses the **exact same** Redis event payload as the upload flow so
        downstream consumers (search-service, ai-service) treat reprocessed
        documents identically to freshly uploaded ones.
        """
        succeeded: list[str] = []
        failed: list[BulkFailedItemSchema] = []

        for doc_id in ids:
            document = self._repository.reset_to_queued(doc_id)
            if document is None:
                failed.append(
                    BulkFailedItemSchema(
                        id=doc_id, name="unknown", reason="Document not found"
                    )
                )
                continue

            storage_key = f"documents/{doc_id}.pdf"
            size_bytes = self._storage.size_bytes(storage_key) or 0
            uploaded_at = document.uploaded_at
            if uploaded_at.tzinfo is None:
                uploaded_at = uploaded_at.replace(tzinfo=UTC)

            try:
                self._publisher.publish_document(
                    {
                        "event_version": "1",
                        "document_id": doc_id,
                        "storage_key": storage_key,
                        "filename": document.filename,
                        "content_type": "application/pdf",
                        "size_bytes": str(size_bytes),
                        "uploaded_at": uploaded_at.isoformat(),
                    }
                )
            except RedisError:
                self._repository.mark_failed(doc_id)
                failed.append(
                    BulkFailedItemSchema(
                        id=doc_id,
                        name=document.filename,
                        reason="Failed to enqueue processing job",
                    )
                )
                continue

            succeeded.append(doc_id)

        return BulkResultSchema(
            requested=len(ids), succeeded=succeeded, failed=failed
        )

    def _get_or_raise(self, document_id: str) -> Document:
        document = self._repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError("No document matches this identifier.")
        return document

    def _summary(self, document: Document) -> DocumentSummarySchema:
        storage_key = f"documents/{document.document_id}.pdf"
        size_bytes = self._storage.size_bytes(storage_key) or 0
        uploaded_at = document.uploaded_at
        if uploaded_at.tzinfo is None:
            uploaded_at = uploaded_at.replace(tzinfo=UTC)
        status = self._repository.api_status(document.status)
        error = self._queue_error() if status == "failed" else None
        return DocumentSummarySchema(
            id=document.document_id,
            name=document.filename,
            ext="PDF",
            # UNKNOWN is the existing database default.  The frontend's display
            # mapping is deliberately left unchanged pending team agreement.
            type=document.document_type.title(),
            status=status,
            risk=None,
            pages=0,
            sizeMb=round(size_bytes / (1024 * 1024), 2),
            counterparty="Unassigned counterparty",
            uploaded=uploaded_at.strftime("%b %d, %H:%M").replace(" 0", " "),
            uploadedAt=int(uploaded_at.timestamp() * 1000),
            time="just now",
            flags=0,
            verdict="Pending",
            progress=None,
            error=error,
        )

    @staticmethod
    def _safe_pdf_filename(filename: str | None) -> str:
        if not filename:
            raise InvalidDocumentError("A PDF file is required.")
        safe_name = filename.replace("\\", "/").split("/")[-1].strip()
        if not safe_name or "\x00" in safe_name or Path(safe_name).suffix.lower() != ".pdf":
            raise InvalidDocumentError("Only PDF files are supported.")
        return safe_name[:255]

    @staticmethod
    def _queue_error() -> DocErrorSchema:
        return DocErrorSchema(
            code="ERR_QUEUE_UNAVAILABLE",
            title="Document processing could not be queued",
            detail="Retry this document when the processing queue is available.",
            job="document_jobs",
            at=datetime.now(UTC).isoformat(),
            retryable=True,
        )
