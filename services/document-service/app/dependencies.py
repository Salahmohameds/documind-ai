"""FastAPI dependencies — injected into route handlers."""

from __future__ import annotations

from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.queue.redis_streams import RedisStreamPublisher
from app.repositories.analysis import AnalysisRepository
from app.repositories.documents import DocumentRepository
from app.services.documents import DocumentService
from app.storage.base import DocumentStorage
from app.storage.local import LocalStorage
from app.config import settings


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session, ensuring it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _build_storage() -> DocumentStorage:
    """Select the storage backend named by STORAGE_TYPE.

    "local" (a block volume) only works for a single replica and is not
    reachable by processing-service's pods — fine for local dev, not for
    Kubernetes. "oci_object_storage" is what makes multiple replicas and the
    processing pipeline actually work.
    """
    if settings.storage_type == "local":
        return LocalStorage(settings.storage_dir)

    from app.storage.oci_object_storage import OCIObjectStorage  # noqa: PLC0415

    return OCIObjectStorage(
        bucket_name=settings.oci_bucket_name,
        namespace=settings.oci_namespace,
        region=settings.oci_region,
        auth_mode=settings.oci_auth_mode,
    )


def get_document_service(db: Session = Depends(get_db)) -> DocumentService:
    """Construct the request-scoped Document Service dependencies."""
    return DocumentService(
        repository=DocumentRepository(db),
        analysis=AnalysisRepository(db),
        storage=_build_storage(),
        publisher=RedisStreamPublisher(
            redis_url=settings.redis_url,
            stream_name=settings.redis_stream_name,
        ),
    )
