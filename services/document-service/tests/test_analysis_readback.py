"""The analysis processing-service writes, read back through GET /documents/{id}.

The pipeline stores its results in three tables this service does not own. It
used to read none of them, so a fully processed document answered with
``risk: null``, ``fields: []`` and no findings while all of it sat in Postgres.
These tests pin the mapping, and in particular the parts of it that are lossy
on purpose — a missing field, a band that is not a number, an absent PII table.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_document_service
from app.main import app
from app.models import Document, ExtractedFields, RiskAssessment
from app.repositories.analysis import AnalysisRepository
from app.repositories.documents import DocumentRepository
from app.services.documents import DocumentService
from app.storage.local import LocalStorage
from tests.conftest import TestSession
from tests.test_documents import RecordingPublisher

DOC_ID = "doc_analysis_fixture"


# ---------------------------------------------------------------------------
# Fixtures — a document plus the rows the pipeline would have written.
# ---------------------------------------------------------------------------


def _seed_document(session) -> None:
    session.add(
        Document(
            document_id=DOC_ID,
            filename="invoice.pdf",
            document_type="INVOICE",
            status="INDEXED",
            uploaded_at=datetime.now(UTC),
        )
    )
    session.commit()


def _seed_fields(session) -> None:
    session.add(
        ExtractedFields(
            document_id=DOC_ID,
            fields={
                "invoice_number": {
                    "value": "4471",
                    "confidence": 0.9,
                    "evidence": {"snippet": "INVOICE #4471", "page": 2},
                },
                "vendor_name": {
                    "value": "Meridian Supply Co",
                    "confidence": 0.8,
                    "evidence": None,
                },
                # Looked for, not found. Counts toward the total, never shown.
                "tax": {"value": None, "confidence": 0.0, "evidence": None},
                "currency": {"value": "", "confidence": 0.0, "evidence": None},
            },
        )
    )
    session.commit()


def _seed_risk(session, **overrides) -> None:
    row = {
        "risk_score": 71,
        "financial_risk": "High",
        "legal_risk": "Medium",
        "operational_risk": "Low",
        "risk_reasons": [
            {
                "rule_id": "R06",
                "title": "Punitive late-payment interest",
                "severity": "low",
                "category": "financial",
                "evidence": {"snippet": "interest at 2% per month.", "page": 3},
            },
            {
                "rule_id": "R01",
                "title": "Uncapped liability",
                "severity": "high",
                "category": "legal",
                "evidence": {"snippet": "liability shall be unlimited", "page": 1},
            },
        ],
    }
    row.update(overrides)
    session.add(RiskAssessment(document_id=DOC_ID, **row))
    session.commit()


@pytest.fixture()
def analysis_client():
    session = TestSession()
    service = DocumentService(
        repository=DocumentRepository(session),
        analysis=AnalysisRepository(session),
        storage=LocalStorage("."),
        publisher=RecordingPublisher(),
    )
    app.dependency_overrides[get_document_service] = lambda: service
    with TestClient(app) as client:
        yield client, session
    session.close()
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Extracted fields
# ---------------------------------------------------------------------------


class TestExtractedFields:
    def test_only_found_fields_are_returned(self, analysis_client):
        client, session = analysis_client
        _seed_document(session)
        _seed_fields(session)

        body = client.get(f"/documents/{DOC_ID}").json()
        keys = [f["key"] for f in body["fields"]]

        assert keys == ["invoice_number", "vendor_name"]

    def test_expected_count_includes_the_misses(self, analysis_client):
        """"2 of 4" is the point of the total — the misses are what it counts."""
        client, session = analysis_client
        _seed_document(session)
        _seed_fields(session)

        body = client.get(f"/documents/{DOC_ID}").json()

        assert len(body["fields"]) == 2
        assert body["fieldsExpected"] == 4

    def test_field_carries_value_confidence_and_page(self, analysis_client):
        client, session = analysis_client
        _seed_document(session)
        _seed_fields(session)

        body = client.get(f"/documents/{DOC_ID}").json()
        found = {f["key"]: f for f in body["fields"]}

        assert found["invoice_number"]["value"] == "4471"
        assert found["invoice_number"]["confidence"] == pytest.approx(0.9)
        assert found["invoice_number"]["page"] == 2

    def test_missing_evidence_falls_back_to_page_one(self, analysis_client):
        """The extractor reports no page when it read the whole document."""
        client, session = analysis_client
        _seed_document(session)
        _seed_fields(session)

        body = client.get(f"/documents/{DOC_ID}").json()
        found = {f["key"]: f for f in body["fields"]}

        assert found["vendor_name"]["page"] == 1

    def test_no_extraction_row_is_empty_not_an_error(self, analysis_client):
        client, session = analysis_client
        _seed_document(session)

        response = client.get(f"/documents/{DOC_ID}")

        assert response.status_code == 200
        assert response.json()["fields"] == []
        assert response.json()["fieldsExpected"] == 0


# ---------------------------------------------------------------------------
# Risk, findings, verdict
# ---------------------------------------------------------------------------


class TestRisk:
    def test_score_and_flag_count_come_from_the_assessment(self, analysis_client):
        client, session = analysis_client
        _seed_document(session)
        _seed_risk(session)

        body = client.get(f"/documents/{DOC_ID}").json()

        assert body["risk"] == 71
        # Flags are the library's exception count; it must mean the same thing
        # here as it does there.
        assert body["flags"] == 2

    @pytest.mark.parametrize(
        ("score", "verdict"),
        [
            (0, "Auto-approved"),
            (33, "Auto-approved"),
            # 34 is the UI's own elevated threshold; a document at or above it
            # is what the dashboard's flagged panel selects for.
            (34, "Needs review"),
            (66, "Needs review"),
            (67, "Needs review"),
            (95, "Needs review"),
        ],
    )
    def test_verdict_uses_the_vocabulary_the_frontend_declares(
        self, analysis_client, score, verdict
    ):
        """`verdict` is a contract, not free text.

        `lib/types.ts` declares exactly three values and the dashboard filters
        on them. Emitting anything else empties that panel without failing.
        """
        client, session = analysis_client
        _seed_document(session)
        _seed_risk(session, risk_score=score)

        assert client.get(f"/documents/{DOC_ID}").json()["verdict"] == verdict

    def test_categories_report_the_band_and_a_matching_score(self, analysis_client):
        """The band is the measurement; the score must land inside its range.

        The UI derives Low/Medium/High from thresholds at 33 and 66, so a
        stand-in outside its own band would contradict the band beside it.
        """
        client, session = analysis_client
        _seed_document(session)
        _seed_risk(session)

        categories = client.get(f"/documents/{DOC_ID}").json()["riskCategories"]
        by_name = {c["name"]: c for c in categories}

        assert [c["name"] for c in categories] == ["Financial", "Legal", "Operational"]
        assert by_name["Financial"]["band"] == "High"
        assert by_name["Financial"]["score"] > 66
        assert by_name["Legal"]["band"] == "Medium"
        assert 33 < by_name["Legal"]["score"] <= 66
        assert by_name["Operational"]["band"] == "Low"
        assert by_name["Operational"]["score"] <= 33

    def test_findings_are_worst_first(self, analysis_client):
        client, session = analysis_client
        _seed_document(session)
        _seed_risk(session)

        findings = client.get(f"/documents/{DOC_ID}").json()["findings"]

        assert [f["severity"] for f in findings] == ["High", "Low"]
        assert findings[0]["id"] == "R01"
        assert findings[0]["title"] == "Uncapped liability"

    def test_finding_description_is_the_matched_text(self, analysis_client):
        """The rule fired because of this text — nothing else explains it better."""
        client, session = analysis_client
        _seed_document(session)
        _seed_risk(session)

        findings = client.get(f"/documents/{DOC_ID}").json()["findings"]

        assert findings[0]["description"] == "liability shall be unlimited"
        assert findings[0]["page"] == 1

    def test_malformed_reasons_do_not_break_the_read(self, analysis_client):
        client, session = analysis_client
        _seed_document(session)
        _seed_risk(session, risk_reasons=["not-an-object", {"title": "Bare"}])

        body = client.get(f"/documents/{DOC_ID}").json()

        assert len(body["findings"]) == 1
        assert body["findings"][0]["title"] == "Bare"
        # No severity recorded is not evidence of a severe problem.
        assert body["findings"][0]["severity"] == "Low"

    def test_failed_run_reports_its_score_but_no_verdict(self, analysis_client):
        """Scored on the way to failing is not the same as judged."""
        client, session = analysis_client
        session.add(
            Document(
                document_id=DOC_ID,
                filename="broken.pdf",
                document_type="INVOICE",
                status="FAILED",
                uploaded_at=datetime.now(UTC),
            )
        )
        session.commit()
        _seed_risk(session, risk_score=12)

        body = client.get(f"/documents/{DOC_ID}").json()

        assert body["status"] == "failed"
        assert body["risk"] == 12
        assert body["verdict"] == "Pending"

    def test_no_risk_row_leaves_risk_null(self, analysis_client):
        client, session = analysis_client
        _seed_document(session)

        body = client.get(f"/documents/{DOC_ID}").json()

        assert body["risk"] is None
        assert body["findings"] == []
        assert body["riskCategories"] == []
        assert body["flags"] == 0


# ---------------------------------------------------------------------------
# Classification, and what is genuinely not stored
# ---------------------------------------------------------------------------


class TestClassification:
    def test_label_comes_from_the_document_row(self, analysis_client):
        client, session = analysis_client
        _seed_document(session)

        classification = client.get(f"/documents/{DOC_ID}").json()["classification"]

        assert classification["label"] == "Invoice"

    def test_confidence_is_zero_because_it_is_not_stored(self, analysis_client):
        """processing-service keeps the winning label and discards the rest.

        Reported as zero and empty rather than invented — if this ever becomes
        non-zero, something started persisting it and this test should change.
        """
        client, session = analysis_client
        _seed_document(session)

        classification = client.get(f"/documents/{DOC_ID}").json()["classification"]

        assert classification["confidence"] == 0.0
        assert classification["runnerUp"] == ""

    def test_unclassified_document_has_no_classification_block(self, analysis_client):
        client, session = analysis_client
        session.add(
            Document(
                document_id=DOC_ID,
                filename="mystery.pdf",
                document_type="UNKNOWN",
                status="UPLOADED",
                uploaded_at=datetime.now(UTC),
            )
        )
        session.commit()

        assert client.get(f"/documents/{DOC_ID}").json()["classification"] is None

    def test_pii_is_empty_because_nothing_produces_it(self, analysis_client):
        """There is no PII stage and no table — the pipeline never calls /pii.

        Pinned so the empty list is understood as a known gap rather than read
        as "this document has no PII".
        """
        client, session = analysis_client
        _seed_document(session)
        _seed_risk(session)

        assert client.get(f"/documents/{DOC_ID}").json()["pii"] == []
