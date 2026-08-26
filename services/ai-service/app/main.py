"""FastAPI application entry point for ai-service.

Wiring only: middleware, error translation, metrics, routers. All behaviour
lives in the modules below it.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.adapters import get_provider
from app.config import settings
from app.errors import AIServiceError
from app.logging_config import setup_logging
from app.pipeline import record_failure
from app.routes import answer, classify, embed, extract, health, pii, risk
from app.schemas import ErrorResponse

logger = logging.getLogger(settings.service_name)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    logger.info(
        "service_starting",
        extra={
            "event": "service_starting",
            "backend": settings.ai_backend,
            "model": settings.model_name,
            "embedding_model": settings.embedding_model,
            "embedding_dim": settings.embedding_dim,
        },
    )
    # Build the provider at startup so a misconfiguration surfaces in the pod
    # logs immediately, rather than on the first request in front of an
    # audience. A failure here still lets the process serve /liveness, so
    # Kubernetes reports the pod as running-but-not-ready, which is accurate.
    try:
        get_provider()
    except Exception as exc:
        logger.error(
            "provider_init_failed",
            extra={"event": "provider_init_failed", "error": str(exc)},
        )
    yield
    logger.info("service_stopping", extra={"event": "service_stopping"})


app = FastAPI(
    title="DocuMind AI - AI Service",
    description=(
        "Classification, extraction, risk analysis, embeddings and RAG "
        "generation behind one provider-agnostic adapter."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Propagate X-Request-ID and log one structured line per request.

    Per services/README.md the header is propagated rather than regenerated, so
    a single id follows a document from api-gateway through document-service and
    the processing worker into this service and back.
    """
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    started = time.monotonic()
    response = await call_next(request)
    duration_ms = int((time.monotonic() - started) * 1000)

    response.headers["X-Request-ID"] = request_id

    if request.url.path not in ("/liveness", "/readiness", "/metrics"):
        logger.info(
            "request_completed",
            extra={
                "event": "request_completed",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "provider": settings.ai_backend,
                "model": settings.model_name,
            },
        )
    return response


@app.exception_handler(AIServiceError)
async def ai_service_error_handler(request: Request, exc: AIServiceError) -> JSONResponse:
    """Translate domain errors into the stable error envelope.

    ``retryable`` is the contract with the processing worker: true means re-queue,
    false means dead-letter. See docs/architecture/ai-service-contract.md.
    """
    request_id = getattr(request.state, "request_id", None)

    try:
        record_failure(request.url.path, exc.code)
    except Exception:  # metrics must never mask the original error
        pass

    logger.warning(
        "request_failed",
        extra={
            "event": "request_failed",
            "request_id": request_id,
            "path": request.url.path,
            "code": exc.code,
            "retryable": exc.retryable,
            "detail": exc.detail,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=exc.code,
            title=exc.title,
            detail=exc.detail,
            retryable=exc.retryable,
            request_id=request_id,
        ).model_dump(),
        headers={"X-Request-ID": request_id} if request_id else None,
    )


@app.get("/metrics", include_in_schema=False)
def metrics() -> PlainTextResponse:
    """Prometheus scrape endpoint. Unauthenticated by design, like the probes."""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(health.router)
app.include_router(embed.router)
app.include_router(classify.router)
app.include_router(extract.router)
app.include_router(risk.router)
app.include_router(answer.router)
app.include_router(pii.router)
