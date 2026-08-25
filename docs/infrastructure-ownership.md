# Infrastructure ownership map

One object, one owner. This table is the tie-breaker whenever it is unclear
who creates, changes or deletes something.

## Terraform owns (this repository)

| Area | Objects |
|---|---|
| Network | VCN, subnets, IGW/NAT/SGW, route tables, security lists, NSGs + rules |
| Compute platform | OKE cluster, node pools, API endpoint placement |
| Identity | Dynamic groups (nodes, workload pods), least-privilege policies |
| Registry | OCIR repositories (immutable tags) |
| Storage | documents/processed buckets, lifecycle rules |
| Data | OCI Database with PostgreSQL (feature-flagged) |
| Observability | Alert topic, subscriptions, alarms |
| Access ops | OCI Bastion (optional) |
| State | bootstrap-state bucket; all remote state objects |

Terraform does **not** own: anything created by Kubernetes (see below),
session objects, or hand-made console resources.

## Kubernetes owns

Deployments, ReplicaSets, Pods, ConfigMaps/Secrets, Services (including the
OCI load balancers they create — see [ADR-009]), Ingress, HPA, PDB,
NetworkPolicies, StorageClasses/PVCs (CSI-provisioned block volumes).

Teardown contract: delete these **first**, then run `terraform destroy`.

## CI/CD owns

Execution orchestration only: plan/apply workflows, plan artifacts,
deployment metadata, evidence export. CI has no standing write access to OCI
outside workflow runs gated on the `demo` environment approval.

## Queue decision pointer

Async processing uses Redis Streams containerized in-cluster locally and on
OKE (compose parity), behind an application-level queue abstraction so OCI
Queue can replace it without touching call sites — rationale lives in
[ADR-004]. Redis therefore needs **no data-subnet firewall rules**: pod-to-pod
traffic is governed by Kubernetes NetworkPolicies.

[ADR-009]: ./adr/ADR-009-load-balancer-ownership.md
[ADR-004]: ./adr/ADR-004-async-processing.md
