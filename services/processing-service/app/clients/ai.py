"""Client for ai-service.

The boundary this file defends: **the worker orchestrates, ai-service decides.**
No prompt, no model name, no scoring rule and no provider credential appears
here. If a change to how a document is classified requires editing this file,
the boundary has been crossed.

The wire contract is ``services/ai-service/app/schemas.py``. Responses are
returned as plain dicts rather than re-modelled with pydantic here: duplicating
another service's schema gives two definitions to keep in step, and the worker
reads a handful of fields from each response. What it does read, it reads
defensively — a missing optional field degrades a stage, it does not crash a job.
"""

from __future__ import annotations

from typing import Any

from app.clients.base import ServiceClient
from app.config import settings


class AIServiceClient(ServiceClient):
    def __init__(self) -> None:
        super().__init__(
            name="ai-service",
            base_url=settings.ai_service_url,
            timeout_s=settings.ai_service_timeout_s,
            auth_token=settings.ai_service_auth_token,
        )

    async def classify(self, *, text: str, document_id: str) -> dict[str, Any]:
        return await self.post_json(
            "/classify",
            {"text": text, "document_id": document_id},
            operation="classify",
        )

    async def extract(
        self, *, text: str, document_id: str, document_type: str | None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"text": text, "document_id": document_id}
        # Passing the type we already classified saves ai-service classifying
        # the same text a second time.
        if document_type:
            payload["document_type"] = document_type
        return await self.post_json("/extract", payload, operation="extract")

    async def summarize(
        self, *, text: str, document_id: str, document_type: str | None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"text": text, "document_id": document_id}
        if document_type:
            payload["document_type"] = document_type
        return await self.post_json("/summarize", payload, operation="summarize")

    async def analyse_risk(
        self, *, text: str, document_id: str, document_type: str | None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "text": text,
            "document_id": document_id,
            "explain": True,
        }
        if document_type:
            payload["document_type"] = document_type
        return await self.post_json("/analysis/risk", payload, operation="risk")


def is_degraded(response: dict[str, Any]) -> bool:
    """Did this response come from a healthy model call?

    ``meta.degraded`` is ai-service's own signal that it fell back to a local
    result — its schema documents this field as existing for the processing
    worker. A job whose outputs are all degraded still completes, but saying so
    is the difference between "we summarised this" and "we produced a summary".
    """
    meta = response.get("meta")
    return bool(meta.get("degraded")) if isinstance(meta, dict) else False
