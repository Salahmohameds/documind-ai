"""Search service proxy routes.

M2 confirmed endpoints:
- ``POST /index``
- ``POST /query``
- ``GET  /search``

All protected by JWT authentication.  The request is forwarded to the
search-service with ``X-User-Email`` and ``X-User-Role`` injected.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import AuthenticatedUser, require_jwt
from app.config import settings
from app.proxy import proxy_request

router = APIRouter(tags=["search"])


@router.post("/index")
async def proxy_index(
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Forward ``POST /index`` to the search service."""
    return await proxy_request(
        request=request,
        target_base_url=settings.search_service_url,
        target_path="/index",
        user=user,
    )


@router.post("/query")
async def proxy_query(
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Forward ``POST /query`` to the search service."""
    return await proxy_request(
        request=request,
        target_base_url=settings.search_service_url,
        target_path="/query",
        user=user,
    )


@router.get("/search")
async def proxy_search(
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Forward ``GET /search`` to the search service."""
    return await proxy_request(
        request=request,
        target_base_url=settings.search_service_url,
        target_path="/search",
        user=user,
    )
