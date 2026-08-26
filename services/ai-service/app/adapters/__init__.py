"""Provider factory - the one place a backend is chosen.

``AI_BACKEND`` is the only switch. Nothing above this module knows which
provider is live, which is what makes ADR-006's "provider swap is a config
change" claim true rather than aspirational.
"""

from __future__ import annotations

import logging
import threading

from app.adapters.base import AIProvider, ChatMessage, ChatResult, EmbedResult
from app.config import Settings, settings as default_settings
from app.errors import ProviderConfigurationError

logger = logging.getLogger("ai-service")

__all__ = [
    "AIProvider",
    "ChatMessage",
    "ChatResult",
    "EmbedResult",
    "build_provider",
    "get_provider",
    "reset_provider",
]

_provider: AIProvider | None = None
_lock = threading.Lock()


def build_provider(cfg: Settings | None = None) -> AIProvider:
    """Construct the provider named by ``AI_BACKEND``."""
    cfg = cfg or default_settings

    if cfg.ai_backend == "mock":
        from app.adapters.mock import MockProvider

        return MockProvider(
            model_name=cfg.model_name,
            embedding_model=cfg.embedding_model,
            embedding_dim=cfg.embedding_dim,
        )

    if cfg.ai_backend == "oci":
        from app.adapters.oci_genai import OCIGenAIProvider

        return OCIGenAIProvider(
            region=cfg.oci_region,
            compartment_id=cfg.oci_compartment_id,
            auth_mode=cfg.oci_auth_mode,
            model_name=cfg.model_name,
            embedding_model=cfg.embedding_model,
            embedding_dim=cfg.embedding_dim,
            timeout_s=cfg.request_timeout_s,
            serving_mode=cfg.oci_serving_mode,
            endpoint=cfg.oci_endpoint,
        )

    if cfg.ai_backend == "openai_compat":
        from app.adapters.openai_compat import OpenAICompatProvider

        return OpenAICompatProvider(
            base_url=cfg.openai_base_url,
            api_key=cfg.openai_api_key,
            model_name=cfg.model_name,
            embedding_model=cfg.embedding_model,
            embedding_dim=cfg.embedding_dim,
            timeout_s=cfg.request_timeout_s,
            model_chain=cfg.model_chain(),
            model_cooldown_s=cfg.model_cooldown_s,
        )

    raise ProviderConfigurationError(f"Unknown AI_BACKEND: {cfg.ai_backend}")


def get_provider() -> AIProvider:
    """Process-wide singleton, built on first use.

    Double-checked locking: FastAPI serves sync routes from a threadpool, so
    two requests can race here on a cold pod.
    """
    global _provider
    if _provider is None:
        with _lock:
            if _provider is None:
                _provider = build_provider()
                logger.info(
                    "provider_initialised",
                    extra={
                        "provider": _provider.name,
                        "model": _provider.chat_model,
                        "embedding_model": _provider.embed_model,
                        "embedding_dim": _provider.embed_dim,
                        "external": _provider.is_external,
                    },
                )
    return _provider


def reset_provider() -> None:
    """Drop the cached provider. Used by tests that swap configuration."""
    global _provider
    with _lock:
        _provider = None
