

import json
import logging
import sys
import time


class JSONFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "service": "search-service",
            "level": record.levelname,
            "timestamp": int(time.time() * 1000),
            "event": record.getMessage(),
        }
        # extra fields attached via logger.info("msg", extra={...})
        for key in ("request_id", "document_id", "duration_ms", "path", "status_code"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload)


def get_logger():
    logger = logging.getLogger("search-service")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
