"""Prometheus metrics for the async worker.

Scraped by role 9's Prometheus. The series that carry the demo narrative:

* ``documind_processing_stream_pending`` — queue depth. This is the number the
  HPA story is about: drive load in, watch it climb, watch replicas follow.
  It is also the signal a KEDA ScaledObject would scale on (proposal §12
  stretch goal), so exporting it is what makes that upgrade a config change
  rather than new code.
* ``documind_processing_job_duration_seconds`` — the async-processing latency
  role 8 compares against the monolith baseline.
* ``documind_processing_stage_duration_seconds`` — where the time actually
  goes, per stage. Answers "is it the model or is it us?" without a trace.
* ``documind_processing_dead_letter_total`` — jobs that exhausted their
  attempts. Should be flat; any slope is an incident.

All series are per-pod; Prometheus aggregates. Nothing here is service state.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

JOBS = Counter(
    "documind_processing_jobs_total",
    "Jobs finished, by terminal outcome.",
    ["outcome"],  # completed | completed_degraded | failed | skipped_duplicate
)

JOB_DURATION = Histogram(
    "documind_processing_job_duration_seconds",
    "End-to-end wall clock for one job, claim to final status write.",
    # Tuned for a pipeline dominated by model calls, up to the 180 s job cap.
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0, 180.0),
)

STAGE_DURATION = Histogram(
    "documind_processing_stage_duration_seconds",
    "Duration of one pipeline stage.",
    ["stage"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

STAGE_FAILURES = Counter(
    "documind_processing_stage_failures_total",
    "Stage failures, by stage and error code. Enrichment failures do not fail "
    "the job, so this is the only place they are visible.",
    ["stage", "error_code"],
)

JOBS_IN_FLIGHT = Gauge(
    "documind_processing_jobs_in_flight",
    "Jobs currently being processed by this pod.",
)

STREAM_PENDING = Gauge(
    "documind_processing_stream_pending",
    "Messages delivered to the consumer group but not yet acknowledged.",
    ["stream", "group"],
)

STREAM_LENGTH = Gauge(
    "documind_processing_stream_length",
    "Total entries in the job stream.",
    ["stream"],
)

RECLAIMED = Counter(
    "documind_processing_reclaimed_total",
    "Messages reclaimed from a worker that stopped holding them — the "
    "self-healing path after a pod dies mid-job.",
)

DEAD_LETTERED = Counter(
    "documind_processing_dead_letter_total",
    "Jobs moved to the dead-letter stream after exhausting their attempts.",
    ["error_code"],
)

UPSTREAM_CALLS = Counter(
    "documind_processing_upstream_calls_total",
    "Calls to a downstream service, by outcome.",
    ["dependency", "operation", "outcome"],
)

UPSTREAM_DURATION = Histogram(
    "documind_processing_upstream_duration_seconds",
    "Downstream call duration.",
    ["dependency", "operation"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

# 0 closed, 1 half_open, 2 open — same encoding ai-service uses, so one Grafana
# panel can render both services' breakers.
CIRCUIT_STATE = Gauge(
    "documind_processing_circuit_breaker_state",
    "Circuit breaker state per dependency: 0=closed, 1=half_open, 2=open.",
    ["dependency"],
)

_CIRCUIT_VALUES = {"closed": 0, "half_open": 1, "open": 2}


def record_circuit_state(dependency: str, state: str) -> None:
    CIRCUIT_STATE.labels(dependency=dependency).set(_CIRCUIT_VALUES.get(state, 0))
