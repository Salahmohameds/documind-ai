# Delivery Timeline — M0 → Final

Weeks are relative (W0 = project start). Exit criteria are demoable states, not intentions.

| Milestone | Weeks | Exit criteria | Lead roles | Supporting |
|-----------|-------|---------------|-----------|------------|
| **W0 pre-flight** | W0 | GenAI access confirmed · quotas confirmed · stack decisions locked (D1–D5 in proposal §26) · security requirements drafted | 1, 7 | 2 |
| **M0 baseline** | W1–W2 | Monolith runs in one container + on a VM · baseline k6 numbers recorded | 3, 8 | 1 |
| **M1 local pipeline** | W3–W4 | 5 services on docker compose · upload → queue → classify/extract → RAG with citations works locally | 3, 5, 6, 4 | 8 |
| **M2 infra live** | W4–W5 | `terraform apply` brings up VCN + OKE + datastores in dev · pre-flight findings closed | 1 | 2, 7 |
| **M3 deployed** | W5–W6 | CI → OCIR → OKE · app reachable through LB · smoke tests green | 2 | all |
| **M4 hardened** | W6–W7 | Probes, limits, HPA, NetworkPolicies, PDB, Vault, security scans gating | 2, 7 | 9 |
| **M5 beyond** | W7–W9 | Tracing live · RAG eval numbers · perf comparison done · self-healing/HPA/rollback demos recorded | 8, 9, 4 | 2 |
| **Final** | W9+buffer | Docs complete · ADRs final · presentation rehearsed · recorded demo backups | 9 | all |

## Who can start what, immediately

- **W0 (now):** roles 1, 2, 3, 7 have real work. Nobody is blocked.
- **W1:** roles 4, 5, 6, 8, 9 start (they consume role 3's API contracts and role 7's standards).
- **Nobody waits idle:** if blocked on another role, take the next task in your folder's README or help write tests.

## Buffer rule

The final week before presentation is **buffer** — no new features. Only hardening, docs, and demo rehearsal.
