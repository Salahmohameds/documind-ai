"""Bulk delete and bulk reprocess tests.

Covers:
- Bulk delete with valid IDs → documents removed
- Bulk delete with nonexistent IDs → reported in failed list
- Bulk delete with mix of valid and nonexistent IDs
- Bulk reprocess with valid IDs → status reset to queued
- Bulk reprocess publishes the same Redis event payload as upload
- Bulk reprocess with nonexistent IDs → reported in failed list
- Empty ids list returns zero requested
"""

from __future__ import annotations

from collections.abc import Mapping

import redis
import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_document_service
from app.main import app
from app.repositories.analysis import AnalysisRepository
from app.repositories.documents import DocumentRepository
from app.services.documents import DocumentService
from app.storage.local import LocalStorage
from tests.conftest import TestSession


class RecordingPublisher:
    """Captures Redis events for assertions, matching test_documents.py."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.events: list[dict[str, str]] = []

    def publish_document(self, fields: Mapping[str, str]) -> str:
        if self.fail:
            raise redis.ConnectionError("Redis is unavailable")
        self.events.append(dict(fields))
        return "1-0"


def _pdf_bytes() -> bytes:
    return b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


@pytest.fixture()
def bulk_client(tmp_path):
    """Wire up a test client with recording publisher and tmp storage."""
    session = TestSession()
    publisher = RecordingPublisher()
    service = DocumentService(
        repository=DocumentRepository(session),
        analysis=AnalysisRepository(session),
        storage=LocalStorage(str(tmp_path)),
        publisher=publisher,
    )
    app.dependency_overrides[get_document_service] = lambda: service
    with TestClient(app) as client:
        yield client, publisher, service, session
    session.close()
    app.dependency_overrides.clear()


def _upload(client: TestClient) -> str:
    """Upload a PDF and return the document ID."""
    r = client.post(
        "/documents",
        files={"file": ("report.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert r.status_code == 202
    return r.json()["id"]


# ── Bulk Delete ─────────────────────────────────────────────────────────


class TestBulkDelete:
    def test_delete_valid_ids(self, bulk_client):
        client, publisher, service, _ = bulk_client
        doc_id = _upload(client)

        r = client.request("DELETE", "/documents", json={"ids": [doc_id]})

        assert r.status_code == 200
        data = r.json()
        assert data["requested"] == 1
        assert doc_id in data["succeeded"]
        assert data["failed"] == []

        # Verify the document is actually gone.
        listed = client.get("/documents")
        assert listed.json()["total"] == 0

    def test_delete_nonexistent_ids(self, bulk_client):
        client, *_ = bulk_client

        r = client.request(
            "DELETE", "/documents", json={"ids": ["nonexistent-1", "nonexistent-2"]}
        )

        assert r.status_code == 200
        data = r.json()
        assert data["requested"] == 2
        assert data["succeeded"] == []
        assert len(data["failed"]) == 2
        assert data["failed"][0]["id"] == "nonexistent-1"
        assert data["failed"][0]["reason"] == "Document not found"

    def test_delete_mix_of_valid_and_nonexistent(self, bulk_client):
        client, *_ = bulk_client
        doc_id = _upload(client)

        r = client.request(
            "DELETE", "/documents", json={"ids": [doc_id, "ghost-id"]}
        )

        assert r.status_code == 200
        data = r.json()
        assert data["requested"] == 2
        assert doc_id in data["succeeded"]
        assert len(data["failed"]) == 1
        assert data["failed"][0]["id"] == "ghost-id"

    def test_delete_empty_ids(self, bulk_client):
        client, *_ = bulk_client

        r = client.request("DELETE", "/documents", json={"ids": []})

        assert r.status_code == 200
        data = r.json()
        assert data["requested"] == 0
        assert data["succeeded"] == []
        assert data["failed"] == []


# ── Bulk Reprocess ──────────────────────────────────────────────────────


class TestBulkReprocess:
    def test_reprocess_valid_ids_resets_to_queued(self, bulk_client):
        client, publisher, service, _ = bulk_client
        doc_id = _upload(client)
        publisher.events.clear()  # Clear the upload event.

        r = client.post("/documents/reprocess", json={"ids": [doc_id]})

        assert r.status_code == 200
        data = r.json()
        assert data["requested"] == 1
        assert doc_id in data["succeeded"]
        assert data["failed"] == []

        # Verify the document status is back to queued.
        status = client.get(f"/documents/{doc_id}/status")
        assert status.json()["status"] == "queued"

    def test_reprocess_publishes_same_event_as_upload(self, bulk_client):
        """The Redis event from reprocess must match the upload event payload."""
        client, publisher, service, _ = bulk_client
        doc_id = _upload(client)

        # Capture the upload event for comparison.
        assert len(publisher.events) == 1
        upload_event = publisher.events[0]

        publisher.events.clear()
        client.post("/documents/reprocess", json={"ids": [doc_id]})

        assert len(publisher.events) == 1
        reprocess_event = publisher.events[0]

        # Both events must have the exact same keys.
        assert set(reprocess_event.keys()) == set(upload_event.keys())

        # The critical fields must match.
        assert reprocess_event["event_version"] == "1"
        assert reprocess_event["document_id"] == doc_id
        assert reprocess_event["storage_key"] == upload_event["storage_key"]
        assert reprocess_event["filename"] == upload_event["filename"]
        assert reprocess_event["content_type"] == "application/pdf"

    def test_reprocess_nonexistent_ids(self, bulk_client):
        client, *_ = bulk_client

        r = client.post(
            "/documents/reprocess", json={"ids": ["ghost-1", "ghost-2"]}
        )

        assert r.status_code == 200
        data = r.json()
        assert data["requested"] == 2
        assert data["succeeded"] == []
        assert len(data["failed"]) == 2
        assert data["failed"][0]["reason"] == "Document not found"

    def test_reprocess_empty_ids(self, bulk_client):
        client, publisher, *_ = bulk_client
        publisher.events.clear()

        r = client.post("/documents/reprocess", json={"ids": []})

        assert r.status_code == 200
        data = r.json()
        assert data["requested"] == 0
        assert data["succeeded"] == []
        assert data["failed"] == []
        assert publisher.events == []

    def test_reprocess_mix_of_valid_and_nonexistent(self, bulk_client):
        client, publisher, *_ = bulk_client
        doc_id = _upload(client)
        publisher.events.clear()

        r = client.post(
            "/documents/reprocess", json={"ids": [doc_id, "ghost-id"]}
        )

        assert r.status_code == 200
        data = r.json()
        assert data["requested"] == 2
        assert doc_id in data["succeeded"]
        assert len(data["failed"]) == 1
        assert data["failed"][0]["id"] == "ghost-id"
        # Only one event should be published (for the valid document).
        assert len(publisher.events) == 1
