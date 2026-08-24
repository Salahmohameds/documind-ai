# DocuMind AI — Final Graduation Project Proposal

**Cloud-Native AI Document Intelligence Platform on OCI**

| Field | Value |
|-------|-------|
| Program | Ejada Egypt Summer Internship 2026 — Cloud Build |
| Track | OCI & Terraform |
| Student | Salah Abdelhady (Intern-18) |
| Tenancy | ociejada |
| Compartment | `intern-18-salah-abdelhady-cmp` |
| Region | `me-jeddah-1` |
| Document version | 1.0 — 2026-08-24 |
| Status | Approved scope — pending Week-0 pre-flight checks |

---

## 0. Positioning Statement

We designed and implemented a cloud-native modernization journey for an AI
document intelligence workload on OCI, starting from a measurable monolithic
baseline and evolving it into a secure, observable, autoscaling microservices
platform on OKE using Infrastructure as Code and CI/CD.

The goal is **not** "we deployed an application on OKE".

The goal is to demonstrate the full engineering lifecycle:

```text
ASSESS → ARCHITECT → PROVISION → CONTAINERIZE → MODERNIZE → SECURE
      → DEPLOY → OBSERVE → SCALE → RECOVER → VALIDATE → MEASURE
```

The **AI is the workload; the Cloud Architecture is the hero.** This is an OCI &
Terraform Cloud Build internship deliverable first, an AI product second.

---

## 1. Objective & Success Criteria

Build DocuMind AI — an intelligent document processing platform — in two stages:

1. **Stage 1 (Baseline):** containerized monolith, load-tested, measured.
2. **Stage 2 (Target):** 5 microservices on OKE with Terraform-provisioned,
   secured, observable infrastructure.

### Success criteria

| # | Criterion | Evidence |
|---|-----------|----------|
| S1 | Full pipeline works end-to-end | Upload → async process → classify → extract → index → RAG answer with citations |
| S2 | Infrastructure is fully reproducible | `terraform apply` from empty compartment recreates everything |
| S3 | Performance comparison uses real numbers | k6 results for monolith vs microservices (P50/P95/P99/error rate) |
| S4 | Platform survives failure injection | Pod deletion → self-healing timed and recorded |
| S5 | Autoscaling demonstrated live | HPA scales under k6 load, scale-down observed |
| S6 | Security is layered and verified | NSG + NetworkPolicy + IAM least privilege + Vault + image scanning evidence |
| S7 | AI quality is measured, not claimed | Golden-set RAG evaluation (hit rate, faithfulness, latency) |
| S8 | Decisions are documented as ADRs | 7 ADRs with options, trade-offs, decisions |

---

## 2. Scope

### In scope (exactly 5 AI features)

1. Document upload (Invoice, Contract)
2. Classification + structured extraction
3. PII detection (deterministic)
4. Contract risk analysis (flagship feature)
5. RAG-based Q&A with citations

### Non-Goals

This project intentionally does **not** include:

* Multi-region production deployment
* Service mesh
* Model training / fine-tuning
* Mobile application
* Complex multi-agent architecture
* Large frontend / enterprise UI
* 10+ microservices
* Enterprise analytics platform

Scope discipline is a deliberate architectural statement, not a limitation.

---

## 3. Application Overview

A user uploads PDF documents (invoices or contracts). The platform stores the
file, processes it asynchronously, and exposes classification results, extracted
structured data, risk scores, and semantic search / RAG Q&A.

### Minimal UI contract

The UI is deliberately one page:

```text
┌──────────────────────────────────────────┐
│              DocuMind AI                 │
├──────────────────────────────────────────┤
│  Upload Document                         │
│  [ contract.pdf ] [ Upload ]             │
│                                          │
│  Status: Processing...                   │
│                                          │
│  Ask about your documents:               │
│  [ What are the payment terms? ]         │
│                                          │
│  Answer: ...                             │
│  Sources: contract_01.pdf - Page 4       │
└──────────────────────────────────────────┘
```

Hard timebox: ~2 days total. Candidate stacks: Streamlit (fastest) or minimal
Vite + React. Decision tracked in the Open Decisions table (§26).

---

## 4. AI Capabilities

### 4.1 Document Classification

```text
invoice.pdf   → INVOICE
contract.pdf  → CONTRACT
```

Classification determines the processing path — we do not send every operation
blindly to an LLM.

### 4.2 Structured Information Extraction

Invoice example:

```json
{
  "vendor": "ABC Corp",
  "invoice_number": "INV-1024",
  "total": 15000,
  "currency": "EGP",
  "due_date": "2026-09-01"
}
```

Contract example:

```json
{
  "parties": ["Company A", "Company B"],
  "start_date": "2026-01-01",
  "end_date": "2027-01-01",
  "payment_terms": "60 days",
  "termination_notice": "90 days"
}
```

### 4.3 PII Detection

Detected entities: email, phone, national ID, bank account, address.

Engineering position: use deterministic techniques (regex / Presidio) for
predictable patterns instead of consuming LLM resources unnecessarily.
Optional redaction output for the security demo.

### 4.4 Risk Analysis — flagship feature

Contracts receive a score plus categorized findings:

```text
Risk Score: 72/100 — HIGH RISK

• Automatic renewal detected          (Legal)
• Short termination notice            (Legal)
• High financial liability            (Financial)
```

Categories: Financial / Legal / Operational. Each finding includes the model's
explanation so results are auditable.

### 4.5 RAG Pipeline

Indexing:

```text
Document → Text Extraction → Chunking → Embeddings → Vector Store
```

Query:

```text
Question → Embedding → Vector Search → Top-K chunks
        → OCI Generative AI → Answer + Citations (document, page)
```

---

## 5. AI Provider Strategy — OCI Generative AI

All inference goes through an internal adapter:

```text
Application services → AI Adapter → OCI Generative AI
                                   ↘ (fallback: OpenAI-compatible endpoint)
```

Key properties:

* **Provider abstraction** — swap models/providers via configuration only.
* **IAM-native auth where possible:** OKE workload → Dynamic Group → IAM policy
  → Generative AI. No hard-coded external API keys.
* Chat + embeddings (+ rerank if available) from hosted pretrained models.

> Talking point: *AI inference remains inside the OCI environment and access is
> controlled through IAM rather than external credentials.*

**Pre-flight requirement:** confirm Generative AI availability for
`me-jeddah-1`, tenancy enablement, and limits before M1 (see §27).

---

## 6. Data Stores

### 6.1 Object Storage

Raw document files + processed artifacts. Bucket naming:

| Bucket | Content |
|--------|---------|
| `documind-documents-{env}` | Original uploads |
| `documind-artifacts-{env}` | Extracted text, JSON results |

### 6.2 Vector Store — ADR-005 (pending final decision)

| Option | Pros | Cons |
|--------|------|------|
| A. PostgreSQL + pgvector | Simplest, metadata + vectors in one store, low overhead | Less "Oracle story" |
| B. Oracle Database 23ai VECTOR | Oracle-native differentiator, strong OCI alignment | Heavier footprint (~2–3 GB RAM), more operational care on small nodes |
| C. OCI OpenSearch | Search-oriented, scalable | Another cluster to operate; overkill at this scale |

Decision criteria: performance, complexity, cost, OCI integration, operational
overhead. Default lean: **pgvector**, unless node capacity comfortably fits
23ai Free after the quota check.

### 6.3 Queue — ADR-004 (pending final decision)

Recommendation: **Redis Streams** (Redis is already needed for rate limiting;
one less system). RabbitMQ acceptable if team expertise favors it. Kafka is
explicitly rejected as overkill.

---

## 7. Microservices Architecture

Exactly **5 services**:

```text
                         ┌─────────────────┐
                         │    Frontend     │
                         └────────┬────────┘
                                  ▼
                         ┌─────────────────┐
                         │  API Gateway    │
                         │ JWT / Routing   │
                         └────────┬────────┘
             ┌────────────────────┼────────────────────┐
             ▼                    ▼                    ▼
      Document Service     Processing Worker       AI Service
             │                    │                    │
             └────────────┬───────┴────────────────────┘
                          ▼
                   Search Service
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
          Vector Store        Object Storage
```

### Responsibilities

| Service | Responsibilities | Key endpoints |
|---------|------------------|---------------|
| `api-gateway` | Routing, JWT auth, request validation, rate limiting, centralized entry point | `POST /auth/login`, proxy `/*` |
| `document-service` | Upload, metadata, processing status, Object Storage integration | `POST /documents`, `GET /documents/{id}`, `GET /documents/{id}/status` |
| `processing-service` | Async job consumer, text extraction, classification, structured extraction, PII detection | queue consumer; `/liveness`, `/readiness` |
| `ai-service` | OCI Generative AI calls, risk analysis, summarization, AI orchestration | `POST /analysis/risk`, `POST /summarize` |
| `search-service` | Chunking/indexing, embeddings, vector search, RAG retrieval | `POST /index`, `POST /query`, `GET /search` |

Authentication lives inside the gateway in v1 (JWT + two roles: `user`,
`admin`). This is sufficient for the RBAC validation item without a dedicated
auth service.

---

## 8. Asynchronous Processing

```text
Upload → Document Service → Create Job → Queue
      → Processing Worker → AI Service → Search indexing → COMPLETED
```

* API immediately returns **`202 Accepted`** with a document/job ID.
* Job states: `RECEIVED → PROCESSING → COMPLETED | FAILED`.
* Failed jobs retry with backoff; terminal failures land in a dead-letter path.
* Benefits: UX, failure isolation, retries, independent worker scaling,
  backpressure, and a natural Kubernetes autoscaling demonstration.

---

## 9. Target OCI Architecture

```text
                         INTERNET
                            │
                            ▼
                   OCI Load Balancer (flexible)
                            │
                            ▼
                 OKE Cluster — Private Nodes
        ┌───────────────────────────────────────┐
        │  ns: documind                         │
        │  api-gateway · document · processing  │
        │  ai-service · search-service          │
        └──────────────────┬────────────────────┘
                           │
        ┌──────────────────┼───────────────────┐
        ▼                  ▼                   ▼
  Object Storage    PostgreSQL/pgvector    OCI Vault
                                            (secrets)

  OCI Generative AI  ◀── IAM Dynamic Group ── OKE workloads
```

### OCI service mapping

| OCI Service | Purpose in project |
|-------------|--------------------|
| OKE | Kubernetes runtime for all 5 services |
| Flexible Load Balancer | Public HTTPS entry point |
| VCN + IGW/NAT/SGW | Network foundation (reuses week-3 module pattern) |
| NSGs | Workload-scoped network rules |
| Object Storage | Document storage + Terraform remote state |
| OCIR | Container image registry |
| Vault | Secrets source of truth |
| Generative AI | LLM + embeddings via IAM auth |
| Logging/Monitoring | Platform observability integration |

---

## 10. Network Design

### Subnet plan (draft — distinct from week 1/2/3 ranges)

| Resource | Name | CIDR |
|----------|------|------|
| VCN | `dm-vcn` | `10.20.0.0/16` |
| Public LB subnet | `dm-public-subnet` | `10.20.1.0/24` |
| OKE workers subnet | `dm-workers-subnet` | `10.20.10.0/24` |
| OKE pods subnet (VCN-native CNI) | `dm-pods-subnet` | `10.20.11.0/24` |
| Data subnet (DB) | `dm-data-subnet` | `10.20.30.0/24` |

Worker nodes have **no public IPs**.

### Gateways

| Gateway | Used for |
|---------|----------|
| Internet Gateway | Controlled public ingress path (via LB) |
| NAT Gateway | Private nodes' outbound internet (image pulls not from OCIR, OS patches) |
| Service Gateway | Private access to Object Storage (and other supported OCI services) |

### NSG matrix (draft)

| NSG | Ingress | Egress |
|-----|---------|--------|
| `dm-nsg-lb` | 443, 80 from `0.0.0.0/0` | To `dm-nsg-api` app ports only |
| `dm-nsg-api` (workers) | App port from `dm-nsg-lb`; internal ports from pods NSG | 443 via NAT/SGW; DB port to `dm-nsg-data`; inter-service ports |
| `dm-nsg-data` | DB port (5432/1521) from workers NSG **only** | Response traffic |

No broad CIDR rules; every rule maps to a named workload path. The database is
never reachable from the internet.

---

## 11. Security Architecture — Defense in Depth

| Layer | Controls |
|-------|----------|
| OCI network | VCN segmentation, private subnets, NSGs, route tables, IGW/NAT/SGW |
| Identity (IAM) | Least-privilege policies per dynamic group; no admin for workloads |
| Kubernetes | NetworkPolicies, RBAC, Secrets, SecurityContexts, resource limits, PDBs |
| Application | JWT, authorization roles, input validation, rate limiting |
| Supply chain | tflint, checkov (IaC) · Trivy (images) · dependency scanning |
| Data | Private DB subnet, PII detection, Vault-managed credentials |

### IAM least privilege (example shape)

```text
Allow dynamic-group dg-documind-workers to manage objects
  in compartment intern-18-salah-abdelhady-cmp
  where any {target.bucket.name = 'documind-documents-dev',
             target.bucket.name = 'documind-artifacts-dev'}

Allow dynamic-group dg-documind-workers to use generative-ai-family
  in compartment intern-18-salah-abdelhady-cmp

Allow dynamic-group dg-documind-ci to read repos in tenancy
  where request.operation = 'READ_CONTAINER_REPO'
```

Workload permission follows workload responsibility: the processing worker can
touch its buckets and call GenAI — it cannot modify the VCN or cluster.

### Secrets flow

```text
OCI Vault (source of truth)
    ↓ sync (manual/scheduled; External Secrets Operator = stretch)
Kubernetes Secret (namespace documind)
    ↓ mounted env
Pod
```

Never in GitHub, never baked into images.

### Threat model (summary — full version in `docs/security/threat-model.md`)

| Threat | Mitigation |
|--------|------------|
| Public worker nodes | Private subnets, no public IPs |
| Excessive IAM | Per-workload dynamic groups + narrow policies |
| Secret leakage | OCI Vault → K8s secrets; gitignore discipline |
| Vulnerable container | Trivy scan gates in CI |
| Terraform misconfiguration | Checkov + plan review before apply |
| Pod-to-pod lateral movement | Default-deny NetworkPolicies + explicit allows |
| Unauthorized API access | JWT + role checks at gateway |
| API abuse | Rate limiting at gateway |
| Data exposure | PII detection (+ optional redaction) |
| Internet-exposed DB | Private data subnet + NSG source restriction |
| Malicious image | OCIR repo scanning + signed versioned tags |

---

## 12. Kubernetes Design

Namespace: `documind`. Per workload: Deployment, Service, ConfigMap (where
appropriate), Secret reference, resource config, probes.

### Health probes

Every service exposes `/liveness` and `/readiness`.

* Liveness — is the container alive? (restart on fail)
* Readiness — can this pod safely receive traffic? (no routing on fail)

Running ≠ healthy; probes enforce that distinction.

### Resources (initial draft — tuned during load tests)

| Service | Requests | Limits |
|---------|----------|--------|
| api-gateway | 250m / 256Mi | 500m / 512Mi |
| document-service | 250m / 512Mi | 500m / 1Gi |
| processing-service | 500m / 512Mi | 1000m / 1Gi |
| ai-service | 500m / 512Mi | 1000m / 1Gi |
| search-service | 250m / 512Mi | 500m / 1Gi |
| postgres (pgvector, if self-hosted) | 500m / 1Gi | 1000m / 2Gi |

### Autoscaling

| Workload | Min | Max | Signal |
|----------|-----|-----|--------|
| api-gateway | 1 | 5 | CPU 65% |
| processing-service | 1 | 10 | queue depth (KEDA — stretch) else CPU |
| ai-service | 1 | 4 | CPU 70% |
| search-service | 1 | 3 | CPU 65% |

CPU-based HPA is the baseline; KEDA on Redis Streams queue length is the
correct signal for async workers and is a stretch goal.

### NetworkPolicies

Default-deny in namespace, then explicit allow paths:
api→document/search, processing→ai/search/object-storage, search→vector-db.
API cannot reach the database directly.

### PodDisruptionBudgets

`minAvailable: 1` for stateless user-facing deployments — supports the
availability/resilience discussion during rolling updates and node drain.

### SecurityContext (all pods)

`runAsNonRoot: true`, read-only root filesystem where possible, dropped Linux
capabilities, no privilege escalation.

---

## 13. Container & Registry Strategy

Dockerfile standards for all five images:

* Multi-stage builds
* Minimal base (alpine/distroless)
* Non-root user
* Health endpoints built in
* Environment-based configuration
* No secrets in layers

Registry: **OCIR** — `<region>.ocir.io/<object-namespace>/documind/<service>:<semver>`
plus immutable git-SHA tags. `latest` is never used for deploys.

```text
Developer → GitHub → CI build+scan → OCIR → OKE pulls → Pods
```

---

## 14. CI/CD Pipeline (GitHub Actions)

### ci.yml — on PR

```text
Lint → Unit tests → tflint → checkov
    → Docker build (all changed services)
    → Trivy scan (fail on HIGH/CRITICAL)
```

### cd.yml — on merge to main

```text
Push images to OCIR (versioned tags)
  → terraform plan (infra changes; manual approve for apply)
  → Deploy manifests/Helm to OKE
  → Smoke tests (/readiness across services, upload happy path)
```

Secrets for the pipeline (OCIR token, kubeconfig) live in GitHub Actions
secrets — documented, rotated, least-scoped. Rollback remains
`kubectl rollout undo` regardless of deployment method.

---

## 15. Terraform Design

Reusable modules + thin environment roots (same philosophy as weeks 1–3):

```text
terraform/
├── environments/
│   ├── dev/
│   └── prod/
└── modules/
    ├── networking/       # VCN, subnets, IGW/NAT/SGW, route tables
    ├── oke/              # cluster, node pool, NSGs (evolved from week-3 oke module)
    ├── iam/              # dynamic groups + policies per workload
    ├── ocir/             # repositories + retention
    ├── object-storage/   # buckets + retention rules
    ├── database/         # pgvector/23ai compute + subnet placement
    ├── load-balancer/    # flexible LB (or OKE-managed LB annotations)
    └── monitoring/       # alarm policies, log groups
```

Design rules carried over from the internship repos: environment roots own the
provider; modules take no env-specific OCIDs; freeform tags
(`Project=DocuMind`, `Env`, `ManagedBy`) on everything; `name_prefix = dm-*`.

### Remote state

OCI Object Storage S3-compatible backend (`s3://w-documind-tfstate/<env>/…`),
one-time bootstrap bucket exactly like `bootstrap-state` in the existing repo.
Customer Secret Key credentials via local env vars only; `backend.hcl` is
gitignored.

---

## 16. Observability

Three signals, all correlation-linked by request ID / trace ID.

### Metrics — Prometheus + Grafana

* Infra: node CPU/memory/network/health
* K8s: pod counts, restarts, HPA activity, deployment status
* App: request count, latency histogram, error rate, queue depth,
  processing duration, AI call latency

Dashboards replace a custom analytics UI. Key board: requests/min, P95,
error rate, replicas vs HPA target, queue depth.

### Logs — structured JSON (standard fields)

```json
{
  "timestamp": "2026-08-24T10:20:00Z",
  "service": "processing-service",
  "level": "INFO",
  "request_id": "req-123",
  "document_id": "doc-456",
  "trace_id": "4bf92f35...",
  "event": "processing_completed",
  "duration_ms": 1830
}
```

Aggregated via Loki (or OCI Logging connector).

### Tracing — OpenTelemetry

OTel SDK in each service → collector → Jaeger/Tempo. Example span breakdown:

```text
Request total 2.16s
├── api-gateway       20ms
├── document-service  40ms
├── processing       180ms
├── ai-service      1.8s   ← expected dominant span
└── search-service   120ms
```

---

## 17. Resilience Demos

### Self-healing

```bash
kubectl delete pod <processing-pod>
watch kubectl get pods
```

Expected: replica deficit detected → replacement scheduled → readiness gate →
traffic restored. Record wall-clock recovery time (feeds §18 table).
Recorded video backup mandatory.

### Rolling update + rollback

```bash
kubectl set image ... ai-service:v2   # v2 contains deliberately broken readiness
kubectl rollout status deployment/ai-service   # stalls
kubectl rollout undo deployment/ai-service
kubectl rollout history deployment/ai-service
```

Demonstrates safe release mechanics end-to-end.

---

## 18. Performance & Load Testing Methodology

Tool: **k6**. Fixed synthetic corpus (~50 generated invoices/contracts, no real
PII) and fixed request mix.

### Protocol (written before any test runs)

1. Same k6 script, same dataset, same VU profile for both architectures.
2. Baseline: monolith single container on an OCI Compute VM (E4.Flex sized
   comparably to one worker node) + local Postgres/Redis containers.
3. Target: 5 microservices on OKE.
4. 3 runs each; report median; record CPU/mem during runs.
5. Fairness caveats documented (single node vs cluster, cold starts, etc.).

### Metrics captured

Requests/sec, avg latency, P50/P95/P99, error rate, CPU %, memory %, pod count,
recovery time after pod kill.

### Results template

| Metric | Monolith | OKE microservices |
|--------|---------:|------------------:|
| Avg latency | measured | measured |
| P95 | measured | measured |
| P99 | measured | measured |
| Requests/sec | measured | measured |
| Error rate | measured | measured |
| Recovery time | measured | measured |

Purpose is not "microservices are faster" — it is explaining *why* the
cloud-native architecture behaves differently under load and failure.

---

## 19. Migration Plan

### Phases (documentation view)

| Phase | Name | Content |
|-------|------|---------|
| 0 | Assessment | Dependencies, storage, config, network, runtime analysis of the monolith design |
| 1 | Monolith baseline | Single-container DocuMind + baseline k6 numbers |
| 2 | Containerization | Production-grade image practices |
| 3 | OCI infra | Terraform: VCN/subnets/NSGs/gateways/IAM/OKE/OCIR/storage/DB |
| 4 | Decomposition | Split into 5 services behind the queue |
| 5 | OKE deployment | Manifests/Helm, namespace documind |
| 6 | CI/CD | Automated build→scan→push→deploy |
| 7 | Hardening | Probes, limits, NetworkPolicies, PDB, Vault, IAM, scanners |
| 8 | Validation | Functional/integration/security/load/failure/autoscaling suites |

### Delivery milestones (execution view)

| Milestone | Exit criteria | Target |
|-----------|---------------|--------|
| W0 pre-flight | GenAI region/access confirmed; quotas confirmed; stack choices locked (§26) | Week 0 |
| M0 | Monolith runs locally + on VM; baseline metrics recorded | W1–W2 |
| M1 | 5 services on docker-compose; full pipeline works; RAG answers with citations | W3–W4 |
| M2 | `terraform apply` brings up VCN+OKE+data stores in dev | W4–W5 |
| M3 | CI builds/pushes/scans; CD deploys; app live through LB | W5–W6 |
| M4 | Probes, limits, HPA, NetworkPolicies, PDB, Vault wired; security scans gating | W6–W7 |
| M5 | Tracing, RAG eval harness, perf comparison runs, all demos recorded | W7–W9 |
| Final | Docs complete, ADRs final, presentation rehearsed | W9 + **buffer** |

M2 can proceed in parallel with M1 if platform/app tracks are split between
team members. A buffer week before presentation day is mandatory.

---

## 20. Validation Matrix

| ✓ | Check | Method |
|---|-------|--------|
| ☐ | Upload document (happy path) | curl/UI + status polling to COMPLETED |
| ☐ | Authentication required | 401 without JWT |
| ☐ | Authorization enforced | 403 wrong role |
| ☐ | Async contract honored | 202 Accepted + job states |
| ☐ | AI classification correct | labeled sample set ≥ 95% |
| ☐ | Extraction schema valid | JSON-schema validation of outputs |
| ☐ | Risk analysis produced | contract sample → score + findings |
| ☐ | PII detected | seeded entities found (regex ground truth) |
| ☐ | Semantic search relevant | golden queries hit expected doc |
| ☐ | RAG answer cites sources | citations present + accurate page refs |
| ☐ | Unauthorized network blocked | NetworkPolicy test pod denied to DB |
| ☐ | DB not internet-reachable | external probe fails; NSG audit |
| ☐ | Pod self-healing | delete pod → recovery timed |
| ☐ | HPA scale up/down | k6 load → replicas rise/fall |
| ☐ | Rolling update zero downtime | continuous k6 during deploy, no error spike |
| ☐ | Rollback works | broken v2 → undo → healthy v1 |
| ☐ | CI blocks vulnerable image | seeded CVE fails pipeline |
| ☐ | IaC scanning active | checkov finding visible in PR |
| ☐ | State reproducibility | destroy → apply → platform restored |

---

## 21. Cost Analysis Approach

Compare monthly/daily cost of:

* **Before:** 1 × Compute VM + storage + AI calls
* **After:** OKE control plane + 2–3 worker nodes + LB + DB + Object Storage + AI + monitoring

Derived figures: cost/day, cost/pod/day (from utilization during HPA demo),
cost per 100 documents processed.

Framing: the conclusion evaluates **cost vs scalability vs resilience vs
operational complexity** — not "microservices are cheaper." Prices from public
OCI price list + measured utilization; assumptions stated inline.

---

## 22. Disaster Recovery

Documentation-first (no multi-region build):

| Concept | Our definition/target |
|---------|----------------------|
| RPO | ≤ 15 min for metadata DB (continuous archiving/WAL); 0 for raw docs (Object Storage durability) |
| RTO | ≤ 60 min: Terraform re-provision + image pull + manifest apply + restore DB backup |

Covered topics: DB backup/restore (tested once), Object Storage durability +
versioning, full infra recreation from Terraform, images persisted in OCIR,
manifests in git, region-failure discussion, DR runbook outline.

Proof point: tear down the dev environment and rebuild it entirely from code
in a recorded session.

---

## 23. RAG Evaluation Harness

Golden dataset: **15–20 items**, each `{question, expected_answer, expected_document, expected_section}`
as JSONL, authored against the synthetic corpus.

Measured per run:

| Metric | Definition |
|--------|------------|
| Retrieval hit@k | Expected chunk/document appears in top-k retrieved |
| Answer correctness | Contains/entails expected key facts (rubric-checked) |
| Faithfulness | Answer grounded in cited chunks; no unsupported claims |
| Latency | End-to-end question → answer |

Output: versioned results file + short analysis in
`tests/rag-evaluation/results/`. Statement enabled: *"We evaluated AI quality
using measurable criteria rather than subjective examples."*

---

## 24. Project Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| GenAI unavailable/not enabled in region/tenancy | Medium | High | Verify W0; adapter fallback to OpenAI-compatible endpoint; ADR-006 documents it |
| Node/LB/DB quota limits | Medium | Medium | W0 quota checks; small shapes; single AZ; mentors pre-approved provisioning |
| Vector DB too heavy for nodes | Medium | Low | pgvector default; 23ai only if capacity proven |
| Demo-day infrastructure flakiness | High | High | Recorded backups of every demo; scripted reset; static screenshots |
| Team bandwidth split across tracks | Medium | Medium | Milestone ownership matrix; weekly integration checkpoint |
| Scope creep (adding features late) | Medium | High | Non-goals section is binding; new ideas go to "future work" |

---

## 25. Documentation Deliverables Map

```text
docs/
├── PROJECT-PROPOSAL.md            ← this document
├── assessment/source-environment.md
├── architecture/architecture.md · network-design.md · security-architecture.md
├── migration/migration-strategy.md
├── validation/validation-matrix.md
├── security/threat-model.md
├── performance/benchmark-results.md
├── cost/cost-analysis.md
├── disaster-recovery/dr-strategy.md
└── adr/
    ├── ADR-001-microservices.md
    ├── ADR-002-oke.md
    ├── ADR-003-private-networking.md
    ├── ADR-004-async-processing.md
    ├── ADR-005-vector-store.md
    ├── ADR-006-oci-generative-ai.md
    └── ADR-007-hpa.md
```

Each ADR: Problem → Options → Decision → Why → Trade-offs.

---

## 26. Open Decisions Tracker

| # | Decision | Status | Lean | Blocking |
|---|----------|--------|------|----------|
| D1 | OCI GenAI available/enabled in me-jeddah-1 + intern tenancy | **Open — verify W0** | yes | Everything AI |
| D2 | Queue technology | Open → decide W0 | Redis Streams | M1 |
| D3 | Vector store | Open until quota check | pgvector | M1 |
| D4 | Frontend stack | Open → freeze W0 | Streamlit | M1 |
| D5 | Monolith baseline host | Open | OCI Compute VM (comparable sizing) | M0 |
| D6 | KEDA for queue-depth scaling | Stretch decision | yes, post-M4 | M5 |
| D7 | Helm vs raw manifests for deploy | Open | raw manifests → Helm later if time | M3 |

---

## 27. Week-0 Pre-Flight Checklist

Run against `intern-18-salah-abdelhady-cmp` before writing application code:

```powershell
# 1. Generative AI models visible? (fails fast if region/tenancy lacks access)
oci generative-ai model list --compartment-id <COMPARTMENT_OCID> --all

# 2. Limits service — what can we actually create?
oci limits service list --compartment-id <COMPARTMENT_OCID>
oci limits limit-definition list --service-name compute --compartment-id <COMPARTMENT_OCID> --all
oci limits limit-definition list --service-name oke --compartment-id <COMPARTMENT_OCID> --all
oci limits limit-definition list --service-name load-balancer --compartment-id <COMPARTMENT_OCID> --all
oci limits limit-definition list --service-name database --compartment-id <COMPARTMENT_OCID> --all

# 3. Availability of specific shapes (example: E4.Flex)
oci limits resource-availability get `
  --service-name compute `
  --limit-name standard-e4-core-count `
  --availability-domain "<AD_NAME>" `
  --compartment-id <COMPARTMENT_OCID>

# 4. Confirm IAM can create dynamic groups/policies in compartment (mentor confirm)

# 5. OCIR namespace
oci os ns get
```

Outputs recorded into `docs/assessment/pre-flight-findings.md`. D1/D3/D5 close
based on these results.

---

## 28. Repository Layout (this folder)

```text
final grad/
├── README.md                        ← navigation
├── docker-compose.yml               ← local monolith + M1 multi-service (added in M0/M1)
├── services/                        ← api-gateway, document, processing, ai, search
├── frontend/
├── kubernetes/                      ← namespace, deployments, services, ingress,
│                                      hpa, network-policies, pdb, configmaps, secrets
├── terraform/
│   ├── environments/dev · prod
│   └── modules/ networking · oke · iam · ocir · object-storage ·
│                database · load-balancer · monitoring
├── tests/unit · integration · smoke · load · rag-evaluation
├── docs/                            ← see §25 map (PROJECT-PROPOSAL.md + ADRs live here)
└── .github/workflows/ci.yml · cd.yml
```

Continuity note: `terraform/modules/networking` and `terraform/modules/oke`
start from the proven week-3 modules (`network`, `subnet`, `oke`) in
`E:\work\Ejada\terraform\nonprd\week3-containerized-oke\modules\`, and remote
state reuses the `bootstrap-state` bucket pattern.

---

## 29. Final Presentation Arc

1. Old world: monolith baseline + its measured problems
2. Target architecture walk-through (diagram above)
3. Terraform modules tour → live `plan` snippet
4. Docker → OCIR → OKE flow evidence
5. Live upload → async processing → classification/extraction/risk
6. RAG question → answer with citations → evaluation numbers
7. k6 load → HPA scaling live
8. `kubectl delete pod` → self-healing live (recorded backup ready)
9. Broken v2 → rollback demo
10. Grafana dashboards + distributed trace waterfall
11. Security architecture recap (threat model highlights)
12. Close: measured performance + cost + DR + lessons learned

Closing line mirrors §0: assess, architect, provision, containerize,
modernize, secure, deploy, observe, scale, recover, validate, measure.
