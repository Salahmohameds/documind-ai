"""Storage contract used by the pipeline.

The mirror image of ``services/document-service/app/storage/base.py``: that
service writes, this one reads. The storage key travels between them in the
stream event, so neither has to know the other's path layout.
"""

from __future__ import annotations

from typing import Protocol


class DocumentReader(Protocol):
    def read(self, storage_key: str, max_bytes: int) -> bytes:
        """Return the object's bytes.

        Raises:
            DocumentNotFoundError: no object at that key (terminal).
            DocumentTooLargeError: object exceeds ``max_bytes`` (terminal).
            StorageUnavailableError: the backend could not be reached
                (retryable — the job goes back on the stream).
        """

    def health_check(self) -> None:
        """Raise if the backend is not usable. Called by the readiness probe."""
