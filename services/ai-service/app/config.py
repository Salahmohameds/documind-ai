"""Application configuration - 100 % from environment variables.

Follows the services/README.md non-negotiable:
  'Configuration: 100 % from environment variables - no hard-coded hosts, keys,
   model names.'

Every default here is a *local development* default that works offline with no
credential. Production values are injected by the Kubernetes ConfigMap
(non-secret) and Secret (secret) that role 2 mounts onto the Deployment.
"""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings

Backend = Literal["mock", "oci", "openai_compat"]


class Settings(BaseSettings):
    """All configuration comes from environment variables.

    Defaults are for **local development only** (docker compose).
    Production values MUST be injected via Kubernetes ConfigMaps/Secrets.
    """

    # --- Application --------------------------------------------------------
    port: int = 8080
    service_name: str = "ai-service"
    log_level: str = "INFO"

    # --- Provider selection -------------------------------------------------
    # 'mock' is the DEFAULT on purpose: the service must start, serve every
    # endpoint and pass its whole test suite with no OCI credential and no
    # network access. See README.md -> "Why mock is the default".
    ai_backend: Backend = "mock"

    model_name: str = "mock-chat-v1"
    embedding_model: str = "mock-embed-v1"
    embedding_dim: int = 384

    temperature: float = 0.0
    max_tokens: int = 1024

    # --- OCI Generative AI (used only when ai_backend == 'oci') -------------
    # NOTE: compartments in OCI are global; the client is separately pointed at
    # a *region endpoint*. A compartment in me-jeddah-1 can therefore be used
    # against a Generative AI region such as me-riyadh-1. See ADR-006.
    oci_region: str = ""
    oci_compartment_id: str = ""
    # 'workload' -> OKE workload identity (production)
    # 'instance' -> instance principal    (VM fallback)
    # 'config'   -> ~/.oci/config         (LOCAL DEV ONLY)
    oci_auth_mode: Literal["workload", "instance", "config"] = "workload"
    oci_serving_mode: Literal["ON_DEMAND", "DEDICATED"] = "ON_DEMAND"
    oci_endpoint: str = ""  # optional override; derived from region when empty

    # --- OpenAI-compatible fallback (ADR-006 contingency) -------------------
    # Also covers Google Gemini via its OpenAI-compatible endpoint.
    openai_base_url: str = ""
    openai_api_key: str = ""  # injected from a K8s Secret - never in git

    # --- Resilience ---------------------------------------------------------
    request_timeout_s: float = 30.0
    max_retries: int = 3
    retry_base_delay_s: float = 0.5
    retry_max_delay_s: float = 8.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_reset_s: float = 30.0

    # --- Budget -------------------------------------------------------------
    token_budget_per_request: int = 8000
    max_embed_batch: int = 96
    max_context_chunks: int = 12

    # --- Security -----------------------------------------------------------
    # PII is redacted before any call that leaves the cluster. The mock adapter
    # performs no egress, so redaction is skipped for it unless forced.
    redact_before_egress: bool = True
    redact_for_mock: bool = False

    # --- Prompts ------------------------------------------------------------
    # Mounted as a ConfigMap in Kubernetes: changing a prompt must NOT require
    # an image rebuild.
    prompts_dir: str = "app/prompts"
    prompt_cache_enabled: bool = True

    # --- Readiness ----------------------------------------------------------
    readiness_cache_ttl_s: float = 10.0

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        # 'model_name' would otherwise collide with pydantic's reserved
        # 'model_' namespace.
        "protected_namespaces": (),
    }

    @property
    def provider_is_external(self) -> bool:
        """True when calls leave the cluster - drives redaction and egress logs."""
        return self.ai_backend != "mock"

    def redaction_enabled(self) -> bool:
        """Redact before egress, but do not pay the cost when nothing egresses."""
        if self.ai_backend == "mock":
            return self.redact_for_mock
        return self.redact_before_egress


# Module-level singleton - import this from anywhere inside the service.
settings = Settings()
