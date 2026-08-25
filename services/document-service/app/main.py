"""Document Service — FastAPI application entry point.

Start locally:
    uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.logging_config import setup_logging
from app.routes import documents, health

# ---------------------------------------------------------------------------
# Logging — must be configured before any logger is used.
# ---------------------------------------------------------------------------
setup_logging()
logger = logging.getLogger(settings.service_name)


# ---------------------------------------------------------------------------
# Application lifespan.
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup / shutdown lifecycle."""
    logger.info(
        "starting",
        extra={
            "port": settings.port,
            "storage_type": settings.storage_type,
            "log_level": settings.log_level,
        },
    )

    yield

    logger.info("shutting_down")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DocuMind AI — Document Service",
    description=(
        "Manages document lifecycle: upload, metadata persistence, "
        "status tracking, and job publishing to Redis Streams."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# --- Routes ----------------------------------------------------------------
app.include_router(health.router)
app.include_router(documents.router)


# --- Global exception handler ---------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all so stack traces are never leaked to clients."""
    logger.exception("unhandled_exception", extra={"error": str(exc)})
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again.",
            "code": "ERR_INTERNAL",
        },
    )
