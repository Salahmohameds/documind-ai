"""Contract risk scoring.

These tests are the reason the score is defensible. An LLM-produced number
could not be tested this way at all - which is precisely why it is not one.
"""

from __future__ import annotations

from app.analysis import risk_rules


def test_score_is_reproducible(client, contract_text):
    """Same document, same score. Every time, on every pod."""
    scores = {
        client.post("/analysis/risk", json={"text": contract_text}).json()["score"]
        for _ in range(5)
    }
    assert len(scores) == 1


def test_findings_cite_the_clause_that_triggered_them(client, contract_text):
    body = client.post("/analysis/risk", json={"text": contract_text}).json()

    assert body["findings"], "the sample contract should trigger at least one rule"
    for finding in body["findings"]:
        assert finding["rule_id"].startswith("R")
        assert finding["severity"] in {"low", "medium", "high"}
        # A presence rule must quote the text it matched. Absence rules have
        # nothing to quote - the point is that the clause is not there.
        if finding["evidence"] is not None:
            assert finding["evidence"]["snippet"]
            assert finding["evidence"]["offset"] is not None


def test_scoring_block_makes_the_number_auditable(client, contract_text):
    scoring = client.post("/analysis/risk", json={"text": contract_text}).json()["scoring"]

    assert scoring["method"] == "deterministic-rules"
    assert scoring["rules_version"] == risk_rules.RULES_VERSION
    assert scoring["rules_evaluated"] == len(risk_rules.RULES)
    assert 0 <= scoring["rules_fired"] <= scoring["rules_evaluated"]


def test_points_reconcile_with_the_findings(client, contract_text):
    """Every point must be attributable to a rule that fired."""
    body = client.post("/analysis/risk", json={"text": contract_text}).json()
    assert body["scoring"]["points_scored"] == sum(f["weight"] for f in body["findings"])


def test_liability_cap_is_recognised_across_an_intervening_clause():
    """Regression: 'liability under this Agreement shall not exceed' is a cap.

    The first version of R02 required the words to be adjacent and so reported
    'no limitation of liability' on a contract that plainly had one.
    """
    text = (
        "This Agreement is between the Parties. Provider's total liability under "
        "this Agreement shall not exceed the fees paid in the preceding twelve months."
    )
    fired = {f.rule_id for f in risk_rules.score_document(text).findings}
    assert "R02" not in fired


def test_absent_liability_cap_is_flagged():
    text = "This Agreement is between the Parties and the Provider shall deliver services."
    fired = {f.rule_id for f in risk_rules.score_document(text).findings}
    assert "R02" in fired


def test_market_rate_interest_is_not_punitive():
    """Regression: the '5' inside '1.5%' must not read as a 5 % rate."""
    text = "Late payments shall accrue interest at a rate of 1.5% per month."
    assert "R06" not in {f.rule_id for f in risk_rules.score_document(text).findings}


def test_high_interest_is_punitive():
    text = "Late payments shall accrue interest at a rate of 4% per month."
    assert "R06" in {f.rule_id for f in risk_rules.score_document(text).findings}


def test_threshold_rule_scans_past_a_sub_threshold_match():
    """'net 30 ... net 90' must still fire: the first match is not the only one."""
    text = "Standard terms are net 30 days. For enterprise clients, net 90 days applies."
    assert "R05" in {f.rule_id for f in risk_rules.score_document(text).findings}


def test_payment_terms_at_sixty_days_do_not_fire():
    text = "Payment is due within 60 days of receipt of a valid invoice."
    assert "R05" not in {f.rule_id for f in risk_rules.score_document(text).findings}


def test_absence_rules_do_not_apply_to_non_contracts():
    """An invoice must not be scored as a contract with every clause missing."""
    result = risk_rules.score_document("Invoice Number: INV-1024\nTotal: 15,000 EGP")
    assert result.rules_fired == 0
    assert result.score == 0


def test_bands_follow_the_score(client, contract_text):
    body = client.post("/analysis/risk", json={"text": contract_text}).json()
    assert body["band"] == risk_rules.band_for(body["score"])
    assert 0 <= body["score"] <= 100


def test_explanation_can_be_skipped_without_losing_the_score(client, contract_text):
    """Load tests need the score without burning tokens on prose."""
    body = client.post(
        "/analysis/risk", json={"text": contract_text, "explain": False}
    ).json()

    assert body["score"] > 0
    assert body["explanation"]
    assert body["meta"]["usage"]["tokens_out"] == 0


def test_explanation_does_not_restate_a_different_score(client, contract_text):
    body = client.post("/analysis/risk", json={"text": contract_text}).json()
    assert str(body["score"]) in body["explanation"]


# --------------------------------------------------------------------------
# Per-category bands (database/schema.sql: risk_assessments)
# --------------------------------------------------------------------------
def test_categories_match_the_database_columns(client, contract_text):
    """risk_assessments stores financial/legal/operational as separate columns.

    Returning only a single band would have left role 5 unable to populate the
    table without inventing values.
    """
    body = client.post("/analysis/risk", json={"text": contract_text}).json()

    assert set(body["categories"]) == {"financial", "legal", "operational"}
    assert all(v in {"low", "medium", "high"} for v in body["categories"].values())


def test_every_finding_carries_a_category(client, contract_text):
    body = client.post("/analysis/risk", json={"text": contract_text}).json()
    for finding in body["findings"]:
        assert finding["category"] in {"financial", "legal", "operational"}


def test_category_band_is_the_worst_severity_in_that_category():
    """One uncapped-indemnity clause must outrank three minor findings."""
    text = "This Agreement between the Parties. Provider shall indemnify Client."
    result = risk_rules.score_document(text)

    legal = [f for f in result.findings if f.category == "legal"]
    assert any(f.severity == "high" for f in legal)
    assert result.categories["legal"] == "high"


def test_category_with_no_findings_is_low_not_unknown():
    """Every rule in that category ran and none matched - that is 'low'."""
    result = risk_rules.score_document("Invoice Number: INV-1024\nTotal: 15,000 EGP")
    assert result.categories == {"financial": "low", "legal": "low", "operational": "low"}


def test_every_rule_is_categorised():
    for rule in risk_rules.RULES:
        assert rule.category in {"financial", "legal", "operational"}
