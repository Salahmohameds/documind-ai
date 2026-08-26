"""Prometheus metrics.

Scraped by role 9's Prometheus and surfaced on the Grafana dashboard. The
series that matter for the demo narrative:

* ``documind_ai_tokens_total`` - cost, live. This is what makes "we enforce a
  token budget" a chart instead of a claim.
* ``documind_ai_circuit_breaker_state`` - lets the resilience story be *shown*:
  kill the provider, watch the gauge go to 2, watch requests fail fast instead
  of piling up behind a timeout.
* ``documind_ai_request_duration_seconds`` - p50/p95/p99 per endpoint, which is
  what role 8 needs for the before/after comparison.

All counters are per-pod; Prometheus aggregates. Nothing here is service state.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter(
    "documind_ai_requests_total",
    "AI service requests by endpoint and outcome.",
    ["endpoint", "provider", "model", "outcome"],
)

REQUEST_DURATION = Histogram(
    "documind_ai_request_duration_seconds",
    "End-to-end handler duration.",
    ["endpoint", "provider"],
    # Tuned for model calls: sub-second local work up to a 30 s timeout.
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0),
)

TOKENS = Counter(
    "documind_ai_tokens_total",
    "Tokens consumed, by direction. 'estimated' marks locally-derived counts.",
    ["direction", "provider", "model", "estimated"],
)

BUDGET_REJECTIONS = Counter(
    "documind_ai_budget_rejections_total",
    "Requests rejected before any provider call because they exceeded the budget.",
    ["endpoint", "reason"],
)

PROVIDER_CALLS = Counter(
    "documind_ai_provider_calls_total",
    "Calls to the model provider, by operation and outcome.",
    ["provider", "operation", "outcome"],
)

MODEL_ROTATIONS = Counter(
    "documind_ai_model_rotations_total",
    "Times a model was parked for rate limiting and the next one was tried.",
    ["provider", "model"],
)

CIRCUIT_STATE = Gauge(
    "documind_ai_circuit_breaker_state",
    "Circuit breaker state: 0=closed, 1=half_open, 2=open.",
    ["provider"],
)

PROVIDER_READY = Gauge(
    "documind_ai_provider_ready",
    "Result of the cached provider reachability probe: 1=reachable, 0=not.",
    ["provider"],
)

PII_REDACTIONS = Counter(
    "documind_ai_pii_redactions_total",
    "PII spans redacted before leaving the cluster, by type.",
    ["type"],
)

DEGRADED = Counter(
    "documind_ai_degraded_responses_total",
    "Responses served from a local fallback because the provider was unusable.",
    ["endpoint"],
)

_CIRCUIT_VALUES = {"closed": 0, "half_open": 1, "open": 2}


def record_circuit_state(provider: str, state: str) -> None:
    CIRCUIT_STATE.labels(provider=provider).set(_CIRCUIT_VALUES.get(state, 0))


def record_tokens(provider: str, model: str, tokens_in: int, tokens_out: int, estimated: bool) -> None:
    flag = "true" if estimated else "false"
    if tokens_in:
        TOKENS.labels(direction="in", provider=provider, model=model, estimated=flag).inc(tokens_in)
    if tokens_out:
        TOKENS.labels(direction="out", provider=provider, model=model, estimated=flag).inc(tokens_out)
