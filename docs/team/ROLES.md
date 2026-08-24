# Team Roles & Ownership — DocuMind AI

9 members. **Only the Cloud Lead and Cloud Deployment Engineer have OCI console access** — everyone else works locally (docker compose) or through pull requests.

| # | Role | Member | OCI access | Starts | Primary folders |
|---|------|--------|-----------|--------|-----------------|
| 1 | Cloud Lead | *(assigned)* | **YES** | **W0** | `terraform/` |
| 2 | Cloud Deployment Engineer | *(assigned)* | **YES** | **W0** | `kubernetes/`, `.github/workflows/`, OCIR |
| 3 | Backend Lead | TBD | no | **W0** | `services/api-gateway/`, `services/document-service/` |
| 4 | AI Engineer | TBD | no (uses OCI GenAI via role 1 setup) | W1 | `services/ai-service/`, `tests/rag-evaluation/` |
| 5 | Distributed Systems Engineer | TBD | no | W1 | `services/processing-service/`, queue design |
| 6 | Data / Search Engineer | TBD | no | W1 | `services/search-service/`, DB schema |
| 7 | Security / DevSecOps Engineer | TBD | no | **W0** | `docs/security/`, CI security gates |
| 8 | QA / Performance Engineer | TBD | no | W1 | `tests/`, k6 scripts, benchmark docs |
| 9 | Observability + Documentation Lead | TBD | no | W1 | dashboards, `docs/`, final presentation |

---

## 1. Cloud Lead — infrastructure owner

**Owns:** VCN, subnets, route tables, IGW/NAT/SGW, NSGs, security lists, IAM + dynamic groups, Vault, OKE infrastructure, database, Object Storage, Load Balancer, Terraform modules, remote state.

**Repo paths:** `terraform/modules/*`, `terraform/environments/dev`, `docs/assessment/`.

**First tasks (W0):** run the pre-flight checklist → record results in `docs/assessment/pre-flight-findings.md`; then build `terraform/modules/networking` (evolve the proven week-3 modules).

**Deliverables:** `terraform apply` from empty compartment reproduces the whole platform. Infra docs + architecture diagrams.

## 2. Cloud Deployment Engineer — OKE + OCIR + CI/CD

**Owns:** OKE node pools, OCIR repos, GitHub Actions, deployments/services/ingress, HPA, PDB, NetworkPolicies, probes, rolling updates, rollbacks, smoke tests.

**Repo paths:** `kubernetes/`, `.github/workflows/ci.yml`, `cd.yml`, `tests/smoke/`.

**First tasks (W0):** CI skeleton (exists — extend it), OCIR namespace + repos, deploy manifests structure. **Depends on role 1 for the cluster.**

**Deliverables:** `git push` → build → scan → OCIR → OKE → smoke-tested. Rolling + rollback demos.

## 3. Backend Lead — gateway + document service

**Owns:** API gateway (JWT, routing, validation, rate limiting), document service (upload, metadata, status), **API contracts for all 5 services**.

**Repo paths:** `services/api-gateway/`, `services/document-service/`, API spec (OpenAPI) in `services/README.md` or `docs/architecture/`.

**First tasks (W0):** define API contracts FIRST (unlocks roles 4, 5, 6, 8), service skeletons, monolith v0 for M0 baseline.

**Deliverables:** upload → `202 Accepted` → status flow working locally; JWT auth demo.

## 4. AI Engineer — OCI Generative AI brain

**Owns:** AI adapter, classification, extraction prompts, risk analysis, summarization, RAG generation, AI evaluation.

**Repo paths:** `services/ai-service/`, `tests/rag-evaluation/`, ADR-006.

**First tasks (W1):** adapter interface (configurable: `MODEL_NAME`, `EMBEDDING_MODEL`, `TEMPERATURE` — never hard-coded), prompts, golden dataset. Needs role 1 to confirm GenAI access; until then develop against a mock/local model behind the same interface.

**Deliverables:** risk scores with explanations, RAG answers with citations, evaluation report.

## 5. Distributed Systems Engineer — async pipeline

**Owns:** processing service, queue (Redis Streams per ADR-004), workers, retries, failure handling, idempotency, job states, dead-letter strategy.

**Repo paths:** `services/processing-service/`, queue design docs.

**First tasks (W1):** job contract + worker skeleton against role 3's API contracts; consumer groups; retry/backoff. Works closely with role 2 on HPA/queue-depth scaling later.

**Deliverables:** upload → queue → worker → COMPLETED with failure injection demo.

## 6. Data / Search Engineer — vector layer

**Owns:** DB schema, chunking, embeddings, vector indexing, similarity search, Top-K retrieval, RAG evaluation dataset (with role 4).

**Repo paths:** `services/search-service/`, schema migrations, ADR-005.

**First tasks (W1):** schema on the compose `postgres` (pgvector already provisioned), chunking + embedding pipeline locally.

**Deliverables:** semantic search + RAG retrieval working locally, then on OKE.

## 7. Security / DevSecOps Engineer — controls design

**Owns:** threat model, IAM least-privilege *requirements* (role 1 implements), K8s RBAC + NetworkPolicies specs, secrets strategy, JWT security, PII handling rules, container/CI security gates (tflint, checkov, Trivy policy).

**Repo paths:** `docs/security/threat-model.md`, CI security jobs, policy-as-code.

**First tasks (W0):** threat model draft + security requirements doc — **these gate roles 1, 2, 3 designs, so they come first.**

**Deliverables:** threat model, security validation evidence, CI gates that actually block.

## 8. QA / Performance Engineer — proof it works

**Owns:** functional + integration test suites, k6 load tests, P50/P95/P99/error-rate measurement, monolith vs OKE comparison, validation matrix evidence.

**Repo paths:** `tests/unit|integration|smoke|load|rag-evaluation/`, `docs/performance/`.

**First tasks (W1):** test plan + golden dataset + k6 harness skeleton against role 3's contracts; M0 baseline runs when monolith exists.

**Deliverables:** measured before/after tables — no invented numbers.

## 9. Observability + Documentation Lead — see it & tell it

**Owns:** Prometheus/Grafana, structured logging standards, OpenTelemetry tracing, alerts; plus documentation assembly, diagrams, demo script, final presentation.

**Repo paths:** monitoring manifests in `kubernetes/`, `docs/*` assembly, presentation materials.

**First tasks (W1):** logging/tracing standards doc (so roles 3–6 implement it correctly from day one), Grafana dashboard definitions.

**Deliverables:** live dashboards during demos, trace waterfalls, final deck.

---

## Weekly rhythm

- **Async:** PRs reviewed by folder owner within 24h.
- **Sync (weekly):** 30-min integration checkpoint — each role demos on `main`.
- **Rule:** blocked on OCI? Ask roles 1/2 in the weekly — never wait more than 2 days.
