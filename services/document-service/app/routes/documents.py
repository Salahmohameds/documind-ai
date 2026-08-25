"""HTTP adapter for the Document Service M1 use cases."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import JSONResponse

from app.dependencies import get_document_service
from app.errors import DocumentServiceError
from app.schemas import (
    DocumentDetailSchema,
    DocumentPageSchema,
    DocumentStatusSchema,
    DocumentSummarySchema,
)
from app.services.documents import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


def _error_response(error: DocumentServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": error.title,
            "detail": error.detail,
            "code": error.code,
            "retryable": error.retryable,
        },
    )


@router.post("", response_model=DocumentSummarySchema, status_code=202)
async def create_document(
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
):
    try:
        return await service.create(file)
    except DocumentServiceError as error:
        return _error_response(error)


@router.get("", response_model=DocumentPageSchema)
def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    service: DocumentService = Depends(get_document_service),
):
    return service.list(page=page, page_size=page_size)


@router.get("/{document_id}/status", response_model=DocumentStatusSchema)
def get_document_status(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
):
    try:
        return service.get_status(document_id)
    except DocumentServiceError as error:
        return _error_response(error)


@router.get("/{document_id}", response_model=DocumentDetailSchema)
def get_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
):
    try:
        return service.get(document_id)
    except DocumentServiceError as error:
        return _error_response(error)
