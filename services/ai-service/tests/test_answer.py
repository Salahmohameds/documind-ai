"""POST /answer - RAG generation and citation integrity."""

from __future__ import annotations


def test_answers_from_context_with_a_citation(client, contract_chunks):
    body = client.post(
        "/answer",
        json={"question": "What are the payment terms?", "chunks": contract_chunks},
    ).json()

    assert body["refused"] is False
    assert body["grounded"] is True
    assert body["citations"]
    assert body["citations"][0]["page"] == 2
    assert body["citations"][0]["document_id"] == "contract_sample"


def test_liability_question_finds_the_liability_page(client, contract_chunks):
    """Regression: the sentence splitter used to drop soft-wrapped lines.

    The liability cap is the one sentence in the sample contract that wraps
    across a line break, so it was silently invisible and this question was
    answered from the wrong page.
    """
    body = client.post(
        "/answer",
        json={"question": "What is the cap on Provider's liability?", "chunks": contract_chunks},
    ).json()

    assert [c["page"] for c in body["citations"]] == [3]


def test_refuses_when_the_context_does_not_support_an_answer(client, contract_chunks):
    """An honest refusal is a correct outcome, not a failure."""
    body = client.post(
        "/answer",
        json={"question": "Who won the World Cup in 1998?", "chunks": contract_chunks},
    ).json()

    assert body["refused"] is True
    assert body["grounded"] is False
    assert body["citations"] == []
    assert body["confidence"] == 0.0


def test_refuses_with_no_chunks_and_spends_nothing(client):
    body = client.post("/answer", json={"question": "Anything at all?", "chunks": []}).json()

    assert body["refused"] is True
    assert body["meta"]["usage"]["tokens_in"] == 0
    assert body["meta"]["usage"]["tokens_out"] == 0


def test_citations_resolve_to_supplied_passages(client, contract_chunks):
    body = client.post(
        "/answer",
        json={"question": "How long does confidentiality last?", "chunks": contract_chunks},
    ).json()

    supplied = {c["chunk_id"] for c in contract_chunks}
    for citation in body["citations"]:
        assert citation["chunk_id"] in supplied
        assert citation["snippet"]


def test_context_is_trimmed_to_the_configured_maximum(client, contract_chunks):
    """40 chunks must not become a 40-chunk prompt."""
    many = []
    for index in range(40):
        base = contract_chunks[index % len(contract_chunks)]
        many.append({**base, "chunk_id": f"chunk-{index}", "score": 1.0 - index / 100})

    body = client.post(
        "/answer", json={"question": "What are the payment terms?", "chunks": many}
    ).json()

    assert "highest-scoring passages" in body["answer"]


def test_invalid_citation_markers_are_dropped(client):
    """A citation the user can click and find nothing behind is worse than none."""
    from app.routes.answer import _resolve_citations

    chunks = [{"chunk_id": "a", "text": "some text", "page": 1, "document_id": "d"}]
    citations, valid, total = _resolve_citations("Claim one [1] and claim two [7].", chunks)

    assert total == 2
    assert valid == 1
    assert len(citations) == 1
    assert citations[0]["chunk_id"] if isinstance(citations[0], dict) else citations[0].chunk_id


def test_repeated_marker_cites_once(client):
    from app.routes.answer import _resolve_citations

    chunks = [{"chunk_id": "a", "text": "text", "page": 1, "document_id": "d"}]
    citations, valid, total = _resolve_citations("A [1]. B [1]. C [1].", chunks)

    assert total == 3
    assert valid == 3
    assert len(citations) == 1


def test_confidence_reflects_citation_validity_only(client, contract_chunks):
    """Documented as citation validity, not semantic confidence - so it is."""
    body = client.post(
        "/answer",
        json={"question": "What are the payment terms?", "chunks": contract_chunks},
    ).json()
    assert body["confidence"] == 1.0
