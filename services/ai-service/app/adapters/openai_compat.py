"""OpenAI-compatible provider - the ADR-006 contingency.

Covers any server speaking the OpenAI REST shape: OpenAI itself, a self-hosted
vLLM/Ollama endpoint, and Google Gemini via its OpenAI-compatible base URL. One
adapter, selected entirely by ``OPENAI_BASE_URL``.

Read this before enabling it in production
------------------------------------------
Choosing this backend is a real trade-off, not a neutral config flip, and
ADR-006 exists because of it:

* The API key lives in a Kubernetes Secret. That is precisely the pattern the
  OCI path was chosen to avoid, and it becomes the weakest link in a
  defence-in-depth story.
* Document text leaves the tenancy over the public internet to a third party.
  For a product whose headline feature is detecting PII in contracts, that is a
  contradiction worth naming out loud. :mod:`app.redaction` reduces the blast
  radius but does not remove it.
* Worker pods sit in a private subnet, so calls egress through the NAT gateway
  - a new rule, and a visible hole in "everything stays private".
* Free tiers have historically trained on submitted content and will not
  survive a k6 run. If this path is used for a demo, use synthetic documents.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.adapters.base import AIProvider, ChatMessage, ChatResult, EmbedResult, estimate_tokens
from app.errors import ProviderConfigurationError, ProviderUnavailableError

logger = logging.getLogger("ai-service")


class OpenAICompatProvider(AIProvider):
    name = "openai_compat"
    is_external = True

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model_name: str,
        embedding_model: str,
        embedding_dim: int,
        timeout_s: float,
    ) -> None:
        if not base_url:
            raise ProviderConfigurationError(
                "OPENAI_BASE_URL is required when AI_BACKEND=openai_compat"
            )
        if not api_key:
            raise ProviderConfigurationError(
                "OPENAI_API_KEY is required when AI_BACKEND=openai_compat. "
                "Inject it from a Kubernetes Secret - never commit it."
            )

        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._chat_model = model_name
        self._embed_model = embedding_model
        self._dim = embedding_dim
        self._timeout_s = timeout_s

        # One pooled client for the process lifetime. httpx.Client is
        # thread-safe, which matters because FastAPI runs sync routes in a
        # worker threadpool.
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=timeout_s,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    # -- identity ---------------------------------------------------------
    @property
    def chat_model(self) -> str:
        return self._chat_model

    @property
    def embed_model(self) -> str:
        return self._embed_model

    @property
    def embed_dim(self) -> int:
        return self._dim

    # -- chat -------------------------------------------------------------
    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float,
        max_tokens: int,
        task: str = "generic",
        context: dict[str, Any] | None = None,
    ) -> ChatResult:
        payload = {
            "model": self._chat_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise ProviderUnavailableError(
                f"OpenAI-compatible chat returned {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(f"OpenAI-compatible chat failed: {exc}") from exc

        choices = data.get("choices") or []
        text = (choices[0].get("message", {}).get("content") if choices else "") or ""

        usage = data.get("usage") or {}
        reported = bool(usage)
        tokens_in = int(usage.get("prompt_tokens", 0) or 0)
        tokens_out = int(usage.get("completion_tokens", 0) or 0)
        if not reported:
            tokens_in = sum(estimate_tokens(m.content) for m in messages)
            tokens_out = estimate_tokens(text)

        return ChatResult(
            text=text,
            model=data.get("model", self._chat_model),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            estimated=not reported,
        )

    # -- embeddings -------------------------------------------------------
    def embed(self, texts: list[str], *, input_type: str = "document") -> EmbedResult:
        # The OpenAI embeddings API has no input_type concept; documents and
        # queries share one space, so the argument is accepted and ignored.
        payload = {"model": self._embed_model, "input": texts}

        try:
            response = self._client.post("/embeddings", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise ProviderUnavailableError(
                f"OpenAI-compatible embed returned {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(f"OpenAI-compatible embed failed: {exc}") from exc

        # Order is not guaranteed by the spec; sort by index before returning.
        items = sorted(data.get("data", []), key=lambda d: d.get("index", 0))
        vectors = [item["embedding"] for item in items]
        dim = len(vectors[0]) if vectors else self._dim

        if vectors and dim != self._dim:
            raise ProviderConfigurationError(
                f"EMBEDDING_DIM={self._dim} but {self._embed_model} returned {dim}-dim "
                "vectors. Fix EMBEDDING_DIM and the vector column together, then "
                "re-index - mixed dimensions cannot be searched."
            )

        usage = data.get("usage") or {}
        return EmbedResult(
            vectors=vectors,
            dim=dim,
            model=data.get("model", self._embed_model),
            tokens_in=int(usage.get("prompt_tokens", 0) or 0)
            or sum(estimate_tokens(t) for t in texts),
            estimated=not usage,
        )

    # -- readiness --------------------------------------------------------
    def probe(self) -> bool:
        """GET /models - cheap and non-billable on every compatible server."""
        try:
            response = self._client.get("/models", timeout=5.0)
            return response.status_code < 500
        except httpx.HTTPError as exc:
            logger.warning(
                "provider_probe_failed",
                extra={"provider": self.name, "error": str(exc)},
            )
            return False
