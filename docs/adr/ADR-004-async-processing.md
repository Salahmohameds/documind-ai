# ADR-004 — Asynchronous Queue Technology

**Status:** Proposed — final pick in Week 0
**Date:** 2026-08-24
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

Lean: **Redis Streams** (single Redis covers queue + rate limiting). Final
confirmation after Week-0 capacity check and team-skill review.

## Consequences

* Consumer-group based worker scaling; KEDA can scale on stream length
  (stretch goal).
* If durability requirements grow, migration path exists behind the internal
  job-producer interface.
