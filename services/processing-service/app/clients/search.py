"""Client for search-service.

Note what is *not* here: no embedding call, no chunking, no vector write.
Per ADR-008 the embeddings boundary belongs to search-service — it owns
chunking, the embedding model and pgvector. The worker hands it text and a
document id; how that becomes vectors is not the worker's business, and
ai-service's ``/embed`` is search-service's dependency, not ours.

``POST /index`` accepts ``content`` as either a string or a list of strings
(``IndexRequest`` in ``services/search-service/src/main.py``). The worker sends
the page list, so page boundaries survive into ``document_chunks.page`` and RAG
citations can name a page.
"""

from __future__ import annotations

from typing import Any

from app.clients.base import ServiceClient
from app.config import settings


class SearchServiceClient(ServiceClient):
    def __init__(self) -> None:
        super().__init__(
            name="search-service",
            base_url=settings.search_service_url,
            timeout_s=settings.search_service_timeout_s,
            auth_token=settings.search_service_auth_token,
        )

    async def index(
        self, *, document_id: str, pages: list[str], text: str
    ) -> dict[str, Any]:
        """Index a document's text.

        Indexing is idempotent from the worker's side by document id — a
        reprocessed document replaces its chunks rather than accumulating a
        second copy. That property lives in search-service; the worker relies
        on it when a reclaimed job re-runs.
        """
        # Drop pages that extracted to nothing so blank pages do not become
        # empty chunks; fall back to the flat text if every page was empty
        # (single-stream PDFs sometimes extract that way).
        content: list[str] | str = [page for page in pages if page.strip()] or text
        return await self.post_json(
            "/index",
            {"document_id": document_id, "content": content},
            operation="index",
        )
