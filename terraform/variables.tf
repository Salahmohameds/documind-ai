# DocuMind AI — Root Input Variables


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
  default     = "me-jeddah-1"
}

variable "compartment_id" {
  description = "OCID of the compartment."
  type        = string
}

variable "environment" {
  description = "Environment name."
  type        = string
  default     = "dev"
}

variable "vcn_cidr" {
  description = "VCN CIDR block."
  type        = string
  default     = "10.20.0.0/16"
}

variable "vcn_dns_label" {
  description = "DNS label for the VCN."
  type        = string
  default     = "documind"
}

variable "subnet_cidrs" {
  description = "Map of subnet CIDRs."
  type        = map(string)
  default = {
    public      = "10.20.1.0/24"
    oke_workers = "10.20.10.0/24"
    oke_pods    = "10.20.11.0/24"
    data        = "10.20.30.0/24"
  }
}

variable "kubernetes_version" {
  description = "Kubernetes version for OKE."
  type        = string
  default     = "v1.33.10"
}

variable "node_shape" {
  description = "OKE node shape."
  type        = string
  default     = "VM.Standard.E4.Flex"
}

variable "node_ocpus" {
  description = "OCPUs per node."
  type        = number
  default     = 2
}

variable "node_memory_gbs" {
  description = "Memory in GBs per node."
  type        = number
  default     = 16
}

variable "node_pool_size" {
  description = "Number of worker nodes."
  type        = number
  default     = 2
}

variable "max_pods_per_node" {
  description = "Maximum pods per node."
  type        = number
  default     = 31
}

variable "node_image_id" {
  description = "OCID of the OKE node image."
  type        = string
  default     = "ocid1.image.oc1.me-jeddah-1.aaaaaaaahdp6j4yf7assbi5kknzogwc4u32bsr6vehtitxfsatnrjw6nrynq"
}

variable "availability_domain" {
  description = "Availability domain name."
  type        = string
  default     = "oXVt:ME-JEDDAH-1-AD-1"
}

variable "ssh_public_key" {
  description = "SSH public key."
  type        = string
  default     = ""
}

variable "object_storage_namespace" {
  description = "OCI Object Storage namespace."
  type        = string
  default     = "axkjllkftxfz"
}

variable "db_admin_password" {
  description = "Admin password for PostgreSQL."
  type        = string
  sensitive   = true
  default     = "DocuMind_2026_SecurePass!"
}

variable "db_shape" {
  description = "PostgreSQL DB System shape."
  type        = string
  default     = "PostgreSQL.VM.Standard.E4.Flex.2.32GB"
}

variable "lb_min_bandwidth" {
  description = "Minimum LB bandwidth in Mbps."
  type        = number
  default     = 10
}

variable "lb_max_bandwidth" {
  description = "Maximum LB bandwidth in Mbps."
  type        = number
  default     = 100
}

variable "alert_emails" {
  description = "Email addresses for monitoring alerts."
  type        = list(string)
  default     = []
}

variable "ocir_repo_prefix" {
  description = "Prefix for OCIR repositories."
  type        = string
  default     = "documind"
}
