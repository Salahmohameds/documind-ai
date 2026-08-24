# ADR-001 — Microservices over Monolith

**Status:** Accepted
**Date:** 2026-08-24
**Deciders:** DocuMind team

## Problem

DocuMind must demonstrate cloud-native modernization. How many services, and
why decompose at all for a workload this size?

## Options

1. Keep the monolith on OKE (one deployment).
2. Decompose into 5 services (api-gateway, document, processing, ai, search).
3. Decompose into 8+ services including auth, workflow, notification.

## Decision

Option 2 — exactly five services. Auth is JWT middleware inside api-gateway;
workflow rules live inside the processing pipeline; notifications are events
in logs/queue.

## Why

* Async processing genuinely benefits: workers scale independently of the API
  and of AI latency spikes.
* Failure isolation: a stuck OCR job cannot take down document upload.
* Each service maps to a distinct scaling profile (CPU-bound vs IO-bound vs
  LLM-latency-bound) — makes HPA demos meaningful rather than cosmetic.
* Option 3 adds operational surface without adding graded value; explicitly
  listed as a non-goal.

## Trade-offs

* Distributed-systems complexity (network hops, tracing need) — mitigated by
  OpenTelemetry + correlation IDs.
* More images/pipelines than monolith — automated by shared CI template.
