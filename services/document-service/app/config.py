"""Application configuration — 100 % from environment variables.

Follows the services/README.md non-negotiable:
  'Configuration: 100 % from environment variables — no hard-coded hosts, keys,
   model names.'
"""

from __future__ import annotations

from typing import Literal

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
    # "local" (a block volume) is single-pod/dev-only: it cannot be shared
    # across document-service replicas and processing-service can never read
    # it. "oci_object_storage" is required for anything beyond a single-pod
    # local dev run.
    storage_type: Literal["local", "oci_object_storage"] = "local"
    storage_dir: str = "/app/storage"
    oci_bucket_name: str = "dm-demo-documents"
    oci_namespace: str = ""
    oci_region: str = ""
    # 'workload' -> OKE workload identity (production)
    # 'instance' -> instance principal    (VM fallback)
    # 'config'   -> ~/.oci/config         (LOCAL DEV ONLY)
    oci_auth_mode: Literal["workload", "instance", "config"] = "workload"

    # --- Upload limits ------------------------------------------------------
    max_upload_mb: int = 25

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Module-level singleton — import this from anywhere inside the service.
settings = Settings()
