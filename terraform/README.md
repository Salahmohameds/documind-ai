# Terraform — DocuMind AI Infrastructure

> **Owner**: Cloud Lead (Role 1)
> **Reviewer**: Cloud Lead for any PR touching `terraform/`

## 🏗 Architecture Overview

Matches the **DocuMind AI — Cloud-Native Architecture on OCI** diagram.

```
INTERNET
    │
    ▼  HTTPS 443 via IGW
┌─────────────────────────────────────────────────────────────────────────┐
│  ORACLE CLOUD INFRASTRUCTURE — region: me-jeddah-1                    │
│                                                                         │
│  VCN — dm-vcn (10.20.0.0/16)                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Public Subnet — 10.20.1.0/24                                    │  │
│  │  ┌──────────────────────┐                                        │  │
│  │  │ OCI Flexible LB      │  NSG: dm-nsg-lb                       │  │
│  │  │ HTTP/S 443            │                                       │  │
│  │  └──────────┬───────────┘                                        │  │
│  ├─────────────┼────────────────────────────────────────────────────┤  │
│  │  Private Subnet — OKE workers 10.20.10.0/24                     │  │
│  │  Private Subnet — pods (VCN-native) 10.20.11.0/24               │  │
│  │  ┌───────────────────────────────────────────────────────────┐   │  │
│  │  │  OKE — dm-oke · managed node pool (private)              │   │  │
│  │  │  namespace: documind                                      │   │  │
│  │  │  ┌──────────┐ ┌───────────┐ ┌────────────┐ ┌──────────┐ │   │  │
│  │  │  │API Gateway│ │Doc Service│ │Processing  │ │AI Service│ │   │  │
│  │  │  └──────────┘ └───────────┘ │Workers     │ └──────────┘ │   │  │
│  │  │                             └────────────┘               │   │  │
│  │  │  ┌──────────────┐                                        │   │  │
│  │  │  │Search Service│     NSG: dm-nsg-workers                │   │  │
│  │  │  └──────────────┘                                        │   │  │
│  │  └───────────────────────────────────────────────────────────┘   │  │
│  ├──────────────────────────────────────────────────────────────────┤  │
│  │  Private Subnet — data 10.20.30.0/24  (NO internet route)      │  │
│  │  ┌───────────────────────┐  ┌───────────────────┐               │  │
│  │  │PostgreSQL + pgvector  │  │Redis (Streams,    │               │  │
│  │  │metadata, jobs         │  │ queue, cache)     │               │  │
│  │  └───────────────────────┘  └───────────────────┘               │  │
│  │  NSG: dm-nsg-data (dm-nsg-workers only, 5432/6379)             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  Regional Services (via SGW / IAM):                                    │
│  OCI GenAI · OCI Vault · OCIR · OCI IAM · Object Storage · Monitoring │
└─────────────────────────────────────────────────────────────────────────┘
```

## 📁 Layout

```text
terraform/
├── environments/
│   ├── dev/                    # Dev environment root
│   │   ├── providers.tf        # OCI provider config
│   │   ├── backend.tf          # Remote state (S3-compatible)
│   │   ├── backend.hcl.example # Backend config template
│   │   ├── main.tf             # Wires all modules
│   │   ├── variables.tf        # Input variables
│   │   ├── outputs.tf          # Resource outputs
│   │   └── terraform.tfvars.example
│   └── prod/                   # Prod environment (same structure)
│
└── modules/
    ├── networking/             # VCN, 4 subnets, 3 gateways, 3 route tables, 4 NSGs
    ├── oke/                    # OKE cluster + node pool (VCN-native pods)
    ├── iam/                    # Dynamic groups + least-privilege policies
    ├── ocir/                   # Container repositories (5 services)
    ├── object-storage/         # Document + processed + state buckets
    ├── database/               # PostgreSQL DB System
    ├── load-balancer/          # Flexible public LB
    └── monitoring/             # Alarms, notifications, logging
```

## 🧩 Modules

| Module | Resources | Purpose |
|--------|-----------|---------|
| **networking** | VCN, 4 subnets, IGW, NAT, SGW, 3 route tables, 4 NSGs, 3 security lists | Foundation network |
| **oke** | OKE Cluster (VCN-native), Node Pool | Kubernetes platform |
| **iam** | 3 dynamic groups, 5 IAM policies | Least-privilege access |
| **ocir** | 5 container repositories | Docker image registry |
| **object-storage** | 3 buckets (docs, processed, tf-state) | File storage |
| **database** | PostgreSQL DB System | Application database |
| **load-balancer** | Flexible LB, backend set, HTTP/HTTPS listeners | Traffic entry point |
| **monitoring** | Alarms, notification topic, log group, logs | Observability |

## 🔐 Security Design (Defense in Depth)

```
Network Level:
  ├── VCN isolation — dm-vcn /16
  ├── 4 subnets (public / private-workers / private-pods / private-data)
  ├── Route tables: public (IGW) / private (NAT+SGW) / data (SGW only)
  ├── NSGs — workload-scoped rules (NSG-to-NSG references)
  ├── Security lists — subnet defaults
  └── Data subnet: zero-trust, NO internet route, dm-nsg-workers only

IAM Level:
  ├── Dynamic Groups per workload
  ├── Least-privilege policies
  └── No admin/broad permissions

Secrets:
  ├── .tfvars and backend.hcl gitignored
  ├── Sensitive variables marked
  └── OCI Vault ready
```

## 📋 Naming Convention

All resources use the `dm` prefix:
- `dm-vcn`, `dm-oke`, `dm-nsg-lb`, `dm-nsg-workers`, `dm-nsg-data`
- `dm-sn-public`, `dm-sn-private-oke-workers`, `dm-sn-private-data`

## 🏷 Tags

All resources get:
```hcl
Project   = "DocuMind"
Env       = "dev" | "prod"
Owner     = "cloud-lead"
ManagedBy = "terraform"
```

## 🚀 Quick Start

### Prerequisites
1. [Terraform](https://www.terraform.io/downloads) >= 1.5.0
2. [OCI CLI](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/cliconcepts.htm) configured
3. OCI API key pair

### Deploy Dev Environment
```powershell
cd terraform/environments/dev

# 1. Create config files from templates
copy terraform.tfvars.example terraform.tfvars
copy backend.hcl.example backend.hcl

# 2. Fill in your OCI values
notepad terraform.tfvars
notepad backend.hcl

# 3. Initialize
terraform init -backend-config=backend.hcl

# 4. Validate
terraform fmt -check -recursive
terraform validate

# 5. Plan
terraform plan -out=tfplan

# 6. Apply
terraform apply tfplan
```

### Get Your OCI Values
```powershell
# Object Storage namespace
oci os ns get

# Availability Domain
oci iam availability-domain list --compartment-id <COMPARTMENT_OCID>

# OKE node images
oci ce node-pool-options get --node-pool-option-id all --compartment-id <COMPARTMENT_OCID>
```

## 🔄 CI/CD Integration

PRs touching `terraform/**` trigger:
1. `terraform fmt -check`
2. `terraform validate`
3. `tflint`
4. `checkov`
5. `terraform plan` (summary in PR comment)

## ⚠️ Important for Team Members

- **NEVER commit** `terraform.tfvars` or `backend.hcl` — they contain your credentials
- **Copy the `.example` files** and fill in your own OCI values
- All personal OCIDs, keys, and passwords are kept in gitignored files only
- Modules are environment-agnostic — no hardcoded OCIDs anywhere
