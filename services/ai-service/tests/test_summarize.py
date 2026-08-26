"""POST /summarize.

Named as an ai-service endpoint in services/README.md, ROLES.md and the
proposal, so it is part of the contract - it existed on paper before it existed
in code, which is exactly the kind of gap that 404s during an integration.
"""

from __future__ import annotations

from app.routes.summarize import _split


def test_summarizes_a_contract(client, contract_text):
    body = client.post("/summarize", json={"text": contract_text}).json()

    assert body["document_type"] == "contract"
    assert body["summary"]
    assert body["insufficient_text"] is False


def test_key_points_are_returned_separately(client, contract_text):
    body = client.post("/summarize", json={"text": contract_text, "max_points": 4}).json()

    assert len(body["key_points"]) <= 4
    # Bullet markers belong to the wire format, not the content.
    assert all(not p.startswith("-") for p in body["key_points"])


def test_max_points_zero_returns_none(client, contract_text):
    body = client.post("/summarize", json={"text": contract_text, "max_points": 0}).json()
    assert body["key_points"] == []


def test_short_text_is_reported_not_padded(client):
    """Padding two words into a paragraph would be inventing content."""
    body = client.post("/summarize", json={"text": "Invoice."}).json()
    assert body["insufficient_text"] is True


def test_document_type_is_inferred(client, invoice_text):
    assert client.post("/summarize", json={"text": invoice_text}).json()["document_type"] == "invoice"


def test_document_type_can_be_supplied(client, contract_text):
    body = client.post(
        "/summarize", json={"text": contract_text, "document_type": "contract"}
    ).json()
    assert body["document_type"] == "contract"


def test_summary_is_deterministic_on_mock(client, contract_text):
    first = client.post("/summarize", json={"text": contract_text}).json()["summary"]
    second = client.post("/summarize", json={"text": contract_text}).json()["summary"]
    assert first == second


def test_oversized_text_is_rejected(client):
    response = client.post("/summarize", json={"text": "word " * 40_000})
    assert response.status_code == 413
    assert response.json()["code"] == "ERR_TOKEN_BUDGET_EXCEEDED"


def test_invalid_max_sentences_is_rejected(client, contract_text):
    assert client.post(
        "/summarize", json={"text": contract_text, "max_sentences": 99}
    ).status_code == 422


# --------------------------------------------------------------------------
# Output parsing
# --------------------------------------------------------------------------
def test_split_separates_prose_from_bullets():
    summary, points = _split("A first line.\nA second line.\n\n- one\n- two", max_points=5)

    assert summary == "A first line. A second line."
    assert points == ["one", "two"]


def test_split_accepts_the_bullet_characters_models_actually_emit():
    _summary, points = _split("Text.\n\n- dash\n* star\n• bullet", max_points=5)
    assert points == ["dash", "star", "bullet"]


def test_split_survives_a_model_ignoring_the_format():
    """No bullets at all must not raise - it just means no key points."""
    summary, points = _split("Just a paragraph with no bullets at all.", max_points=5)

    assert summary == "Just a paragraph with no bullets at all."
    assert points == []


def test_split_honours_max_points():
    _summary, points = _split("T.\n\n- a\n- b\n- c\n- d", max_points=2)
    assert points == ["a", "b"]
