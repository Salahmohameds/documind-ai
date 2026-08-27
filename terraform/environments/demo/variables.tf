# ---------------------------------------------------------------------------
# Provider / tenancy
# ---------------------------------------------------------------------------

variable "region" {
  description = "OCI region key (team default: me-jeddah-1)."
  type        = string
}

variable "config_file_profile" {
  description = "~/.oci/config profile. Empty string lets OCI_* environment variables / SDK defaults take over (CI)."
  type        = string
  default     = "DEFAULT"
}

variable "tenancy_ocid" {
  description = "Tenancy OCID (required — dynamic groups live at tenancy scope)."

  type = string
  validation {
    condition     = startswith(var.tenancy_ocid, "ocid1.tenancy.")
    error_message = "tenancy_ocid must be a tenancy OCID (ocid1.tenancy...)."
  }
}

variable "user_ocid" {
  description = "User OCID for explicit API-key auth in CI. Leave null locally."
  type        = string
  default     = null
  sensitive   = true
}

variable "fingerprint" {
  description = "API-key fingerprint for explicit auth in CI."
  type        = string
  default     = null
  sensitive   = true
}

variable "private_key_path" {
  description = "Path to the API signing key for explicit auth in CI."
  type        = string
  default     = null
  sensitive   = true
}

variable "compartment_id" {
  description = "Compartment that owns every DocuMind demo resource."

  type = string
  validation {
    condition     = startswith(var.compartment_id, "ocid1.compartment.")
    error_message = "compartment_id must be a compartment OCID."
  }
}

variable "owner" {
  description = "Owner freeform tag value (email or team handle)."
  type        = string
}

# ---------------------------------------------------------------------------
# Naming / network
# ---------------------------------------------------------------------------

variable "environment" {
  description = "Environment name."

  type    = string
  default = "demo"

  validation {
    condition     = var.environment == "demo"
    error_message = "This root is the demo environment; other environments get their own folder later."
  }
}

variable "vcn_cidr" {
  description = "VCN CIDR (must not overlap kubernetes services CIDR — validated below)."
  type        = string
  default     = "10.20.0.0/16"
}

variable "vcn_dns_label" {
  description = "VCN DNS label."
  type        = string
  default     = "dmvcn"
}

variable "subnets" {
  description = <<-EOT
    Subnet overrides. Only overrides need to be listed; oke_api's route/private
    mode is derived from oke_endpoint_public automatically.
  EOT
  type = map(object({
    cidr        = string
    dns_label   = string
    private     = bool
    route       = string
    enable_logs = optional(bool, false)
  }))
  default = {
    public_lb = {
      cidr = "10.20.1.0/24", dns_label = "publb", private = false, route = "igw", enable_logs = true
    }
    oke_api = {
      cidr = "10.20.2.0/28", dns_label = "okeapi", private = false, route = "igw"
    }
    oke_workers = {
      cidr = "10.20.10.0/24", dns_label = "okeworkers", private = true, route = "nat"
    }
    oke_pods = {
      cidr = "10.20.64.0/18", dns_label = "okepods", private = true, route = "nat"
    }
    data = {
      cidr = "10.20.30.0/24", dns_label = "data", private = true, route = "none"
    }
  }
}

variable "admin_cidrs" {
  description = "CIDRs allowed to the Kubernetes API, worker SSH and bastion. Your laptop IP /32 — never 0.0.0.0/0."
  type        = list(string)

  validation {
    condition = length(var.admin_cidrs) > 0 && !contains(var.admin_cidrs, "0.0.0.0/0") && alltrue([
      for c in var.admin_cidrs : can(cidrnetmask(c))
    ])
    error_message = "Set admin_cidrs to specific client CIDRs (e.g. [\"203.0.113.7/32\"]); 0.0.0.0/0 is rejected."
  }
}

variable "enable_service_gateway" {
  description = "Private Oracle Services Network path (OCIR/Object Storage/GenAI)."
  type        = bool
  default     = true
}

variable "enable_flow_logs" {
  description = "VCN flow logs on subnets flagged enable_logs (log ingestion cost)."
  type        = bool
  default     = false
}

# ---------------------------------------------------------------------------
# OKE
# ---------------------------------------------------------------------------

variable "enable_oke" {
  description = "Create the OKE cluster and node pools (Stage B of the burst runbook)."
  type        = bool
  default     = true
}

variable "oke_endpoint_public" {
  description = "Public Kubernetes API endpoint (intern laptop kubectl). NSGs still restrict to admin_cidrs."
  type        = bool
  default     = true
}

variable "oke_cluster_type" {
  description = <<-EOT
    BASIC_CLUSTER keeps cost minimal; ENHANCED_CLUSTER enables OKE
    Workload Identity (pod-level resource principals).

    This demo's pods (ai-service, processing-service, document-service)
    authenticate to Object Storage / OCI Generative AI / Vault as the
    dm-demo-dg-workloads dynamic group via OKE Workload Identity, which
    Oracle only supports on Enhanced Clusters -- a Basic Cluster would
    accept the same IAM policy/dynamic-group configuration but pods would
    never actually receive credentials, so all those calls would fail
    auth regardless of how correct the IAM policies are. Defaulting to
    ENHANCED_CLUSTER here is required for this project's runtime AI/
    storage/secrets access to work, not just a hardening choice.
  EOT

  type    = string
  default = "ENHANCED_CLUSTER"

  validation {
    condition     = contains(["BASIC_CLUSTER", "ENHANCED_CLUSTER"], var.oke_cluster_type)
    error_message = "oke_cluster_type must be BASIC_CLUSTER or ENHANCED_CLUSTER."
  }
}

variable "manage_dynamic_groups" {
  description = <<-EOT
    Passed through to module.iam. Keep false: the tenancy administrator
    (Eng. Belal) already created dm-demo-dg-oke-nodes and
    dm-demo-dg-workloads by hand with the matching rules this project
    expects, and the deployment user has no tenancy-level dynamic-group
    permissions (confirmed: `oci iam dynamic-group list` returns 404 for
    this identity). Only set true if a future deployment identity
    genuinely has tenancy-level IAM rights and should own these groups.
  EOT
  type        = bool
  default     = false
}

variable "kubernetes_version" {
  description = "Kubernetes version; empty selects the latest the region offers."
  type        = string
  default     = ""
}

variable "node_pools" {
  description = "Node pool map consumed by modules/oke (see module docs)."

  type = map(object({
    size           = number
    shape          = string
    ocpus          = optional(number, 1)
    memory_in_gbs  = optional(number, 8)
    boot_volume_gb = optional(number, 50)
    labels         = optional(map(string), {})
  }))

  validation {
    condition     = alltrue([for p in values(var.node_pools) : p.size >= 1 && p.size <= 5])
    error_message = "Pool sizes must be between 1 and 5 (shared-tenancy quota guard)."
  }

  default = {
    apps = { size = 1, shape = "VM.Standard.E4.Flex", ocpus = 2, memory_in_gbs = 8 }
  }
}

variable "max_pods_per_node" {
  description = "Max pods per node under VCN-native CNI."
  type        = number
  default     = 31
}

variable "node_image_id" {
  description = "Pin a node image OCID when auto-resolution returns nothing on restricted compartments."
  type        = string
  default     = ""
}

variable "availability_domain_index" {
  description = "Zero-based AD index used for pools and database placement."
  type        = number
  default     = 0
}

variable "ssh_public_key" {
  description = "Optional worker SSH key. Prefer empty + bastion sessions."
  type        = string
  default     = ""
  sensitive   = true
}

variable "services_cidr" {
  description = "Kubernetes Service CIDR. Overlap with the VCN fails at plan time via the check block."

  type    = string
  default = "10.96.0.0/16"

  validation {
    condition     = can(cidrnetmask(var.services_cidr))
    error_message = "services_cidr must be valid CIDR notation."
  }
}

# ---------------------------------------------------------------------------
# Optional components
# ---------------------------------------------------------------------------

variable "enable_bastion" {
  description = "Create an OCI Bastion anchored to the API-endpoint subnet."
  type        = bool
  default     = false
}

variable "enable_monitoring" {
  description = "Alert topic + node/LB alarms."
  type        = bool
  default     = true
}

variable "alert_emails" {
  description = "Emails subscribed to alerts."
  type        = set(string)
  default     = []
}

variable "cpu_threshold_percent" {
  description = "Node CPU alarm threshold (%)."
  type        = number
  default     = 85
}

variable "memory_threshold_percent" {
  description = "Node memory alarm threshold (%)."
  type        = number
  default     = 90
}

variable "lb_5xx_threshold" {
  description = "LB 5xx-per-interval alarm threshold."
  type        = number
  default     = 5
}

variable "lb_ocid" {
  description = "Kubernetes-created Service LB OCID discovered post-deploy; null skips LB alarms."
  type        = string
  default     = null
}

# ---------------------------------------------------------------------------
# Database with PostgreSQL (optional)
# ---------------------------------------------------------------------------

variable "enable_database" {
  description = "Create OCI Database with PostgreSQL (quota/cost sensitive)."
  type        = bool
  default     = false
}

variable "db_version" {
  description = "PostgreSQL major version."
  type        = string
  default     = "16"
}

variable "db_shape" {
  description = "Database shape."
  type        = string
  default     = "VM.Standard.E4.Flex"
}

variable "db_instance_ocpus" {
  description = "OCPUs per database node."
  type        = number
  default     = 1
}

variable "db_instance_memory_gbs" {
  description = "Memory GB per database node."
  type        = number
  default     = 8
}

variable "db_instance_count" {
  description = "Number of database nodes."
  type        = number
  default     = 1
}

variable "db_password_mode" {
  description = "VAULT_SECRET (recommended) or PLAIN_TEXT for throwaway bursts."
  type        = string
  default     = "PLAIN_TEXT"

  validation {
    condition     = contains(["VAULT_SECRET", "PLAIN_TEXT"], var.db_password_mode)
    error_message = "db_password_mode must be VAULT_SECRET or PLAIN_TEXT."
  }
}

variable "db_admin_password" {
  description = "Admin password in PLAIN_TEXT mode. Sensitive — lives in state; keep the state bucket locked down."
  type        = string
  default     = ""
  sensitive   = true
}

variable "db_password_secret_id" {
  description = "Vault secret OCID in VAULT_SECRET mode."
  type        = string
  default     = ""
}

variable "db_enable_daily_backups" {
  description = "Daily backups (small cost). Disable only if quota-blocked."
  type        = bool
  default     = true
}

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

variable "ocir_namespace" {
  description = <<-EOT
    OCIR repository-path prefix override. Empty (the default) uses
    "<tenancy Object Storage namespace>/documind", matching every
    Kubernetes Deployment manifest's image path
    (REGION.ocir.io/NAMESPACE/documind/<service>:TAG). Set this only if you
    need a different prefix -- and update the image paths in kubernetes/
    to match.
  EOT
  type        = string
  default     = ""
}
