"""Shared fixtures.

Two non-negotiables, both enforced here rather than trusted to each test:

* **No test calls a real model, a real Redis or a real Postgres.** ai-service
  and search-service are answered by ``httpx.MockTransport``, Redis by
  ``fakeredis``, and Postgres by in-memory SQLite. The suite runs offline with
  no compose stack, which is what lets CI gate every PR on it.
* **The environment is pinned before ``app.config`` is imported**, because
  ``Settings`` reads the environment once at import time. A developer's stray
  ``STORAGE_TYPE=oci`` must not change what the tests exercise.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]

# Must happen before anything imports app.config.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["STORAGE_TYPE"] = "local"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["MAX_RETRIES"] = "0"          # keep retry-path tests fast
os.environ["RETRY_BASE_DELAY_S"] = "0"
os.environ["RECLAIM_INTERVAL_S"] = "0"   # reclaim on every tick
os.environ["READ_BLOCK_MS"] = "0"     # non-blocking reads: fakeredis ignores BLOCK timeouts
os.environ["GRACEFUL_SHUTDOWN_S"] = "1"

import fakeredis.aioredis  # noqa: E402
import httpx  # noqa: E402
from sqlalchemy import StaticPool, create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.database as database  # noqa: E402

# One shared in-memory database for the whole process: session_scope() opens
# its own sessions deep inside the pipeline, so they must all land on the same
# SQLite connection or each would see an empty database.
TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
database.engine = TEST_ENGINE
database.SessionLocal = sessionmaker(
    bind=TEST_ENGINE, autocommit=False, autoflush=False
)

from app.models import Base  # noqa: E402


@pytest.fixture(autouse=True)
def _database() -> None:
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def redis():
    """An in-process Redis that speaks real Streams commands."""
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def sample_pdf() -> bytes:
    """A minimal single-page PDF carrying enough text to pass extraction.

    Built by hand rather than checked in as a binary: the offsets are what make
    it a valid PDF, and a generated file keeps the fixture readable and
    reviewable in the diff.
    """
    return build_pdf(
        "MASTER SERVICES AGREEMENT between Acme Corp and Globex Ltd. "
        "Payment terms are net 30 days. Total contract value 250000 USD. "
        "This agreement auto-renews annually unless terminated in writing."
    )


def build_pdf(text: str) -> bytes:
    """Assemble a one-page PDF with `text` in its content stream."""
    escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    stream = f"BT /F1 12 Tf 40 750 Td ({escaped}) Tj ET".encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)


# --------------------------------------------------------------------------
# Canned downstream responses, shaped exactly like the real contracts
# (services/ai-service/app/schemas.py, services/search-service/src/main.py).
# --------------------------------------------------------------------------
def meta(degraded: bool = False) -> dict:
    return {
        "provider": "mock",
        "model": "mock-chat-v1",
        "duration_ms": 5,
        "usage": {"tokens_in": 10, "tokens_out": 5, "estimated": True},
        "degraded": degraded,
    }


AI_RESPONSES = {
    "/classify": lambda: {
        "label": "contract",
        "confidence": 0.91,
        "scores": {"contract": 0.91, "invoice": 0.05, "unknown": 0.04},
        "rationale": "Contract vocabulary throughout.",
        "meta": meta(),
    },
    "/extract": lambda: {
        "document_type": "contract",
        "fields": {
            "parties": {"value": "Acme Corp; Globex Ltd", "confidence": 0.9},
            "total": {"value": "250000", "confidence": 0.8},
        },
        "meta": meta(),
    },
    "/summarize": lambda: {
        "document_type": "contract",
        "summary": "A services agreement between Acme and Globex, net 30.",
        "key_points": ["Net 30 payment terms", "Auto-renews annually"],
        "insufficient_text": False,
        "meta": meta(),
    },
    "/analysis/risk": lambda: {
        "score": 62,
        "band": "medium",
        "findings": [
            {
                "rule_id": "AUTO_RENEWAL",
                "title": "Automatic renewal clause",
                "severity": "medium",
                "weight": 10,
                "category": "legal",
            }
        ],
        "categories": {"financial": "low", "legal": "high", "operational": "medium"},
        "explanation": "Auto-renewal without a notice window.",
        "scoring": {
            "method": "deterministic-rules",
            "rules_version": "1.0.0",
            "points_scored": 62,
            "points_possible": 100,
            "rules_evaluated": 12,
            "rules_fired": 1,
        },
        "meta": meta(),
    },
}


class FakeUpstream:
    """An httpx transport standing in for ai-service and search-service.

    ``failures`` maps a path to a status code (or an exception) the next call
    should produce, which is how the failure-policy tests drive one specific
    stage into failing without touching the others.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.failures: dict[str, object] = {}
        self.degraded_paths: set[str] = set()
        self.chunks_indexed = 3

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls.append(path)

        failure = self.failures.get(path)
        if isinstance(failure, Exception):
            raise failure
        if isinstance(failure, int):
            return httpx.Response(failure, json={"detail": "induced failure"})

        if path == "/index":
            return httpx.Response(
                200,
                json={
                    "document_id": "doc_test",
                    "chunks_indexed": self.chunks_indexed,
                },
            )
        if path in ("/liveness", "/readiness"):
            return httpx.Response(200, json={"status": "ok"})

        builder = AI_RESPONSES.get(path)
        if builder is None:
            return httpx.Response(404, json={"detail": f"no stub for {path}"})

        payload = builder()
        if path in self.degraded_paths:
            payload["meta"]["degraded"] = True
        return httpx.Response(200, json=payload)


@pytest.fixture
def upstream() -> FakeUpstream:
    return FakeUpstream()


# --------------------------------------------------------------------------
# Consumer-test helpers. Shared here rather than imported between test modules
# so no test file depends on another's internals.
# --------------------------------------------------------------------------
DOCUMENT_ID = "doc_test"


class StubPipeline:
    """Stands in for the pipeline so consumer behaviour is tested in isolation."""

    def __init__(self, *, error: Exception | None = None, result=None) -> None:
        from app.pipeline import PipelineResult

        self.error = error
        self.result = result or PipelineResult()
        self.runs: list[str] = []

    async def run(self, event):
        self.runs.append(event.job_id)
        if self.error:
            raise self.error
        return self.result


def job_fields(**overrides) -> dict[str, str]:
    """The event document-service actually publishes today."""
    from datetime import UTC, datetime

    fields = {
        "event_version": "1",
        "document_id": DOCUMENT_ID,
        "storage_key": f"documents/{DOCUMENT_ID}.pdf",
        "filename": "contract.pdf",
        "content_type": "application/pdf",
        "size_bytes": "12345",
        "uploaded_at": datetime.now(UTC).isoformat(),
    }
    fields.update(overrides)
    return fields


async def publish(redis_client, **overrides) -> str:
    from app.config import settings

    return await redis_client.xadd(settings.redis_stream_name, job_fields(**overrides))


async def pending_count(redis_client) -> int:
    from app.config import settings

    summary = await redis_client.xpending(
        settings.redis_stream_name, settings.redis_consumer_group
    )
    return int(summary.get("pending") or 0)


async def drain_once(consumer) -> None:
    """Run one read/dispatch cycle and wait for the dispatched jobs."""
    import asyncio

    await consumer._tick()
    if consumer._tasks:
        await asyncio.gather(*list(consumer._tasks), return_exceptions=True)


@pytest.fixture
def seeded_document() -> str:
    """The `documents` row document-service creates before it publishes."""
    from datetime import UTC, datetime

    from app.database import session_scope
    from app.models import Document

    with session_scope() as session:
        session.add(
            Document(
                document_id=DOCUMENT_ID,
                filename="contract.pdf",
                document_type="UNKNOWN",
                status="UPLOADED",
                uploaded_at=datetime.now(UTC),
            )
        )
    return DOCUMENT_ID
