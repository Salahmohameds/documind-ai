# Processing Service

The asynchronous document processing worker — the consumer half of DocuMind's
`202 Accepted` pipeline.

```text
User → api-gateway → document-service → Redis Stream → processing-service
                                                     → ai-service + search-service
                                                     → PostgreSQL
```

document-service returns `202` the moment a PDF is stored and publishes a job.
This service consumes that job and does the actual work: fetch the document,
extract its text, ask ai-service what it is and what is risky about it, hand the
text to search-service for indexing, and record the outcome so the frontend can
show progress.

It is an **orchestrator**. There is no prompt, no model name, no scoring rule and
no vector arithmetic anywhere in this codebase, and there should never be —
those belong to ai-service and search-service respectively.

## Pipeline

| # | Stage | Calls | Writes | Spine? |
|---|-------|-------|--------|--------|
| 1 | claim | — | `processing_jobs`, `documents.status` | yes |
| 2 | fetch | Object Storage | — | yes |
| 3 | extract_text | pypdf | — | yes |
| 4 | classify | `POST /classify` | `documents.document_type` | no |
| 5 | extract | `POST /extract` | `extracted_fields` | no |
| 6 | summarize | `POST /summarize` | `document_summaries` | no |
| 7 | risk | `POST /analysis/risk` | `risk_assessments` | no |
| 8 | index | `POST /index` | `document_chunks` (via search-service) | yes |
| 9 | complete | — | `processing_jobs`, `documents` | yes |

Stages 5–7 run concurrently — classification comes first because its result
steers the other three prompts.

**Graded failure.** A *spine* stage failing fails the job. An *enrichment*
stage failing does not: a document whose text is extracted and indexed is
searchable and answers RAG questions even if the risk model was unreachable, and
the missing piece can be backfilled. Skipped stages are named in the
`processing_completed` log line and counted in
`documind_processing_stage_failures_total`.

## Status model

`processing_jobs` carries the real lifecycle:

```text
QUEUED → PROCESSING → COMPLETED
                    → FAILED
```

with `attempt`, `consumer_name`, `stage`, `error_code`, `error_message`,
`degraded`, `queued_at`, `started_at`, `finished_at` and `duration_ms`.

`documents.status` is **not** widened to match. Its CHECK constraint is
`UPLOADED|PROCESSING|INDEXED|FAILED` and document-service already maps its own
vocabulary onto those values; changing it would require that service to change
in lockstep. So the worker writes the same uppercase values there
(`COMPLETED → INDEXED`) and keeps the richer lifecycle in `processing_jobs`.

`degraded` marks a job that completed but where at least one AI response came
back with `meta.degraded` — a local fallback rather than a healthy model call.
Completed-with-caveats is a different outcome from completed.

## Event contract

Consumed from the `document_jobs` stream, exactly as document-service publishes
it today:

| Field | Required | Note |
|-------|----------|------|
| `event_version` | no | Defaults to `1`. Anything else is rejected, not guessed at. |
| `document_id` | **yes** | |
| `storage_key` | **yes** | Validated against traversal before use. |
| `filename` | no | Logging only. |
| `content_type`, `size_bytes`, `uploaded_at` | no | `uploaded_at` becomes `queued_at`. |
| `user_id` | no | Read if present. There is no auth model in M1. |
| `request_id` | no | Adopted as the correlation id if present, otherwise generated. If document-service starts forwarding the caller's `X-Request-ID`, one id will span the whole upload→processing→AI path with no change here. |

Unknown fields are ignored, so role 3 can add one without a lockstep deploy.

Three things the worker derives rather than demands:

* **`job_id`** — the Redis message id. Redis assigns it, it is unique and
  monotonic, and it is identical across redeliveries, which is exactly what an
  idempotency key needs.
* **`document_type`** — produced by `/classify`. Nothing upstream knows it at
  publish time.
* **`user_id`** — nullable until there is an auth model.

## Reliability

| Concern | Mechanism |
|---------|-----------|
| Never lose a job | Ack only *after* the terminal status is committed. A transient failure is not acked at all. |
| Pod dies mid-job | `XAUTOCLAIM` reclaims messages idle beyond `RECLAIM_MIN_IDLE_MS`. |
| Duplicate delivery | `processing_jobs.job_id` is the message id; a `COMPLETED` row short-circuits the pipeline. |
| Poison message | Attempt budget (`MAX_ATTEMPTS`), then the `document_jobs_dead` stream, capped with `MAXLEN ~`. |
| Attempt counting | The larger of Redis' delivery counter and the persisted attempt — each covers the other's gap. |
| Dependency down | Per-dependency circuit breaker; retry with full-jitter backoff under a total deadline. |
| Hung job | `JOB_TIMEOUT_S` caps one job; each HTTP call is capped separately. |
| Rolling update | SIGTERM → readiness 503 → stop reading → drain → cancel the rest **un-acked**. |
| Diagnosis | Structured JSON logs carrying `job_id`, `document_id` and `request_id` on every line. |

`request_id` is propagated to ai-service and search-service as `X-Request-ID`;
both echo it. One id ties an upload to the model call it caused.

### Statelessness

Nothing is held in a pod that another pod needs. All state is in Redis and
Postgres; the circuit breaker is per-pod on purpose (a shared one would make one
pod's network problem everybody's outage). Any pod can take over any job, so
`replicas: 10` and `kubectl delete pod` are both uneventful.

The one caveat: `STORAGE_TYPE=local` reads a filesystem, and a block volume is
ReadWriteOnce. Multi-replica deployments need `STORAGE_TYPE=oci`.

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /liveness` | Process alive **and the consumer task still running**. Does not touch Postgres or Redis. |
| `GET /readiness` | Postgres + Redis + storage + consumer group. 503 while draining. |
| `GET /metrics` | Prometheus. Includes `documind_processing_stream_pending` — the queue-depth signal for HPA/KEDA. |

Liveness deliberately tracks the consumer, not the HTTP server: a worker whose
consumer task has died answers HTTP perfectly while the queue silently grows,
and nothing else in the platform detects that.

## Configuration

Every value comes from the environment; nothing is hardcoded. Defaults are for
local development and work offline against `docker compose`.

| Variable | Default | Notes |
|----------|---------|-------|
| `PORT` | `8080` | |
| `LOG_LEVEL` | `INFO` | |
| `DATABASE_URL` | local compose DSN | Secret in the cluster. |
| `REDIS_URL` | `redis://localhost:6379/0` | Secret in the cluster. |
| `REDIS_STREAM_NAME` | `document_jobs` | **Must match document-service.** |
| `REDIS_CONSUMER_GROUP` | `processing-workers` | |
| `REDIS_DEAD_LETTER_STREAM` | `document_jobs_dead` | |
| `READ_BLOCK_MS` | `5000` | `<= 0` means poll instead of blocking (`BLOCK 0` would block forever). |
| `READ_BATCH_SIZE` | `10` | |
| `MAX_ATTEMPTS` | `3` | Before the dead-letter stream. |
| `RECLAIM_MIN_IDLE_MS` | `300000` | Must exceed `JOB_TIMEOUT_S`. |
| `RECLAIM_INTERVAL_S` | `30` | |
| `CONCURRENCY` | `4` | Jobs in flight per pod. |
| `JOB_TIMEOUT_S` | `180` | |
| `GRACEFUL_SHUTDOWN_S` | `30` | Must be below `terminationGracePeriodSeconds`. |
| `STORAGE_TYPE` | `local` | `local` \| `oci` |
| `STORAGE_DIR` | `/app/storage` | `local` only. |
| `OCI_BUCKET_NAME` / `OCI_NAMESPACE` / `OCI_REGION` | — | `oci` only. |
| `OCI_AUTH_MODE` | `workload` | `workload` \| `instance` \| `config` |
| `MAX_DOCUMENT_BYTES` | `33554432` | 32 MB. |
| `AI_SERVICE_URL` | `http://ai-service:8080` | |
| `AI_SERVICE_TIMEOUT_S` | `60` | Above ai-service's own 45 s deadline. |
| `SEARCH_SERVICE_URL` | `http://search-service:8080` | |
| `SEARCH_SERVICE_TIMEOUT_S` | `30` | |
| `SEARCH_SERVICE_AUTH_TOKEN` | `""` | Empty sends no `Authorization` header. Secret in the cluster. |
| `AI_SERVICE_AUTH_TOKEN` | `""` | ai-service has no auth in v1. |
| `MAX_RETRIES` | `3` | |
| `RETRY_BASE_DELAY_S` / `RETRY_MAX_DELAY_S` | `0.5` / `8` | Full-jitter backoff. |
| `CIRCUIT_BREAKER_THRESHOLD` / `CIRCUIT_BREAKER_RESET_S` | `5` / `30` | |
| `MIN_EXTRACTED_CHARS` | `40` | Below this the PDF is treated as a scan. |

## Local run

```bash
# Whole stack
docker compose up -d --build

# Or just this service against the compose data tier
docker compose up -d postgres redis ai-service search-service
cd services/processing-service
pip install -r requirements.txt
DATABASE_URL=postgresql://documind:documind_dev_only@localhost:5432/documind \
REDIS_URL=redis://localhost:6379/0 \
STORAGE_DIR=/tmp/documind-storage \
AI_SERVICE_URL=http://localhost:8082 \
SEARCH_SERVICE_URL=http://localhost:8080 \
uvicorn app.main:app --port 8083
```

## Tests

```bash
cd services/processing-service && python -m pytest tests -q
```

No test calls a real model, a real Redis or a real Postgres: `fakeredis`,
`httpx.MockTransport` and in-memory SQLite stand in, so the suite runs offline
with no compose stack.

## Deployment

```bash
docker build --build-arg INSTALL_OCI=true -t <region>.ocir.io/<ns>/documind/processing-service:<sha> .
kubectl apply -f kubernetes/namespace/ -f kubernetes/configmaps/ -f kubernetes/secrets/
kubectl apply -f kubernetes/deployments/ -f kubernetes/services/
kubectl apply -f kubernetes/hpa/ -f kubernetes/pdb/ -f kubernetes/network-policies/
```

`INSTALL_OCI=true` is required whenever `STORAGE_TYPE=oci` — the SDK is an
optional layer so the default image and the test suite stay free of it.

## Not in scope

* **OCR.** Scanned, image-only PDFs have no text layer and fail terminally with
  `ERR_NO_TEXT_LAYER`. Supporting them needs tesseract in the image or OCI
  Vision behind another adapter; failing honestly is correct until one exists.
* **Non-PDF formats.** document-service accepts PDFs only.
* **AI logic.** Classification, extraction, summarisation and risk scoring
  belong to ai-service; chunking, embeddings and retrieval to search-service.
