# Kubernetes — DocuMind AI

> Owner: **Cloud Deployment Engineer (role 2)**. Security specs from role 7
> (NetworkPolicies, RBAC, SecurityContext) — role 2 implements.

## Layout

```text
kubernetes/
├── namespace/            # documind namespace (+ labels)
├── deployments/          # one Deployment per service
├── services/             # ClusterIP per service; LB Service for ingress
├── ingress/              # ingress / LB routing to api-gateway
├── hpa/                  # HorizontalPodAutoscaler per service
├── network-policies/     # default-deny + explicit allows
├── pdb/                  # PodDisruptionBudget (minAvailable: 1)
├── configmaps/           # non-secret config per service
└── secrets/              # ONLY *.example templates — real values via Vault/kubectl
```

## Deployment requirements (every Deployment)

- Probes: `/liveness` + `/readiness`
- `resources.requests` and `resources.limits` set
- `securityContext`: `runAsNonRoot: true`, drop capabilities, no privilege escalation
- Image tags are **immutable versions** (`:v1.2.3` or git SHA) — never `:latest`
- Labels: `app.kubernetes.io/name`, `app.kubernetes.io/part-of=documind`

## HPA targets (initial, from proposal §12)

| Workload | Min | Max | Trigger |
|----------|-----|-----|---------|
| api-gateway | 1 | 5 | CPU 65% |
| document-service | 1 | 3 | CPU 65% |
| processing-service | 1 | 10 | queue depth (KEDA, stretch) / CPU |
| ai-service | 1 | 4 | CPU 70% |
| search-service | 1 | 3 | CPU 65% |

## Apply order

```bash
kubectl apply -f namespace/
kubectl apply -f configmaps/ -f secrets/
kubectl apply -f deployments/ -f services/
kubectl apply -f ingress/
kubectl apply -f hpa/ -f pdb/ -f network-policies/
```

Rollback demo: `kubectl rollout undo deployment/<svc>` — see proposal §17.
