"""Structured logging with automatic job/request correlation.

Follows the services/README.md non-negotiable:
  'Structured JSON: timestamp, service, level, request_id, trace_id, event, …'

The difference from document-service's version is the context filter. A worker
has no HTTP request to hang a correlation id on, and the alternative — passing
``job_id`` explicitly into every log call across nine pipeline stages — is the
kind of thing that gets forgotten exactly where it matters. Instead the
consumer sets the contextvars once when it claims a message, and every log line
emitted anywhere beneath it carries them.

``request_id`` is propagated to ai-service and search-service as
``X-Request-ID``; both already echo it. One id therefore ties an upload in
document-service's log to the model call in ai-service's.
"""

from __future__ import annotations

import contextvars
import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from app.config import settings

# "-" rather than None so the field is always present and always a string:
# a log pipeline that sometimes sees null and sometimes a string is a log
# pipeline with two schemas.
job_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("job_id", default="-")
document_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "document_id", default="-"
)
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class CorrelationFilter(logging.Filter):
    """Attach the current job's identifiers to every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.job_id = job_id_var.get()
        record.document_id = document_id_var.get()
        record.request_id = request_id_var.get()
        return True


def bind_job_context(*, job_id: str, document_id: str, request_id: str) -> None:
    """Bind correlation ids for the current asyncio task.

    Each job runs in its own task, and contextvars are copied per task, so
    concurrent jobs in one pod do not overwrite each other's ids.
    """
    job_id_var.set(job_id)
    document_id_var.set(document_id)
    request_id_var.set(request_id)


def setup_logging() -> None:
    """Configure the root logger with structured JSON output."""
    handler = logging.StreamHandler(sys.stdout)

    formatter = JsonFormatter(
        fmt=(
            "%(asctime)s %(name)s %(levelname)s %(message)s "
            "%(job_id)s %(document_id)s %(request_id)s"
        ),
        rename_fields={
            "asctime": "timestamp",
            "name": "service",
            "levelname": "level",
            "message": "event",
        },
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    # Silence noisy third-party loggers in non-debug mode.
    if settings.log_level.upper() != "DEBUG":
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
