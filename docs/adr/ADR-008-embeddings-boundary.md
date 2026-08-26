# ADR-008 — Embeddings: ai-service owns the model client, the network hop is optional

**Status:** Proposed
**Date:** 2026-08-26
**Deciders:** role 4 (AI Engineer), role 6 (Data / Search Engineer)
**Supersedes nothing. Depends on:** ADR-005 (pgvector), ADR-006 (AI provider)

## Problem

`docs/team/ROLES.md` lists embeddings under **both** role 4 (AI adapter) and
role 6 (embeddings, vector indexing). `services/search-service/src/embeddings.py`
already contains an `OCIGenerativeAIEmbedder` whose `embed()` raises
`NotImplementedError` with a message addressed to the AI Engineer. Two people
own one thing, and neither can finish it alone.

Separately: embeddings are the **highest-volume model call in the platform** —
every chunk of every document at index time, plus every query at search time.
Whatever we decide here is paid hundreds of times per document and once per
search, so it is also a cost and latency decision, not only an ownership one.

## Options

1. **search-service owns everything.** It already has the interface. But it
   would need OCI credentials, its own token accounting, and a second copy of
   the retry/circuit-breaker logic — a second place for credentials to live.
2. **ai-service owns the model client and exposes `POST /embed`; search-service
   always calls it over HTTP.** One credential location, one budget, one
   breaker. Costs a network round-trip on the highest-volume path.
3. **Run embeddings locally in-pod** (`sentence-transformers`,
   `all-MiniLM-L6-v2`, 384-dim — already stubbed as the `local_st` backend).
   Free, no egress, no token spend. But it puts torch in an image and makes
   "ai-service owns the model client" meaningless for the highest-volume call.
4. **Option 2's interface, with option 3 available on either side of it.**

## Decision

**Option 4.**

* `ai-service` exposes `POST /embed`, batch-first, supporting all three backends
  (`mock`, `oci`, `openai_compat`). It is the only component that holds provider
  credentials and the only place the token budget is enforced.
* `search-service` gains an `ai_service` backend in its existing
  `EMBEDDING_BACKEND` factory that HTTP-calls that endpoint, **and keeps
  `local_st` as an in-process option.**
* Which is used is an environment variable per deployment.

`OCIGenerativeAIEmbedder` in search-service is deleted rather than implemented:
its job is now done by `ai-service`.

## Why

The argument for centralising — *one place credentials live, one place the token
budget is enforced* — is entirely an argument about **hosted** embeddings. Local
sentence-transformers need no credential and spend no tokens. Mandating the HTTP
hop for a local model would add a network round-trip, a new failure mode, and a
torch dependency in a second image **in exchange for nothing**. The prior
proposal held both positions at once (centralise for credential control; run
locally to save money) without noticing they cancel.

Making the hop configurable resolves it honestly:

| Deployment | `EMBEDDING_BACKEND` | Why |
|---|---|---|
| Local dev / CI | `mock` | Offline, instant, no dependencies |
| Load test (role 8) | `local_st` in-process | No token spend, no hop polluting p95 |
| Demo with a real provider | `ai_service` | Credentials and budget in one place |

The interface is fixed either way, so search-service's code does not change when
the decision does — which is the property that actually matters.

## Consequences

**Good**

* One model client, one credential surface, one token budget, one circuit
  breaker. Role 6 never needs an OCI credential.
* Role 6 is unblocked immediately: `POST /embed` works today on the mock
  backend, offline.
* `EMBEDDING_DIM` mismatches are rejected at the boundary instead of being
  written into the pgvector column, where they are unsearchable and silent.
* The load test can avoid both token spend and an artificial network hop.

**Bad / accepted**

* Two places can produce vectors (ai-service, and search-service's `local_st`).
  Mitigated because they are selected by one variable and never both at once.
* When `ai_service` is selected, indexing gains a network dependency. Mitigated
  by batching (`MAX_EMBED_BATCH=96`) and by ai-service's own retries.
* **Vectors from different backends are not comparable.** Switching
  `EMBEDDING_BACKEND` requires a full re-index. This is true of any embedding
  change and is called out in the deployment runbook, not solved here.

## Notes

`POST /embed` takes `input_type: "document" | "query"`. Cohere-family models
project documents and queries into different spaces, and passing the wrong one
degrades retrieval **with no error at all**. The mock deliberately ignores the
parameter so both land in the same space offline.

The mock embedder in ai-service uses signed feature hashing over unigrams and
bigrams, so related texts are measurably closer than unrelated ones. This is a
deliberate improvement on search-service's `MockEmbedder`, a SHA-256 hash chain
whose cosine similarity is noise — useless for smoke-testing retrieval. Neither
is valid for reported metrics, and `run_evaluation.py` now refuses to write a
results file when `EMBEDDING_BACKEND=mock`.
