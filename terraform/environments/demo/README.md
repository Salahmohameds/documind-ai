# Demo environment

The single burst environment for the 3-day OCI deployment window. Wires
`networking` → `bastion?` → `object_storage` → `ocir` → `oke?` → `iam` →
`database?` → `monitoring?`. Everything optional is feature-flagged so the
footprint stays small and teardown is clean.

## Prerequisites (one-time)

1. **State bucket** — apply [`../../bootstrap-state/`](../../bootstrap-state/)
   once and note the `namespace` output.
2. **backend.hcl** — `cp backend.hcl.example backend.hcl`, paste the namespace
   (gitignored), keep `config_file_profile` for local runs.
3. **terraform.tfvars** — `cp terraform.tfvars.example terraform.tfvars`;
   fill compartment, region, your IP in `admin_cidrs`.

## Staged deploy (matches docs/plan/DEPLOYMENT-RUNBOOK.md)

```bash
terraform init                                   # configures native oci backend
terraform fmt -check -recursive && terraform validate

# Stage A — network only
terraform plan -out=tfplan-a                     # enable_oke = false
terraform apply tfplan-a

# Stage B — cluster + IAM
terraform plan -out=tfplan-b                     # enable_oke = true
terraform show tfplan-b                          # review
terraform apply tfplan-b
```

Then: kubeconfig (see the `kubeconfig_hint` output) → deploy Kubernetes
manifests from `kubernetes/` → run smoke tests.

## Teardown

Delete Kubernetes Service/PVC resources first, then
`terraform plan -destroy` → review → `terraform apply` that plan. The state
bucket is never destroyed by this stack.

## Security model in one line

Private workers/pods/data, NSG-per-role with no world-open API port
(`admin_cidrs` is validated against `0.0.0.0/0`), Vault-first database
passwords, and state locked to a versioned private bucket.
