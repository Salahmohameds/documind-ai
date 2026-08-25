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
    service_name: str = "document-service"
    log_level: str = "INFO"

    # --- PostgreSQL ---------------------------------------------------------
    database_url: str = (
        "postgresql://documind:documind_dev_only@localhost:5432/documind"
    )

    # --- Redis --------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"
    redis_stream_name: str = "document_jobs"

    # --- Storage ------------------------------------------------------------
    storage_type: str = "local"  # "local" | "oci_object_storage"
    storage_dir: str = "/app/storage"
    oci_bucket_name: str = "dm-documents"

    # --- Upload limits ------------------------------------------------------
    max_upload_mb: int = 25

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Module-level singleton — import this from anywhere inside the service.
settings = Settings()
