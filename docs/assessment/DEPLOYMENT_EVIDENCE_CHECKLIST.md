# DEPLOYMENT EVIDENCE CHECKLIST — DocuMind AI

Capture **during the paid burst only**. After `terraform destroy` there is no retake without paying again.

Naming: `NN-short-description.png` (or `.mp4` / `.txt` / `.json`) under `docs-evidence/` (create on deploy day; do not invent numbers in git before then).

**Compartment on every OCI screenshot:** `shared-group-b-cmp`  
`ocid1.compartment.oc1..aaaaaaaafqtm2ncck55cuafnypwinggayfapkgvy6lsbz3yhsvisvbdl5rjq`  
**Region:** `me-jeddah-1`  
**Git SHA on every log header:** the deploy commit (audit baseline was `eec4349`).

Do **not** screenshot intern-18.

Legend: 📸 screenshot · 📹 video 1080p with narration · 📄 file/log

---

## 0 — Before Day 1 (gate; not OCI spend)

| ✓ | Evidence | Type |
|---|---------|------|
| ☐ | `git rev-parse HEAD` and CI **green** on that SHA | 📸 + 📄 |
| ☐ | `terraform.tfvars` shows shared-group-b OCID (redact nothing about intern-18 because it must not appear) | 📸 |
| ☐ | `backend.hcl` bucket/namespace/key/region (namespace may be `axkjllkftxfz` — confirm live `oci os ns get`) | 📄 |
| ☐ | Admin confirmation: dynamic groups exist | 📸 |
| ☐ | Console quotas for OKE / E4.Flex / LB / NAT / public IP / PSQL | 📸 |
| ☐ | GenAI `list-models` success in the region you will call (Jeddah 404 and Riyadh 401 were the pre-deploy facts) | 📄 |
| ☐ | kind or compose rehearsal: upload → COMPLETED | 📹 optional |

---

## 1 — Terraform

| ✓ | Evidence | Type | Notes |
|---|---------|------|--------|
| ☐ | `terraform init` against OCI backend | 📄 | locking mentioned if visible |
| ☐ | `terraform plan -out=tfplan` full text | 📄 `docs-evidence/terraform-plan.txt` | review before apply |
| ☐ | `terraform show tfplan` resource counts | 📄 |
| ☐ | `terraform apply` full log | 📄 `docs-evidence/terraform-apply-session.txt` |
| ☐ | `terraform output -json` | 📄 | redact DB password if any |
| ☐ | State in Object Storage: bucket `documind-tfstate`, versioning Enabled | 📸 |
| ☐ | Stage A vs Stage B plans if split (`enable_oke`) | 📄 |

---

## 2 — OCI console — network

| ✓ | Evidence | Type |
|---|---------|------|
| ☐ | Compartment name `shared-group-b-cmp` in the header | 📸 |
| ☐ | VCN `10.20.0.0/16` | 📸 |
| ☐ | Subnets: public_lb `10.20.1.0/24`, oke_api `10.20.2.0/28`, workers `10.20.10.0/24`, pods `10.20.64.0/18`, data `10.20.30.0/24` | 📸 |
| ☐ | IGW, NAT, Service Gateway | 📸 |
| ☐ | Route tables (public vs NAT vs data) | 📸 |
| ☐ | NSG list: lb, oke-api, workers, pods, data | 📸 |
| ☐ | NSG rules: 6443/22 from admin CIDR only — **not** 0.0.0.0/0 | 📸 |
| ☐ | Worker nodes: **no public IP** | 📸 |

---

## 3 — OKE

| ✓ | Evidence | Type |
|---|---------|------|
| ☐ | Cluster ACTIVE, type (must be ENHANCED if workload identity is in the story) | 📸 |
| ☐ | Kubernetes version from catalog (pre-deploy catalog included 1.33/1.34) | 📸 |
| ☐ | CNI `OCI_VCN_IP_NATIVE` | 📸 |
| ☐ | Node pool Ready, shape `VM.Standard.E4.Flex`, private subnet | 📸 |
| ☐ | `kubectl get nodes -o wide` (private IPs) | 📸 |
| ☐ | Dedicated API endpoint subnet | 📸 |

---

## 4 — OCIR images

| ✓ | Evidence | Type |
|---|---------|------|
| ☐ | Repositories for api-gateway, document, processing, ai, search, **frontend** | 📸 |
| ☐ | Immutable tags = git SHA (no sole `:latest`) | 📸 |
| ☐ | Trivy output for at least one image | 📄 / 📸 |
| ☐ | Node can pull (pod not `ImagePullBackOff`) | 📸 |

---

## 5 — Kubernetes workload

| ✓ | Evidence | Type |
|---|---------|------|
| ☐ | `kubectl get ns` — `documind` | 📸 |
| ☐ | `kubectl get deploy,po,svc,ing,hpa,pdb -n documind` | 📸 |
| ☐ | All intended pods Running / Ready | 📹 rollout |
| ☐ | Services: ClusterIP internals + LB/Ingress | 📸 |
| ☐ | Ingress / Service LB → OCI load balancer OCID | 📸 |
| ☐ | Public IP in browser | 📸 |
| ☐ | ConfigMaps (no secrets) | 📸 |
| ☐ | Secrets exist (values **not** shown) | 📸 |
| ☐ | processing-service probes `/liveness` `/readiness` | 📄 describe |
| ☐ | NetworkPolicy default-deny + allow paths | 📸 |
| ☐ | RBAC / ServiceAccounts | 📸 |

---

## 6 — Data plane

| ✓ | Evidence | Type |
|---|---------|------|
| ☐ | Postgres: OCI PSQL **or** in-cluster — endpoint **private** | 📸 |
| ☐ | `psql` or app: `vector` extension, `documents`, `document_chunks`, `processing_jobs` | 📄 |
| ☐ | Redis stream `document_jobs` + consumer group | 📄 |
| ☐ | Object Storage documents + processed buckets | 📸 |
| ☐ | DB **not** reachable from the public internet | 📸 |

---

## 7 — IAM / Vault / secrets

| ✓ | Evidence | Type |
|---|---------|------|
| ☐ | Dynamic groups (admin-created) matching rules | 📸 |
| ☐ | Policies: OCIR pull, objects, generative-ai-family, secret-family | 📸 |
| ☐ | Vault (if used) + secret OCID, not the secret payload | 📸 |
| ☐ | Pod uses workload identity (no API key file in the container) | 📸 / 📄 `env` redacted |

---

## 8 — Application UI and API

| ✓ | Evidence | Type |
|---|---------|------|
| ☐ | UI loads via public LB | 📸 |
| ☐ | 401 without JWT / 403 wrong role | 📸 |
| ☐ | Login via **api-gateway** (if that is the final path) | 📸 |
| ☐ | Upload PDF → `202` → poll → `COMPLETED` | 📹 |
| ☐ | Classification (invoice + contract) | 📸 |
| ☐ | Extraction JSON | 📸 |
| ☐ | Risk score + explanation | 📸 |
| ☐ | PII / redaction | 📸 |
| ☐ | Semantic search | 📸 |
| ☐ | RAG answer **with citations** (doc + page) | 📹 |
| ☐ | Health: `/readiness` on each service | 📄 |

---

## 9 — AI / RAG (real provider)

| ✓ | Evidence | Type |
|---|---------|------|
| ☐ | `AI_BACKEND` is `oci` (or documented fallback), **not** mock, on the cluster | 📄 |
| ☐ | `EMBEDDING_BACKEND` is not mock for the scored RAG run | 📄 |
| ☐ | Model IDs + region (e.g. Riyadh endpoint + Jeddah compartment) | 📄 |
| ☐ | One successful embed + one successful chat (keep tokens small) | 📄 |
| ☐ | RAG eval output with `"reportable": true` | 📄 `tests/rag-evaluation/` |
| ☐ | Refusal on unanswerable questions if in the golden set | 📄 |

Do not submit mock 50/50 accuracy as OCI GenAI evidence.

---

## 10 — Logs and monitoring

| ✓ | Evidence | Type |
|---|---------|------|
| ☐ | Structured JSON log with `request_id` / `trace_id` | 📄 |
| ☐ | OCI Logging (if enabled) or cluster logs | 📸 |
| ☐ | Grafana: RPS, P95, errors, HPA, queue depth | 📸 ×5 |
| ☐ | OTel / Jaeger waterfall including AI span | 📸 |
| ☐ | Terraform alarms / ONS topic (if `enable_monitoring`) | 📸 |
| ☐ | Flow logs only if you turned them on | 📸 |

---

## 11 — HPA, self-healing, rollout

| ✓ | Evidence | Type | Must show |
|---|---------|------|-----------|
| ☐ | HPA scale up then down | 📹 | `kubectl get hpa -w` + Grafana |
| ☐ | `kubectl delete pod` → replacement Ready | 📹 | terminal clock |
| ☐ | Rolling update under light traffic | 📹 | |
| ☐ | `kubectl rollout undo` after a bad tag | 📹 | |

---

## 12 — Load test

| ✓ | Evidence | Type |
|---|---------|------|
| ☐ | k6 smoke + baseline (and spike if time) | 📄 JSON |
| ☐ | Grafana during the run | 📹 |
| ☐ | RPS, P50/P95/P99, error rate | 📄 |
| ☐ | Three official runs if the runbook still requires it | 📄 |

Thresholds in `tests/load/lib/config.js` were placeholders at audit time — replace with measured values, do not invent them.

---

## 13 — Security scans (deploy commit)

| ✓ | Evidence | Type |
|---|---------|------|
| ☐ | CI green: gitleaks, unit tests, docker/trivy | 📸 |
| ☐ | checkov / tflint from `terraform-pr` or local | 📄 |
| ☐ | NetworkPolicy: test pod cannot reach Postgres | 📸 |
| ☐ | NSG + private DB screenshots (cross-link §2 / §6) | 📸 |

---

## 14 — Architecture and cost

| ✓ | Evidence | Type |
|---|---------|------|
| ☐ | Final architecture (console VCN map + drawio if updated to `10.20.64.0/18` pods) | 📸 |
| ☐ | Resource list in compartment (everything tagged `Project=DocuMind-AI`) | 📸 |
| ☐ | OCI cost / budget screen **Day 5** | 📸 |
| ☐ | Which resources were MUST EXIST vs destroyed | 📄 |

---

## 15 — Teardown (keep state)

| ✓ | Evidence | Type |
|---|---------|------|
| ☐ | `kubectl delete` Services/Ingress **first** | 📄 |
| ☐ | OCI console: Kubernetes LB **gone** | 📸 |
| ☐ | `terraform destroy` log | 📄 |
| ☐ | Post-destroy inventory: no VCN/OKE/LB/nodes/PSQL in shared-group-b | 📸 + 📄 |
| ☐ | `documind-tfstate` bucket **still present**, versioning on | 📸 |
| ☐ | Evidence folder backed up off the cluster | — |

---

## Capture order (deploy day)

1. Plan + apply logs  
2. Network + OKE + OCIR console  
3. `kubectl` Ready + LB URL  
4. Functional + AI/RAG  
5. HPA / heal / k6 / Grafana  
6. Cost  
7. Destroy + empty compartment + keep state  

If Day 2 has no LB→app path, still capture **partial** evidence; teardown still happens on the last burst day.
