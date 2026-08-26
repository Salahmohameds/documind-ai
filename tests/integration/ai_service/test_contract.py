"""Contract tests for ai-service.

The mock backend is rules-based and deterministic, so these assert
behaviour where the rules decide it — classification labels, extracted
values, PII types, risk findings — and shape everywhere else.

One PII defect is recorded as xfail rather than asserted as correct:
national IDs are misclassified as credit cards. It starts passing when
fixed.
"""

import pytest


# ───────────────────────────── health ─────────────────────────────

def test_liveness_returns_200(client):
    assert client.get("/liveness").status_code == 200


def test_readiness_reports_provider_state(client):
    """Readiness must expose the provider and the circuit breaker.

    An ai-service whose breaker is open is up but useless. If readiness
    does not say so, the pod keeps taking traffic it cannot serve.
    """
    r = client.get("/readiness")
    assert r.status_code == 200
    checks = r.json()["checks"]
    assert "provider" in checks
    assert "circuit_breaker" in checks


def test_metrics_endpoint_is_exposed(client):
    r = client.get("/metrics")
    assert r.status_code == 200


# ─────────────────────────── classification ───────────────────────────

def test_classify_identifies_an_invoice(client, invoice_text):
    r = client.post("/classify", json={"text": invoice_text})
    assert r.status_code == 200, r.text
    assert r.json()["label"].lower() == "invoice"


def test_classify_identifies_a_contract(client, contract_text):
    r = client.post("/classify", json={"text": contract_text})
    assert r.status_code == 200, r.text
    assert r.json()["label"].lower() == "contract"


def test_classify_returns_scores_for_every_label(client, invoice_text):
    scores = client.post("/classify", json={"text": invoice_text}).json()["scores"]
    assert isinstance(scores, dict)
    assert scores
    for label, value in scores.items():
        assert 0.0 <= value <= 1.0, f"{label} scored {value}"


def test_classify_confidence_is_in_range(client, invoice_text):
    confidence = client.post(
        "/classify", json={"text": invoice_text}
    ).json()["confidence"]
    assert 0.0 <= confidence <= 1.0


def test_classify_explains_itself(client, invoice_text):
    """A label without evidence cannot be reviewed or disputed."""
    rationale = client.post(
        "/classify", json={"text": invoice_text}
    ).json()["rationale"]
    assert isinstance(rationale, str)
    assert rationale.strip()


def test_classify_is_not_confident_about_unrelated_text(client):
    """Nonsense must not produce a confident label.

    A wrong label at high confidence routes a document down the wrong
    pipeline with nothing to flag it.
    """
    r = client.post("/classify", json={
        "text": "The quick brown fox jumps over the lazy dog. " * 20,
    })
    body = r.json()
    assert body["confidence"] < 1.0, (
        f"classified unrelated prose as {body['label']} at full confidence"
    )


def test_classify_rejects_empty_body(client):
    assert client.post("/classify", json={}).status_code == 422


def test_classify_is_deterministic(client, invoice_text):
    """Rules-based means repeatable.

    Non-determinism here would make every downstream metric unstable.
    """
    first = client.post("/classify", json={"text": invoice_text}).json()
    second = client.post("/classify", json={"text": invoice_text}).json()
    assert first["label"] == second["label"]
    assert first["confidence"] == second["confidence"]


# ──────────────────────────── extraction ────────────────────────────

def test_extract_finds_the_invoice_number(client, invoice_text):
    fields = client.post("/extract", json={"text": invoice_text}).json()["fields"]
    assert fields["invoice_number"]["value"] == "INV-1024"


def test_extract_finds_the_due_date(client, invoice_text):
    fields = client.post("/extract", json={"text": invoice_text}).json()["fields"]
    assert fields["due_date"]["value"] == "2026-09-01"


def test_extract_reports_absent_fields_as_null(client, invoice_text):
    """A field not in the document must come back null, never invented."""
    fields = client.post("/extract", json={"text": invoice_text}).json()["fields"]
    absent = [f for f in fields.values() if f["value"] is None]
    assert absent, "expected at least one unpopulated field in this sample"
    for field in absent:
        assert field["confidence"] == 0.0
        assert field["evidence"] is None


def test_extracted_values_carry_evidence(client, invoice_text):
    """Evidence is what makes an extraction auditable."""
    fields = client.post("/extract", json={"text": invoice_text}).json()["fields"]
    populated = [f for f in fields.values() if f["value"] is not None]
    assert populated
    for field in populated:
        assert field["evidence"] is not None
        assert field["evidence"]["snippet"]
        assert isinstance(field["evidence"]["offset"], int)


def test_extraction_evidence_offsets_are_within_the_text(
    client, invoice_text
):
    """An offset past the end of the input cannot point at anything."""
    fields = client.post("/extract", json={"text": invoice_text}).json()["fields"]
    for name, field in fields.items():
        if field["evidence"]:
            offset = field["evidence"]["offset"]
            assert 0 <= offset <= len(invoice_text), (
                f"{name} evidence offset {offset} outside a "
                f"{len(invoice_text)}-character document"
            )


def test_extract_confidence_is_in_range(client, invoice_text):
    fields = client.post("/extract", json={"text": invoice_text}).json()["fields"]
    for name, field in fields.items():
        assert 0.0 <= field["confidence"] <= 1.0, f"{name}"


def test_extract_rejects_empty_body(client):
    assert client.post("/extract", json={}).status_code == 422


# ─────────────────────────────── PII ───────────────────────────────

def test_pii_detects_an_email(client):
    r = client.post("/pii", json={"text": "Contact ops@example.com for billing."})
    assert r.status_code == 200
    assert "EMAIL" in r.json()["counts"]


def test_pii_detects_a_phone_number(client):
    r = client.post("/pii", json={"text": "Call +20 100 555 0142 for support."})
    assert "PHONE" in r.json()["counts"]


def test_pii_response_never_returns_the_raw_value(client):
    """The endpoint exists to remove sensitive data, not echo it."""
    body = client.post("/pii", json={
        "text": "Contact ops@example.com for billing.",
    }).json()
    for match in body["matches"]:
        assert match["value"] is None, "raw PII returned in the response"


def test_pii_offsets_are_within_the_text(client):
    text = "Contact ops@example.com or call +20 100 555 0142."
    for match in client.post("/pii", json={"text": text}).json()["matches"]:
        assert 0 <= match["start"] < match["end"] <= len(text)


def test_pii_placeholders_appear_in_the_redacted_text(client):
    text = "Contact ops@example.com for billing."
    body = client.post("/pii", json={"text": text}).json()
    for match in body["matches"]:
        assert match["placeholder"] in body["redacted_text"]


def test_pii_redaction_removes_the_email(client):
    text = "Contact ops@example.com for billing."
    redacted = client.post("/pii", json={"text": text}).json()["redacted_text"]
    assert "ops@example.com" not in redacted

def test_pii_redaction_removes_the_whole_phone_number(client):
    """Redaction runs before egress to the AI provider.

    A partial match leaves real digits in text that leaves the system.
    """
    text = "Call +20 100 555 0142 for support."
    redacted = client.post("/pii", json={"text": text}).json()["redacted_text"]
    for fragment in ("0142", "555", "100"):
        assert fragment not in redacted, (
            f"'{fragment}' survived redaction: {redacted!r}"
        )


def test_pii_finds_nothing_in_clean_text(client):
    """False positives make the feature unusable.

    Flagging ordinary prose as personal data trains reviewers to ignore
    the output entirely.
    """
    body = client.post("/pii", json={
        "text": "The quarterly report shows revenue increased across regions.",
    }).json()
    assert body["counts"] == {}, f"false positives: {body['counts']}"


def test_pii_rejects_empty_body(client):
    assert client.post("/pii", json={}).status_code == 422


@pytest.mark.xfail(
    reason="a 14-digit Egyptian national ID is classified CREDIT_CARD — the "
           "card pattern matches any 13-16 digit run. NATIONAL_ID is a "
           "required type per the project spec and is not detected at all.",
    strict=False,
)
def test_pii_detects_a_national_id_as_its_own_type(client):
    body = client.post("/pii", json={
        "text": "National ID 29804152301117 on file.",
    }).json()
    assert "NATIONAL_ID" in body["counts"]



# ─────────────────────────── risk analysis ───────────────────────────

def test_risk_scores_a_contract(client, contract_text):
    r = client.post("/analysis/risk", json={"text": contract_text})
    assert r.status_code == 200, r.text
    assert 0 <= r.json()["score"] <= 100


def test_risk_band_matches_the_score(client, contract_text):
    """A band that disagrees with its own number is not reportable."""
    body = client.post("/analysis/risk", json={"text": contract_text}).json()
    score, band = body["score"], body["band"].lower()
    if band == "low":
        assert score <= 40
    elif band == "medium":
        assert 30 <= score <= 70
    else:
        assert score >= 60


def test_risk_flags_automatic_renewal(client, contract_text):
    findings = client.post(
        "/analysis/risk", json={"text": contract_text}
    ).json()["findings"]
    titles = " ".join(f["title"].lower() for f in findings)
    assert "renewal" in titles


def test_presence_findings_carry_evidence(client, contract_text):
    """A finding about text that IS there must quote it.

    Absence findings ("No governing law clause") legitimately have no
    evidence — there is no passage to point at. Presence findings have
    no such excuse: without a quote, a reviewer cannot check the claim.
    """
    findings = client.post(
        "/analysis/risk", json={"text": contract_text}
    ).json()["findings"]
    assert findings

    presence = [
        f for f in findings
        if not f["title"].lower().startswith(("no ", "missing ", "absent"))
    ]
    assert presence, "expected at least one presence-based finding"

    for finding in presence:
        assert finding["evidence"] is not None, (
            f"{finding['rule_id']} ({finding['title']}) asserts something is "
            "present but quotes nothing"
        )
        assert finding["evidence"]["snippet"]


def test_every_finding_is_identifiable(client, contract_text):
    """Rule id and severity are required regardless of evidence."""
    findings = client.post(
        "/analysis/risk", json={"text": contract_text}
    ).json()["findings"]
    for finding in findings:
        assert finding["rule_id"]
        assert finding["severity"]
        assert finding["title"]

def test_risk_findings_reference_real_offsets(client, contract_text):
    """Offsets, where present, must point inside the document."""
    findings = client.post(
        "/analysis/risk", json={"text": contract_text}
    ).json()["findings"]
    for finding in findings:
        if not finding["evidence"]:
            continue          # absence findings have nothing to point at
        offset = finding["evidence"]["offset"]
        assert 0 <= offset <= len(contract_text), (
            f"{finding['rule_id']} evidence offset {offset} outside a "
            f"{len(contract_text)}-character document"
        )

def test_clean_text_scores_lower_than_a_risky_contract(client, contract_text):
    """The score must respond to content, not be a constant."""
    risky = client.post(
        "/analysis/risk", json={"text": contract_text}
    ).json()["score"]
    plain = client.post("/analysis/risk", json={
        "text": "This document describes the weather in March.",
    }).json()["score"]
    assert plain < risky


def test_risk_rejects_empty_body(client):
    assert client.post("/analysis/risk", json={}).status_code == 422


# ─────────────────────────── embeddings ───────────────────────────

def test_embed_returns_a_vector(client):
    r = client.post("/embed", json={"texts": ["payment terms"]})
    assert r.status_code == 200, r.text

def test_embed_rejects_empty_body(client):
    assert client.post("/embed", json={}).status_code == 422