"""Structured logging setup.

Deliberately mirrors services/document-service/app/logging_config.py so both
services emit the same shape and one log parser covers the whole platform.

Follows the services/README.md non-negotiable:
  'Structured JSON: timestamp, service, level, request_id, trace_id, event, ...'
"""

from __future__ import annotations

import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from app.config import settings


def setup_logging() -> None:
    """Configure the root logger with structured JSON output."""
    handler = logging.StreamHandler(sys.stdout)

    formatter = JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "name": "service",
            "levelname": "level",
            "message": "event",
        },
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    # Silence noisy third-party loggers in non-debug mode.
    if settings.log_level.upper() != "DEBUG":
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
