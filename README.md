# DocuMind AI — Final Graduation Project

**Cloud-Native AI Document Intelligence Platform on OCI**
Ejada Egypt Summer Internship 2026 — Cloud Build (OCI & Terraform track)

> We designed and implemented a cloud-native modernization journey for an AI
> document intelligence workload on OCI, starting from a measurable monolithic
> baseline and evolving it into a secure, observable, autoscaling microservices
> platform on OKE using Infrastructure as Code and CI/CD.

## Read this first

**[docs/PROJECT-PROPOSAL.md](docs/PROJECT-PROPOSAL.md)** — the complete,
authoritative project document: objective, scope/non-goals, AI features,
5-service architecture, OCI network & security design, Kubernetes design,
CI/CD, observability, migration phases M0–M5, testing methodology, cost/DR
approach, validation matrix, open decisions, and the Week-0 pre-flight
checklist.

## Quick facts

| Item | Value |
|------|-------|
| Services | 5 — `api-gateway`, `document`, `processing`, `ai`, `search` |
| AI provider | OCI Generative AI via adapter + IAM dynamic groups |
| Async | `202 Accepted` → queue → processing workers |
| Infra | Terraform modules (`networking`, `oke`, `iam`, `ocir`, storage, db, lb, monitoring) |
| Runtime | OKE private node pool, VCN-native CNI, NSGs + NetworkPolicies |
| Registry | OCIR, versioned tags, Trivy-gated |

## Status

| Milestone | Scope | Status |
|-----------|-------|--------|
| W0 | Pre-flight: GenAI access, quotas, stack decisions | **Next up** |
| M0 | Monolith baseline + k6 numbers | Pending |
| M1 | 5 services local (compose) | Pending |
| M2 | Terraform infra on OCI dev | Pending |
| M3 | CI/CD → OCIR → OKE live | Pending |
| M4 | Hardening (probes, HPA, netpol, PDB, Vault) | Pending |
| M5 | Tracing, RAG eval, perf comparison, recorded demos | Pending |

## Repository layout

See §28 of [the proposal](docs/PROJECT-PROPOSAL.md). Architecture Decision
Records live in [`docs/adr/`](docs/adr/) — ADR-001 through ADR-007.
