# Terraform — DocuMind AI

> Owner: **Cloud Lead (role 1)**. Reviewer for any PR touching this folder: Cloud Lead.

## Layout

```text
terraform/
├── environments/
│   └── dev/          # thin root: wires modules, owns provider + backend
└── modules/
    ├── networking/   # VCN, subnets, IGW/NAT/SGW, route tables
    ├── oke/          # cluster, node pool, NSGs (evolve from week-3 modules)
    ├── iam/          # dynamic groups + least-privilege policies
    ├── ocir/         # repositories + retention
    ├── object-storage/ # buckets (documents, artifacts, tfstate)
    ├── database/     # PostgreSQL + pgvector provisioning
    ├── load-balancer/
    └── monitoring/
```

## Conventions

- Environment roots own the `provider {}` and `backend {}` — modules never do.
- Modules take **no environment-specific OCIDs** — everything via variables.
- Naming: `dm-<env>-<resource>` (e.g. `dm-dev-vcn`). Tags on everything:
  `Project=DocuMind`, `Env`, `Owner`, `ManagedBy=terraform`.
- `*.tfvars` and `backend.hcl` are gitignored — commit only `*.example`.
- Remote state: OCI Object Storage S3-compatible backend (see proposal §15);
  bootstrap pattern reused from the internship repo.

## Workflow

```powershell
cd terraform/environments/dev
copy terraform.tfvars.example terraform.tfvars   # fill locally, never commit
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan -out=tfplan        # attach plan summary to the PR
terraform apply tfplan
```

CI runs fmt + validate + tflint + checkov on every PR touching `terraform/**`.

## Starting point

The week-3 modules in the internship repo
(`E:\work\Ejada\terraform\nonprd\week3-containerized-oke\modules\` — network,
subnet, oke) are the proven baseline to evolve into `modules/networking` and
`modules/oke`.
