# DEPLOYMENT BLOCKERS — DocuMind AI

**These are the only issues that must be fixed before a paid OCI apply/deploy.**

Audit SHA: `eec4349fecac8bdb38fba812514bec893c204118` (`main`).  
Target: `shared-group-b-cmp` / `me-jeddah-1` only.  
Do not use `intern-18-salah-abdelhady-cmp`.

A blocker means: starting `terraform apply` or pushing workloads to OKE would fail, target the wrong thing, or burn budget with no demo.

---

## B1 — Kubernetes is not a deployable platform

**Why it blocks:** There is nothing to `kubectl apply` for the user-facing path.

On disk after pull:

- Implemented: `processing-service` only (Deployment, Service, HPA, PDB, ConfigMap, Secret example, NetworkPolicy).
- `kubernetes/ingress/` is `.gitkeep`.
- No Deployment/Service for `api-gateway`, `document-service`, `ai-service`, `search-service`, or the Next.js frontend.
- No in-cluster Redis (ADR-004 requires it on OKE).
- No in-cluster Postgres, and Terraform `enable_database` defaults to **false**.
- processing ConfigMap already points at `ai-service.documind.svc.cluster.local` and `search-service.documind.svc.cluster.local` — those Services do not exist.
- No frontend Dockerfile, so there is no OCIR image for the UI.

**Fix before apply:** add the missing manifests (or a Helm chart), plus Redis and a concrete Postgres decision; build a frontend image. Rehearse on kind.

---

## B2 — Intern cannot create dynamic groups; Terraform IAM always does

**Why it blocks:** `terraform apply` on `environments/demo` always calls `modules/iam`, which creates two **tenancy** dynamic groups.

Verified this session:

```
oci iam dynamic-group list --compartment-id <tenancy>
→ 404 NotAuthorizedOrNotFound
```

Admin must create DGs. This user cannot. Applying IAM as intern will error and can leave a half-applied stack (network/OKE already paid).

**Fix before apply:** admin creates `dm-demo-dg-oke-nodes` and `dm-demo-dg-workloads` (or agreed names) and the four policies; intern applies a root that does **not** create DGs — or admin applies IAM. Also set `oke_cluster_type = "ENHANCED_CLUSTER"` if workload identity is required (`BASIC_CLUSTER` is the code default and cannot do it).

---

## B3 — CI on `main` is red

**Why it blocks:** The burst runbook requires CI green. Images are not a gated artifact.

Latest run on `eec4349` (33038546953):

| Job | Result |
|-----|--------|
| Terraform fmt / validate / tflint / checkov | success |
| Secret scan (gitleaks) | success |
| Python unit tests | success |
| Docker build + Trivy scan | **failure** |

Cause (from the log): `search-service` installs `sentence-transformers` → PyTorch + NVIDIA CUDA wheels. Trivy then fails with **no space left on device** (0 MB free).

**Fix before apply:** stop pulling CUDA into the CI image (optional extra / extra stage), prune more aggressively, or drop unused `sentence-transformers` while `EMBEDDING_BACKEND=mock` / ai-service owns embeddings.

---

## B4 — No Terraform remote state and no demo tfvars

**Why it blocks:** Demo backend is `backend "oci" {}` filled only by gitignored `backend.hcl`. This workspace has:

- no `terraform/environments/demo/terraform.tfvars`
- no `terraform/environments/demo/backend.hcl`
- no `terraform/bootstrap-state/terraform.tfvars`

OCIR listing showed **0** repositories. Object Storage namespace GET succeeded (`axkjllkftxfz`). There is no confirmed `documind-tfstate` bucket from this audit.

`terraform plan` was **not** run: a real backend init would talk to a bucket that is not known to exist; creating that bucket is a mutation and was forbidden here.

**Fix before apply:** apply `bootstrap-state` once into **shared-group-b** (admin/intern as allowed); write `backend.hcl` + `terraform.tfvars` with the shared-group-b OCID, real `admin_cidrs`, and review `enable_*` flags. Never commit those files.

---

## B5 — No database and no queue on OKE

**Why it blocks:** document, processing, and search cannot run without Postgres + Redis.

- Compose provides both. Kubernetes does not.
- `enable_database = false` in example/defaults.
- `oci psql db-system-collection list-db-systems` works and returned **`items: []`**.
- Redis is in-cluster by design — **zero** Redis manifests.

**Fix before apply:** either enable OCI PostgreSQL **after** a console quota check, or add a Postgres Deployment + PVC; add Redis Deployment + Service + Secret. Run migrations (`schema.sql` + `002_processing_jobs.sql`). Resolve the duplicate `002_drop_ivfflat_index.sql` vs `002_processing_jobs.sql` naming.

---

## B6 — OCIR is empty and there is no image pipeline to OKE

**Why it blocks:** processing Deployment image is `REGION.ocir.io/NAMESPACE/documind/processing-service:REPLACE_WITH_GIT_SHA`. LIST:

```
repository-count: 0
```

CI builds images then deletes them; it does not push. No frontend image exists at all.

**Fix before apply:** create repos (Terraform `modules/ocir` or admin), push immutable git-SHA tags for all five services **and** frontend, document pull auth (node DG vs imagePullSecrets).

---

## B7 — Generative AI and production AI path are not confirmed

**Why it blocks:** a burst that only runs `AI_BACKEND=mock` cannot evidence OCI GenAI. A burst that sets `AI_BACKEND=oci` without models/IAM will fail or hang jobs.

Verified:

| Check | Result |
|-------|--------|
| `me-jeddah-1` `list-models` | **404** NotAuthorizedOrNotFound |
| `me-riyadh-1` subscribed | **READY** |
| `me-riyadh-1` `list-models` | **401** NotAuthenticated |
| Adapter | `oci_genai.py` states it has **not** been run against a live endpoint |
| Compose | `AI_BACKEND` unset → mock; search `EMBEDDING_BACKEND=mock` |
| RAG eval | refuses to write reportable scores on mock |

**Fix before apply:** admin enables/authenticates GenAI in a subscribed region; record chat + embedding model IDs; wire ConfigMap/Secret; confirm DG policy `use generative-ai-family`; run one **metadata/list** success (not a large paid generation) before apply.

---

## B8 — GitHub Environment `demo` does not gate apply/destroy

**Why it blocks:** `deploy-demo.yml` and `destroy-demo.yml` call `terraform apply` / destroy. Both set `environment: demo`. GitHub API:

```
name: demo
protection_rules: []
can_admins_bypass: true
```

Plan and apply are the **same job**, so even a future reviewer would approve **before** seeing the plan.

**Fix before apply:** required reviewers on `demo`; split plan and apply jobs (apply needs a second approval after the plan artifact). Do not run these workflows until that exists. Prefer a laptop apply with a reviewed `tfplan` if GitHub secrets are incomplete.

---

## B9 — Service limits / quotas are invisible

**Why it blocks:** a failed OKE/node/LB/NAT apply still costs time and can strand resources.

```
oci limits service list --compartment-id <tenancy>
→ 404 NotAuthorizedOrNotFound
```

**Fix before apply:** **MANUAL CONSOLE CHECK REQUIRED** — OKE cluster count, node pool, `VM.Standard.E4.Flex` OCPU/memory in `ME-JEDDAH-1-AD-1`, load balancer, public IP, NAT, block volume, VCN, PostgreSQL, Bastion, OCIR. Do not guess. Do not apply if any **MUST EXIST** item is zero.

---

## Not blockers (do not delay apply by themselves)

- Docs still mentioning intern-18 (must be corrected before someone copies the wrong OCID — treat as a **process** risk; tfvars.example is REPLACE_ME).
- Docker Engine down on this audit laptop (another machine can build).
- tflint/checkov/trivy/gitleaks/kubeconform/k6 **not installed locally** (CI already ran a subset).
- Architecture pod CIDR `10.20.11.0/18` vs Terraform `10.20.64.0/18` (Terraform is correct).
- WAF not in Terraform (can be out of burst scope if agreed).

---

*Full context: `FINAL_PRE_DEPLOYMENT_READINESS.md`.*
