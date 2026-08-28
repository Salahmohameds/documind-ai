# DocuMind AI — Final Graduation Project

**Cloud-Native AI Document Intelligence Platform on OCI**
Ejada Egypt Summer Internship 2026 — Cloud Build (OCI & Terraform track)

> We designed and implemented a cloud-native modernization journey for an AI
> document intelligence workload on OCI, starting from a measurable monolithic
> baseline and evolving it into a secure, observable, autoscaling microservices
> platform on OKE using Infrastructure as Code and CI/CD.

## Read this first

**[docs/README.md](docs/README.md)** — the documentation index. Start there for
anything beyond this page.

**[docs/PROJECT-PROPOSAL.md](docs/PROJECT-PROPOSAL.md)** — the complete,
authoritative project document: objective, scope/non-goals, AI features,
5-service architecture, OCI network & security design, Kubernetes design,
CI/CD, observability, migration phases M0–M5, testing methodology, cost/DR
approach, validation matrix, open decisions, and the Week-0 pre-flight
checklist.

**[docs/validation/DOCUMIND_OCI_FINAL_DEPLOYMENT_VALIDATION.docx](docs/validation/DOCUMIND_OCI_FINAL_DEPLOYMENT_VALIDATION.docx)** —
the final deployment validation report: the burst happened, this is what is
actually live in OCI right now, verified section by section against the real
cluster and registry — architecture, Terraform modules, every Kubernetes
resource, security posture, internal/public connectivity, an end-to-end
functional test, and the one remaining open finding with its exact root cause.

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
| A — Prepare | Pre-flight · monolith baseline · services on compose · deploy-ready (images in OCIR, TF plan reviewed) | **Done** |
| B — Burst | terraform apply → deploy → full validation → evidence capture | **Done — see [final validation report](docs/validation/DOCUMIND_OCI_FINAL_DEPLOYMENT_VALIDATION.docx)** |
| C — Deliver | Perf/cost analysis · docs · ADRs · presentation | **In progress** |

5 of 6 services are live and verified on OKE, publicly reachable, with one
precisely-diagnosed open item (an unapplied Terraform IAM policy — see the
final validation report's §5.5/§14/§27). Destroy-and-verify-empty has not yet
been run for this burst.

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
