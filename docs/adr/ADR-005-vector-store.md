# ADR-005 — Vector Store

**Status:** Accepted
**Date:** 2026-08-25
**Deciders:** DocuMind team

## Problem

RAG requires storing and searching document embeddings. Which vector store should be used?

## Options

| Option                                    | Pros                                                                             | Cons                                                                         |
| ----------------------------------------- | -------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **A. PostgreSQL + pgvector**              | Simple; metadata + vectors in one DB; one backup story; low operational overhead | Less distinctive; vector index tuning required                               |
| **B. Oracle Database 23ai (VECTOR type)** | Oracle-native differentiator; strong OCI/Ejada alignment; SQL + vectors unified  | Higher operational/resource overhead for the current project scope           |
| **C. OCI OpenSearch**                     | Managed; search-oriented; k-NN support                                           | Additional service to operate; cost; unnecessary for the current corpus size |

## Decision

**PostgreSQL + pgvector is the final choice for the current implementation.**

The decision is based on its lower operational complexity, straightforward integration with the existing PostgreSQL infrastructure, and suitability for the project's current deployment scope and corpus size.

Oracle Database 23ai was not selected for this phase. This is an operational and project-scope decision, not a statement that Oracle 23ai is technically incapable of supporting the workload. No comparative benchmark between PostgreSQL + pgvector and Oracle Database 23ai was performed.

OCI OpenSearch was not selected because the current project corpus is relatively small and does not justify introducing a dedicated managed search service at this stage.

## Consequences

* PostgreSQL serves both relational metadata and vector data.
* The Search Service has a simple database dependency through PostgreSQL.
* Database backup and recovery remain centralized around PostgreSQL.
* PostgreSQL + pgvector is already implemented and running successfully through Docker Compose.
* The vector layer is abstracted behind the Search Service, allowing a different vector backend to be introduced later if project requirements change.
* RAG retrieval quality is evaluated separately through the project's RAG evaluation dataset and evaluation scripts.

