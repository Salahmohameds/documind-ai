"""Application configuration — 100 % from environment variables.

Follows the services/README.md non-negotiable:
  'Configuration: 100 % from environment variables — no hard-coded hosts, keys,
   model names.'

Every default is a *local development* default that works against
`docker compose up` with no credential. Production values are injected by the
Kubernetes ConfigMap (non-secret) and Secret (secret) on the Deployment.
"""

from __future__ import annotations

import os
import socket
from typing import Literal

from pydantic_settings import BaseSettings

StorageType = Literal["local", "oci"]


class Settings(BaseSettings):
    """All configuration comes from environment variables."""

    # --- Application --------------------------------------------------------
    port: int = 8080
    service_name: str = "processing-service"
    log_level: str = "INFO"

    # --- PostgreSQL ---------------------------------------------------------
    database_url: str = (
        "postgresql://documind:documind_dev_only@localhost:5432/documind"
    )

    # --- Redis Streams ------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"
    # Must match document-service's `redis_stream_name`. Changing one without
    # the other silently produces a worker that consumes nothing.
    redis_stream_name: str = "document_jobs"
    redis_consumer_group: str = "processing-workers"
    redis_dead_letter_stream: str = "document_jobs_dead"
    # Cap the dead-letter stream so a sustained failure cannot fill Redis.
    # Approximate trimming (MAXLEN ~) is O(1) where exact trimming is not.
    dead_letter_maxlen: int = 10_000

    # How long XREADGROUP blocks waiting for work. Long enough that an idle
    # worker is not spinning; short enough that shutdown feels immediate.
    read_block_ms: int = 5_000
    read_batch_size: int = 10

    # --- Reliability --------------------------------------------------------
    # Attempts across ALL workers, counted by Redis' delivery counter — not a
    # per-process retry loop. A pod that dies mid-job does not consume the
    # budget silently: the next claim sees delivery_count incremented.
    max_attempts: int = 3
    # A message held longer than this is presumed abandoned (pod evicted,
    # OOM-killed, node drained) and is reclaimed by another worker. Must exceed
    # job_timeout_s or healthy in-flight work gets stolen mid-flight.
    reclaim_min_idle_ms: int = 300_000
    reclaim_interval_s: float = 30.0
    # Jobs processed concurrently per pod. The work is I/O-bound (HTTP to
    # ai-service dominates), so this is worth more than extra pods until the
    # CPU-based HPA has a reason to fire.
    concurrency: int = 4
    # Hard ceiling on one job. Without it a hung downstream call holds a slot
    # forever and the pod slowly stops doing work while still passing probes.
    job_timeout_s: float = 180.0
    graceful_shutdown_s: float = 30.0

    # --- Object storage -----------------------------------------------------
    storage_type: StorageType = "local"
    storage_dir: str = "/app/storage"
    oci_bucket_name: str = "dm-demo-documents"
    oci_namespace: str = ""
    oci_region: str = ""
    # 'workload' -> OKE workload identity (production)
    # 'instance' -> instance principal    (VM fallback)
    # 'config'   -> ~/.oci/config         (LOCAL DEV ONLY)
    oci_auth_mode: Literal["workload", "instance", "config"] = "workload"
    # Refuse to load anything larger into memory. document-service caps uploads
    # at 25 MB; this is the same limit with headroom.
    max_document_bytes: int = 32 * 1024 * 1024

    # --- Downstream services ------------------------------------------------
    ai_service_url: str = "http://ai-service:8080"
    # ai-service caps its own total call at request_deadline_s (45 s default),
    # so this sits above that: we want to see its error, not our timeout.
    ai_service_timeout_s: float = 60.0
    ai_service_auth_token: str = ""

    search_service_url: str = "http://search-service:8080"
    search_service_timeout_s: float = 30.0
    # Empty means "send no Authorization header", which is what compose does
    # (search-service runs with DISABLE_AUTH=true there). Injected from a
    # Kubernetes Secret in the cluster — never in git.
    search_service_auth_token: str = ""

    # --- Resilience (per-dependency circuit breaker + bounded retry) --------
    max_retries: int = 3
    retry_base_delay_s: float = 0.5
    retry_max_delay_s: float = 8.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_reset_s: float = 30.0

    # --- Observability ------------------------------------------------------
    # services/README.md: 'export OTel when OTEL_EXPORTER_OTLP_ENDPOINT is set'.
    # Empty by default so compose, where no collector runs, does not retry gRPC
    # exports in the background forever. The Kubernetes ConfigMap sets it.
    otel_exporter_otlp_endpoint: str = ""

    # --- Text extraction ----------------------------------------------------
    # Below this, the PDF is treated as having no usable text layer. A handful
    # of stray ligatures from an image-only scan is not text.
    min_extracted_chars: int = 40

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def consumer_name(self) -> str:
        """Identify this worker inside the consumer group.

        Under Kubernetes ``HOSTNAME`` is the pod name, which makes ``XPENDING``
        output directly traceable to a pod's logs. The pid disambiguates two
        workers sharing a host during local development.
        """
        host = os.getenv("HOSTNAME") or socket.gethostname()
        return f"{host}-{os.getpid()}"


# Module-level singleton — import this from anywhere inside the service.
settings = Settings()
