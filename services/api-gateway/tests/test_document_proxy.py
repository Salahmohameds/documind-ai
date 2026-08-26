"""Document service proxy route tests.

Covers:
- Protected routes with no token → 401
- Protected routes with expired token → 401
- Valid token → request forwarded to downstream
- Forwarded request contains X-User-Email and X-User-Role
- Authorization header is NOT forwarded
- Path parameters (document_id) are preserved
- Query parameters are preserved
- Downstream status code / body returned correctly
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import jwt as pyjwt
import respx

from app.auth.jwt_handler import create_token
from app.config import settings


# ── Helpers ──────────────────────────────────────────────────────────────


def _valid_token(email: str = "test@example.com", role: str = "user") -> str:
    return create_token(email=email, role=role)


def _expired_token() -> str:
    payload = {
        "sub": "test@example.com",
        "exp": datetime.now(UTC) - timedelta(hours=1),
        "role": "user",
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


_DOC_URL = settings.document_service_url


# ── 401 — No token ──────────────────────────────────────────────────────


class TestNoToken:
    def test_post_documents_no_token(self, client):
        assert client.post("/documents").status_code == 401

    def test_get_documents_no_token(self, client):
        assert client.get("/documents").status_code == 401

    def test_get_document_by_id_no_token(self, client):
        assert client.get("/documents/abc-123").status_code == 401

    def test_get_document_status_no_token(self, client):
        assert client.get("/documents/abc-123/status").status_code == 401


# ── 401 — Expired token ────────────────────────────────────────────────


class TestExpiredToken:
    def test_post_documents_expired(self, client):
        r = client.post("/documents", headers=_auth(_expired_token()))
        assert r.status_code == 401
        assert r.json()["code"] == "ERR_AUTH"

    def test_get_document_by_id_expired(self, client):
        r = client.get("/documents/abc-123", headers=_auth(_expired_token()))
        assert r.status_code == 401


# ── Valid token — forwarding ────────────────────────────────────────────


class TestValidTokenForwarding:
    @respx.mock
    def test_post_documents_forwarded(self, client):
        route = respx.post(f"{_DOC_URL}/documents").mock(
            return_value=httpx.Response(202, json={"id": "doc-1", "status": "queued"})
        )
        r = client.post(
            "/documents",
            json={"file": "test.pdf"},
            headers=_auth(_valid_token()),
        )
        assert r.status_code == 202
        assert r.json()["id"] == "doc-1"
        assert route.called

    @respx.mock
    def test_get_documents_forwarded(self, client):
        docs = [{"id": "doc-1"}, {"id": "doc-2"}]
        route = respx.get(f"{_DOC_URL}/documents").mock(
            return_value=httpx.Response(200, json=docs)
        )
        r = client.get("/documents", headers=_auth(_valid_token()))
        assert r.status_code == 200
        assert r.json() == docs
        assert route.called

    @respx.mock
    def test_get_document_by_id_forwarded(self, client):
        doc = {"id": "doc-42", "title": "Report.pdf", "status": "processed"}
        route = respx.get(f"{_DOC_URL}/documents/doc-42").mock(
            return_value=httpx.Response(200, json=doc)
        )
        r = client.get("/documents/doc-42", headers=_auth(_valid_token()))
        assert r.status_code == 200
        assert r.json() == doc
        assert route.called

    @respx.mock
    def test_get_document_status_forwarded(self, client):
        status = {"document_id": "doc-42", "status": "processing", "progress": 75}
        route = respx.get(f"{_DOC_URL}/documents/doc-42/status").mock(
            return_value=httpx.Response(200, json=status)
        )
        r = client.get("/documents/doc-42/status", headers=_auth(_valid_token()))
        assert r.status_code == 200
        assert r.json() == status
        assert route.called


# ── Header injection ────────────────────────────────────────────────────


class TestHeaderInjection:
    @respx.mock
    def test_x_user_email_injected(self, client):
        route = respx.get(f"{_DOC_URL}/documents").mock(
            return_value=httpx.Response(200, json=[])
        )
        client.get("/documents", headers=_auth(_valid_token(email="bob@co.com")))
        assert route.calls[0].request.headers["X-User-Email"] == "bob@co.com"

    @respx.mock
    def test_x_user_role_injected(self, client):
        route = respx.get(f"{_DOC_URL}/documents").mock(
            return_value=httpx.Response(200, json=[])
        )
        client.get("/documents", headers=_auth(_valid_token(role="admin")))
        assert route.calls[0].request.headers["X-User-Role"] == "admin"

    @respx.mock
    def test_authorization_not_forwarded(self, client):
        route = respx.post(f"{_DOC_URL}/documents").mock(
            return_value=httpx.Response(202, json={"id": "x"})
        )
        client.post("/documents", json={}, headers=_auth(_valid_token()))
        sent_headers = {k.lower() for k in route.calls[0].request.headers.keys()}
        assert "authorization" not in sent_headers


# ── Path params and query params ────────────────────────────────────────


class TestRequestPreservation:
    @respx.mock
    def test_path_param_preserved(self, client):
        """The document_id path parameter reaches the downstream URL."""
        route = respx.get(f"{_DOC_URL}/documents/my-doc-id").mock(
            return_value=httpx.Response(200, json={"id": "my-doc-id"})
        )
        client.get("/documents/my-doc-id", headers=_auth(_valid_token()))
        assert route.called

    @respx.mock
    def test_query_params_preserved(self, client):
        """Query parameters on GET /documents are forwarded."""
        route = respx.get(f"{_DOC_URL}/documents").mock(
            return_value=httpx.Response(200, json=[])
        )
        client.get(
            "/documents",
            params={"page": "2", "limit": "10"},
            headers=_auth(_valid_token()),
        )
        sent_url = str(route.calls[0].request.url)
        assert "page=2" in sent_url
        assert "limit=10" in sent_url


# ── Downstream response preservation ────────────────────────────────────


class TestDownstreamResponse:
    @respx.mock
    def test_404_from_downstream(self, client):
        respx.get(f"{_DOC_URL}/documents/nonexistent").mock(
            return_value=httpx.Response(404, json={"error": "not_found"})
        )
        r = client.get("/documents/nonexistent", headers=_auth(_valid_token()))
        assert r.status_code == 404
        assert r.json()["error"] == "not_found"

    @respx.mock
    def test_500_from_downstream(self, client):
        respx.get(f"{_DOC_URL}/documents/err").mock(
            return_value=httpx.Response(500, json={"error": "internal"})
        )
        r = client.get("/documents/err", headers=_auth(_valid_token()))
        assert r.status_code == 500
