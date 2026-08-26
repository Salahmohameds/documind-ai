"""Classification and field extraction."""

from __future__ import annotations

from app.analysis import extraction


def test_contract_is_classified_as_a_contract(client, contract_text):
    body = client.post("/classify", json={"text": contract_text}).json()

    assert body["label"] == "contract"
    assert body["confidence"] > 0.5
    assert body["rationale"]


def test_invoice_is_classified_as_an_invoice(client, invoice_text):
    body = client.post("/classify", json={"text": invoice_text}).json()
    assert body["label"] == "invoice"


def test_scores_expose_the_runner_up(client, contract_text):
    """0.51/0.49 and 0.95/0.05 are very different. The API must not hide it."""
    scores = client.post("/classify", json={"text": contract_text}).json()["scores"]

    assert set(scores) == {"invoice", "contract", "receipt", "report"}
    assert abs(sum(scores.values()) - 1.0) < 1e-6


def test_unrecognisable_text_is_unknown_not_a_guess(client):
    """A confident wrong label sends the wrong field set downstream."""
    body = client.post("/classify", json={"text": "asdf qwer zxcv hjkl"}).json()

    assert body["label"] == "unknown"
    assert body["confidence"] == 0.0


def test_classification_is_deterministic(client, contract_text):
    labels = {
        client.post("/classify", json={"text": contract_text}).json()["label"]
        for _ in range(3)
    }
    assert labels == {"contract"}


def test_invoice_fields_are_extracted(client, invoice_text):
    fields = client.post("/extract", json={"text": invoice_text}).json()["fields"]

    assert fields["invoice_number"]["value"] == "INV-1024"
    assert fields["vendor_name"]["value"] == "ABC Corp"
    assert fields["due_date"]["value"] == "2026-09-01"
    assert fields["currency"]["value"] == "EGP"


def test_trailing_currency_amounts_are_extracted(client, invoice_text):
    """Regression: '980 EGP' is the regional norm, not an edge case.

    The first money pattern only accepted a leading currency symbol, so every
    amount on the sample invoice came back empty.
    """
    fields = client.post("/extract", json={"text": invoice_text}).json()["fields"]

    assert fields["subtotal"]["value"] == "14,000 EGP"
    assert fields["tax"]["value"] == "980 EGP"
    assert fields["total_amount"]["value"] == "15,000 EGP"


def test_absent_field_is_null_not_guessed(client, invoice_text):
    """The sample invoice has a Due Date but no Invoice Date.

    A generic `date:` fallback happily reported the due date as the invoice
    date. An honest null beats a confident wrong value.
    """
    fields = client.post("/extract", json={"text": invoice_text}).json()["fields"]

    assert fields["invoice_date"]["value"] is None
    assert fields["invoice_date"]["confidence"] == 0.0
    assert fields["invoice_date"]["evidence"] is None


def test_contract_fields_are_extracted(client, contract_text):
    fields = client.post("/extract", json={"text": contract_text}).json()["fields"]

    assert fields["effective_date"]["value"] == "2026-01-01"
    assert fields["expiry_date"]["value"] == "2026-12-31"
    assert fields["auto_renewal"]["value"] == "yes"
    assert fields["termination_notice_days"]["value"] == "15"
    assert "two (2) years" in (fields["confidentiality_period"]["value"] or "")


def test_multiline_parties_clause_is_extracted(client, contract_text):
    """Regression: the parties clause wraps, so a dot-based pattern found nothing."""
    fields = client.post("/extract", json={"text": contract_text}).json()["fields"]

    parties = fields["parties"]["value"] or ""
    assert "Company A" in parties
    assert "Company B" in parties


def test_every_extracted_value_carries_locatable_evidence(client, invoice_text):
    fields = client.post("/extract", json={"text": invoice_text}).json()["fields"]

    for name, field in fields.items():
        if field["value"] is None:
            continue
        assert field["evidence"] is not None, f"{name} has a value but no evidence"
        assert field["evidence"]["offset"] is not None


def test_document_type_is_inferred_when_not_supplied(client, invoice_text):
    assert client.post("/extract", json={"text": invoice_text}).json()["document_type"] == "invoice"


def test_requested_field_subset_is_honoured(client, invoice_text):
    body = client.post(
        "/extract", json={"text": invoice_text, "fields": ["invoice_number", "currency"]}
    ).json()
    assert set(body["fields"]) == {"invoice_number", "currency"}


def test_verify_against_source_accepts_a_present_value():
    text = "Total: 15,000 EGP due on 2026-09-01."
    found, offset, snippet = extraction.verify_against_source("15,000 EGP", text)

    assert found is True
    assert offset is not None
    assert snippet


def test_verify_against_source_rejects_an_invented_value():
    """The guard against a model inventing an invoice total."""
    text = "Total: 15,000 EGP due on 2026-09-01."
    found, offset, snippet = extraction.verify_against_source("99,999 USD", text)

    assert found is False
    assert offset is None
    assert snippet is None


def test_verify_against_source_tolerates_reflowed_whitespace():
    """Models reflow text; that alone should not invalidate a real value."""
    text = "Provider's total liability\nshall not exceed the fees paid."
    found, _offset, _snippet = extraction.verify_against_source(
        "total liability shall not exceed", text
    )
    assert found is True


# --------------------------------------------------------------------------
# Label set vs the database CHECK constraint
# --------------------------------------------------------------------------
def test_labels_are_limited_to_what_the_schema_can_store(client, contract_text, invoice_text):
    """documents.document_type CHECK IN ('INVOICE','CONTRACT','UNKNOWN').

    Returning 'receipt' would have thrown a constraint violation the first time
    role 5 persisted a classification.
    """
    for text in (contract_text, invoice_text, "asdf qwer zxcv"):
        label = client.post("/classify", json={"text": text}).json()["label"]
        assert label in {"invoice", "contract", "unknown"}


def test_receipt_is_unknown_with_the_near_miss_named(client):
    """A confident receipt is still an unsupported type - say so, don't guess."""
    receipt = (
        "RECEIPT\nMerchant: Corner Shop\nCashier: 04\nTransaction ID: TX-99\n"
        "Card ending 4242\nChange due: 5.00\nThank you for your purchase"
    )
    body = client.post("/classify", json={"text": receipt}).json()

    assert body["label"] == "unknown"
    assert "receipt" in body["rationale"].lower()


def test_unsupported_type_extracts_no_fields(client):
    """Better to return nothing than to run the invoice field set on a receipt."""
    receipt = "RECEIPT\nMerchant: Corner Shop\nTransaction ID: TX-99\nCard ending 4242"
    body = client.post("/extract", json={"text": receipt}).json()

    assert body["document_type"] == "unknown"
    assert body["fields"] == {}
