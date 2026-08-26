"""Document service proxy routes.

Confirmed contract endpoints:
- ``POST /documents``
- ``GET  /documents``
- ``GET  /documents/{document_id}``
- ``GET  /documents/{document_id}/status``

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
