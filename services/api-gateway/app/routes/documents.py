"""Document service proxy routes.

Confirmed contract endpoints:
- ``POST   /documents``
- ``GET    /documents``
- ``DELETE /documents``
- ``POST   /documents/reprocess``
- ``GET    /documents/{document_id}``
- ``GET    /documents/{document_id}/status``

All protected by JWT authentication.  The request is forwarded to the
document-service with ``X-User-Email`` and ``X-User-Role`` injected.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import AuthenticatedUser, require_jwt
from app.config import settings
from app.proxy import proxy_request

router = APIRouter(tags=["documents"])


@router.post("/documents")
async def proxy_create_document(
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Forward ``POST /documents`` to the document service."""
    return await proxy_request(
        request=request,
        target_base_url=settings.document_service_url,
        target_path="/documents",
        user=user,
    )


@router.get("/documents")
async def proxy_list_documents(
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Forward ``GET /documents`` to the document service."""
    return await proxy_request(
        request=request,
        target_base_url=settings.document_service_url,
        target_path="/documents",
        user=user,
    )


@router.delete("/documents")
async def proxy_delete_documents(
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Forward ``DELETE /documents`` to the document service.

    Bulk, collection-level and body-carrying: the ``{"ids": [...]}`` payload is
    relayed verbatim by ``proxy_request``, which forwards a body on any method.
    Per-id outcomes come back inside a 200 ``BulkResult`` — a document that
    could not be deleted is reported in ``failed[]``, not as an error status.
    """
    return await proxy_request(
        request=request,
        target_base_url=settings.document_service_url,
        target_path="/documents",
        user=user,
    )


# Declared ahead of ``/documents/{document_id}`` so the literal ``reprocess``
# path is never a candidate for the parameterised route.
@router.post("/documents/reprocess")
async def proxy_reprocess_documents(
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Forward ``POST /documents/reprocess`` to the document service.

    Same bulk contract as delete: ``{"ids": [...]}`` in, a 200 ``BulkResult``
    out.  document-service resets each document to *queued* and republishes the
    processing job using the identical Redis payload the upload flow emits.
    """
    return await proxy_request(
        request=request,
        target_base_url=settings.document_service_url,
        target_path="/documents/reprocess",
        user=user,
    )


@router.get("/documents/{document_id}")
async def proxy_get_document(
    document_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Forward ``GET /documents/{document_id}`` to the document service."""
    return await proxy_request(
        request=request,
        target_base_url=settings.document_service_url,
        target_path=f"/documents/{document_id}",
        user=user,
    )


@router.get("/documents/{document_id}/status")
async def proxy_get_document_status(
    document_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Forward ``GET /documents/{document_id}/status`` to the document service."""
    return await proxy_request(
        request=request,
        target_base_url=settings.document_service_url,
        target_path=f"/documents/{document_id}/status",
        user=user,
    )
