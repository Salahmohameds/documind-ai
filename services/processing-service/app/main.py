"""Processing Service — async document processing worker.

The HTTP app here is not the service; the Redis consumer is. FastAPI is present
so the worker can satisfy the platform's probe contract (services/README.md)
and be scraped by Prometheus. The consumer runs as an asyncio task started in
the lifespan, sharing the event loop with the (near-idle) probe handlers.

Why one process rather than a sidecar or a bare script:

* Kubernetes needs an HTTP endpoint to probe. A bare script gives the kubelet
  nothing to ask, so a wedged worker looks healthy forever.
* Queue depth has to be exported for the HPA story, and Prometheus scrapes HTTP.
* Sharing the loop means the probes see the consumer's real state directly,
  rather than a heartbeat file or a socket between two processes.

Start locally:
    uvicorn app.main:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.clients.ai import AIServiceClient
from app.clients.search import SearchServiceClient
from app.config import settings
from app.logging_config import setup_logging
from app.pipeline import ProcessingPipeline
from app.queue.consumer import StreamConsumer
from app.routes import health
from app.storage import build_reader

setup_logging()
logger = logging.getLogger(settings.service_name)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Start the consumer, then drain it cleanly on SIGTERM.

    Uvicorn turns SIGTERM into a lifespan shutdown, so the ordering below is
    the graceful-shutdown sequence:

        SIGTERM → readiness 503 (pod leaves the endpoints list)
                → consumer stops reading NEW messages
                → in-flight jobs finish, up to graceful_shutdown_s
                → anything still running is cancelled and left UN-ACKED
                → another pod's XAUTOCLAIM picks it up

    Nothing is lost at any point in that sequence, which is what makes a
    rolling update and a node drain uneventful.
    """
    app.state.shutting_down = False

    logger.info(
        "service_starting",
        extra={
            "port": settings.port,
            "storage_type": settings.storage_type,
            "stream": settings.redis_stream_name,
            "group": settings.redis_consumer_group,
            "concurrency": settings.concurrency,
            "log_level": settings.log_level,
        },
    )

    redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        # Detects a connection killed by a network blip rather than blocking
        # forever on a socket the other end has forgotten about.
        health_check_interval=30,
    )
    reader = build_reader()
    ai_client = AIServiceClient()
    search_client = SearchServiceClient()

    pipeline = ProcessingPipeline(
        reader=reader, ai_client=ai_client, search_client=search_client
    )
    consumer = StreamConsumer(redis=redis, pipeline=pipeline)

    app.state.redis = redis
    app.state.reader = reader
    app.state.ai_client = ai_client
    app.state.search_client = search_client
    app.state.consumer = consumer

    # The consumer retries its own errors internally; a failure to even start
    # (Redis unreachable at boot) leaves the task done, which liveness reports
    # and Kubernetes acts on. Serving /liveness while failing to consume is the
    # one state this service must never sit in quietly.
    app.state.consumer_task = asyncio.create_task(consumer.run(), name="stream-consumer")

    try:
        yield
    finally:
        logger.info("service_stopping")
        app.state.shutting_down = True

        await consumer.stop()
        task = app.state.consumer_task
        try:
            # The consumer drains in-flight jobs itself; this bound is that
            # drain plus the outstanding XREADGROUP block, so a worker parked
            # on an empty queue still shuts down promptly.
            await asyncio.wait_for(
                task,
                timeout=settings.graceful_shutdown_s
                + (settings.read_block_ms / 1000)
                + 5,
            )
        except TimeoutError:
            logger.warning("consumer_shutdown_timeout")
            task.cancel()
        except asyncio.CancelledError:
            pass

        await ai_client.aclose()
        await search_client.aclose()
        await redis.aclose()
        logger.info("service_stopped")


app = FastAPI(
    title="DocuMind AI — Processing Service",
    description=(
        "Asynchronous document processing worker. Consumes jobs from Redis "
        "Streams, orchestrates ai-service and search-service, and records the "
        "outcome in PostgreSQL."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)


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
            "detail": "An unexpected error occurred.",
            "code": "ERR_INTERNAL",
        },
    )
