"""Storage contracts used by Document Service business logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import UploadFile


@dataclass(frozen=True)
class StoredObject:
    storage_key: str
    size_bytes: int


class DocumentStorage(Protocol):
    async def save_pdf(
        self, upload: UploadFile, storage_key: str, max_bytes: int
    ) -> StoredObject:
        """Validate and persist a PDF, returning its stable storage key."""

    def delete(self, storage_key: str) -> None:
        """Best-effort cleanup when metadata persistence fails."""

    def size_bytes(self, storage_key: str) -> int | None:
        """Return the stored size when available to a local backend."""
