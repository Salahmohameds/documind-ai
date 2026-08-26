"""Postgres vector store round trip.

The in-memory backend does an exact scan, so it cannot surface index
misconfiguration. Postgres is what compose runs and what ships to OKE,
so it needs its own coverage.

Requires a live service configured with VECTOR_STORE_BACKEND=postgres:

    docker compose up -d postgres
    cd services/search-service
    VECTOR_STORE_BACKEND=postgres DB_HOST=localhost DB_NAME=documind \
        DB_USER=documind DB_PASSWORD=documind_dev_only \
        DISABLE_AUTH=true EMBEDDING_BACKEND=mock \
        uvicorn src.main:app --port 8095

    SEARCH_SERVICE_URL=http://localhost:8095 \
        pytest tests/integration/search_service/test_postgres_backend.py
"""

import os

import pytest

# document_chunks.document_id has a foreign key to documents, and seed.sql
# inserts exactly two rows. Indexing under any other id fails on the
# constraint, not on anything this test is trying to measure.
SEEDED_DOCUMENT_ID = "invoice_sample"

pytestmark = pytest.mark.skipif(
    os.environ.get("VECTOR_STORE_BACKEND") != "postgres",
    reason="set VECTOR_STORE_BACKEND=postgres to run the Postgres round trip",
)


def test_indexed_content_is_retrievable(client):
    """Index, then search, and expect what went in to come back.

    This failed against an ivfflat index built with lists=100. The index
    partitions vectors into 100 clusters and probes one by default, so a
    small corpus put every chunk in one or two clusters and any query
    landing elsewhere returned nothing — with a 200 and an empty list,
    never an error. Silent, and only on the path that ships.
    """
    marker = "quarterly reconciliation statement for the Helvetica account"

    indexed = client.post("/index", json={
        "document_id": SEEDED_DOCUMENT_ID,
        "content": marker,
    })
    assert indexed.status_code == 200, indexed.text
    assert indexed.json()["chunks_indexed"] >= 1

    found = client.get("/search", params={
        "question": "quarterly reconciliation statement",
        "top_k": 10,
    })
    assert found.status_code == 200

    results = found.json()["results"]
    assert results, (
        "search returned no results for content that was just indexed. "
        "Check the vector index: an ivfflat index whose lists count is "
        "large relative to the row count returns empty result sets "
        "without raising. pgvector suggests lists ~ rows/1000."
    )


def test_search_is_not_empty_for_seeded_corpus(client):
    """Any question should reach something in a non-empty store.

    Not an assertion about relevance — the mock embedder has no semantic
    signal, so ranking is meaningless. This only asserts that retrieval
    reaches the data at all.
    """
    r = client.get("/search", params={"question": "invoice", "top_k": 10})
    assert r.status_code == 200
    assert r.json()["results"], "empty result set against a seeded store"
    