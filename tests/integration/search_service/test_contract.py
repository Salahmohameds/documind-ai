"""Contract tests for search-service.

These assert the shape of the API — status codes, response fields, types,
and boundary behaviour — not the quality of retrieval. Quality cannot be
measured while EMBEDDING_BACKEND=mock, because the mock embedder is a
hash chain with no semantic signal.
"""

import pytest


# ───────────────────────────── health ─────────────────────────────

def test_liveness_returns_200(client):
    r = client.get("/liveness")
    assert r.status_code == 200
    assert r.json()["status"] == "alive"


def test_readiness_returns_200(client):
    r = client.get("/readiness")
    assert r.status_code == 200
    assert "status" in r.json()


def test_health_endpoints_need_no_auth(client):
    """Probes must answer without a token — Kubernetes cannot present one."""
    for path in ("/liveness", "/readiness"):
        assert client.get(path).status_code == 200


# ───────────────────────────── index ─────────────────────────────

def test_index_returns_document_id_and_chunk_count(client, doc_id):
    r = client.post("/index", json={
        "document_id": doc_id,
        "content": "Payment is due within 45 days.",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["document_id"] == doc_id
    assert isinstance(body["chunks_indexed"], int)
    assert body["chunks_indexed"] >= 1


def test_index_rejects_empty_body(client):
    r = client.post("/index", json={})
    assert r.status_code == 422
    missing = {e["loc"][-1] for e in r.json()["detail"]}
    assert {"document_id", "content"} <= missing


def test_index_rejects_missing_content(client, doc_id):
    r = client.post("/index", json={"document_id": doc_id})
    assert r.status_code == 422


def test_index_rejects_missing_document_id(client):
    r = client.post("/index", json={"content": "some text"})
    assert r.status_code == 422


def test_longer_content_produces_more_chunks(client, doc_id):
    """Chunking must actually split — otherwise retrieval granularity is lost."""
    short = client.post("/index", json={
        "document_id": f"{doc_id}_short",
        "content": "One short sentence.",
    }).json()["chunks_indexed"]

    long = client.post("/index", json={
        "document_id": f"{doc_id}_long",
        "content": "This is a sentence. " * 400,
    }).json()["chunks_indexed"]

    assert long > short


# ───────────────────────────── search ─────────────────────────────

def test_search_returns_expected_envelope(client, indexed_doc):
    r = client.get("/search", params={"question": "payment terms", "top_k": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["question"] == "payment terms"
    assert isinstance(body["results"], list)


def test_search_result_fields_and_types(client, indexed_doc):
    r = client.get("/search", params={"question": "payment", "top_k": 5})
    results = r.json()["results"]
    assert results, "expected at least one result for an indexed corpus"

    for item in results:
        assert isinstance(item["chunk_id"], str)
        assert isinstance(item["document_id"], str)
        assert isinstance(item["text"], str)
        # page is None for content indexed through POST /index — the
        # endpoint takes raw text with no page structure, so nothing can
        # assign one. Documents indexed by index_sample_documents.py do
        # carry page numbers, because it parses [PAGE n] markers first.
        # Citations are a core feature, so whatever feeds the real
        # pipeline must preserve page information. Tracked as a finding.
        assert item["page"] is None or isinstance(item["page"], int)
        assert isinstance(item["similarity"], (int, float))


def test_search_requires_question(client):
    r = client.get("/search", params={"top_k": 3})
    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"][-1] == "question"


def test_search_respects_top_k(client, indexed_doc):
    r = client.get("/search", params={"question": "payment", "top_k": 1})
    assert len(r.json()["results"]) <= 1


def test_search_results_ordered_by_descending_similarity(client, indexed_doc):
    r = client.get("/search", params={"question": "payment terms", "top_k": 10})
    scores = [item["similarity"] for item in r.json()["results"]]
    assert scores == sorted(scores, reverse=True)


def test_indexed_document_is_retrievable(client, indexed_doc):
    """Round trip: what goes in must come back out."""
    r = client.get("/search", params={"question": "payment due 45 days", "top_k": 50})
    doc_ids = {item["document_id"] for item in r.json()["results"]}
    assert indexed_doc in doc_ids


def test_search_handles_empty_question_string(client):
    r = client.get("/search", params={"question": "", "top_k": 3})
    assert r.status_code in (200, 422)


@pytest.mark.xfail(
    reason="no upper bound on top_k — a large value is accepted and the "
           "service attempts to rank the entire store. Harmless with a "
           "7-chunk corpus, a denial-of-service vector at scale.",
    strict=False,
)
def test_search_rejects_unbounded_top_k(client):
    r = client.get("/search", params={"question": "test", "top_k": 999999})
    assert r.status_code == 422