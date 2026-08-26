"""Cross-cutting guarantees: budget, prompts, adapter selection, error envelope.

These are the properties other roles code against, so they are pinned here
rather than left to good intentions.
"""

from __future__ import annotations

import pytest

from app import budget, prompts
from app.adapters import build_provider, get_provider
from app.config import Settings
from app.errors import ProviderConfigurationError, TokenBudgetExceededError


# --------------------------------------------------------------------------
# Adapter selection
# --------------------------------------------------------------------------
def test_default_backend_is_mock():
    """The service must start and serve with no credential and no network."""
    assert Settings().ai_backend == "mock"


def test_mock_provider_is_not_external():
    """Drives redaction and egress logging - it must not lie about egress."""
    provider = get_provider()
    assert provider.name == "mock"
    assert provider.is_external is False


def test_unknown_backend_is_rejected():
    cfg = Settings()
    cfg.ai_backend = "gemini-direct"  # type: ignore[assignment]
    with pytest.raises(ProviderConfigurationError):
        build_provider(cfg)


def test_oci_backend_requires_region_and_compartment():
    """Fail at construction with a useful message, not at 2 a.m. on a demo."""
    cfg = Settings()
    cfg.ai_backend = "oci"  # type: ignore[assignment]
    cfg.oci_region = ""
    with pytest.raises(ProviderConfigurationError, match="OCI_REGION"):
        build_provider(cfg)


def test_openai_compat_backend_requires_a_key():
    cfg = Settings()
    cfg.ai_backend = "openai_compat"  # type: ignore[assignment]
    cfg.openai_base_url = "https://example.invalid/v1"
    cfg.openai_api_key = ""
    with pytest.raises(ProviderConfigurationError, match="OPENAI_API_KEY"):
        build_provider(cfg)


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
def test_nothing_is_hard_coded(monkeypatch):
    """services/README.md: 100 % from environment variables."""
    monkeypatch.setenv("MODEL_NAME", "cohere.command-a")
    monkeypatch.setenv("EMBEDDING_DIM", "1024")
    monkeypatch.setenv("TEMPERATURE", "0.7")

    cfg = Settings()
    assert cfg.model_name == "cohere.command-a"
    assert cfg.embedding_dim == 1024
    assert cfg.temperature == 0.7


def test_redaction_is_on_for_external_backends_by_default():
    cfg = Settings()
    cfg.ai_backend = "oci"  # type: ignore[assignment]
    assert cfg.redaction_enabled() is True
    assert cfg.provider_is_external is True


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------
def test_oversized_text_is_rejected_before_any_provider_call():
    with pytest.raises(TokenBudgetExceededError):
        budget.check_text_budget("x" * 100_000, limit=100, endpoint="/test")


def test_text_within_budget_passes():
    assert budget.check_text_budget("short enough", limit=1000, endpoint="/test") > 0


def test_budget_rejection_is_not_retryable():
    """Re-sending an oversized payload fails identically. Dead-letter it."""
    with pytest.raises(TokenBudgetExceededError) as exc:
        budget.check_text_budget("x" * 100_000, limit=100, endpoint="/test")
    assert exc.value.retryable is False


def test_trim_context_keeps_the_best_scoring_chunks():
    chunks = [{"text": "word " * 20, "score": i / 10} for i in range(10)]
    kept, trimmed = budget.trim_context(chunks, max_chunks=3, token_limit=10_000)

    assert len(kept) == 3
    assert trimmed is True
    assert [c["score"] for c in kept] == [0.9, 0.8, 0.7]


def test_trim_context_reports_when_it_dropped_nothing():
    chunks = [{"text": "short", "score": 1.0}]
    kept, trimmed = budget.trim_context(chunks, max_chunks=10, token_limit=10_000)

    assert kept == chunks
    assert trimmed is False


def test_trim_context_respects_the_token_limit():
    chunks = [{"text": "word " * 500, "score": 1.0} for _ in range(10)]
    kept, trimmed = budget.trim_context(chunks, max_chunks=10, token_limit=200)

    assert len(kept) < 10
    assert trimmed is True


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------
def test_every_prompt_the_service_uses_is_present():
    for name in ("answer", "classify", "extract", "risk_explain"):
        assert prompts.load(name).strip()


def test_placeholders_are_substituted():
    rendered = prompts.render("answer", context="PASSAGE-A", question="QUESTION-B")

    assert "PASSAGE-A" in rendered
    assert "QUESTION-B" in rendered
    assert "{{context}}" not in rendered


def test_unknown_placeholder_is_left_alone_not_fatal():
    """A prompt edited through the ConfigMap must not take the service down."""
    rendered = prompts.render("answer", context="A")
    assert "{{question}}" in rendered


def test_missing_prompt_raises_a_useful_error():
    from app.errors import PromptNotFoundError

    with pytest.raises(PromptNotFoundError, match="ConfigMap"):
        prompts.load("no_such_prompt")


def test_answer_prompt_instructs_the_exact_refusal_string():
    """The route matches on this string; the prompt must specify it verbatim."""
    from app.routes.answer import REFUSAL

    assert REFUSAL in prompts.load("answer")


# --------------------------------------------------------------------------
# Error envelope and request correlation
# --------------------------------------------------------------------------
def test_errors_use_the_stable_envelope(client):
    response = client.post("/embed", json={"texts": ["x"] * 500})
    body = response.json()

    assert set(body) == {"code", "title", "detail", "retryable", "request_id"}
    assert body["code"].startswith("ERR_")
    assert isinstance(body["retryable"], bool)


def test_request_id_is_propagated_not_regenerated(client):
    """One id follows a document across every service in the pipeline."""
    response = client.post(
        "/classify",
        json={"text": "Invoice Number: INV-1"},
        headers={"X-Request-ID": "trace-me-123"},
    )
    assert response.headers["X-Request-ID"] == "trace-me-123"


def test_request_id_is_generated_when_absent(client):
    response = client.get("/liveness")
    assert response.headers.get("X-Request-ID")


def test_request_id_appears_in_error_responses(client):
    response = client.post(
        "/embed", json={"texts": ["x"] * 500}, headers={"X-Request-ID": "err-trace"}
    )
    assert response.json()["request_id"] == "err-trace"


def test_openapi_schema_is_generated(client):
    """Role 3 and role 5 code against this, not against the implementation."""
    schema = client.get("/openapi.json").json()
    paths = set(schema["paths"])

    assert {"/embed", "/classify", "/extract", "/analysis/risk", "/answer", "/pii"} <= paths
