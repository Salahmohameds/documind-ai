"""Local reader: the path-traversal guard and the size ceiling.

The storage key arrives over a Redis stream. Anything with write access to that
stream can name a path, so the reader validates rather than trusts.
"""

from __future__ import annotations

import pytest

from app.errors import (
    DocumentNotFoundError,
    DocumentTooLargeError,
    InvalidDocumentError,
    StorageUnavailableError,
)
from app.storage.local import LocalDocumentReader


@pytest.fixture
def storage_root(tmp_path):
    root = tmp_path / "storage"
    (root / "documents").mkdir(parents=True)
    (root / "documents" / "doc_1.pdf").write_bytes(b"%PDF-1.4 hello")
    # A secret next to, but outside, the storage root.
    (tmp_path / "secret.txt").write_bytes(b"do not read me")
    return root


def test_reads_a_stored_object(storage_root):
    reader = LocalDocumentReader(str(storage_root))
    assert reader.read("documents/doc_1.pdf", 1024) == b"%PDF-1.4 hello"


def test_missing_object_is_terminal(storage_root):
    reader = LocalDocumentReader(str(storage_root))
    with pytest.raises(DocumentNotFoundError) as excinfo:
        reader.read("documents/nope.pdf", 1024)
    # Terminal: retrying cannot make the object exist.
    assert excinfo.value.retryable is False


@pytest.mark.parametrize(
    "malicious_key",
    [
        "../secret.txt",
        "documents/../../secret.txt",
        "/etc/passwd",
    ],
)
def test_rejects_traversal_outside_the_root(storage_root, malicious_key):
    reader = LocalDocumentReader(str(storage_root))
    with pytest.raises(InvalidDocumentError):
        reader.read(malicious_key, 1024)


def test_oversized_object_is_rejected_before_reading(storage_root):
    reader = LocalDocumentReader(str(storage_root))
    with pytest.raises(DocumentTooLargeError):
        reader.read("documents/doc_1.pdf", max_bytes=4)


def test_health_check_fails_when_the_root_is_absent(tmp_path):
    reader = LocalDocumentReader(str(tmp_path / "does-not-exist"))
    with pytest.raises(StorageUnavailableError):
        reader.health_check()
