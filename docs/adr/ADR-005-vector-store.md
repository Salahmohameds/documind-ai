# ADR-005 — Vector Store

**Status:** Proposed — final decision after Week-0 capacity check
**Date:** 2026-08-24
**Deciders:** DocuMind team

## Problem

RAG requires storing and searching document embeddings. Which store?

## Options

| Option | Pros | Cons |
|--------|------|------|
| **A. PostgreSQL + pgvector** | Simplest; metadata + vectors in one DB; one backup story; low RAM | Less distinctive; HNSW tuning manual |
| B. Oracle Database 23ai (VECTOR type) | Oracle-native differentiator (Ejada context); SQL+vectors unified; strong OCI story | 23ai Free container needs ~2–3 GB RAM minimum; heavier ops on small intern nodes |
| C. OCI OpenSearch | Managed, search-oriented, k-NN support | Another service to operate; cost; overkill for ~50-doc corpus |

## Decision

Default lean: **Option A (pgvector)**. Option B is chosen instead if the
Week-0 check shows worker-node capacity comfortably fits it — the Oracle
alignment is a genuine plus in this internship's context. Option C rejected
for scale reasons.

Evaluation criteria applied: performance, complexity, cost, OCI integration,
operational overhead.

## Consequences

* One relational engine serves metadata + vectors → simpler NetworkPolicy
  path (search-service → db only) and DR plan (single pg_dump/WAL story).
* Corpus is small (~50 docs × chunks); any option performs fine at this size —
  decision is therefore dominated by operational weight, not raw performance.
