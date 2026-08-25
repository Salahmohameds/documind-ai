import logging
import sys
from pythonjsonlogger import jsonlogger

from request_id_middleware import get_request_id


class RequestIDLogFilter(logging.Filter):
    """
    Runs on every log record before it's formatted. Reads the current
    request's ID out of the ContextVar (set by RequestIDMiddleware) and
    attaches it to the record, so every log line gets a request_id field
    with zero effort from whoever writes the log call. As of the current
    request_id_middleware.py, this value IS the OpenTelemetry trace ID —
    so a log line's request_id and a trace's ID in the Jaeger UI are the
    same string. Paste one into the other's search box and they match.

    Outside of a request (e.g. startup logs, background jobs with no
    incoming HTTP request, or no active span), get_request_id() returns
    "-" — so this never errors, it just logs "-" when there's genuinely
    nothing to correlate.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True  # True = keep this record, don't drop it


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

    # avoid duplicate handlers if configure_logging is called more than once
    logger.handlers = [handler]
    logger.propagate = False

    return logger
