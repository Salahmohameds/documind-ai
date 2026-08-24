# ADR-006 — AI Provider: OCI Generative AI behind an Adapter

**Status:** Accepted (pending region-access confirmation)
**Date:** 2026-08-24
**Deciders:** DocuMind team

## Problem

Which LLM/embedding provider powers classification support, extraction
assists, risk analysis, and RAG answers — and how do workloads authenticate?

## Options

1. Direct OpenAI/Azure OpenAI API keys stored as K8s secrets.
2. **OCI Generative AI via IAM dynamic-group auth**, behind an internal
   adapter interface with an OpenAI-compatible fallback.
3. Self-hosted open models on OKE.

## Decision

Option 2. All calls flow through an internal `AI Adapter`:

```text
services → AI Adapter → OCI Generative AI (chat + embeddings [+ rerank])
                     ↘ fallback: OpenAI-compatible endpoint (config-only swap)
```

Workload auth: OKE workload identity → Dynamic Group → least-privilege policy
scoped to the intern compartment.

## Why

* No external API credentials leave the tenancy — inference stays inside OCI;
  access governed by IAM, not pasted secrets.
* Adapter isolates provider specifics → model/provider swaps are config
  changes; tests mock the interface.
* Option 3 is out: no GPU budget/time; listed as future work.

## Contingency

If Week-0 verification shows Generative AI unavailable/not enabled for
`me-jeddah-1` or the tenancy: switch the adapter to the OpenAI-compatible
fallback via environment configuration; this ADR records why, keeping the
architecture narrative intact.

## Trade-offs

* Model catalog/limits differ from consumer APIs; prompt tuning required.
* Extra abstraction layer to maintain (small, single module).
