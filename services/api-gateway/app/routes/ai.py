"""AI service proxy routes and /qa orchestration.

Proxy endpoints (all JWT-protected, forwarded to AI_SERVICE_URL):
- ``POST /embed``
- ``POST /classify``
- ``POST /extract``
- ``POST /analysis/risk``
- ``POST /summarize``
- ``POST /pii``
- ``POST /answer``

Orchestration endpoint:
- ``POST /qa`` — chains Search /query → AI /answer at the Gateway level,
  so there is no Search → AI dependency.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from app.auth.dependencies import AuthenticatedUser, require_jwt
from app.config import settings
from app.proxy import get_client, proxy_request

logger = logging.getLogger(settings.service_name)

router = APIRouter(tags=["ai"])


# ── Simple proxy routes ─────────────────────────────────────────────────
# These follow the exact same pattern as search.py and documents.py:
# JWT-protected, forwarded verbatim via proxy_request().


@router.post("/embed")
async def proxy_embed(
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Forward ``POST /embed`` to the AI service."""
    return await proxy_request(
        request=request,
        target_base_url=settings.ai_service_url,
        target_path="/embed",
        user=user,
    )


@router.post("/classify")
async def proxy_classify(
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Forward ``POST /classify`` to the AI service."""
    return await proxy_request(
        request=request,
        target_base_url=settings.ai_service_url,
        target_path="/classify",
        user=user,
    )


@router.post("/extract")
async def proxy_extract(
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Forward ``POST /extract`` to the AI service."""
    return await proxy_request(
        request=request,
        target_base_url=settings.ai_service_url,
        target_path="/extract",
        user=user,
    )


@router.post("/analysis/risk")
async def proxy_analysis_risk(
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Forward ``POST /analysis/risk`` to the AI service."""
    return await proxy_request(
        request=request,
        target_base_url=settings.ai_service_url,
        target_path="/analysis/risk",
        user=user,
    )


@router.post("/summarize")
async def proxy_summarize(
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Forward ``POST /summarize`` to the AI service."""
    return await proxy_request(
        request=request,
        target_base_url=settings.ai_service_url,
        target_path="/summarize",
        user=user,
    )


@router.post("/pii")
async def proxy_pii(
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Forward ``POST /pii`` to the AI service."""
    return await proxy_request(
        request=request,
        target_base_url=settings.ai_service_url,
        target_path="/pii",
        user=user,
    )


@router.post("/answer")
async def proxy_answer(
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Forward ``POST /answer`` to the AI service."""
    return await proxy_request(
        request=request,
        target_base_url=settings.ai_service_url,
        target_path="/answer",
        user=user,
    )


# ── POST /qa — orchestration ────────────────────────────────────────────
# This is NOT a simple proxy.  The Gateway orchestrates:
#   Client → Gateway /qa → Search /query → AI /answer → Client
# so there is no Search → AI dependency.


class QARequest(BaseModel):
    """Request body for the ``/qa`` orchestration endpoint."""

    question: str


@router.post("/qa")
async def qa_orchestration(
    body: QARequest,
    request: Request,
    user: AuthenticatedUser = Depends(require_jwt),
):
    """Orchestrate a question-answering flow across Search and AI services.

    1. Call Search ``/query`` with the question to retrieve relevant chunks.
    2. Map the search results to the AI ``/answer`` contract.
    3. Call AI ``/answer`` with the question and chunks.
    4. Return the AI response to the client.
    """
    client = get_client()

    # ── Headers injected for downstream services ────────────────────────
    downstream_headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-User-Email": user.email,
        "X-User-Role": user.role,
    }

    # Propagate request ID if present.
    request_id = request.headers.get("X-Request-ID")
    if request_id:
        downstream_headers["X-Request-ID"] = request_id

    # ── Step 1: Call Search Service /query ───────────────────────────────
    search_url = f"{settings.search_service_url.rstrip('/')}/query"

    try:
        search_response = await client.post(
            search_url,
            json={"question": body.question},
            headers=downstream_headers,
        )
    except httpx.TimeoutException:
        logger.error("qa_search_timeout", extra={"target_url": search_url})
        return JSONResponse(
            status_code=504,
            content={
                "error": "Gateway Timeout",
                "detail": "Search service did not respond in time.",
                "code": "ERR_PROXY_TIMEOUT",
            },
        )
    except httpx.HTTPError as exc:
        logger.error(
            "qa_search_error",
            extra={"target_url": search_url, "error": str(exc)},
        )
        return JSONResponse(
            status_code=502,
            content={
                "error": "Bad Gateway",
                "detail": "Search service did not respond.",
                "code": "ERR_PROXY",
            },
        )

    if search_response.status_code != 200:
        logger.error(
            "qa_search_failed",
            extra={
                "target_url": search_url,
                "status_code": search_response.status_code,
            },
        )
        return JSONResponse(
            status_code=502,
            content={
                "error": "Bad Gateway",
                "detail": "Search service returned an error.",
                "code": "ERR_SEARCH_FAILED",
            },
        )

    # ── Step 2: Parse search results and map to AI /answer contract ─────
    # Search Service QueryResponse: { "question": "...", "results": [...] }
    # Each SearchResultItem: { chunk_id, document_id, text, page, similarity }
    #
    # AI /answer expects: { "question": "...", "chunks": [...] }
    # Each chunk: { chunk_id, document_id, text, page, score }
    #
    # Mapping: "results" → "chunks", "similarity" → "score".
    search_data = search_response.json()

    # Support both "results" (actual search-service contract) and "chunks"
    # (in case a future search-service version uses that name).
    raw_chunks = search_data.get("results") or search_data.get("chunks") or []

    chunks = []
    for item in raw_chunks:
        chunk = {
            "chunk_id": item.get("chunk_id"),
            "document_id": item.get("document_id"),
            "text": item.get("text"),
            "page": item.get("page"),
            # Map "similarity" → "score" for AI contract compatibility.
            "score": item.get("score") or item.get("similarity"),
        }
        chunks.append(chunk)

    # ── Step 3: Call AI Service /answer ──────────────────────────────────
    ai_url = f"{settings.ai_service_url.rstrip('/')}/answer"

    try:
        ai_response = await client.post(
            ai_url,
            json={"question": body.question, "chunks": chunks},
            headers=downstream_headers,
        )
    except httpx.TimeoutException:
        logger.error("qa_ai_timeout", extra={"target_url": ai_url})
        return JSONResponse(
            status_code=504,
            content={
                "error": "Gateway Timeout",
                "detail": "AI service did not respond in time.",
                "code": "ERR_PROXY_TIMEOUT",
            },
        )
    except httpx.HTTPError as exc:
        logger.error(
            "qa_ai_error",
            extra={"target_url": ai_url, "error": str(exc)},
        )
        return JSONResponse(
            status_code=502,
            content={
                "error": "Bad Gateway",
                "detail": "AI service did not respond.",
                "code": "ERR_PROXY",
            },
        )

    # ── Step 4: Return the AI response ──────────────────────────────────
    return Response(
        content=ai_response.content,
        status_code=ai_response.status_code,
        media_type="application/json",
    )
