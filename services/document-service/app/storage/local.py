"""Local, development-only implementation of the document storage contract."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import UploadFile

from app.errors import InvalidDocumentError, UploadTooLargeError
from app.storage.base import StoredObject

_CHUNK_SIZE = 1024 * 1024
_PDF_HEADER_SCAN_BYTES = 1024


class LocalStorage:
    """Stores documents below one configured root without exposing file paths."""

    def __init__(self, root: str) -> None:
        self._root = Path(root)

    def _path_for(self, storage_key: str) -> Path:
        key = PurePosixPath(storage_key)
        if key.is_absolute() or ".." in key.parts:
            raise InvalidDocumentError("The generated storage key is invalid.")
        path = self._root.joinpath(*key.parts)
        try:
            path.resolve().relative_to(self._root.resolve())
        except ValueError as exc:
            raise InvalidDocumentError("The generated storage key is invalid.") from exc
        return path

    async def save_pdf(
        self, upload: UploadFile, storage_key: str, max_bytes: int
    ) -> StoredObject:
        destination = self._path_for(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        total = 0
        header = bytearray()

        try:
            with temporary.open("xb") as target:
                while chunk := await upload.read(_CHUNK_SIZE):
                    total += len(chunk)
                    if total > max_bytes:
                        raise UploadTooLargeError(
                            "A document may not exceed 25 MB."
                        )
                    if len(header) < _PDF_HEADER_SCAN_BYTES:
                        header.extend(
                            chunk[: _PDF_HEADER_SCAN_BYTES - len(header)]
                        )
                    target.write(chunk)

            if b"%PDF-" not in header:
                raise InvalidDocumentError(
                    "The uploaded file is not a valid PDF document."
                )

            os.replace(temporary, destination)
            return StoredObject(storage_key=storage_key, size_bytes=total)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

    def delete(self, storage_key: str) -> None:
        self._path_for(storage_key).unlink(missing_ok=True)

    def size_bytes(self, storage_key: str) -> int | None:
        path = self._path_for(storage_key)
        return path.stat().st_size if path.exists() else None
