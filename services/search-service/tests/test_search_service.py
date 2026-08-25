"""
Basic unit tests for search-service.
Run from services/search-service/: pytest tests/
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.chunking import chunk_text
from src.embeddings import MockEmbedder
from src.vector_store import InMemoryVectorStore


def test_chunk_text_produces_chunks():
    text = "Sentence one. " * 100  # long enough to require multiple chunks
    chunks = chunk_text(text, document_id="doc1", chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert all(c.document_id == "doc1" for c in chunks)
    assert all(len(c.text) > 0 for c in chunks)


def test_chunk_text_empty_input():
    assert chunk_text("", document_id="doc1") == []


def test_mock_embedder_deterministic():
    embedder = MockEmbedder(dim=32)
    v1 = embedder.embed("hello world")
    v2 = embedder.embed("hello world")
    assert v1 == v2  # same text -> same vector
    assert len(v1) == 32


def test_mock_embedder_different_text_different_vector():
    embedder = MockEmbedder(dim=32)
    v1 = embedder.embed("hello world")
    v2 = embedder.embed("goodbye world")
    assert v1 != v2


def test_vector_store_roundtrip():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        path = tmp.name
    try:
        store = InMemoryVectorStore(path=path)
        store.clear()
        embedder = MockEmbedder(dim=32)

        store.add_chunk(
            chunk_id="c1", document_id="doc1", text="payment terms are 60 days",
            embedding=embedder.embed("payment terms are 60 days"),
        )
        store.add_chunk(
            chunk_id="c2", document_id="doc1", text="the sky is blue",
            embedding=embedder.embed("the sky is blue"),
        )

        assert store.count() == 2

        query_emb = embedder.embed("payment terms are 60 days")  # exact match
        results = store.search(query_emb, top_k=1)
        assert len(results) == 1
        assert results[0].chunk_id == "c1"
        assert results[0].similarity > 0.99  # near-identical vector
    finally:
        os.remove(path)


if __name__ == "__main__":
    test_chunk_text_produces_chunks()
    test_chunk_text_empty_input()
    test_mock_embedder_deterministic()
    test_mock_embedder_different_text_different_vector()
    test_vector_store_roundtrip()
    print("All tests passed.")
