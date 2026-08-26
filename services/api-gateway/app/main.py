"""API Gateway — FastAPI application entry point.

Start locally:
    uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.logging_config import setup_logging
from app.routes import auth, health

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
            "jwt_algorithm": settings.jwt_algorithm,
            "jwt_expiration_hours": settings.jwt_expiration_hours,
            "log_level": settings.log_level,
        },
    )

    yield

    logger.info("shutting_down")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DocuMind AI — API Gateway",
    description=(
        "Centralized entry point: JWT authentication, routing, "
        "request validation, and rate limiting."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# --- Routes ----------------------------------------------------------------
app.include_router(health.router)
app.include_router(auth.router)


# --- Middleware: request ID propagation ------------------------------------
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Propagate or create X-Request-ID for correlation.

    Per services/README.md: 'Propagate traceparent / X-Request-ID headers.'
    """
    request_id = (
        request.headers.get("X-Request-ID")
        or request.headers.get("traceparent")
        or str(uuid.uuid4())
    )
    start = time.time()

    response = await call_next(request)

    duration_ms = round((time.time() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id

    logger.info(
        f"{request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


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
