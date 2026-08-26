"""The observability contract from services/monitoring/GUIDE.md.

Two things are worth pinning here, because both fail silently:

* **Log lines carry the OTel trace ID as ``request_id``.** That equality is the
  entire mechanism behind "paste the id from Grafana into Jaeger". If it drifts
  the logs still look perfectly correlated — every line has a plausible id —
  and the two systems simply never join.
* **A job produces one root span with a child per stage.** A worker whose only
  inbound HTTP is health probes gets nothing useful from
  ``FastAPIInstrumentor`` alone; if the job spans regress, traces keep arriving
  and keep showing nothing but ``GET /liveness``.
"""

from __future__ import annotations

import logging

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.logging_config import CorrelationFilter
from app.observability import current_trace_id, job_span, stage_span


@pytest.fixture
def spans() -> InMemorySpanExporter:
    """A real tracer provider that keeps spans in memory instead of exporting."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    # The SDK refuses to replace an already-set global provider, so set the
    # private slot: these tests need a provider they can read back.
    trace._TRACER_PROVIDER = provider  # noqa: SLF001
    yield exporter
    trace._TRACER_PROVIDER = None  # noqa: SLF001


def test_trace_id_is_a_dash_outside_any_span(spans):
    """Never invent a disconnected id — the fallback the platform middleware uses."""
    assert current_trace_id() == "-"


def test_trace_id_is_32_char_hex_inside_a_span(spans):
    """The exact format Jaeger's search box takes."""
    with job_span(job_id="1-0", document_id="doc_1", attempt=1):
        trace_id = current_trace_id()

    assert len(trace_id) == 32
    assert int(trace_id, 16) > 0


def test_log_records_carry_the_trace_id_as_request_id(spans):
    """The join between a Grafana log line and a Jaeger trace."""
    record = logging.LogRecord(
        "processing-service", logging.INFO, __file__, 1, "job_started", None, None
    )

    with job_span(job_id="1-0", document_id="doc_1", attempt=1):
        expected = current_trace_id()
        CorrelationFilter().filter(record)

    assert record.request_id == expected


def test_a_job_produces_a_root_span_with_a_child_per_stage(spans):
    with job_span(job_id="1724-0", document_id="doc_1", attempt=2):
        for stage in ("fetch", "extract_text", "classify", "index"):
            with stage_span(stage):
                pass

    finished = spans.get_finished_spans()
    root = [s for s in finished if s.name == "process_document"]
    stages = [s for s in finished if s.name.startswith("stage.")]

    assert len(root) == 1
    assert [s.name for s in stages] == [
        "stage.fetch",
        "stage.extract_text",
        "stage.classify",
        "stage.index",
    ]
    # All one trace, so the breakdown renders as a single waterfall rather than
    # four unrelated traces.
    assert {s.context.trace_id for s in finished} == {root[0].context.trace_id}
    assert all(s.parent.span_id == root[0].context.span_id for s in stages)


def test_job_span_carries_the_identifiers_needed_to_find_it(spans):
    """A trace nobody can search by document id is a trace nobody uses."""
    with job_span(job_id="1724-0", document_id="doc_abc", attempt=3):
        pass

    attributes = spans.get_finished_spans()[0].attributes
    assert attributes["documind.job_id"] == "1724-0"
    assert attributes["documind.document_id"] == "doc_abc"
    assert attributes["documind.attempt"] == 3
