# ADR-004 — Asynchronous Queue Technology

**Status:** Accepted — implemented in `services/processing-service`
**Date:** 2026-08-24 (decided) · 2026-08-26 (accepted on implementation)
**Deciders:** DocuMind team

## Problem

Document processing must be asynchronous (`202 Accepted` → job → worker).
Which queue?

## Options

| Option | Pros | Cons |
|--------|------|------|
| **Redis Streams** | Already needed (rate limiting/cache); consumer groups built in; one less system to run | Persistence weaker than broker-grade (AOF config needed) |
| RabbitMQ | Mature routing/retry/DLQ semantics | Extra cluster to deploy/observe on OKE |
| Kafka | Industry standard streaming | Massively overkill at this scale; heavy footprint |

## Decision

**Redis Streams** (single Redis covers queue + rate limiting), confirmed after
the Week-0 capacity check and now implemented.

The concern with Redis Streams was never throughput; it was that RabbitMQ ships
retry and dead-letter semantics that Redis leaves to the application. Those are
the mechanisms below. They are ~200 lines in `app/queue/consumer.py`, which was
judged a better trade than operating a second broker on OKE for one queue.

### Consumption

* One consumer group, `processing-workers`, across every replica. Each message
  goes to exactly one pod, which is what makes `replicas: 10` a scaling story
  rather than ten workers racing on the same documents.
* The group is created at id `0`, not `$`. `$` means "only messages published
  after this moment", which would silently skip everything already queued when
  the first worker starts on a fresh environment.
* Consumer name is the pod name, so `XPENDING` output traces a held message
  back to a specific pod's logs.

### Acknowledgement

* `XACK` happens **after** the terminal outcome is committed to Postgres, never
  on receipt. Acking first and then crashing loses the document with no trace.
* A *transient* failure is deliberately **not** acked. The message stays pending
  and is redelivered, which is the retry mechanism — there is no in-process
  retry loop for the job as a whole.
* A *terminal* failure is acked immediately. Retrying a document that is not a
  PDF cannot change the outcome, and an unacked poison message would circulate
  through the fleet forever.

### Recovery from a dead worker

A pending message belonging to a pod that no longer exists is invisible to
`XREADGROUP` — it was already delivered, so it is nobody's "new" message — and
would sit there indefinitely. `XAUTOCLAIM` on a 30 s interval reclaims anything
idle beyond `RECLAIM_MIN_IDLE_MS` (default 5 min, deliberately above
`JOB_TIMEOUT_S` so healthy in-flight work is not stolen). This is what makes
`kubectl delete pod` mid-job a self-healing demonstration rather than a lost
document.

### Attempt counting

The attempt is the larger of Redis' delivery counter and one past the count
persisted in `processing_jobs`. Two sources because each covers the other's gap:
the Redis counter survives a pod being OOM-killed (where none of our code runs
to increment anything), and the persisted row survives a Redis failover. Taking
the max means neither a lost pod nor a lost counter hands a poison message an
unbounded budget.

### Dead-letter path

After `MAX_ATTEMPTS` (default 3) the message is copied to `document_jobs_dead`
with its failure code, reason, attempt count and original message id, then
acked. The stream is capped with `MAXLEN ~` so a sustained failure cannot fill
Redis and take the live queue down with it. Replaying is a manual `XADD` back
onto `document_jobs` — a new message id, so the idempotency gate does not
suppress it.

### Idempotency

At-least-once delivery is the normal behaviour of the broker, not a corner
case: an ack can be lost, a pod can die between the commit and the ack, and a
reclaim can fire on a false-positive idle timeout. `processing_jobs.job_id` is
the Redis message id, so a redelivered message lands on the same primary key; a
row already marked `COMPLETED` short-circuits the whole pipeline. Without that
gate, each redelivery re-indexes the document, overwrites its risk assessment
and spends model tokens arriving back where it already was.

## Consequences

* Consumer-group based worker scaling. CPU-based HPA is the baseline; KEDA on
  `pendingEntriesCount` is the correct signal and is prepared as a commented
  `ScaledObject` in `kubernetes/hpa/` — enabling it is installing KEDA, not an
  application change. The worker already exports
  `documind_processing_stream_pending`.
* Redis durability is now on the critical path for job delivery. AOF must be
  enabled on the production instance; the outcome of every job is in Postgres
  regardless, so a Redis loss costs in-flight jobs, not completed work.
* If durability requirements grow, the migration path is intact: the producer
  writes through `RedisStreamPublisher` and the consumer through
  `StreamConsumer`, so a broker swap touches two files rather than the pipeline.
