"""Shared fixtures.

Non-negotiable (services/README.md and the AI Engineer's own rule): **no test
ever calls a real model.** The backend is pinned to ``mock`` here before the
application is imported, so a stray ``AI_BACKEND=oci`` in a developer's shell
cannot turn ``pytest`` into a billable event.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]

# Must happen before anything imports app.config, which reads the environment
# once at import time.
os.environ["AI_BACKEND"] = "mock"
os.environ["PROMPTS_DIR"] = str(SERVICE_ROOT / "app" / "prompts")
os.environ.setdefault("LOG_LEVEL", "WARNING")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def contract_text() -> str:
    return (REPO_ROOT / "sample_documents" / "contract_sample.txt").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def invoice_text() -> str:
    return (REPO_ROOT / "sample_documents" / "invoice_sample.txt").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def contract_chunks(contract_text: str) -> list[dict]:
    """The sample contract split on its own [PAGE n] markers."""
    chunks = []
    for index, part in enumerate(contract_text.split("[PAGE ")[1:], start=1):
        body = part.split("]", 1)[1].strip()
        chunks.append(
            {
                "chunk_id": f"contract_sample-{index}",
                "document_id": "contract_sample",
                "page": index,
                "text": body,
                "score": 1.0,
            }
        )
    return chunks


@pytest.fixture(autouse=True)
def _reset_breaker():
    """Keep breaker state from leaking between tests."""
    from app.pipeline import breaker, reset_probe_cache

    breaker.reset()
    reset_probe_cache()
    yield
    breaker.reset()
    reset_probe_cache()
