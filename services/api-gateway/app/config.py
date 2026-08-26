"""Application configuration — 100 % from environment variables.

Follows the services/README.md non-negotiable:
  'Configuration: 100 % from environment variables — no hard-coded hosts, keys,
   model names.'
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All configuration comes from environment variables.

    Defaults are for **local development only** (docker compose).
    Production values MUST be injected via Kubernetes ConfigMaps/Secrets.
    """

    # --- Application --------------------------------------------------------
    port: int = 8080
    service_name: str = "api-gateway"
    log_level: str = "INFO"

    # --- JWT ----------------------------------------------------------------
    # HS256 project-wide standard (matches search-service).
    # MUST be overridden in production via OCI Vault → K8s Secret.
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # --- Downstream services ------------------------------------------------
    # Local defaults assume services run directly on the host.
    # In docker-compose / K8s these resolve to container DNS names.
    search_service_url: str = "http://localhost:8080"
    document_service_url: str = "http://localhost:8081"
    ai_service_url: str = "http://localhost:8082"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Module-level singleton — import this from anywhere inside the service.
settings = Settings()
