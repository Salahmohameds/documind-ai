"""Shared fixtures for document-service contract tests.

Runs against a live service over HTTP. Point at any instance with
DOCUMENT_SERVICE_URL — local uvicorn today, OKE later.

Start a local instance with postgres and redis up:

    docker compose up -d postgres redis
    cd services/document-service
    DATABASE_URL=postgresql://documind:documind_dev_only@localhost:5432/documind \
        REDIS_URL=redis://localhost:6379/0 \
        STORAGE_TYPE=local STORAGE_DIR=./storage \
        uvicorn app.main:app --port 8081
"""

import io
import os

import httpx
import pytest

BASE_URL = os.environ.get("DOCUMENT_SERVICE_URL", "http://localhost:8081")
TIMEOUT = float(os.environ.get("DOCUMENT_SERVICE_TIMEOUT", "15"))

FIXTURES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "fixtures"
)


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL.rstrip("/"), timeout=TIMEOUT) as c:
        try:
            c.get("/liveness")
        except httpx.ConnectError:
            pytest.skip(
                f"no document-service at {BASE_URL} — "
                "set DOCUMENT_SERVICE_URL or start a local instance"
            )
        yield c


@pytest.fixture(scope="session")
def sample_pdf():
    """A generated contract from the synthetic corpus.

    Skips rather than fails if the corpus has not been generated — it is
    gitignored, so a fresh clone will not have it. Regenerate with
    tests/fixtures/generator/generate.py.
    """
    path = os.path.join(FIXTURES, "documents", "contract_0000.pdf")
    if not os.path.exists(path):
        pytest.skip(
            "corpus not generated — run tests/fixtures/generator/generate.py"
        )
    with open(path, "rb") as f:
        return f.read()


@pytest.fixture
def pdf_upload():
    """Build a multipart upload payload.

    A fixture rather than a plain function so test modules pick it up
    automatically — under --import-mode=importlib, importing from
    conftest by name does not resolve.
    """
    def _build(content, filename="test.pdf"):
        return {"file": (filename, io.BytesIO(content), "application/pdf")}
    return _build


@pytest.fixture
def uploaded(client, sample_pdf, pdf_upload):
    """Upload a document and return its id."""
    r = client.post("/documents", files=pdf_upload(sample_pdf, "contract_0000.pdf"))
    assert r.status_code == 202, r.text
    return r.json()["id"]