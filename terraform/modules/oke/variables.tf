# OKE Module — Variables

variable "compartment_id" {
  description = "OCID of the compartment."
  type        = string
}

variable "name_prefix" {
  description = "Prefix for all resource names."
  type        = string
}

variable "environment" {
  description = "Environment name (dev, prod)."
  type        = string
}

variable "vcn_id" {
  description = "OCID of the VCN."
  type        = string
}

variable "subnet_oke_workers_id" {
  description = "OCID of the private OKE workers subnet."
  type        = string
}

variable "subnet_oke_pods_id" {
  description = "OCID of the private OKE pods subnet (VCN-native)."
  type        = string
}

variable "subnet_lb_id" {
  description = "OCID of the public LB subnet (for service LBs)."
  type        = string
}

variable "nsg_oke_api_id" {
  description = "OCID of the OKE API endpoint NSG."
  type        = string
}

variable "nsg_workers_id" {
  description = "OCID of the OKE worker nodes NSG."
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version for the cluster."
  type        = string
  default     = "v1.33.10"
}

variable "cluster_endpoint_public" {
  description = "Whether the cluster API endpoint is public."
  type        = bool
  default     = true
}

variable "node_shape" {
  description = "Shape of the worker nodes."
  type        = string
  default     = "VM.Standard.E4.Flex"
}

variable "node_shape_config" {
  description = "Flex shape configuration (ocpus, memory_in_gbs). Set to null for fixed shapes."
  type = object({
    ocpus         = number
    memory_in_gbs = number
  })
  default = {
    ocpus         = 2
    memory_in_gbs = 16
  }
}

variable "node_pool_size" {
  description = "Number of worker nodes."
  type        = number
  default     = 2
}

variable "max_pods_per_node" {
  description = "Maximum number of pods per node (VCN-native)."
  type        = number
  default     = 31
}

variable "node_image_id" {
  description = "OCID of the node image (Oracle Linux for OKE)."
  type        = string
}

variable "availability_domain" {
  description = "Availability domain for node placement. Empty = use first AD."
  type        = string
  default     = ""
}

variable "ssh_public_key" {
  description = "SSH public key for node access (optional)."
  type        = string
  default     = ""
}

variable "services_cidr" {
  description = "CIDR for Kubernetes services."
  type        = string
  default     = "10.96.0.0/16"
}

variable "tags" {
  description = "Freeform tags."
  type        = map(string)
  default     = {}
}
