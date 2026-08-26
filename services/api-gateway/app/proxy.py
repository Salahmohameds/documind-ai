"""Async reverse proxy helper.

Forwards requests from the API Gateway to downstream services using
``httpx.AsyncClient``.  Injects ``X-User-Email`` and ``X-User-Role``
headers, strips the original ``Authorization`` header, and returns the
downstream response verbatim (status code, body, selected headers).
"""

from __future__ import annotations

import logging

import httpx
from fastapi import Request
from fastapi.responses import Response

from app.auth.dependencies import AuthenticatedUser
from app.config import settings

logger = logging.getLogger(settings.service_name)

# Persistent async client — connection pooling across requests.
# Created once, closed on application shutdown (see main.py lifespan).
http_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """Return the module-level ``httpx.AsyncClient``, creating it lazily."""
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=30.0)
    return http_client


async def close_client() -> None:
    """Close the shared HTTP client (called during app shutdown)."""
    global http_client
    if http_client is not None:
        await http_client.aclose()
        http_client = None


# Headers that should NOT be forwarded from the client to downstream.
_HOP_BY_HOP = frozenset(
    {
        "host",
        "authorization",
        "content-length",
        "transfer-encoding",
        "connection",
        "keep-alive",
        "te",
        "trailer",
        "upgrade",
    }
)

# Response headers that should NOT be relayed back to the client.
_SKIP_RESPONSE_HEADERS = frozenset(
    {
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
    }
)


async def proxy_request(
    *,
    request: Request,
    target_base_url: str,
    target_path: str,
    user: AuthenticatedUser,
) -> Response:
    """Forward a client request to a downstream service.

    Parameters
    ----------
    request:
        The incoming FastAPI ``Request`` object.
    target_base_url:
        The downstream service base URL (e.g. ``http://localhost:8080``).
    target_path:
        The path on the downstream service (e.g. ``/index``).
    user:
        The authenticated user extracted from the JWT.

    Returns
    -------
    A ``fastapi.responses.Response`` containing the downstream status code,
    body, and safe response headers.
    """
    client = get_client()

    # ── Build forwarded headers ──────────────────────────────────────────
    forwarded_headers: dict[str, str] = {}
    for key, value in request.headers.items():
        if key.lower() not in _HOP_BY_HOP:
            forwarded_headers[key] = value

    # Inject user identity for downstream services.
    forwarded_headers["X-User-Email"] = user.email
    forwarded_headers["X-User-Role"] = user.role

    # Propagate request ID if present.
    request_id = request.headers.get("X-Request-ID")
    if request_id:
        forwarded_headers["X-Request-ID"] = request_id

    # ── Build target URL ─────────────────────────────────────────────────
    target_url = f"{target_base_url.rstrip('/')}{target_path}"

    # ── Read body ────────────────────────────────────────────────────────
    body = await request.body()

    # ── Forward ──────────────────────────────────────────────────────────
    try:
        downstream_response = await client.request(
            method=request.method,
            url=target_url,
            headers=forwarded_headers,
            content=body if body else None,
            params=dict(request.query_params),
        )
    except httpx.HTTPError as exc:
        logger.error(
            "proxy_error",
            extra={
                "target_url": target_url,
                "error": str(exc),
            },
        )
        return Response(
            content='{"error":"Service unavailable","detail":"Downstream service did not respond.","code":"ERR_PROXY"}',
            status_code=502,
            media_type="application/json",
        )

    # ── Build response ───────────────────────────────────────────────────
    response_headers: dict[str, str] = {}
    for key, value in downstream_response.headers.items():
        if key.lower() not in _SKIP_RESPONSE_HEADERS:
            response_headers[key] = value

    return Response(
        content=downstream_response.content,
        status_code=downstream_response.status_code,
        headers=response_headers,
    )
