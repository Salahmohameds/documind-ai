"""OpenTelemetry wiring — services/monitoring/GUIDE.md.

Follows the platform contract in services/README.md:
  'Tracing: Propagate traceparent / X-Request-ID headers; export OTel when
   OTEL_EXPORTER_OTLP_ENDPOINT is set'

and the setup in ``services/monitoring/app_instrumentation/``. Those three
modules live outside every service's Docker build context, so the guide's
"use the 3 files in your service" means vendoring their behaviour — which is
what this module does, with three deliberate differences for a worker.

**1. The interesting span is a job, not a request.**
``FastAPIInstrumentor`` traces inbound HTTP. This service's inbound HTTP is two
health probes; tracing them would produce a dashboard full of ``GET /liveness``
and nothing about the work. So the app is still instrumented (probe latency is
real, and it keeps the service consistent with the others), but the span that
matters is opened per *job* by the consumer, with a child span per pipeline
stage. That is the trace the proposal's §16 span breakdown actually depicts:
document-service → processing → ai-service → search-service.

**2. httpx, not requests.** The guide installs
``opentelemetry-instrumentation-requests``. This service calls ai-service and
search-service with httpx, so it instruments that client instead. Same effect:
``traceparent`` is injected into every outbound call, so the downstream spans
attach to this job's trace rather than starting their own.

**3. Export is opt-in, not defaulted.**
``services/monitoring/app_instrumentation/otel_setup.py`` defaults the endpoint
to the in-cluster collector, which means a worker running under
``docker compose`` — where no collector exists — retries gRPC exports forever in
the background and floods its own logs. services/README.md words the contract
as "export **when** OTEL_EXPORTER_OTLP_ENDPOINT is set", so an unset endpoint
disables the exporter entirely. The Kubernetes ConfigMap sets it; compose does
not.

Everything else follows the guide exactly, including the part that matters most
for the Grafana story: **``request_id`` is the OTel trace ID**, formatted the
same 32-char hex way ``request_id_middleware.py`` formats it. Paste a trace ID
from a log line into Jaeger's search box and it resolves.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span

from app.config import settings

logger = logging.getLogger(settings.service_name)

_TRACER_NAME = "documind.processing"


def tracer() -> trace.Tracer:
    return trace.get_tracer(_TRACER_NAME)


def setup_tracing(app: FastAPI) -> bool:
    """Install the tracer provider and instrument FastAPI + httpx.

    Returns whether spans are actually exported. When the endpoint is unset the
    provider is still installed — so ``current_trace_id`` keeps working and log
    correlation is unaffected — but nothing leaves the process.
    """
    resource = Resource.create(
        {
            "service.name": settings.service_name,
            "service.namespace": "documind",
        }
    )
    provider = TracerProvider(resource=resource)

    endpoint = settings.otel_exporter_otlp_endpoint.strip()
    exporting = bool(endpoint)
    if exporting:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # noqa: PLC0415
            OTLPSpanExporter,
        )

        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
        )

    trace.set_tracer_provider(provider)

    from opentelemetry.instrumentation.fastapi import (  # noqa: PLC0415
        FastAPIInstrumentor,
    )
    from opentelemetry.instrumentation.httpx import (  # noqa: PLC0415
        HTTPXClientInstrumentor,
    )

    # Probes and /metrics are excluded: at a 10-second readiness period they
    # would be the overwhelming majority of spans, and none of them describe
    # work this service did.
    FastAPIInstrumentor.instrument_app(
        app, excluded_urls="liveness,readiness,metrics"
    )
    # This is what carries `traceparent` to ai-service and search-service.
    HTTPXClientInstrumentor().instrument()

    logger.info(
        "tracing_configured",
        extra={"exporting": exporting, "otlp_endpoint": endpoint or None},
    )
    return exporting


def setup_metrics(app: FastAPI) -> None:
    """Expose the shared HTTP series the platform Grafana dashboard queries.

    ``http_requests_total`` and ``http_request_duration_highr_seconds`` are what
    ``kubernetes/monitoring/grafana-dashboard-configmap.yaml`` groups by job. A
    worker contributes almost nothing to them — its only inbound traffic is
    probes — but appearing on the shared board as a job with a flat line is more
    useful than being absent from it, and the worker's real signals live in
    ``app/metrics.py`` alongside these.
    """
    from prometheus_fastapi_instrumentator import Instrumentator  # noqa: PLC0415

    Instrumentator(
        should_group_status_codes=False,
        excluded_handlers=["/metrics"],
    ).instrument(app)


def current_trace_id() -> str:
    """The active trace ID as 32-char hex, or '-' when there is no span.

    Identical semantics to
    ``services/monitoring/app_instrumentation/request_id_middleware.py``,
    including the ``'-'`` fallback: inventing a disconnected id here would
    recreate exactly the problem trace-ID-as-request-ID was introduced to fix.
    """
    span_context = trace.get_current_span().get_span_context()
    if span_context.trace_id == 0:
        return "-"
    return format(span_context.trace_id, "032x")


@contextmanager
def job_span(*, job_id: str, document_id: str, attempt: int) -> Iterator[Span]:
    """The root span for one job — the worker's equivalent of a request span."""
    with tracer().start_as_current_span("process_document") as span:
        span.set_attribute("documind.job_id", job_id)
        span.set_attribute("documind.document_id", document_id)
        span.set_attribute("documind.attempt", attempt)
        yield span


@contextmanager
def stage_span(stage: str) -> Iterator[Span]:
    """A child span for one pipeline stage.

    This is what turns "the job took 2.1 s" into "1.8 s of it was the risk
    model" without adding a log line per stage.
    """
    with tracer().start_as_current_span(f"stage.{stage}") as span:
        span.set_attribute("documind.stage", stage)
        yield span
