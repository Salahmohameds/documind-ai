"""Search proxy route tests — M2.

Covers:
- Protected route with no token → 401
- Protected route with malformed token → 401
- Protected route with expired token → 401
- Protected route with valid token → forwarded to downstream
- Forwarded request contains X-User-Email
- Forwarded request contains X-User-Role
- Original Authorization header is NOT forwarded
- HTTP method, body, and query parameters are preserved
- Downstream status code / body are returned correctly
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import httpx
import jwt as pyjwt
import pytest
import respx

from app.auth.jwt_handler import create_token
from app.config import settings


# ── Helpers ──────────────────────────────────────────────────────────────


def _valid_token(email: str = "test@example.com", role: str = "user") -> str:
    """Create a valid JWT for testing."""
    return create_token(email=email, role=role)


def _expired_token() -> str:
    """Create a JWT that has already expired."""
    payload = {
        "sub": "test@example.com",
        "exp": datetime.now(UTC) - timedelta(hours=1),
        "role": "user",
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── 401 — No token ──────────────────────────────────────────────────────


class TestNoToken:
    """Requests without a Bearer token must receive 401."""

    def test_post_index_no_token(self, client):
        r = client.post("/index", json={"doc": "hello"})
        assert r.status_code == 401

    def test_post_query_no_token(self, client):
        r = client.post("/query", json={"q": "test"})
        assert r.status_code == 401

    def test_get_search_no_token(self, client):
        r = client.get("/search", params={"q": "test"})
        assert r.status_code == 401


# ── 401 — Malformed token ───────────────────────────────────────────────


class TestMalformedToken:
    """Requests with a garbage token must receive 401."""

    def test_post_index_malformed(self, client):
        r = client.post("/index", json={}, headers=_auth_header("not.a.jwt"))
        assert r.status_code == 401

    def test_get_search_malformed(self, client):
        r = client.get("/search", headers=_auth_header("xyz"))
        assert r.status_code == 401


# ── 401 — Expired token ────────────────────────────────────────────────


class TestExpiredToken:
    """Requests with an expired JWT must receive 401."""

    def test_post_query_expired(self, client):
        r = client.post("/query", json={}, headers=_auth_header(_expired_token()))
        assert r.status_code == 401
        data = r.json()
        assert data["code"] == "ERR_AUTH"

    def test_get_search_expired(self, client):
        r = client.get("/search", headers=_auth_header(_expired_token()))
        assert r.status_code == 401


# ── Valid token — forwarding ────────────────────────────────────────────


class TestValidTokenForwarding:
    """With a valid JWT the request must be forwarded to the search service."""

    @respx.mock
    def test_post_index_forwarded(self, client):
        """POST /index is forwarded and downstream response returned."""
        route = respx.post(f"{settings.search_service_url}/index").mock(
            return_value=httpx.Response(200, json={"indexed": True})
        )

        r = client.post(
            "/index",
            json={"document_id": "doc-1", "content": "hello world"},
            headers=_auth_header(_valid_token()),
        )

        assert r.status_code == 200
        assert r.json() == {"indexed": True}
        assert route.called

    @respx.mock
    def test_post_query_forwarded(self, client):
        """POST /query is forwarded correctly."""
        route = respx.post(f"{settings.search_service_url}/query").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        r = client.post(
            "/query",
            json={"query": "find something"},
            headers=_auth_header(_valid_token()),
        )

        assert r.status_code == 200
        assert r.json() == {"results": []}
        assert route.called

    @respx.mock
    def test_get_search_forwarded(self, client):
        """GET /search is forwarded correctly."""
        route = respx.get(f"{settings.search_service_url}/search").mock(
            return_value=httpx.Response(200, json={"hits": []})
        )

        r = client.get(
            "/search",
            params={"q": "test", "limit": "10"},
            headers=_auth_header(_valid_token()),
        )

        assert r.status_code == 200
        assert r.json() == {"hits": []}
        assert route.called


# ── Header injection ────────────────────────────────────────────────────


class TestHeaderInjection:
    """Verify that X-User-Email and X-User-Role are injected."""

    @respx.mock
    def test_x_user_email_injected(self, client):
        """The forwarded request must contain X-User-Email."""
        route = respx.post(f"{settings.search_service_url}/index").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        client.post(
            "/index",
            json={},
            headers=_auth_header(_valid_token(email="alice@example.com")),
        )

        assert route.called
        sent_request = route.calls[0].request
        assert sent_request.headers["X-User-Email"] == "alice@example.com"

    @respx.mock
    def test_x_user_role_injected(self, client):
        """The forwarded request must contain X-User-Role."""
        route = respx.post(f"{settings.search_service_url}/index").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        client.post(
            "/index",
            json={},
            headers=_auth_header(_valid_token(role="admin")),
        )

        assert route.called
        sent_request = route.calls[0].request
        assert sent_request.headers["X-User-Role"] == "admin"

    @respx.mock
    def test_authorization_header_not_forwarded(self, client):
        """The original Authorization header must NOT be forwarded."""
        route = respx.post(f"{settings.search_service_url}/index").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        client.post(
            "/index",
            json={},
            headers=_auth_header(_valid_token()),
        )

        assert route.called
        sent_request = route.calls[0].request
        assert "authorization" not in {k.lower() for k in sent_request.headers.keys()}


# ── Method, body, query params preservation ─────────────────────────────


class TestRequestPreservation:
    """HTTP method, body, and query parameters must be preserved."""

    @respx.mock
    def test_post_body_preserved(self, client):
        """The JSON body is forwarded to the downstream service."""
        route = respx.post(f"{settings.search_service_url}/query").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        body = {"query": "test query", "top_k": 5}
        client.post("/query", json=body, headers=_auth_header(_valid_token()))

        assert route.called
        import json

        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["query"] == "test query"
        assert sent_body["top_k"] == 5

    @respx.mock
    def test_get_query_params_preserved(self, client):
        """Query parameters are forwarded to the downstream service."""
        route = respx.get(f"{settings.search_service_url}/search").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        client.get(
            "/search",
            params={"q": "hello", "limit": "20"},
            headers=_auth_header(_valid_token()),
        )

        assert route.called
        sent_url = str(route.calls[0].request.url)
        assert "q=hello" in sent_url
        assert "limit=20" in sent_url


# ── Downstream response preservation ────────────────────────────────────


class TestDownstreamResponse:
    """The downstream status code and body must be returned to the client."""

    @respx.mock
    def test_downstream_status_code_preserved(self, client):
        """Non-200 status codes from downstream are preserved."""
        respx.post(f"{settings.search_service_url}/index").mock(
            return_value=httpx.Response(
                422, json={"error": "validation_error", "detail": "missing field"}
            )
        )

        r = client.post("/index", json={}, headers=_auth_header(_valid_token()))

        assert r.status_code == 422
        assert r.json()["error"] == "validation_error"

    @respx.mock
    def test_downstream_body_preserved(self, client):
        """Response body from downstream is returned verbatim."""
        expected = {"results": [{"id": 1, "score": 0.95}], "total": 1}
        respx.post(f"{settings.search_service_url}/query").mock(
            return_value=httpx.Response(200, json=expected)
        )

        r = client.post("/query", json={"q": "test"}, headers=_auth_header(_valid_token()))

        assert r.status_code == 200
        assert r.json() == expected

    @respx.mock
    def test_downstream_500_preserved(self, client):
        """A 500 from downstream is returned as-is (not masked by the gateway)."""
        respx.get(f"{settings.search_service_url}/search").mock(
            return_value=httpx.Response(500, json={"error": "internal"})
        )

        r = client.get("/search", headers=_auth_header(_valid_token()))

        assert r.status_code == 500
        assert r.json()["error"] == "internal"


# ── M1 routes remain public ─────────────────────────────────────────────


class TestM1RoutesStillPublic:
    """Health and auth routes must remain accessible without a JWT."""

    def test_liveness_still_public(self, client):
        assert client.get("/liveness").status_code == 200

    def test_readiness_still_public(self, client):
        assert client.get("/readiness").status_code == 200

    def test_login_still_public(self, client):
        r = client.post(
            "/auth/login",
            json={"email": "admin@documind.com", "password": "password123"},
        )
        assert r.status_code == 200

    def test_register_still_public(self, client):
        r = client.post(
            "/auth/register",
            json={
                "name": "M2 User",
                "email": "m2test@example.com",
                "org": "TestOrg",
                "password": "securepassword",
            },
        )
        assert r.status_code == 200
