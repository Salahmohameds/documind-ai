"""Shared fixtures for search-service contract tests.

These run against a live search-service over HTTP. Point them at any
instance with SEARCH_SERVICE_URL — local uvicorn today, the OKE service
later — without changing a line of test code.

Start a local instance with:
    cd services/search-service
    DISABLE_AUTH=true VECTOR_STORE_BACKEND=memory \
        uvicorn src.main:app --port 8090
"""

import os
import uuid

import httpx
import pytest

BASE_URL = os.environ.get("SEARCH_SERVICE_URL", "http://localhost:8090")
TIMEOUT = float(os.environ.get("SEARCH_SERVICE_TIMEOUT", "10"))


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def client(base_url):
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as c:
        try:
            c.get("/liveness")
        except httpx.ConnectError:
            pytest.skip(
                f"no search-service at {base_url} — "
                "set SEARCH_SERVICE_URL or start a local instance"
            )
        yield c


@pytest.fixture
def doc_id():
    """A unique document id per test.

    The in-memory store persists for the lifetime of the process and is
    written to disk relative to the service's working directory, so tests
    cannot assume an empty store. Namespacing by uuid keeps each test
    independent of whatever else has been indexed.
    """
    return f"qa_{uuid.uuid4().hex[:12]}"


@pytest.fixture
def indexed_doc(client, doc_id):
    """Index a document with known content and return its id."""
    content = (
        "Payment is due within 45 days of receipt of a valid invoice. "
        "Late payments accrue interest at 1.5% per month. "
        "Either party may terminate for cause upon 30 days written notice."
    )
    response = client.post("/index", json={"document_id": doc_id, "content": content})
    assert response.status_code == 200, response.text
    return doc_id