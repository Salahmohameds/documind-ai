# ADR-009: Load Balancer ownership — Kubernetes owns Service load balancers

- **Status:** Accepted (supersedes the deleted `terraform/modules/load-balancer`)
- **Date:** 2026-08-25
- **Deciders:** Cloud Lead, Cloud Deployment Engineer

## Context

The original architecture diagram shows an OCI Flexible Load Balancer in
front of OKE **and** a Kubernetes Ingress inside the cluster. Two systems
(Terraform CLI and the OKE cloud-controller-manager) can both create OCI load
balancers. If both do, we get:

- two billable LBs where one suffices;
- no single owner of backend health/routing state;
- destroy-ordering hazards (Terraform deleting a VIP that Kubernetes recreated).

The first Terraform implementation (`Terraform_Files` branch) shipped a
`load-balancer` module with an empty backend set and placeholder backends fed
by `var.backend_ips` — a manual-registration model that fights how OKE works.

## Options considered

| Option | Description | Verdict |
|---|---|---|
| A — Terraform owns the LB | Terraform provisions LB + listeners + backends pointing at NodePorts | Rejected: backend IPs churn as pools scale; Terraform cannot track K8s service topology |
| B — Kubernetes owns the LB | `type: LoadBalancer` Services / Ingress create OCI LBs via the OKE CCM in the public subnet; Terraform only prepares the subnet + NSGs | **Accepted** |
| C — Both | Hybrid with annotations binding K8s to a pre-made LB | Rejected: fragile coupling, undocumented annotation surface |

## Decision

**Option B.** The `load-balancer` module is deleted. Consequences:

1. Terraform provisions the *prerequisites*: public subnet, NSG rules for
   internet → 443/80 and LB ↔ NodePort/kube-proxy paths.
2. Workload manifests create the actual LB (`service.beta.kubernetes.io/oci-*`
   annotations), proven in the internship week-3 lab.
3. The resulting LB OCID is unknown to Terraform by design; if LB alarms are
   wanted, its OCID is pasted into `lb_ocid` tfvars after first deploy.
4. Teardown order matters: delete Services/PVCs before `terraform destroy`
   so the CCM releases the LB and volumes cleanly (runbook step).

## WAF note

OCI WAF attaches to a managed LB origin. With Kubernetes owning the LB, WAF
integration is deferred until after the burst (documented, not implemented);
if added later it must attach to the K8s-created LB's IP, never re-create one.
