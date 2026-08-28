# Documentation

This is the index for every document in this repository outside the code itself —
architecture decisions, the project proposal, deployment runbooks, security posture,
and the final OCI deployment validation. Start here.

## Start here

| Document | What it is |
|---|---|
| **[PROJECT-PROPOSAL.md](PROJECT-PROPOSAL.md)** | The authoritative project document — objective, scope, architecture, CI/CD, observability, migration phases, testing methodology, cost/DR approach |
| **[validation/DOCUMIND_OCI_FINAL_DEPLOYMENT_VALIDATION.docx](validation/DOCUMIND_OCI_FINAL_DEPLOYMENT_VALIDATION.docx)** | **The final deliverable** — a full, live, read-only validation of the actual deployed OCI/OKE environment, section by section, every claim backed by a command and its real output |

## Architecture

| Document | Covers |
|---|---|
| [architecture/documind-oci-architecture.drawio](architecture/documind-oci-architecture.drawio) | The system architecture diagram (editable, draw.io) |
| [architecture/ai-service-contract.md](architecture/ai-service-contract.md) | ai-service's request/response contract |
| [adr/](adr/) | 9 Architecture Decision Records — microservices split (ADR-001), OKE choice (ADR-002), private networking (ADR-003), async processing (ADR-004), vector store (ADR-005), OCI Generative AI (ADR-006), HPA (ADR-007), embeddings boundary (ADR-008), load-balancer ownership (ADR-009) |
| [infrastructure-ownership.md](infrastructure-ownership.md) | Who owns which OCI resource — Terraform vs. hand-managed by the tenancy admin |

## Planning and delivery

| Document | Covers |
|---|---|
| [plan/TIMELINE.md](plan/TIMELINE.md) | Week-by-week delivery schedule |
| [plan/DEPLOYMENT-RUNBOOK.md](plan/DEPLOYMENT-RUNBOOK.md) | The burst deployment runbook |
| [plan/EVIDENCE-CHECKLIST.md](plan/EVIDENCE-CHECKLIST.md) | What evidence to capture during the burst |
| [team/ROLES.md](team/ROLES.md) | The 9 project roles and their ownership |

## Security

| Document | Covers |
|---|---|
| [security/threat-model.md](security/threat-model.md) | The threat model this design is built against |

## Validation and testing

| Document | Covers |
|---|---|
| **[validation/DOCUMIND_OCI_FINAL_DEPLOYMENT_VALIDATION.docx](validation/DOCUMIND_OCI_FINAL_DEPLOYMENT_VALIDATION.docx)** | **Live OCI/OKE deployment validation** — the final Phase 5 deliverable. Terraform module deep-dive, every Kubernetes resource verified live, internal/public connectivity tests, end-to-end functional test, security audit, and the definitive root-cause finding on the one open blocker. |
| [validation/test-strategy.md](validation/test-strategy.md) | The application-level test strategy (pre-deployment, local/compose) |
| [validation/test-cases.md](validation/test-cases.md) | The full test case catalogue |
| [validation/test-results.md](validation/test-results.md) | Local functional test results (corpus accuracy, PII/risk pipeline) — complements, and predates, the live deployment validation above |
| [validation/monolith-vs-oke.md](validation/monolith-vs-oke.md) | The monolith vs. OKE comparison that motivated the migration |

## Assessment (pre-deployment gap analysis)

| Document | Covers |
|---|---|
| [assessment/pre-flight-findings.md](assessment/pre-flight-findings.md) | Pre-flight findings before the burst |
| [assessment/DEPLOYMENT_BLOCKERS.md](assessment/DEPLOYMENT_BLOCKERS.md) | Known blockers going into deployment |
| [assessment/DEPLOYMENT_EVIDENCE_CHECKLIST.md](assessment/DEPLOYMENT_EVIDENCE_CHECKLIST.md) | Evidence checklist for the deployment attempt |
| [assessment/FINAL_PRE_DEPLOYMENT_READINESS.md](assessment/FINAL_PRE_DEPLOYMENT_READINESS.md) | Final go/no-go readiness assessment |

## Folder-level READMEs (outside `docs/`)

- [terraform/README.md](../terraform/README.md) — module conventions and usage
- [services/README.md](../services/README.md) — per-service local-run reference
- [kubernetes/README.md](../kubernetes/README.md) — manifest conventions (image tags, deploy-time substitutions)
- [tests/README.md](../tests/README.md) — test suite conventions

## Reading order for a first-time reviewer

1. [PROJECT-PROPOSAL.md](PROJECT-PROPOSAL.md) — what this project is and why
2. [adr/](adr/) — the architectural decisions and their rationale
3. **[validation/DOCUMIND_OCI_FINAL_DEPLOYMENT_VALIDATION.docx](validation/DOCUMIND_OCI_FINAL_DEPLOYMENT_VALIDATION.docx)** — what is actually deployed, live, right now, and what isn't yet
4. [validation/test-results.md](validation/test-results.md) — how the application logic itself was validated before deployment
