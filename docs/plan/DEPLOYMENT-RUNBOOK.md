# Deployment Burst Runbook

> The only paid OCI window (~4–5 days). Owners: Cloud Lead (role 1) runs infra,
> Deployment Engineer (role 2) runs deployment, QA (role 8) drives evidence.
> Print [EVIDENCE-CHECKLIST.md](EVIDENCE-CHECKLIST.md) and check items off live.

---

## 0. Go / No-Go gate (before Day 1)

Burst starts **only if every box is checked** (from TIMELINE.md M2):

- ☐ Terraform `validate` clean + reviewed real `terraform plan` (no surprises)
- ☐ All 5 images in OCIR with immutable tags
- ☐ Full stack deployed on **kind** at least once, all demos rehearsed + backup-recorded
- ☐ CI green on `main`
- ☐ OCI **budget alert** active (role 1)
- ☐ `terraform.tfvars` + `backend.hcl` ready locally (never committed)
- ☐ Evidence checklist distributed; camera/OBS tested; screenshot naming agreed
- ☐ Rollback decision rule agreed: **if Day 2 ends without a working LB→app path, we still continue for evidence of partial work, but teardown happens Day 5 regardless**

## 1. Day 1 — Infrastructure up (role 1, role 2 assists)

```powershell
cd terraform/environments/demo
terraform init -reconfigure
terraform apply tfplan          # plan already reviewed pre-burst
```

Sequence & checks:

1. Apply `networking` first (stage A if using staged applies) → verify VCN, subnets, IGW/NAT/SGW, route tables, NSGs in console → 📸 screenshots
2. Apply `oke` + datastores → cluster ACTIVE, node pool ready → 📸
3. Verify: worker nodes private (no public IPs) → 📸 · kubeconfig generated
4. Smoke: `kubectl get nodes` from laptop (via bastion/VPN path as designed)

**Evidence from Day 1:** terraform apply output (full log saved to `docs-evidence/`), resource explorer screenshots (VCN map, OKE pool, NSG list), private-IPs proof.

## 2. Day 2 — Deploy the platform (role 2)

1. Trigger CD (or first manual `kubectl apply -f kubernetes/...` if CD needs a green run first — record whichever path is real)
2. Watch rollout: `kubectl get pods -n documind -w` → 📹 screen record
3. Verify LB public IP → app reachable from browser → 📸
4. Smoke suite (`tests/smoke/`): all `/readiness` green, upload happy path → `202` → `COMPLETED`
5. Fix window: any breakage gets fixed today — that's what the buffer day is for
6. End-of-day gate: **upload→RAG works through the public LB** (or documented partial)

## 3. Day 3 — Evidence day (role 8 drives, all hands)

Run in this order (each maps to EVIDENCE-CHECKLIST.md):

1. **Functional matrix** — auth (401/403), upload, classify, extract JSON, risk score, PII, semantic search, RAG answer with citations → 📸 each
2. **RAG evaluation** — golden set vs real OCI GenAI → save results file
3. **k6 official runs** — same script/corpus as local baseline; 3 runs; capture RPS/P50/P95/P99/error + CPU/mem/pods during run → 📹 Grafana during load test
4. **HPA live** — load → replicas 1→N → scale down → 📹 (keep `kubectl get hpa -w` visible)
5. **Self-healing** — `kubectl delete pod` → time recovery → 📹 (terminal clock visible)
6. **Rolling update + rollback** — deploy deliberately-broken v2 → rollout stalls → `rollout undo` → healthy → 📹
7. **Security evidence** — NetworkPolicy deny (test pod → DB blocked) 📸 · DB unreachable from internet 📸 · NSG rules list 📸 · Vault→K8s secret sync 📸 · CI green run + Trivy output 📸
8. **Observability** — Grafana boards (request rate, P95, errors, HPA, queue depth) 📸 · OTel trace waterfall showing AI span 📸
9. **Monolith comparison** — if running monolith on Compute VM: do it today, same k6 script, then **terminate VM immediately**

## 4. Day 4 — Buffer

Re-run anything flaky or missed. Re-record any video below 1080p / without narration. **Do not start new features.**

## 5. Day 5 — Teardown (role 1 + role 2)

Order matters (avoid orphaned billing):

```bash
# 1. Workload first — LB Service creates a billable OCI LB
kubectl delete -f kubernetes/ingress/ -f kubernetes/services/   # LB gone
kubectl delete all -n documind --all
kubectl delete ns documind

# 2. Verify LB actually deleted in OCI console (not just k8s) → 📸
# 3. Then infrastructure
terraform destroy                # full log saved to docs-evidence/
# 4. Post-destroy inventory (reuse the week-1..3 cleanup scripts/pattern)
```

Verification (same discipline as weeks 1–3):

- ☐ Compartment resource explorer: **empty** (no VCN, LB, instances, volumes) → 📸
- ☐ `oci lb load-balancer list` → empty 📸
- ☐ No orphaned public IPs, block volumes, mount targets 📸
- ☐ Budget actuals screenshot (for cost analysis) 📸
- ☐ OCIR repos kept (free) — images remain for reproducibility

## 6. If things go wrong

| Failure | Response |
|---------|----------|
| Terraform apply fails Day 1 | Fix in place; we hold 2 buffer days for exactly this |
| Quota/limit hit | Smaller shapes / single AD; document deviation in ADR |
| App broken Day 2 EOD | Continue Day 3 with partial evidence; capture what works |
| GenAI IAM fails | Switch adapter to fallback endpoint (env change), note in ADR-006 |
| Anything unrecoverable | `terraform destroy` early — never leave paid resources running overnight while debugging |
