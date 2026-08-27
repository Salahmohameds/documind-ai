"""AI service proxy and /qa orchestration tests.

Covers:
- AI proxy routes require JWT (401 without token).
- POST /classify is forwarded to AI_SERVICE_URL/classify.
- JSON body is preserved through the proxy.
- Downstream response (status + body) is returned correctly.
- X-User-Email and X-User-Role are injected.
- /qa orchestration: Search /query → AI /answer full flow.
- /qa: Search failure → 502.
- /qa: AI failure → 502.
- /qa: Unauthorized access → 401.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import httpx
import jwt as pyjwt
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


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


_AI_URL = settings.ai_service_url
_SEARCH_URL = settings.search_service_url


# ── 401 — No token ──────────────────────────────────────────────────────


class TestAIProxyNoToken:
    """AI proxy routes must return 401 without a Bearer token."""

    def test_post_classify_no_token(self, client):
        assert client.post("/classify", json={"text": "hello"}).status_code == 401

    def test_post_embed_no_token(self, client):
        assert client.post("/embed", json={"texts": ["a"]}).status_code == 401

    def test_post_extract_no_token(self, client):
        assert client.post("/extract", json={"text": "x"}).status_code == 401

    def test_post_analysis_risk_no_token(self, client):
        assert client.post("/analysis/risk", json={"text": "x"}).status_code == 401

    def test_post_summarize_no_token(self, client):
        assert client.post("/summarize", json={"text": "x"}).status_code == 401

    def test_post_pii_no_token(self, client):
        assert client.post("/pii", json={"text": "x"}).status_code == 401

    def test_post_answer_no_token(self, client):
        assert client.post("/answer", json={"question": "?", "chunks": []}).status_code == 401

    def test_post_qa_no_token(self, client):
        assert client.post("/qa", json={"question": "?"}).status_code == 401


# ── 401 — Expired token ─────────────────────────────────────────────────


class TestAIProxyExpiredToken:
    """AI proxy routes must return 401 with an expired JWT."""

    def test_post_classify_expired(self, client):
        r = client.post("/classify", json={"text": "x"}, headers=_auth(_expired_token()))
        assert r.status_code == 401
        assert r.json()["code"] == "ERR_AUTH"

    def test_post_qa_expired(self, client):
        r = client.post("/qa", json={"question": "?"}, headers=_auth(_expired_token()))
        assert r.status_code == 401
        assert r.json()["code"] == "ERR_AUTH"


# ── AI proxy forwarding — POST /classify ────────────────────────────────


class TestClassifyProxy:
    """POST /classify must be forwarded to the AI service."""

    @respx.mock
    def test_classify_forwarded(self, client):
        """POST /classify is forwarded and downstream response returned."""
        ai_response = {
            "document_id": "doc-1",
            "label": "contract",
            "confidence": 0.73,
            "scores": {"invoice": 0.10, "contract": 0.73, "receipt": 0.17, "report": 0.0},
            "rationale": "Matched 8 contract signals",
            "meta": {"provider": "mock", "model": "mock-chat-v1", "duration_ms": 12},
        }
        route = respx.post(f"{_AI_URL}/classify").mock(
            return_value=httpx.Response(200, json=ai_response)
        )

        r = client.post(
            "/classify",
            json={"text": "This is a service agreement between...", "document_id": "doc-1"},
            headers=_auth(_valid_token()),
        )

        assert r.status_code == 200
        assert r.json() == ai_response
        assert route.called

    @respx.mock
    def test_classify_body_preserved(self, client):
        """The JSON body is forwarded verbatim to the AI service."""
        route = respx.post(f"{_AI_URL}/classify").mock(
            return_value=httpx.Response(200, json={"label": "unknown"})
        )

        body = {"text": "test document content", "document_id": "doc-42"}
        client.post("/classify", json=body, headers=_auth(_valid_token()))

        assert route.called
        sent_body = json.loads(route.calls[0].request.content)
        assert sent_body["text"] == "test document content"
        assert sent_body["document_id"] == "doc-42"

    @respx.mock
    def test_classify_x_user_email_injected(self, client):
        """X-User-Email header is injected into the forwarded request."""
        route = respx.post(f"{_AI_URL}/classify").mock(
            return_value=httpx.Response(200, json={"label": "unknown"})
        )

        client.post(
            "/classify",
            json={"text": "test"},
            headers=_auth(_valid_token(email="alice@example.com")),
        )

        assert route.called
        assert route.calls[0].request.headers["X-User-Email"] == "alice@example.com"

    @respx.mock
    def test_classify_x_user_role_injected(self, client):
        """X-User-Role header is injected into the forwarded request."""
        route = respx.post(f"{_AI_URL}/classify").mock(
            return_value=httpx.Response(200, json={"label": "unknown"})
        )

        client.post(
            "/classify",
            json={"text": "test"},
            headers=_auth(_valid_token(role="admin")),
        )

        assert route.called
        assert route.calls[0].request.headers["X-User-Role"] == "admin"

    @respx.mock
    def test_classify_downstream_error_preserved(self, client):
        """Non-200 status codes from the AI service are preserved."""
        error_response = {
            "code": "ERR_TOKEN_BUDGET_EXCEEDED",
            "title": "Token budget exceeded",
            "detail": "Payload over limit",
            "retryable": False,
            "request_id": "req-123",
        }
        respx.post(f"{_AI_URL}/classify").mock(
            return_value=httpx.Response(413, json=error_response)
        )

        r = client.post(
            "/classify",
            json={"text": "x" * 100000},
            headers=_auth(_valid_token()),
        )

        assert r.status_code == 413
        assert r.json()["code"] == "ERR_TOKEN_BUDGET_EXCEEDED"
        assert r.json()["retryable"] is False


# ── /qa orchestration — full flow ───────────────────────────────────────


class TestQAOrchestration:
    """/qa must chain Search /query → AI /answer and return the result."""

    @respx.mock
    def test_qa_full_flow(self, client):
        """Complete /qa flow: search → map results → AI answer → response."""
        # Mock Search /query
        search_results = {
            "question": "What are the payment terms?",
            "results": [
                {
                    "chunk_id": "chunk-1",
                    "document_id": "contract_sample",
                    "text": "Payment is due within 60 days of receipt.",
                    "page": 2,
                    "similarity": 0.83,
                },
                {
                    "chunk_id": "chunk-2",
                    "document_id": "contract_sample",
                    "text": "Late payments accrue interest at 1.5% per month.",
                    "page": 3,
                    "similarity": 0.71,
                },
            ],
        }
        search_route = respx.post(f"{_SEARCH_URL}/query").mock(
            return_value=httpx.Response(200, json=search_results)
        )

        # Mock AI /answer
        ai_answer = {
            "answer": "Payment is due within 60 days of receipt of a valid invoice. [1]",
            "citations": [
                {
                    "chunk_id": "chunk-1",
                    "document_id": "contract_sample",
                    "page": 2,
                    "snippet": "Payment is due within 60 days of receipt.",
                }
            ],
            "grounded": True,
            "refused": False,
            "confidence": 1.0,
            "meta": {"provider": "mock", "model": "mock-chat-v1", "duration_ms": 50},
        }
        ai_route = respx.post(f"{_AI_URL}/answer").mock(
            return_value=httpx.Response(200, json=ai_answer)
        )

        # Make the /qa request
        r = client.post(
            "/qa",
            json={"question": "What are the payment terms?"},
            headers=_auth(_valid_token()),
        )

        assert r.status_code == 200
        assert r.json() == ai_answer

        # Verify search was called with the question
        assert search_route.called
        search_body = json.loads(search_route.calls[0].request.content)
        assert search_body["question"] == "What are the payment terms?"

        # Verify AI /answer was called with question + mapped chunks
        assert ai_route.called
        ai_body = json.loads(ai_route.calls[0].request.content)
        assert ai_body["question"] == "What are the payment terms?"
        assert len(ai_body["chunks"]) == 2

        # Verify similarity → score mapping
        assert ai_body["chunks"][0]["score"] == 0.83
        assert ai_body["chunks"][0]["chunk_id"] == "chunk-1"
        assert ai_body["chunks"][0]["text"] == "Payment is due within 60 days of receipt."
        assert ai_body["chunks"][1]["score"] == 0.71

    @respx.mock
    def test_qa_user_headers_forwarded_to_search(self, client):
        """X-User-Email and X-User-Role are sent to the search service."""
        search_route = respx.post(f"{_SEARCH_URL}/query").mock(
            return_value=httpx.Response(200, json={"question": "?", "results": []})
        )
        respx.post(f"{_AI_URL}/answer").mock(
            return_value=httpx.Response(200, json={"answer": "No context."})
        )

        client.post(
            "/qa",
            json={"question": "?"},
            headers=_auth(_valid_token(email="bob@co.com", role="admin")),
        )

        assert search_route.called
        assert search_route.calls[0].request.headers["X-User-Email"] == "bob@co.com"
        assert search_route.calls[0].request.headers["X-User-Role"] == "admin"

    @respx.mock
    def test_qa_user_headers_forwarded_to_ai(self, client):
        """X-User-Email and X-User-Role are sent to the AI service."""
        respx.post(f"{_SEARCH_URL}/query").mock(
            return_value=httpx.Response(200, json={"question": "?", "results": []})
        )
        ai_route = respx.post(f"{_AI_URL}/answer").mock(
            return_value=httpx.Response(200, json={"answer": "No context."})
        )

        client.post(
            "/qa",
            json={"question": "?"},
            headers=_auth(_valid_token(email="carol@co.com", role="user")),
        )

        assert ai_route.called
        assert ai_route.calls[0].request.headers["X-User-Email"] == "carol@co.com"
        assert ai_route.calls[0].request.headers["X-User-Role"] == "user"


# ── /qa — Search failure ────────────────────────────────────────────────


class TestQASearchFailure:
    """/qa must return 502 when the Search service fails."""

    @respx.mock
    def test_search_returns_500(self, client):
        """Search returning 500 causes /qa to return 502."""
        respx.post(f"{_SEARCH_URL}/query").mock(
            return_value=httpx.Response(500, json={"error": "internal"})
        )

        r = client.post(
            "/qa",
            json={"question": "What?"},
            headers=_auth(_valid_token()),
        )

        assert r.status_code == 502
        assert r.json()["code"] == "ERR_SEARCH_FAILED"

    @respx.mock
    def test_search_connection_error(self, client):
        """Search connection failure causes /qa to return 502."""
        respx.post(f"{_SEARCH_URL}/query").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        r = client.post(
            "/qa",
            json={"question": "What?"},
            headers=_auth(_valid_token()),
        )

        assert r.status_code == 502
        assert r.json()["code"] == "ERR_PROXY"

    @respx.mock
    def test_search_timeout(self, client):
        """Search timeout causes /qa to return 504."""
        respx.post(f"{_SEARCH_URL}/query").mock(
            side_effect=httpx.ReadTimeout("Timed out")
        )

        r = client.post(
            "/qa",
            json={"question": "What?"},
            headers=_auth(_valid_token()),
        )

        assert r.status_code == 504
        assert r.json()["code"] == "ERR_PROXY_TIMEOUT"


# ── /qa — AI failure ────────────────────────────────────────────────────


class TestQAAIFailure:
    """/qa must return 502 when the AI service fails after search succeeds."""

    @respx.mock
    def test_ai_returns_500(self, client):
        """AI returning 500 is passed through (preserving status)."""
        respx.post(f"{_SEARCH_URL}/query").mock(
            return_value=httpx.Response(200, json={"question": "?", "results": []})
        )
        respx.post(f"{_AI_URL}/answer").mock(
            return_value=httpx.Response(
                500,
                json={
                    "code": "ERR_PROVIDER_MISCONFIGURED",
                    "title": "Config error",
                    "detail": "...",
                    "retryable": False,
                    "request_id": "req-1",
                },
            )
        )

        r = client.post(
            "/qa",
            json={"question": "What?"},
            headers=_auth(_valid_token()),
        )

        # AI service errors are passed through with their status code
        assert r.status_code == 500
        assert r.json()["code"] == "ERR_PROVIDER_MISCONFIGURED"

    @respx.mock
    def test_ai_connection_error(self, client):
        """AI connection failure causes /qa to return 502."""
        respx.post(f"{_SEARCH_URL}/query").mock(
            return_value=httpx.Response(200, json={"question": "?", "results": []})
        )
        respx.post(f"{_AI_URL}/answer").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        r = client.post(
            "/qa",
            json={"question": "What?"},
            headers=_auth(_valid_token()),
        )

        assert r.status_code == 502
        assert r.json()["code"] == "ERR_PROXY"

    @respx.mock
    def test_ai_timeout(self, client):
        """AI timeout causes /qa to return 504."""
        respx.post(f"{_SEARCH_URL}/query").mock(
            return_value=httpx.Response(200, json={"question": "?", "results": []})
        )
        respx.post(f"{_AI_URL}/answer").mock(
            side_effect=httpx.ReadTimeout("Timed out")
        )

        r = client.post(
            "/qa",
            json={"question": "What?"},
            headers=_auth(_valid_token()),
        )

        assert r.status_code == 504
        assert r.json()["code"] == "ERR_PROXY_TIMEOUT"


# ── Existing routes still work ──────────────────────────────────────────


class TestExistingRoutesUnaffected:
    """Adding AI routes must not break existing health/auth routes."""

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
