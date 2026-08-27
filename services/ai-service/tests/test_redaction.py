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


# --------------------------------------------------------------------------
# National ID vs credit card
# --------------------------------------------------------------------------
def _types(value: str) -> list[str]:
    return [m.type for m in redaction.detect(f"Value: {value} on file.")]


def test_egyptian_national_id_is_not_a_credit_card():
    """Reported by a teammate, reproduced with this exact value.

    A 14-digit Egyptian national ID passes the Luhn checksum roughly one time
    in ten. CREDIT_CARD used to be evaluated first, so those IDs were labelled
    as card numbers - which is why it looked intermittent.
    """
    assert _types("28503150212349") == ["NATIONAL_ID"]


def test_egyptian_national_ids_across_centuries():
    assert _types("29001011234567") == ["NATIONAL_ID"]  # 2 -> born 1900s
    assert _types("30105212112345") == ["NATIONAL_ID"]  # 3 -> born 2000s


def test_saudi_national_id_is_recognised():
    assert _types("1234567890") == ["NATIONAL_ID"]


def test_real_cards_are_still_cards():
    assert _types("4242424242424242") == ["CREDIT_CARD"]  # Visa
    assert _types("378282246310005") == ["CREDIT_CARD"]  # Amex
    assert _types("5555555555554444") == ["CREDIT_CARD"]  # Mastercard


def test_fourteen_digit_diners_card_is_still_a_card():
    """Diners Club is 14 digits starting 36 - the same length as an Egyptian ID.

    It is not a valid ID structurally (36 is not a century digit), so the
    validators separate them without either one shadowing the other.
    """
    assert _types("36700102000000") == ["CREDIT_CARD"]


def test_malformed_id_is_still_redacted_as_unclassified():
    """The leak the strict validators would otherwise have opened.

    Tightening NATIONAL_ID made its label correct but meant a malformed or
    foreign identifier matched nothing at all. An unclassified long digit run
    is redacted anyway - the label just says we could not tell what it was.
    """
    assert _types("28503159912349") == ["ID_NUMBER"]  # governorate 99
    assert _types("29915011234567") == ["ID_NUMBER"]  # month 99
    assert _types("1234567812345678") == ["ID_NUMBER"]  # 16 digits, fails Luhn


def test_invalid_dates_are_rejected_as_national_ids():
    from app.redaction import _egypt_national_id_ok

    assert _egypt_national_id_ok("29001011234567") is True
    assert _egypt_national_id_ok("29002301234567") is False  # 30 February
    assert _egypt_national_id_ok("19001011234567") is False  # century digit 1
    assert _egypt_national_id_ok("2900101123456") is False  # 13 digits


def test_business_numbers_are_not_swallowed_by_the_safety_net():
    """The catch-all must not start eating invoice totals and order numbers."""
    for text in (
        "Invoice Number: INV-1024",
        "Total: 15,000 EGP",
        "Due Date: 2026-09-01",
        "Subtotal: 14,000 EGP",
    ):
        assert redaction.redact(text).matches == [], text
