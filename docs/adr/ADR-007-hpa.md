# ADR-007 — Autoscaling Approach

**Status:** Accepted (KEDA as stretch)
**Date:** 2026-08-24
**Deciders:** DocuMind team

## Problem

How do workloads scale under load, and what signal should drive scaling?

## Options

1. Fixed replicas.
2. CPU-based HPA on all deployments.
3. Signal-appropriate scaling: HPA(CPU) for request-driven services +
   KEDA on queue depth for async workers.

## Decision

Baseline: **HPA with CPU targets** everywhere (api 65%, ai 70%, processing 65%,
search 65%) with min/max per §12 of the proposal. Stretch goal after M4:
**KEDA scaling processing workers on Redis Streams queue length**, which is
the technically correct signal for async work.

## Why

* Fixed replicas cannot demonstrate elasticity — a mandatory demo item.
* CPU-based HPA is native, zero extra components, reliable for the live demo;
  load test drives CPU predictably via busy endpoints + real pipeline jobs.
* Queue-depth scaling demonstrates deeper understanding but adds a KEDA
  install + config risk late in the timeline → stretch, not baseline.

## Trade-offs

* CPU is an imperfect proxy for LLM-bound latency (ai-service scales on CPU
  while its pain is upstream GenAI latency) — documented; mitigated by keeping
  min replicas ≥ 1 and PDBs.
* Scale-down flapping during demos handled with conservative stabilization
  windows so graphs read cleanly on presentation day.
