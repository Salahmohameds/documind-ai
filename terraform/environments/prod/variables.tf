# DocuMind AI — Prod Environment — Variables
# Same structure as dev, but with production-grade defaults


# ─── OCI Provider ────────────────────────────────────────────────────────────
variable "tenancy_ocid" {
  description = "OCID of the OCI tenancy."
  type        = string
}

variable "user_ocid" {
  description = "OCID of the OCI user for the provider."
  type        = string
}

variable "fingerprint" {
  description = "Fingerprint of the API signing key."
  type        = string
}

variable "private_key_path" {
  description = "Path to the OCI API private key file."
  type        = string
}

variable "region" {
  description = "OCI region."
  type        = string
}

variable "compartment_id" {
  description = "OCID of the compartment."
  type        = string
}

# ─── Environment ─────────────────────────────────────────────────────────────
variable "environment" {
  description = "Environment name."
  type        = string
  default     = "prod"
}

# ─── Networking ──────────────────────────────────────────────────────────────
variable "vcn_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "vcn_dns_label" {
  type    = string
  default = "documind"
}

variable "subnet_cidrs" {
  type = map(string)
  default = {
    public      = "10.20.1.0/24"
    oke_workers = "10.20.10.0/24"
    oke_pods    = "10.20.11.0/24"
    data        = "10.20.30.0/24"
  }
}

# ─── OKE ─────────────────────────────────────────────────────────────────────
variable "kubernetes_version" {
  type    = string
  default = "v1.33.10"
}

variable "node_shape" {
  type    = string
  default = "VM.Standard.E4.Flex"
}

variable "node_ocpus" {
  type    = number
  default = 4
}

variable "node_memory_gbs" {
  type    = number
  default = 32
}

variable "node_pool_size" {
  type    = number
  default = 3
}

variable "max_pods_per_node" {
  type    = number
  default = 31
}

variable "node_image_id" {
  type = string
}

variable "availability_domain" {
  type = string
}

variable "ssh_public_key" {
  type    = string
  default = ""
}

# ─── Object Storage ─────────────────────────────────────────────────────────
variable "object_storage_namespace" {
  type = string
}

# ─── Database ────────────────────────────────────────────────────────────────
variable "db_admin_password" {
  type      = string
  sensitive = true
}

variable "db_shape" {
  type    = string
  default = "PostgreSQL.VM.Standard.E4.Flex.4.64GB"
}

# ─── Load Balancer ───────────────────────────────────────────────────────────
variable "lb_min_bandwidth" {
  type    = number
  default = 100
}

variable "lb_max_bandwidth" {
  type    = number
  default = 400
}

# ─── Monitoring ──────────────────────────────────────────────────────────────
variable "alert_emails" {
  type    = list(string)
  default = []
}

# ─── OCIR ────────────────────────────────────────────────────────────────────
variable "ocir_repo_prefix" {
  type    = string
  default = "documind"
}
