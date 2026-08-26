"""POST /embed - the endpoint search-service consumes."""

from __future__ import annotations

from app.analysis.text import cosine


def test_embed_returns_one_vector_per_text(client):
    response = client.post("/embed", json={"texts": ["alpha", "beta", "gamma"]})
    assert response.status_code == 200

    body = response.json()
    assert body["count"] == 3
    assert len(body["embeddings"]) == 3
    assert all(len(v) == body["dim"] == 384 for v in body["embeddings"])


def test_embed_is_deterministic(client):
    """Same text, same vector - across calls and across pods.

    search-service indexes with one call and queries with another. If the two
    disagreed, retrieval would return nothing and the cause would be invisible.
    """
    first = client.post("/embed", json={"texts": ["payment terms"]}).json()["embeddings"][0]
    second = client.post("/embed", json={"texts": ["payment terms"]}).json()["embeddings"][0]
    assert first == second


def test_embed_input_type_does_not_change_the_vector_for_mock(client):
    """Documents and queries must land in the same space offline.

    Real Cohere-family models embed the two differently on purpose. The mock
    must not, or every local retrieval test would return nothing.
    """
    doc = client.post("/embed", json={"texts": ["net 60 days"], "input_type": "document"})
    query = client.post("/embed", json={"texts": ["net 60 days"], "input_type": "query"})
    assert doc.json()["embeddings"][0] == query.json()["embeddings"][0]


def test_mock_embeddings_carry_real_lexical_signal(client):
    """The property that distinguishes this mock from a hash chain.

    search-service's own MockEmbedder is a SHA-256 chain: deterministic, but
    cosine similarity between related texts is pure noise, so nothing built on
    it can be smoke-tested. Related texts must score above unrelated ones here.
    """
    body = client.post(
        "/embed",
        json={
            "texts": [
                "payment is due within 60 days of receipt of a valid invoice",
                "payment terms and invoice due dates",
                "the quick brown fox jumped over the lazy dog",
            ]
        },
    ).json()
    related, similar, unrelated = body["embeddings"]

    assert cosine(related, similar) > cosine(related, unrelated)
    assert cosine(related, similar) > 0.0


def test_embed_vectors_are_normalised(client):
    body = client.post("/embed", json={"texts": ["some reasonable amount of text here"]}).json()
    norm = sum(v * v for v in body["embeddings"][0]) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_empty_batch_is_rejected(client):
    assert client.post("/embed", json={"texts": []}).status_code == 422


def test_oversized_batch_is_rejected_not_truncated(client):
    """Silently dropping half a batch would corrupt the index invisibly."""
    response = client.post("/embed", json={"texts": ["x"] * 500})
    assert response.status_code == 413

    body = response.json()
    assert body["code"] == "ERR_BATCH_TOO_LARGE"
    assert body["retryable"] is False  # resending the same batch cannot help


def test_response_carries_accounting_metadata(client):
    meta = client.post("/embed", json={"texts": ["hello world"]}).json()["meta"]
    assert meta["provider"] == "mock"
    assert meta["usage"]["tokens_in"] > 0
    assert meta["usage"]["estimated"] is True
    assert meta["degraded"] is False
