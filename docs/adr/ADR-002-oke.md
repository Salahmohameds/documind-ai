# ADR-002 — Oracle Kubernetes Engine (OKE) as Runtime

**Status:** Accepted
**Date:** 2026-08-24
**Deciders:** DocuMind team

## Problem

Where should the modernized workload run on OCI?

## Options

1. **OKE managed node pool** (VCN-native pod networking).
2. Container Instances (serverless containers).
3. Compute VMs + docker-compose.

## Decision

Option 1: OKE with VCN-native CNI and a private managed node pool.

## Why

* Required by the program's mandatory outcomes (OKE deployment, HPA,
  rolling updates, self-healing demos).
* VCN-native pod networking gives pods real VCN addresses → NSGs can segment
  pod traffic directly (reuses proven week-3 module code).
* Managed node pool removes node lifecycle burden from interns.

## Trade-offs

* Highest cost of the three options (~control plane + nodes); accepted and
  analyzed in the cost section rather than hidden.
* Basic vs Enhanced cluster tiering limits some features; we stay within
  basic-tier capabilities (HPA, NetworkPolicies work fine).
