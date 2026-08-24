# Evidence Checklist — Burst Capture List

> Print this. During the burst (W5), check items off **live**. After teardown
> there is no retake without paying again. Naming: `NN-short-description.png`
> in the matching `docs-evidence/` folder (same style as weeks 1–3).
> 📹 = video (1080p, narrate what you're doing), 📸 = screenshot, 📄 = saved log/file.

## A — Infrastructure (Day 1 · role 1)

| ✓ | Evidence | Type | Save to |
|---|----------|------|---------|
| ☐ | `terraform apply` full output | 📄 | `docs-evidence/terraform-apply-session.txt` |
| ☐ | VCN + subnets + route tables console views | 📸 | `docs-evidence/01-vcn.png` … |
| ☐ | IGW / NAT / SGW details | 📸 | `docs-evidence/02-gateways.png` |
| ☐ | NSG rules list (lb / workers / data) | 📸 | `docs-evidence/03-nsgs.png` |
| ☐ | OKE cluster ACTIVE + node pool (private IPs proof) | 📸 | `docs-evidence/04-oke.png` |
| ☐ | Datastores: PostgreSQL instance, Object Storage buckets | 📸 | `docs-evidence/05-datastores.png` |
| ☐ | IAM: dynamic groups + policies | 📸 | `docs-evidence/06-iam.png` |

## B — Deployment (Day 2 · role 2)

| ✓ | Evidence | Type | Save to |
|---|----------|------|---------|
| ☐ | CI run green (tests, trivy, gitleaks) on the deploy commit | 📸 | `docs-evidence/07-ci-run.png` |
| ☐ | OCIR repos with versioned images | 📸 | `docs-evidence/08-ocir.png` |
| ☐ | `kubectl get pods -n documind` all Running/Ready | 📹 | `docs-evidence/09-rollout.mp4` |
| ☐ | LB public IP + app loading in browser | 📸 | `docs-evidence/10-lb-app.png` |
| ☐ | Smoke suite output (readiness + upload happy path) | 📄 | `docs-evidence/smoke-run.txt` |

## C — Application features (Day 3 · roles 3–6)

| ✓ | Evidence | Type |
|---|----------|------|
| ☐ | 401 without JWT · 403 wrong role | 📸 |
| ☐ | Upload → `202 Accepted` → status polling → `COMPLETED` | 📹 |
| ☐ | Classification result (invoice + contract) | 📸 |
| ☐ | Extraction JSON (invoice + contract) | 📸 |
| ☐ | Risk score + findings + explanation | 📸 |
| ☐ | PII detection output (+ redaction if implemented) | 📸 |
| ☐ | Semantic search results | 📸 |
| ☐ | RAG answer **with citations** (doc + page) | 📹 |
| ☐ | RAG evaluation results vs real OCI GenAI | 📄 `tests/rag-evaluation/results/` |
| ☐ | Vault → K8s secret → pod (sync proof) | 📸 |

## D — Platform behavior demos (Day 3 · roles 2, 8)

| ✓ | Demo | Type | Must show |
|---|------|------|-----------|
| ☐ | **HPA autoscaling** | 📹 | load ↑ → replicas 1→N → scale down; `kubectl get hpa -w` + Grafana visible |
| ☐ | **Self-healing** | 📹 | `kubectl delete pod` → replacement → Ready; terminal clock for recovery time |
| ☐ | **Rolling update** | 📹 | v2 rollout while k6 runs (no error spike) |
| ☐ | **Rollback** | 📹 | broken v2 stalls → `rollout undo` → healthy v1 |
| ☐ | **Load test official** | 📹 + 📄 | Grafana during k6 + saved k6 JSON/summary (3 runs) |

## E — Security & observability (Day 3 · roles 7, 9)

| ✓ | Evidence | Type |
|---|----------|------|
| ☐ | NetworkPolicy deny: test pod → DB **blocked**; allowed path works | 📸 |
| ☐ | DB not reachable from internet (external probe fails) | 📸 |
| ☐ | Trivy scan output (HIGH/CRITICAL report on an image) | 📸 |
| ☐ | checkov/tflint output from CI | 📸 |
| ☐ | Grafana: request rate · P95 · error rate · pods/HPA · queue depth | 📸 ×5 |
| ☐ | OTel trace waterfall (API→document→processing→AI→search, AI span dominant) | 📸 |
| ☐ | Structured JSON log lines with `request_id`/`trace_id` | 📄 |

## F — Performance & cost (Day 3–5 · roles 8, 1)

| ✓ | Evidence | Type |
|---|----------|------|
| ☐ | Monolith baseline numbers (local or same-day VM) — same k6 script | 📄 |
| ☐ | OKE numbers: RPS, P50/P95/P99, error rate, CPU/mem/pods | 📄 |
| ☐ | Recovery time measurement (from self-healing video) | 📄 |
| ☐ | OCI budget screen: actual spend during burst | 📸 (Day 5) |

## G — Teardown proof (Day 5 · roles 1, 2)

| ✓ | Evidence | Type |
|---|----------|------|
| ☐ | `kubectl delete` workload + **LB deleted in OCI console** (not just k8s) | 📸 |
| ☐ | `terraform destroy` full output | 📄 `docs-evidence/terraform-destroy-session.txt` |
| ☐ | Post-destroy inventory: compartment **empty** (resource explorer + CLI lists) | 📸 |
| ☐ | No orphaned public IPs / volumes / mount targets | 📸 |
| ☐ | OCIR repos retained (free) for reproducibility | 📸 |

## Counting rule

Final submission needs **every box ticked**. If something can't be captured,
write the reason in `docs/validation/validation-matrix.md` next to the item —
an honest gap beats a missing explanation.
