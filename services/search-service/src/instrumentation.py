"""Vendored request-ID/logging/tracing/metrics setup for search-service.

``services/monitoring/app_instrumentation/`` is a repo-wide reference
implementation that intentionally lives outside every service's Docker build
context (see ``services/processing-service/app/observability.py`` for the
rationale) — the guide's "use these 3 files in your service" means vendoring
their behaviour, not importing the package directly. This module is that
vendored copy for search-service: same request-ID propagation, log shape,
tracing, and metrics behaviour as the reference, self-contained so it ships
inside this service's own image.
"""

from __future__ import annotations

import contextvars
import logging
import os
import sys

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_fastapi_instrumentator import Instrumentator
from pythonjsonlogger import jsonlogger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# --- request ID -------------------------------------------------------------

request_id_ctx_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


def get_request_id() -> str:
    return request_id_ctx_var.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    HEADER_NAME = "X-Trace-ID"  # this is the OTel trace ID, not a synthetic ID

    async def dispatch(self, request: Request, call_next):
        span_context = trace.get_current_span().get_span_context()

        if span_context.trace_id != 0:
            request_id = format(span_context.trace_id, "032x")
        else:
            request_id = "-"

        token = request_id_ctx_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx_var.reset(token)

        response.headers[self.HEADER_NAME] = request_id
        return response


# --- logging ------------------------------------------------------------

class RequestIDLogFilter(logging.Filter):
    """Attaches the active request's ID (== the OTel trace ID) to every log
    record, so a log line and a Jaeger trace share one searchable string."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def configure_logging(service_name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(service_name)
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level", "name": "service"},
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIDLogFilter())

    logger.handlers = [handler]
    logger.propagate = False

    return logger


# --- tracing / metrics -------------------------------------------------------

OTEL_EXPORTER_ENDPOINT = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT", "otel-collector.monitoring.svc.cluster.local:4317"
)


def setup_tracing(app, service_name: str):
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)


def setup_metrics(app):
    Instrumentator(
        should_group_status_codes=False,
        excluded_handlers=["/metrics", "/health"],
    ).instrument(app).expose(app, endpoint="/metrics")
