"""The path every provider call takes.

Routes never touch a provider directly. They go through here, which guarantees
the same five things happen on every call, in the same order, forever:

    redact -> budget -> resilience -> call -> account

Putting that in one place is the reason the security claim holds. "PII is
redacted before egress" is only true if it is impossible to forget, and a route
author cannot forget a step they never write.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.adapters import get_provider
from app.adapters.base import ChatMessage
from app.config import settings
from app.metrics import (
    DEGRADED,
    PII_REDACTIONS,
    PROVIDER_CALLS,
    PROVIDER_READY,
    REQUEST_DURATION,
    REQUESTS,
    record_circuit_state,
    record_tokens,
)
from app.redaction import RedactionResult, redact
from app.resilience import CircuitBreaker, call_with_resilience
from app.schemas import ResponseMeta, Usage

logger = logging.getLogger("ai-service")

#: One breaker per pod, shared by every endpoint: they all depend on the same
#: provider, so a failure discovered by /answer is equally true for /embed.
breaker = CircuitBreaker(
    threshold=settings.circuit_breaker_threshold,
    reset_after_s=settings.circuit_breaker_reset_s,
)


@dataclass
class CallOutcome:
    """Result of one provider call plus everything needed to report on it."""

    text: str = ""
    vectors: list[list[float]] = field(default_factory=list)
    dim: int = 0
    model: str = ""
    provider: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    estimated: bool = False
    degraded: bool = False


# --------------------------------------------------------------------------
# Redaction
# --------------------------------------------------------------------------
def prepare_text(text: str) -> tuple[str, RedactionResult | None]:
    """Redact before the text can reach a provider that leaves the cluster.

    Returns ``(text_to_send, redaction_result_or_None)``. The mock provider
    performs no egress, so redaction is skipped for it by default - paying to
    scrub text that never leaves the pod would only make local development
    slower and the offline output harder to read.
    """
    if not settings.redaction_enabled():
        return text, None

    result = redact(text)
    for pii_type, count in result.counts.items():
        PII_REDACTIONS.labels(type=pii_type).inc(count)

    if result.matches:
        logger.info(
            "pii_redacted",
            extra={
                "event": "pii_redacted",
                # Types and counts only. Never the values, and never the text.
                "counts": result.counts,
                "total": len(result.matches),
            },
        )
    return result.text, result


# --------------------------------------------------------------------------
# Provider calls
# --------------------------------------------------------------------------
def chat(
    messages: list[ChatMessage],
    *,
    task: str,
    endpoint: str,
    context: dict[str, Any] | None = None,
) -> CallOutcome:
    """Single completion, wrapped in retries, a breaker, and accounting."""
    provider = get_provider()

    def invoke():
        return provider.chat(
            messages,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            task=task,
            context=context,
        )

    try:
        result = call_with_resilience(
            invoke,
            breaker=breaker,
            max_retries=settings.max_retries,
            base_delay_s=settings.retry_base_delay_s,
            max_delay_s=settings.retry_max_delay_s,
            timeout_s=settings.request_timeout_s,
            deadline_s=settings.request_deadline_s,
            operation=f"chat:{task}",
        )
    except Exception:
        PROVIDER_CALLS.labels(provider=provider.name, operation="chat", outcome="error").inc()
        record_circuit_state(provider.name, breaker.state)
        raise

    PROVIDER_CALLS.labels(provider=provider.name, operation="chat", outcome="success").inc()
    record_circuit_state(provider.name, breaker.state)
    record_tokens(provider.name, result.model, result.tokens_in, result.tokens_out, result.estimated)

    return CallOutcome(
        text=result.text,
        model=result.model,
        provider=provider.name,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        estimated=result.estimated,
    )


def embed(texts: list[str], *, input_type: str, endpoint: str) -> CallOutcome:
    """Batch embedding, wrapped identically."""
    provider = get_provider()

    def invoke():
        return provider.embed(texts, input_type=input_type)

    try:
        result = call_with_resilience(
            invoke,
            breaker=breaker,
            max_retries=settings.max_retries,
            base_delay_s=settings.retry_base_delay_s,
            max_delay_s=settings.retry_max_delay_s,
            timeout_s=settings.request_timeout_s,
            deadline_s=settings.request_deadline_s,
            operation="embed",
        )
    except Exception:
        PROVIDER_CALLS.labels(provider=provider.name, operation="embed", outcome="error").inc()
        record_circuit_state(provider.name, breaker.state)
        raise

    PROVIDER_CALLS.labels(provider=provider.name, operation="embed", outcome="success").inc()
    record_circuit_state(provider.name, breaker.state)
    record_tokens(provider.name, result.model, result.tokens_in, 0, result.estimated)

    return CallOutcome(
        vectors=result.vectors,
        dim=result.dim,
        model=result.model,
        provider=provider.name,
        tokens_in=result.tokens_in,
        estimated=result.estimated,
    )


# --------------------------------------------------------------------------
# Response metadata
# --------------------------------------------------------------------------
def build_meta(
    *,
    started: float,
    outcome: CallOutcome | None,
    endpoint: str,
    request_id: str | None,
    redaction: RedactionResult | None,
    degraded: bool = False,
) -> ResponseMeta:
    """Assemble the meta block and emit the per-request metrics."""
    provider = get_provider()
    duration_s = time.monotonic() - started

    REQUEST_DURATION.labels(endpoint=endpoint, provider=provider.name).observe(duration_s)
    REQUESTS.labels(
        endpoint=endpoint,
        provider=provider.name,
        model=outcome.model if outcome else provider.chat_model,
        outcome="degraded" if degraded else "success",
    ).inc()
    if degraded:
        DEGRADED.labels(endpoint=endpoint).inc()

    return ResponseMeta(
        provider=outcome.provider if outcome else provider.name,
        model=outcome.model if outcome else "rules-only",
        duration_ms=int(duration_s * 1000),
        usage=Usage(
            tokens_in=outcome.tokens_in if outcome else 0,
            tokens_out=outcome.tokens_out if outcome else 0,
            estimated=outcome.estimated if outcome else True,
        ),
        request_id=request_id,
        degraded=degraded,
        redacted=bool(redaction and redaction.matches),
    )


def record_failure(endpoint: str, code: str) -> None:
    """Count a request that ended in an error response."""
    provider = get_provider()
    REQUESTS.labels(
        endpoint=endpoint, provider=provider.name, model=provider.chat_model, outcome=code
    ).inc()


# --------------------------------------------------------------------------
# Readiness
# --------------------------------------------------------------------------
_probe_cache: tuple[float, bool] = (0.0, False)


def provider_reachable(force: bool = False) -> bool:
    """Cached provider reachability for /readiness.

    Cached because the readiness probe runs every few seconds on every pod, and
    an uncached network round-trip per probe would generate more traffic than
    the workload does. The TTL is ``READINESS_CACHE_TTL_S``.
    """
    global _probe_cache
    provider = get_provider()
    now = time.monotonic()
    checked_at, value = _probe_cache

    if not force and (now - checked_at) < settings.readiness_cache_ttl_s:
        return value

    ok = provider.probe()
    _probe_cache = (now, ok)
    PROVIDER_READY.labels(provider=provider.name).set(1 if ok else 0)
    return ok


def reset_probe_cache() -> None:
    """Used by tests; also the right hook for a future SIGHUP."""
    global _probe_cache
    _probe_cache = (0.0, False)
