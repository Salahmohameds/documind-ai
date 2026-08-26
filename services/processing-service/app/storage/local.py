"""Local-filesystem reader — development and compose only.

document-service writes uploads into a directory; in compose the same named
volume is mounted here read-only, so the worker reads exactly the bytes that
service wrote.

This does not survive the move to OKE with more than one replica: a block
volume is ReadWriteOnce, so a second pod cannot mount it. That is the whole
reason the OCI Object Storage backend exists — see ``oci_object_storage.py``.

The path-traversal guard is copied from document-service's ``LocalStorage``
deliberately. The storage key arrives over a Redis stream, and a message
carrying ``../../etc/passwd`` must be rejected by the reader itself rather than
trusted because "the producer built it".
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from app.errors import (
    DocumentNotFoundError,
    DocumentTooLargeError,
    InvalidDocumentError,
    StorageUnavailableError,
)


class LocalDocumentReader:
    def __init__(self, root: str) -> None:
        self._root = Path(root)

    def _path_for(self, storage_key: str) -> Path:
        key = PurePosixPath(storage_key)
        if key.is_absolute() or ".." in key.parts:
            raise InvalidDocumentError(f"Rejected storage key: {storage_key!r}")
        path = self._root.joinpath(*key.parts)
        try:
            path.resolve().relative_to(self._root.resolve())
        except ValueError as exc:
            raise InvalidDocumentError(
                f"Storage key escapes the storage root: {storage_key!r}"
            ) from exc
        return path

    def read(self, storage_key: str, max_bytes: int) -> bytes:
        path = self._path_for(storage_key)

        try:
            size = path.stat().st_size
        except FileNotFoundError as exc:
            raise DocumentNotFoundError(
                f"No stored object for key {storage_key!r}"
            ) from exc
        except OSError as exc:
            raise StorageUnavailableError(
                f"Could not stat {storage_key!r}: {exc}"
            ) from exc

        # Checked before reading, not after: the point is to avoid pulling an
        # oversized object into the pod's memory at all.
        if size > max_bytes:
            raise DocumentTooLargeError(
                f"Object {storage_key!r} is {size} bytes, over the "
                f"{max_bytes}-byte limit"
            )

        try:
            return path.read_bytes()
        except OSError as exc:
            raise StorageUnavailableError(
                f"Could not read {storage_key!r}: {exc}"
            ) from exc

    def health_check(self) -> None:
        if not self._root.is_dir():
            raise StorageUnavailableError(
                f"Storage root {self._root} does not exist or is not a directory"
            )
