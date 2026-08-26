"""PII redaction - the security control, tested as one."""

from __future__ import annotations

from app import redaction


def test_email_is_redacted():
    result = redaction.redact("Contact billing@abccorp.example.com for questions.")
    assert "billing@abccorp.example.com" not in result.text
    assert "[EMAIL_1]" in result.text
    assert result.counts == {"EMAIL": 1}


def test_valid_card_number_is_redacted():
    # 4242 4242 4242 4242 is the canonical Luhn-valid test number.
    result = redaction.redact("Paid with card 4242 4242 4242 4242 today.")
    assert "4242 4242 4242 4242" not in result.text
    assert result.counts.get("CREDIT_CARD") == 1


def test_luhn_invalid_long_number_is_not_a_card():
    """Reference numbers are long too. The checksum keeps them out."""
    matches = redaction.detect("Reference 1234567812345678 for this shipment.")
    assert not any(m.type == "CREDIT_CARD" for m in matches)


def test_business_fields_survive_redaction():
    """The line that keeps the product working.

    Redacting invoice numbers and totals would destroy the extraction this
    service exists to perform, and they are not personal data.
    """
    text = "Invoice Number: INV-1024\nSubtotal: 14,000 EGP\nTotal: 15,000 EGP"
    result = redaction.redact(text)

    assert "INV-1024" in result.text
    assert "14,000" in result.text
    assert "15,000" in result.text


def test_dates_are_not_mistaken_for_phone_numbers():
    result = redaction.redact("Due Date: 2026-09-01 and effective 2026-01-01.")
    assert "2026-09-01" in result.text


def test_repeated_value_gets_distinct_placeholders():
    result = redaction.redact("Write to a@b.com or a@b.com again.")
    assert "[EMAIL_1]" in result.text
    assert "[EMAIL_2]" in result.text


def test_restore_reverses_redaction():
    original = "Contact billing@abccorp.example.com about invoice INV-1024."
    result = redaction.redact(original)
    assert result.restore(result.text) == original


def test_offsets_point_at_the_original_span():
    text = "Reach me at someone@example.com please."
    match = redaction.detect(text)[0]
    assert text[match.start : match.end] == match.value


def test_clean_text_is_returned_untouched():
    text = "This Agreement is between two companies."
    result = redaction.redact(text)
    assert result.text == text
    assert result.matches == []


def test_ip_address_octets_are_validated():
    assert any(m.type == "IP_ADDRESS" for m in redaction.detect("Host 10.20.30.40 responded."))
    assert not any(m.type == "IP_ADDRESS" for m in redaction.detect("Version 999.888.777.666"))


def test_pii_endpoint_withholds_values_by_default(client):
    body = client.post("/pii", json={"text": "Mail me at a@b.com"}).json()

    assert body["counts"] == {"EMAIL": 1}
    assert body["matches"][0]["value"] is None
    assert "[EMAIL_1]" in body["redacted_text"]


def test_pii_endpoint_returns_values_on_request(client):
    body = client.post(
        "/pii", json={"text": "Mail me at a@b.com", "include_values": True}
    ).json()
    assert body["matches"][0]["value"] == "a@b.com"


def test_mock_backend_does_not_redact(client, contract_text):
    """No egress, nothing to protect against - and readable local output."""
    body = client.post("/analysis/risk", json={"text": contract_text}).json()
    assert body["meta"]["redacted"] is False
