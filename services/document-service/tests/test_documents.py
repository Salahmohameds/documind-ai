"""M1 API tests covering upload, persistence, queueing, and failure behavior."""

from __future__ import annotations

from collections.abc import Mapping

import redis
import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_document_service
from app.main import app
from app.repositories.documents import DocumentRepository
from app.services.documents import DocumentService
from app.storage.local import LocalStorage
from tests.conftest import TestSession


class RecordingPublisher:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.events: list[dict[str, str]] = []

    def publish_document(self, fields: Mapping[str, str]) -> str:
        if self.fail:
            raise redis.ConnectionError("Redis is unavailable")
        self.events.append(dict(fields))
        return "1-0"


@pytest.fixture()
def document_client(tmp_path):
    session = TestSession()
    publisher = RecordingPublisher()
    service = DocumentService(
        repository=DocumentRepository(session),
        storage=LocalStorage(str(tmp_path)),
        publisher=publisher,
    )
    app.dependency_overrides[get_document_service] = lambda: service
    with TestClient(app) as client:
        yield client, publisher, service
    session.close()
    app.dependency_overrides.clear()


def _pdf_bytes() -> bytes:
    return b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def test_upload_persists_then_publishes_a_storage_key(document_client):
    client, publisher, _service = document_client

    response = client.post(
        "/documents",
        files={"file": ("invoice.pdf", _pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["id"].startswith("doc_")
    assert body["status"] == "queued"
    assert body["progress"] is None
    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert event["document_id"] == body["id"]
    assert event["storage_key"] == f"documents/{body['id']}.pdf"
    assert "file_path" not in event

    listed = client.get("/documents")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    detail = client.get(f"/documents/{body['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == body["id"]

    status = client.get(f"/documents/{body['id']}/status")
    assert status.status_code == 200
    assert status.json()["status"] == "queued"


def test_rejects_non_pdf_before_persistence_or_queueing(document_client):
    client, publisher, _service = document_client

    response = client.post(
        "/documents",
        files={"file": ("notes.txt", b"not a PDF", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["code"] == "ERR_UNSUPPORTED_DOCUMENT"
    assert publisher.events == []
    assert client.get("/documents").json()["total"] == 0


def test_rejects_pdf_extension_without_pdf_signature(document_client):
    client, publisher, _service = document_client

    response = client.post(
        "/documents",
        files={"file": ("not-really.pdf", b"plain text", "application/pdf")},
    )

    assert response.status_code == 415
    assert publisher.events == []


def test_marks_document_failed_and_returns_503_when_redis_fails(document_client):
    client, publisher, service = document_client
    publisher.fail = True

    response = client.post(
        "/documents",
        files={"file": ("invoice.pdf", _pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "ERR_QUEUE_UNAVAILABLE"
    assert response.json()["retryable"] is True

    page = service.list(page=1, page_size=10)
    assert page.total == 1
    document_id = page.rows[0].id
    status = client.get(f"/documents/{document_id}/status")
    assert status.status_code == 200
    assert status.json()["status"] == "failed"
    assert status.json()["error"]["retryable"] is True
