# Threat Model — DocuMind AI

> Owner: Security / DevSecOps Engineer (role 7). Draft in W0 — this gates the
> IAM, networking, and CI designs. Status: **DRAFT**.

## Scope

AI document intelligence platform on OCI: 5 microservices on OKE (private
nodes), OCI-managed data stores, OCI Generative AI via IAM, CI/CD via GitHub
Actions + OCIR.

## Assets & trust boundaries

| Asset | Boundary crossings |
|-------|--------------------|
| Uploaded documents (may contain real PII) | Internet → LB → OKE → Object Storage |
| Extracted structured data + vectors | services → PostgreSQL/pgvector |
| JWT signing secret, DB credentials | Vault → K8s Secret → pods |
| OCI credentials (workload identity) | dynamic groups → policies |
| Container images | CI → OCIR → OKE kubelet |
| Terraform state | CI/laptops → Object Storage backend |

## Threat register

| # | Threat | Vector | Mitigation | Owner (implements) | Status |
|---|--------|--------|------------|--------------------|--------|
| T1 | Public exposure of workers/DB | misconfigured subnet/NSG | private subnets, NSG source rules, no public IPs | role 1 | ☐ |
| T2 | Over-privileged workload IAM | broad policies | per-workload dynamic groups, least privilege | role 1 | ☐ |
| T3 | Secret leakage via git/images/env dumps | repo scan, image layers | gitignore + pre-commit + Vault→K8s sync, no secrets in Dockerfiles | role 7 | ☐ |
| T4 | Vulnerable container image | base image CVE | Trivy gate in CI (fail HIGH/CRITICAL), minimal bases, non-root | role 2 | ☐ |
| T5 | IaC misconfiguration | insecure TF resources | tflint + checkov in CI, plan review | role 7 | ☐ |
| T6 | Lateral movement pod→pod | flat pod network | default-deny NetworkPolicies + explicit allows | role 2 | ☐ |
| T7 | Unauthorized API access | missing/weak auth | JWT at gateway, role checks, short expiry | role 3 | ☐ |
| T8 | API abuse / DoS | flood upload/chat | rate limiting at gateway, HPA + queue backpressure | role 3 | ☐ |
| T9 | PII exposure in processed artifacts | extraction outputs stored raw | PII detection, redaction option, bucket policies | roles 4/5 | ☐ |
| T10 | Prompt injection via document content | crafted PDF text | input sanitization, output grounding to citations, no tool access from LLM | role 4 | ☐ |
| T11 | Supply chain (actions/plugins) | compromised CI dep | pinned action SHAs, minimal tokens, dependabot | role 2 | ☐ |
| T12 | State file exposure | TF state contains secrets | private bucket, backend auth via customer secret key, never commit state | role 1 | ☐ |

## Security requirements handed to other roles

- **Role 1 (Cloud Lead):** NSG matrix from proposal §10, IAM policy shape from §11, Vault structure.
- **Role 2 (Deployment):** NetworkPolicy default-deny set, SecurityContext baseline (non-root, read-only fs, drop caps), Trivy thresholds.
- **Role 3 (Backend):** JWT claims design (sub, exp, roles), validation rules, rate-limit defaults.
- **Roles 4/5:** PII detection points in pipeline; prompt-injection mitigations.

## Review cadence

Revisit at each milestone exit (M1, M3, M5). Every "Status ☐" must become
✅ with evidence link (screenshot, test, or policy file) before final submission.
