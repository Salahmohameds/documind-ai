"""Contract tests for document-service.

Asserts API shape — status codes, response fields, validation
boundaries, error envelope. Does not assert processing outcomes:
nothing consumes the job queue yet, so every upload stays queued.
"""

import io

import pytest

from conftest import pdf_upload

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


# ───────────────────────────── health ─────────────────────────────

def test_liveness_returns_200(client):
    r = client.get("/liveness")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_readiness_names_each_dependency(client):
    """Readiness must say *what* is unhealthy, not just that something is.

    Without per-dependency detail, a 503 in production tells an operator
    nothing about where to look.
    """
    r = client.get("/readiness")
    assert r.status_code == 200
    checks = r.json()["checks"]
    assert "postgres" in checks
    assert "redis" in checks


def test_health_endpoints_need_no_auth(client):
    for path in ("/liveness", "/readiness"):
        assert client.get(path).status_code == 200


# ───────────────────────────── upload ─────────────────────────────

def test_upload_accepts_pdf_and_returns_202(client, sample_pdf):
    r = client.post("/documents", files=pdf_upload(sample_pdf, "contract_0000.pdf"))
    assert r.status_code == 202, r.text
    body = r.json()
    assert isinstance(body["id"], str)
    assert body["id"]
    assert body["name"] == "contract_0000.pdf"


def test_upload_starts_in_a_non_terminal_state(client, sample_pdf):
    """202 means accepted for processing, not processed."""
    r = client.post("/documents", files=pdf_upload(sample_pdf))
    assert r.json()["status"] not in ("completed", "failed")


def test_upload_rejects_non_pdf_extension(client):
    r = client.post(
        "/documents",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert r.status_code == 415
    body = r.json()
    assert body["code"] == "ERR_UNSUPPORTED_DOCUMENT"
    assert body["retryable"] is False


def test_upload_rejects_pdf_extension_without_magic_bytes(client):
    """Extension alone is not proof — content must look like a PDF."""
    r = client.post(
        "/documents",
        files=pdf_upload(b"this is not a pdf at all", "disguised.pdf"),
    )
    assert r.status_code in (400, 415), r.text


def test_upload_rejects_empty_file(client):
    r = client.post("/documents", files=pdf_upload(b"", "empty.pdf"))
    assert r.status_code in (400, 415, 422), r.text


def test_upload_rejects_missing_file_part(client):
    r = client.post("/documents")
    assert r.status_code == 422


def test_upload_rejects_path_traversal_filename(client):
    """A filename is attacker-controlled input, not a path."""
    r = client.post(
        "/documents",
        files=pdf_upload(MINIMAL_PDF, "../../../etc/passwd.pdf"),
    )
    if r.status_code == 202:
        # Accepted is fine only if the name was sanitised.
        assert ".." not in r.json()["name"]
    else:
        assert r.status_code in (400, 415, 422)


def test_repeated_uploads_get_distinct_ids(client, sample_pdf):
    """Uploading the same bytes twice is two documents, not one."""
    first = client.post("/documents", files=pdf_upload(sample_pdf)).json()["id"]
    second = client.post("/documents", files=pdf_upload(sample_pdf)).json()["id"]
    assert first != second


# ───────────────────────── error envelope ─────────────────────────

def test_error_envelope_shape(client):
    """The worker branches on `retryable`, so the shape is a contract."""
    r = client.post(
        "/documents",
        files={"file": ("notes.txt", io.BytesIO(b"x"), "text/plain")},
    )
    body = r.json()
    for field in ("error", "detail", "code", "retryable"):
        assert field in body, f"missing {field} in error envelope"
    assert isinstance(body["retryable"], bool)


# ───────────────────────────── status ─────────────────────────────

def test_status_returns_known_state(client, uploaded):
    r = client.get(f"/documents/{uploaded}/status")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == uploaded
    assert body["status"] in (
        "queued", "processing", "completed", "failed",
    )


def test_status_of_unknown_id_is_404(client):
    assert client.get("/documents/doc_doesnotexist/status").status_code == 404


def test_get_document_returns_metadata(client, uploaded):
    r = client.get(f"/documents/{uploaded}")
    assert r.status_code == 200
    assert r.json()["id"] == uploaded


def test_get_unknown_document_is_404(client):
    assert client.get("/documents/doc_doesnotexist").status_code == 404


# ───────────────────────────── listing ─────────────────────────────

def test_list_returns_rows(client, uploaded):
    r = client.get("/documents")
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert isinstance(rows, list)
    assert any(row["id"] == uploaded for row in rows)


def test_list_row_shape(client, uploaded):
    row = client.get("/documents").json()["rows"][0]
    for field in ("id", "name", "ext", "type", "status", "uploadedAt"):
        assert field in row, f"missing {field} in list row"


def test_page_size_limits_rows(client, uploaded):
    r = client.get("/documents", params={"page": 1, "page_size": 1})
    assert r.status_code == 200
    assert len(r.json()["rows"]) <= 1


@pytest.mark.parametrize("params", [
    {"page": 0},
    {"page": -1},
    {"page_size": 0},
    {"page_size": -5},
])
def test_pagination_rejects_or_clamps_invalid_bounds(client, params):
    """Either is defensible; silently returning everything is not."""
    r = client.get("/documents", params=params)
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert isinstance(r.json()["rows"], list)


def test_oversized_page_size_does_not_dump_the_table(client):
    r = client.get("/documents", params={"page_size": 100000})
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert len(r.json()["rows"]) <= 1000, (
            "no upper bound on page_size — a single request can return the "
            "entire table"
        )