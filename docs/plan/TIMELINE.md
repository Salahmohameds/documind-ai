# Delivery Timeline — Prepare-First, Burst-Deploy Strategy

## Why this plan

OCI budget is limited and a running platform (OKE nodes, LB, NAT, database) is
expensive per day. So we **do not run infrastructure for weeks**. Instead:

1. **Prepare everything for free** — code, containers, manifests, CI, Terraform
   (plan-validated against the real tenancy), and full rehearsals on a local
   **kind** cluster (Kubernetes-in-Docker).
2. **One short paid deployment burst (~4–5 days)** — apply → deploy → test →
   capture ALL evidence → destroy.
3. **Deliver from recorded evidence** — analysis, docs, and presentation use
   the screenshots/videos/numbers captured during the burst.

> Rule: **after the burst there is no "retake" without paying again.** Every
> screenshot, video, and measurement must be on the checklist
> ([EVIDENCE-CHECKLIST.md](EVIDENCE-CHECKLIST.md)) before teardown starts.

---

## Phase overview

| Phase | Weeks | OCI cost | What happens |
|-------|-------|----------|--------------|
| **A — Prepare** | W0–W4 | ~zero (only trivial GenAI test calls) | All code, containers, manifests, CI, Terraform; rehearsals on docker compose + kind; images pushed to OCIR (OCIR storage is free) |
| **B — Deployment burst** | W5 (4–5 days) | **The only paid window** | terraform apply → CI/CD deploy → full validation → evidence capture → destroy + verify empty |
| **C — Deliver** | W6–W8 | zero | Performance/cost analysis from captured numbers, docs, ADRs, presentation, video editing |

---

## Phase A — Prepare (W0–W4, local only)

| Milestone | Weeks | Exit criteria | Lead roles |
|-----------|-------|---------------|-----------|
| **W0 pre-flight** | W0 | GenAI access confirmed (test call) · quotas confirmed · decisions D1–D5 closed · security requirements drafted | 1, 7 |
| **M0 monolith** | W1–W2 | Monolith runs in one container (resource-limited locally) · baseline k6 numbers recorded (local, caveats documented) | 3, 8 |
| **M1 local pipeline** | W2–W3 | 5 services on docker compose · upload → queue → classify/extract → RAG with citations → risk score works end-to-end locally | 3, 5, 6, 4 |
| **M2 deploy-ready** | W3–W4 | See burst readiness below | 1, 2 |

### M2 "deploy-ready" definition (the go/no-go for the burst)

- ☐ Terraform complete: `terraform validate` clean + **real `terraform plan` reviewed** (plan is read-only — free) attached to PR
- ☐ All 5 images built and **pushed to OCIR** (free) with version tags
- ☐ All k8s manifests **rehearsed on kind**: deploy, probes, HPA scaling, NetworkPolicies, PDB, rolling update, rollback, pod-delete self-healing — **recorded on kind as backup footage**
- ☐ CI green on `main`: gitleaks + trivy + tflint/checkov
- ☐ RAG evaluation run locally; golden dataset frozen
- ☐ Budget alert configured in OCI (role 1) before day 1
- ☐ Evidence checklist printed; screenshot naming agreed (`NN-description.png` like weeks 1–3)
- ☐ Demo script rehearsed end-to-end at least once

## Phase B — Deployment burst (W5, ~4–5 days)

Full runbook: [DEPLOYMENT-RUNBOOK.md](DEPLOYMENT-RUNBOOK.md)

| Day | Focus | Owner |
|-----|-------|-------|
| 1 | `terraform apply` (network → OKE → datastores) · verify VCN/NSGs/OKE in console · screenshots | 1 (+2) |
| 2 | CI/CD deploy all services → LB live → smoke tests · fix issues (buffer built in) | 2 |
| 3 | **Evidence day**: functional tests · k6 official load runs · HPA live demo · self-healing timed · rolling update + rollback · RAG eval vs real GenAI · Grafana + tracing captures · monolith-vs-OKE numbers | 8 (+ all) |
| 4 | Buffer: re-run/record anything missing or flaky | all |
| 5 | **Teardown**: delete k8s workload (LB first!) → `terraform destroy` → post-destroy inventory proof → compartment verified empty | 1, 2 |

**Cost guardrails:** budget alert day 0 · smallest viable node pool (2 × E4.Flex 1 OCPU) · LB deleted before nodes · same-day destroy verification (orphaned LBs/NAT gateways are the classic money leaks).

## Phase C — Deliver (W6–W8, zero OCI cost)

| Milestone | Exit criteria | Lead roles |
|-----------|--------------|-----------|
| **M-final docs** | Performance comparison + cost analysis written from burst numbers · DR docs · ADRs finalized | 8, 9, 1 |
| **Presentation** | Demo video edited · slides · walkthrough rehearsed · validation matrix fully ✅ with evidence links | 9 | 

## Weekly rhythm (unchanged)

- PRs reviewed by folder owner within 24h · 30-min weekly integration checkpoint · blocked on OCI → ask roles 1/2, never wait >2 days.
