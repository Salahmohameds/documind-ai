"""Shared HTTP plumbing for the downstream service clients.

One ``httpx.AsyncClient`` per dependency per process, created at startup and
closed at shutdown. Creating a client per call would throw away connection
pooling on the hottest path in the platform — under the k6 spike scenario that
is a new TCP+TLS handshake per AI call, per job, per pod.

Every request carries ``X-Request-ID``. ai-service and search-service both read
that header and echo it (see their request middleware), so a single id ties an
upload in document-service's logs to the model call it eventually caused.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.config import settings
from app.errors import (
    UpstreamRejectedError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from app.logging_config import request_id_var
from app.metrics import UPSTREAM_CALLS, UPSTREAM_DURATION
from app.resilience import CircuitBreaker, call_with_resilience

logger = logging.getLogger(settings.service_name)


class ServiceClient:
    """A resilient JSON POST client for one downstream service."""

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        timeout_s: float,
        auth_token: str = "",
    ) -> None:
        self._name = name
        self._auth_token = auth_token
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_s, connect=min(10.0, timeout_s)),
            # Bounded so one slow dependency cannot consume every socket the
            # pod has. Sized against concurrency, not left at the default.
            limits=httpx.Limits(
                max_connections=settings.concurrency * 4,
                max_keepalive_connections=settings.concurrency * 2,
            ),
        )
        self._breaker = CircuitBreaker(
            name=name,
            threshold=settings.circuit_breaker_threshold,
            reset_after_s=settings.circuit_breaker_reset_s,
        )

    @property
    def breaker(self) -> CircuitBreaker:
        return self._breaker

    async def aclose(self) -> None:
        await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        headers = {"X-Request-ID": request_id_var.get()}
        # No token means no header — which is exactly what compose needs, where
        # search-service runs with DISABLE_AUTH=true. Sending 'Bearer ' with an
        # empty token would be rejected as malformed rather than ignored.
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        return headers

    async def post_json(
        self, path: str, payload: dict[str, Any], *, operation: str
    ) -> dict[str, Any]:
        """POST JSON with retry, backoff and the dependency's circuit breaker."""
        started = time.monotonic()
        try:
            result = await call_with_resilience(
                lambda: self._post_once(path, payload, operation),
                breaker=self._breaker,
                max_retries=settings.max_retries,
                base_delay_s=settings.retry_base_delay_s,
                max_delay_s=settings.retry_max_delay_s,
                operation=operation,
                # Cap the whole call — retries and backoff included — at twice
                # one attempt's timeout. A job holds a concurrency slot for the
                # duration, so an unbounded retry chain is a throughput bug.
                deadline_s=self._client.timeout.read * 2
                if self._client.timeout.read
                else None,
            )
        except Exception:
            UPSTREAM_CALLS.labels(
                dependency=self._name, operation=operation, outcome="error"
            ).inc()
            raise
        else:
            UPSTREAM_CALLS.labels(
                dependency=self._name, operation=operation, outcome="success"
            ).inc()
            return result
        finally:
            UPSTREAM_DURATION.labels(
                dependency=self._name, operation=operation
            ).observe(time.monotonic() - started)

    async def _post_once(
        self, path: str, payload: dict[str, Any], operation: str
    ) -> dict[str, Any]:
        try:
            response = await self._client.post(
                path, json=payload, headers=self._headers()
            )
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError(
                f"{self._name} {operation} timed out: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamUnavailableError(
                f"{self._name} {operation} transport error: {exc}"
            ) from exc

        # 429 and 5xx are the dependency's state, not our request: retry.
        # Other 4xx mean the request itself is wrong, and sending it again
        # changes nothing.
        if response.status_code == 429 or response.status_code >= 500:
            raise UpstreamUnavailableError(
                f"{self._name} {operation} returned {response.status_code}: "
                f"{_body_excerpt(response)}"
            )
        if response.status_code >= 400:
            raise UpstreamRejectedError(
                f"{self._name} {operation} rejected the request with "
                f"{response.status_code}: {_body_excerpt(response)}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise UpstreamUnavailableError(
                f"{self._name} {operation} returned a non-JSON body"
            ) from exc


def _body_excerpt(response: httpx.Response, limit: int = 300) -> str:
    """A short, safe slice of an error body for the log line."""
    try:
        return response.text[:limit]
    except Exception:  # pragma: no cover — a body that cannot even be decoded
        return "<unreadable body>"
