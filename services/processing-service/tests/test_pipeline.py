"""The orchestration, end to end, against mocked ai-service and search-service.

The behaviours that carry real risk and are therefore pinned here:

* the lowercase→uppercase mappings that the database CHECK constraints demand;
* graded failure — an enrichment stage may fail without failing the job, but a
  spine stage must fail it;
* ``meta.degraded`` propagating into a completed-with-caveats outcome.
"""

from __future__ import annotations

import httpx
import pytest

from app.clients.ai import AIServiceClient
from app.clients.search import SearchServiceClient
from app.database import session_scope
from app.errors import DocumentNotFoundError, ProcessingError
from app.models import (
    Document,
    DocumentSummary,
    ExtractedFields,
    ProcessingJob,
    RiskAssessment,
)
from app.pipeline import JobEvent, ProcessingPipeline
from app.repositories.jobs import to_document_type, to_risk_band
from app.storage.local import LocalDocumentReader

from tests.conftest import DOCUMENT_ID

JOB_ID = "1724692800000-0"


@pytest.fixture
def storage(tmp_path, sample_pdf):
    root = tmp_path / "storage"
    (root / "documents").mkdir(parents=True)
    (root / "documents" / f"{DOCUMENT_ID}.pdf").write_bytes(sample_pdf)
    return LocalDocumentReader(str(root))


@pytest.fixture
def seeded_job(seeded_document):
    """The job row the consumer would have claimed before the pipeline runs."""
    from datetime import UTC, datetime

    with session_scope() as session:
        session.add(
            ProcessingJob(
                job_id=JOB_ID,
                document_id=DOCUMENT_ID,
                status="PROCESSING",
                attempt=1,
                queued_at=datetime.now(UTC),
            )
        )
    return DOCUMENT_ID


@pytest.fixture
def pipeline(storage, upstream, seeded_job):
    ai = AIServiceClient()
    search = SearchServiceClient()
    # Swap in the mock transport, keeping the real client, breaker and retry
    # code in the path — the point is to test our behaviour, not httpx's.
    ai._client = httpx.AsyncClient(
        transport=upstream.transport(), base_url="http://ai-service:8080"
    )
    search._client = httpx.AsyncClient(
        transport=upstream.transport(), base_url="http://search-service:8080"
    )
    return ProcessingPipeline(reader=storage, ai_client=ai, search_client=search)


@pytest.fixture
def event():
    return JobEvent(
        job_id=JOB_ID,
        document_id=DOCUMENT_ID,
        storage_key=f"documents/{DOCUMENT_ID}.pdf",
        filename="contract.pdf",
        attempt=1,
    )


# --------------------------------------------------------------------------
# Happy path
# --------------------------------------------------------------------------
async def test_full_pipeline_persists_every_result(pipeline, event, upstream):
    result = await pipeline.run(event)

    assert result.degraded is False
    assert result.skipped_stages == []
    assert result.chunks_indexed == 3
    assert result.page_count == 1

    # Every downstream endpoint was called exactly once.
    assert sorted(upstream.calls) == [
        "/analysis/risk",
        "/classify",
        "/extract",
        "/index",
        "/summarize",
    ]

    with session_scope() as session:
        document = session.get(Document, DOCUMENT_ID)
        # 'contract' from ai-service, uppercased for the CHECK constraint.
        assert document.document_type == "CONTRACT"

        assert session.get(ExtractedFields, DOCUMENT_ID).fields["total"]["value"] == (
            "250000"
        )

        summary = session.get(DocumentSummary, DOCUMENT_ID)
        assert "Acme" in summary.summary
        assert summary.key_points == [
            "Net 30 payment terms",
            "Auto-renews annually",
        ]

        risk = session.get(RiskAssessment, DOCUMENT_ID)
        assert risk.risk_score == 62
        # Title case, again for the CHECK constraint.
        assert (risk.financial_risk, risk.legal_risk, risk.operational_risk) == (
            "Low",
            "High",
            "Medium",
        )
        assert risk.risk_reasons[0]["rule_id"] == "AUTO_RENEWAL"


async def test_classification_result_steers_the_later_calls(pipeline, event):
    """/extract and /summarize receive the type /classify produced.

    Otherwise ai-service classifies the same text three more times.
    """
    sent: list[dict] = []
    original = pipeline._ai.post_json

    async def capture(path, payload, *, operation):
        sent.append({"path": path, "payload": payload})
        return await original(path, payload, operation=operation)

    pipeline._ai.post_json = capture
    await pipeline.run(event)

    for call in sent:
        if call["path"] in ("/extract", "/summarize", "/analysis/risk"):
            assert call["payload"]["document_type"] == "contract"


# --------------------------------------------------------------------------
# Graded failure
# --------------------------------------------------------------------------
@pytest.mark.parametrize("stage_path", ["/classify", "/extract", "/summarize", "/analysis/risk"])
async def test_enrichment_failure_does_not_fail_the_job(pipeline, event, upstream, stage_path):
    """A dead AI stage still leaves a searchable, indexed document."""
    upstream.failures[stage_path] = 503

    result = await pipeline.run(event)

    assert result.skipped_stages != []
    # The spine still ran: the document is indexed and therefore findable.
    assert result.chunks_indexed == 3
    assert "/index" in upstream.calls


async def test_index_failure_fails_the_job(pipeline, event, upstream):
    """Indexing is spine: without it the document is invisible to search."""
    upstream.failures["/index"] = 503

    with pytest.raises(ProcessingError) as excinfo:
        await pipeline.run(event)

    # Retryable, so the consumer leaves it pending rather than dead-lettering.
    assert excinfo.value.retryable is True


async def test_missing_object_fails_the_job_terminally(pipeline, upstream):
    event = JobEvent(
        job_id=JOB_ID,
        document_id=DOCUMENT_ID,
        storage_key="documents/absent.pdf",
        filename="absent.pdf",
        attempt=1,
    )

    with pytest.raises(DocumentNotFoundError) as excinfo:
        await pipeline.run(event)

    assert excinfo.value.retryable is False
    # Nothing downstream was called for a document we could not even read.
    assert upstream.calls == []


async def test_classification_failure_leaves_the_type_unknown(pipeline, event, upstream):
    upstream.failures["/classify"] = 503

    result = await pipeline.run(event)

    assert result.document_type == "UNKNOWN"
    with session_scope() as session:
        assert session.get(Document, DOCUMENT_ID).document_type == "UNKNOWN"


# --------------------------------------------------------------------------
# Degraded outcomes
# --------------------------------------------------------------------------
async def test_degraded_ai_response_marks_the_job_degraded(pipeline, event, upstream):
    """ai-service says it fell back to a local result; the job records that."""
    upstream.degraded_paths.add("/analysis/risk")

    result = await pipeline.run(event)

    assert result.degraded is True


async def test_insufficient_text_does_not_store_a_summary(pipeline, event, upstream):
    """Storing ai-service's 'there was not enough text' as a summary is worse
    than storing nothing."""
    from tests.conftest import AI_RESPONSES

    original = AI_RESPONSES["/summarize"]
    AI_RESPONSES["/summarize"] = lambda: {
        **original(),
        "insufficient_text": True,
        "summary": "",
    }
    try:
        result = await pipeline.run(event)
    finally:
        AI_RESPONSES["/summarize"] = original

    assert "summarize" in result.skipped_stages
    with session_scope() as session:
        assert session.get(DocumentSummary, DOCUMENT_ID) is None


# --------------------------------------------------------------------------
# The mappings, directly
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("invoice", "INVOICE"),
        ("contract", "CONTRACT"),
        ("unknown", "UNKNOWN"),
        ("CONTRACT", "CONTRACT"),
        # An unexpected label is a classifier problem, not a reason to throw a
        # CHECK-constraint violation from deep inside a job.
        ("receipt", "UNKNOWN"),
        (None, "UNKNOWN"),
    ],
)
def test_document_type_mapping(label, expected):
    assert to_document_type(label) == expected


@pytest.mark.parametrize(
    ("band", "expected"),
    [("low", "Low"), ("medium", "Medium"), ("high", "High"), (None, None)],
)
def test_risk_band_mapping(band, expected):
    assert to_risk_band(band) == expected
