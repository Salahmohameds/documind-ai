-- 002 — processing-service job ledger and summary storage.
--
-- Deliberately additive. The `documents` CHECK constraint is NOT touched:
-- document-service maps its lifecycle onto the existing uppercase values
-- (queued→UPLOADED, processing→PROCESSING, completed→INDEXED, failed→FAILED)
-- in app/repositories/documents.py, and widening the constraint here would
-- require that service to change in lockstep. The richer job lifecycle the
-- frontend needs — attempt counts, error detail, durations — lives in
-- processing_jobs instead, keyed by the job id.

CREATE TABLE IF NOT EXISTS processing_jobs (
    -- The Redis stream message id (e.g. '1724692800000-0'). Redis assigns it,
    -- it is unique and monotonic, and it is stable across redelivery — which
    -- is exactly what makes it usable as the idempotency key. A worker that
    -- receives the same message twice writes the same primary key twice.
    job_id          TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    -- Nullable: there is no auth/user model in M1. The consumer reads the
    -- field from the event when the producer starts sending it.
    user_id         TEXT,
    status          TEXT NOT NULL
                    CHECK (status IN ('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED')),
    -- Redis delivery count. >1 means this job was reclaimed from a worker
    -- that died or timed out holding it.
    attempt         INT NOT NULL DEFAULT 1,
    -- The consumer that last held the job — the pod name under Kubernetes,
    -- so a failed job can be traced back to a specific pod's logs.
    consumer_name   TEXT,
    stage           TEXT,
    error_code      TEXT,
    error_message   TEXT,
    -- True when the pipeline completed but at least one AI response came back
    -- with meta.degraded — a local fallback rather than a healthy model call.
    -- Completed-with-caveats is a different outcome from completed.
    degraded        BOOLEAN NOT NULL DEFAULT FALSE,
    queued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    duration_ms     INT
);

CREATE INDEX IF NOT EXISTS idx_processing_jobs_document_id
    ON processing_jobs (document_id);

CREATE INDEX IF NOT EXISTS idx_processing_jobs_status
    ON processing_jobs (status);


-- ai-service /summarize had no home in the schema; every other AI output
-- (fields, risk, chunks) already has a table.
CREATE TABLE IF NOT EXISTS document_summaries (
    document_id     TEXT PRIMARY KEY REFERENCES documents(document_id) ON DELETE CASCADE,
    summary         TEXT NOT NULL,
    key_points      JSONB,
    style           TEXT,
    summarized_at   TIMESTAMPTZ DEFAULT now()
);
