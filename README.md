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

## Delivery strategy — prepare first, burst-deploy

OCI budget is limited, so the platform is **never left running**: everything is
prepared locally for free (compose, **kind** cluster rehearsals, Terraform
plan-validated, images pushed to OCIR), then deployed in **one short paid
burst (~4–5 days)** — apply → deploy → test → capture all evidence → destroy.

- Plan: [docs/plan/TIMELINE.md](docs/plan/TIMELINE.md)
- Burst runbook: [docs/plan/DEPLOYMENT-RUNBOOK.md](docs/plan/DEPLOYMENT-RUNBOOK.md)
- Evidence capture list: [docs/plan/EVIDENCE-CHECKLIST.md](docs/plan/EVIDENCE-CHECKLIST.md)

## Status

| Phase | Scope | Status |
|-------|-------|--------|
| A — Prepare (W0–W4) | Pre-flight · monolith baseline · 5 services on compose · deploy-ready (kind-rehearsed, images in OCIR, TF plan reviewed) | **W0 in progress** |
| B — Burst (W5, ~5 days) | terraform apply → deploy → full validation → evidence capture → destroy + verify empty | Pending |
| C — Deliver (W6–W8) | Perf/cost analysis from burst numbers · docs · ADRs · presentation · video | Pending |

## Team

9 roles — see **[docs/team/ROLES.md](docs/team/ROLES.md)** for ownership,
start weeks, and folder responsibilities. Only the Cloud Lead and Cloud
Deployment Engineer hold OCI access. Timeline: [docs/plan/TIMELINE.md](docs/plan/TIMELINE.md).
Contribution rules: [CONTRIBUTING.md](CONTRIBUTING.md).

## Repository layout

See §28 of [the proposal](docs/PROJECT-PROPOSAL.md). Folder-level conventions:
[terraform/](terraform/README.md) · [services/](services/README.md) ·
[kubernetes/](kubernetes/README.md) · [tests/](tests/README.md).
Architecture Decision Records live in [`docs/adr/`](docs/adr/) — ADR-001 through ADR-007.
