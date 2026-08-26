"""Upload validation against malformed documents.

The happy-path corpus proves the service accepts good input. These
prove it refuses bad input — and, where it accepts, that it does so
safely.

Fixtures are generated, not committed. Build them with
tests/fixtures/generator/edge_cases.py.
"""

import io
import os

import pytest

EDGE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "fixtures", "edge-cases",
)


def edge_case(name):
    path = os.path.join(EDGE_DIR, name)
    if not os.path.exists(path):
        pytest.skip(
            "edge cases not generated — run "
            "tests/fixtures/generator/edge_cases.py"
        )
    with open(path, "rb") as f:
        return f.read()


def upload(client, content, filename):
    return client.post(
        "/documents",
        files={"file": (filename, io.BytesIO(content), "application/pdf")},
    )


# ───────────────────── rejected at the door ─────────────────────

def test_zero_byte_file_is_rejected(client):
    r = upload(client, edge_case("empty.pdf"), "empty.pdf")
    assert r.status_code in (400, 415, 422), r.text


def test_text_file_named_pdf_is_rejected(client):
    """Extension is a claim, not evidence."""
    r = upload(client, edge_case("not_a_pdf.pdf"), "report.pdf")
    assert r.status_code in (400, 415), r.text


def test_oversized_file_is_rejected(client):
    """Above the cap the request must be refused, not buffered."""
    r = upload(client, edge_case("oversized.pdf"), "huge.pdf")
    assert r.status_code in (400, 413, 415, 422), r.text


def test_rejections_use_the_error_envelope(client):
    """A rejection the worker cannot parse is a rejection that gets retried."""
    r = upload(client, edge_case("not_a_pdf.pdf"), "report.pdf")
    body = r.json()
    for field in ("error", "detail", "code", "retryable"):
        assert field in body, f"missing {field}"
    assert body["retryable"] is False, (
        "a malformed file will be malformed on retry — marking it retryable "
        "puts it in a loop"
    )


# ────────────────── accepted, must fail downstream ──────────────────

def test_truncated_pdf_is_accepted_at_upload(client):
    """The header is valid, so upload validation cannot catch this.

    It has to fail during extraction instead — which is the point. The
    contract here is only that the document does not reach a terminal
    success state without being processed.
    """
    r = upload(client, edge_case("truncated.pdf"), "truncated.pdf")
    assert r.status_code == 202, r.text
    assert r.json()["status"] not in ("completed",)


def test_corrupt_body_is_accepted_at_upload(client):
    r = upload(client, edge_case("corrupt_body.pdf"), "corrupt.pdf")
    assert r.status_code == 202, r.text


def test_textless_pdf_is_accepted_at_upload(client):
    """Stands in for a scanned document.

    Structurally valid, no extractable text. Processing must report that
    rather than indexing an empty document — but nothing consumes the
    queue yet, so this only asserts the upload half.
    """
    r = upload(client, edge_case("no_text.pdf"), "scanned.pdf")
    assert r.status_code == 202, r.text


def test_hundred_page_pdf_is_accepted(client):
    r = upload(client, edge_case("long_100_pages.pdf"), "long.pdf")
    assert r.status_code == 202, r.text


# ─────────────────────────── filenames ───────────────────────────

def test_traversal_filename_does_not_escape_storage(client):
    """A filename is attacker-controlled input, not a path."""
    r = upload(client, edge_case("traversal_name.pdf"),
               "../../../etc/passwd.pdf")
    if r.status_code == 202:
        assert ".." not in r.json()["name"]
        assert "/" not in r.json()["name"]
        assert "\\" not in r.json()["name"]
    else:
        assert r.status_code in (400, 415, 422)


def test_null_byte_filename_is_handled(client):
    """Some path handling truncates at a null byte.

    A name that looks safe up to the null can resolve somewhere else.
    """
    r = upload(client, edge_case("null_byte_name.pdf"), "safe\x00.pdf")
    assert r.status_code in (202, 400, 415, 422), r.text
    if r.status_code == 202:
        assert "\x00" not in r.json()["name"]


def test_unicode_filename_is_accepted(client):
    """Not an attack — just a case naive path handling gets wrong."""
    r = upload(client, edge_case("unicode_name.pdf"),
               "عقد-الخدمات-٢٠٢٦.pdf")
    assert r.status_code == 202, r.text
    assert r.json()["name"]


def test_very_long_filename_is_handled(client, sample_pdf):
    """Filesystems cap component length, typically at 255 bytes."""
    r = upload(client, sample_pdf, "a" * 300 + ".pdf")
    assert r.status_code in (202, 400, 413, 422), r.text
    if r.status_code == 202:
        assert len(r.json()["name"]) <= 255


def test_filename_without_a_stem_is_handled(client, sample_pdf):
    r = upload(client, sample_pdf, ".pdf")
    assert r.status_code in (202, 400, 415, 422), r.text