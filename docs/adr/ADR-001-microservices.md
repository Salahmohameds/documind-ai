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

## Amendment (2026-08-27) — frontend does not route through api-gateway for this demo

api-gateway's routes are all real and JWT-protected (`/auth/*`, proxy routes
for documents/search/ai, plus a `/qa` orchestration endpoint) — it is not a
stub. The frontend, however, has no real authentication anywhere yet
(sign-in/sign-up are entirely client-side mocked; no session/JWT is ever
issued or stored), and every api-gateway route requires a valid Bearer JWT
with no bypass. Wiring the frontend through the gateway therefore means
building real login/session handling first, not swapping URLs — a genuine
feature change that cannot safely be done and tested in the time available
before this burst (no live cluster or Docker to integration-test it).

**Decision for this demo:** frontend's server-side `/api/*` route handlers
continue calling document-service/search-service/ai-service directly (see
`frontend/documind/lib/server/backend.ts`), and are exposed via their own
`kubernetes/services/frontend-service.yaml` LoadBalancer. api-gateway is
still deployed and exposed via its own LoadBalancer
(`kubernetes/services/api-gateway-service.yaml`) so its JWT auth, proxying,
and `/qa` orchestration can be demonstrated directly (e.g. via Postman/curl),
independent of the frontend. This is a deliberate, documented deviation from
the original target diagram, not an oversight — revisit once the frontend's
auth flow is built out.
