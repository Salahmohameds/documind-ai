# ADR-003 — Private Networking for All Workloads

**Status:** Accepted
**Date:** 2026-08-24
**Deciders:** DocuMind team

## Problem

How exposed should worker nodes, databases, and internal services be?

## Options

1. Public worker subnet (fastest to debug).
2. Private workers + public LB only, NSG-scoped rules, NAT/SGW egress.

## Decision

Option 2. Only the load balancer lives in a public subnet. Workers, pods, and
the database are fully private. Outbound uses NAT Gateway (internet) and
Service Gateway (Object Storage). Every ingress/egress rule maps to a named
NSG path (lb→api, workers→data), no broad CIDRs.

## Why

* Database must never be internet-reachable — hard security requirement.
* Mirrors production-shaped design; strengthens the threat-model story.
* OCI layer (NSGs) + Kubernetes layer (NetworkPolicies) = defense in depth,
  each demonstrable independently.

## Trade-offs

* Debugging requires bastion/kubectl paths instead of direct SSH.
* NAT gateway adds cost; scoped to dev environment sizing.
