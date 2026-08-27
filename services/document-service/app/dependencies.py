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
from app.storage.local import LocalStorage
from app.config import settings


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session, ensuring it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_document_service(db: Session = Depends(get_db)) -> DocumentService:
    """Construct the request-scoped Document Service dependencies.

    Only local storage is implemented in M1.  Selecting OCI storage before its
    adapter exists fails explicitly instead of silently writing to local disk.
    """
    if settings.storage_type != "local":
        raise RuntimeError(
            "Unsupported STORAGE_TYPE. M1 supports only local storage."
        )

    return DocumentService(
        repository=DocumentRepository(db),
        analysis=AnalysisRepository(db),
        storage=LocalStorage(settings.storage_dir),
        publisher=RedisStreamPublisher(
            redis_url=settings.redis_url,
            stream_name=settings.redis_stream_name,
        ),
    )
