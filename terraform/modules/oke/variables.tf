variable "compartment_id" {
  description = "Compartment OCID for the cluster and node pools."
  type        = string
}

variable "name_prefix" {
  description = "Display-name prefix (e.g. dm-demo)."
  type        = string
}

variable "vcn_id" {
  description = "VCN OCID hosting the cluster."
  type        = string
}

variable "environment" {
  description = "Environment label applied to node metadata."
  type        = string
}

variable "cluster_type" {
  description = "BASIC_CLUSTER (cheap lab) or ENHANCED_CLUSTER (required for OKE Workload Identity)."
  type        = string
  default     = "BASIC_CLUSTER"

  validation {
    condition     = contains(["BASIC_CLUSTER", "ENHANCED_CLUSTER"], var.cluster_type)
    error_message = "cluster_type must be BASIC_CLUSTER or ENHANCED_CLUSTER."
  }
}

variable "cni_type" {
  description = "Pod networking CNI."
  type        = string
  default     = "OCI_VCN_IP_NATIVE"

  validation {
    condition     = contains(["OCI_VCN_IP_NATIVE", "FLANNEL_OVERLAY"], var.cni_type)
    error_message = "cni_type must be OCI_VCN_IP_NATIVE or FLANNEL_OVERLAY."
  }
}

variable "kubernetes_version" {
  description = "Kubernetes version (e.g. v1.33.1). Empty selects the latest offered by the region."
  type        = string
  default     = ""
}

variable "endpoint_public" {
  description = "Public Kubernetes API endpoint. The oke_api subnet route must match (igw when true, nat when false)."
  type        = bool
  default     = true
}

variable "endpoint_subnet_id" {
  description = "Dedicated Kubernetes API endpoint subnet OCID."
  type        = string
}

variable "worker_subnet_id" {
  description = "Private worker-node subnet OCID."
  type        = string
}

variable "pod_subnet_ids" {
  description = "Pod subnet OCIDs (required for VCN-native CNI)."
  type        = list(string)
}

variable "lb_subnet_id" {
  description = "Public subnet used by Service load balancers."
  type        = string
}

variable "nsg_api_id" {
  description = "NSG attached to the API endpoint."
  type        = string
}

variable "nsg_workers_id" {
  description = "NSG attached to worker nodes."
  type        = string
}

variable "nsg_pods_id" {
  description = "NSG attached to pod VNICs (VCN-native only)."
  type        = string
}

variable "node_pools" {
  description = <<-EOT
    Node pools keyed by logical name. Flex shapes use ocpus/memory_in_gbs;
    fixed shapes ignore them. labels land as initial node labels.
  EOT
  type = map(object({
    size           = number
    shape          = string
    ocpus          = optional(number, 1)
    memory_in_gbs  = optional(number, 8)
    boot_volume_gb = optional(number, 50)
    labels         = optional(map(string), {})
  }))

  validation {
    condition     = length(var.node_pools) > 0 && alltrue([for p in values(var.node_pools) : p.size >= 1])
    error_message = "Define at least one node pool with size >= 1."
  }

  validation {
    condition     = alltrue([for p in values(var.node_pools) : p.ocpus >= 1 && p.memory_in_gbs >= 1])
    error_message = "Flex ocpus and memory_in_gbs must both be >= 1."
  }
}

variable "max_pods_per_node" {
  description = "Max pods per worker (VCN-native CNI)."
  type        = number
  default     = 31
}

variable "services_cidr" {
  description = "Kubernetes Service CIDR (must not overlap the VCN — validated at the environment root)."
  type        = string
  default     = "10.96.0.0/16"
}

variable "pods_cidr" {
  description = "Flannel overlay pod CIDR. Ignored with OCI_VCN_IP_NATIVE."
  type        = string
  default     = "10.244.0.0/16"
}

variable "node_image_id" {
  description = "OKE-compatible node image OCID. Empty auto-selects the newest matching Oracle Linux OKE image."
  type        = string
  default     = ""
}

variable "availability_domain_index" {
  description = "Zero-based availability-domain index for every pool's placement."
  type        = number
  default     = 0

  validation {
    condition     = var.availability_domain_index >= 0
    error_message = "availability_domain_index must be >= 0."
  }
}

variable "ssh_public_key" {
  description = "Optional SSH public key for worker nodes. Prefer empty in shared tenancies."
  type        = string
  default     = ""
  sensitive   = true
}

variable "dashboard_enabled" {
  description = "Enable the Kubernetes dashboard add-on (keep off for demos)."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Freeform tags applied to the cluster and pools."
  type        = map(string)
  default     = {}
}
