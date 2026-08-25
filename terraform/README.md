# Terraform — DocuMind AI

> Owner: Cloud Lead. Every change goes through a PR running
> `terraform-pr.yml` (fmt / validate / tflint / checkov). Applies happen only
> through the approval-gated `deploy-demo.yml`.

## Layout

```text
terraform/
├── bootstrap-state/        # ONE bucket for all remote state (native oci backend)
├── environments/
│   └── demo/               # the burst environment root (feature-flagged)
└── modules/
    ├── networking/         # VCN, subnets, gateways, RTs, SLs, NSGs, flow logs
    ├── oke/                # cluster + node_pools map (VCN-native CNI)
    ├── iam/                # dynamic groups + least-privilege policies
    ├── ocir/               # per-service immutable repositories
    ├── object-storage/     # documents / processed buckets
    ├── database/           # OCI Database with PostgreSQL (optional)
    ├── monitoring/         # ONS topic + alarms (optional)
    └── bastion/            # OCI Bastion (optional)
```

## Conventions

- Environment roots own the `provider {}` and `backend {}`; modules never do.
- Modules take zero environment-specific OCIDs; everything is variables.
- Naming: `dm-<env>-<resource>`; tags `Project=DocuMind-AI`,
  `Environment`, `Owner`, `ManagedBy=Terraform` on everything.
- Collections (`subnets`, `node_pools`, NSG rules, buckets, policies) are maps
  iterated with `for_each`; `count` only gates whole optional components.
- Variable validation rejects bad input before OCI sees it: CIDR syntax,
  containment, overlap, `0.0.0.0/0` admin access, pool sizes, password policy.
- Only `*.example` files are committed — real tfvars/backend.hcl stay local.

## Remote state (mandatory)

Native [`oci` backend] since Terraform 1.12: state lives in the private,
versioned `documind-tfstate` bucket created by `bootstrap-state/`, with
**locking** and normal OCI credentials (no customer secret keys). State keys:
`documind/<environment>/terraform.tfstate`. Never commit or destroy the
bucket while environments reference it.

[oci backend]: https://developer.hashicorp.com/terraform/language/backend/oci

## Workflow

```bash
cd terraform/bootstrap-state && terraform apply        # once
cd ../environments/demo
cp backend.hcl.example backend.hcl                     # paste namespace
cp terraform.tfvars.example terraform.tfvars           # fill values
terraform init -backend-config=backend.hcl
terraform plan -out=tfplan && terraform show tfplan    # review
terraform apply tfplan                                 # exact reviewed plan
```

Pre-deploy checks: `scripts/oci-preflight.sh`, then
`scripts/inventory.sh --compartment <ocid>` to snapshot what already exists.

## Provider versioning

Pinned `oracle/oci ~> 8.0` and Terraform `>= 1.12`. The lockfile is
committed; upgrades happen deliberately via PR, never implicitly.

## Decisions worth remembering

- LB ownership → Kubernetes ([ADR-009]); no Terraform LB module exists.
- Queue → Redis in-cluster behind an app abstraction ([ADR-004]).
- Kubernetes API is restricted to `admin_cidrs` (never `0.0.0.0/0`);
  private-endpoint mode pairs with the bastion module.

[ADR-009]: ../docs/adr/ADR-009-load-balancer-ownership.md
[ADR-004]: ../docs/adr/ADR-004-async-processing.md
