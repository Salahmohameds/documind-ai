# Networking Module — Variables

variable "compartment_id" {
  description = "OCID of the compartment to create resources in."
  type        = string
}

variable "name_prefix" {
  description = "Prefix for all resource names (e.g. dm)."
  type        = string
}

variable "vcn_cidr" {
  description = "CIDR block for the VCN."
  type        = string
  default     = "10.20.0.0/16"
}

variable "vcn_dns_label" {
  description = "DNS label for the VCN."
  type        = string
  default     = "documind"
}

variable "subnet_cidrs" {
  description = "Map of subnet CIDRs. Keys: public, oke_workers, oke_pods, data."
  type        = map(string)
  default = {
    public      = "10.20.1.0/24"
    oke_workers = "10.20.10.0/24"
    oke_pods    = "10.20.11.0/24"
    data        = "10.20.30.0/24"
  }
}

variable "tags" {
  description = "Freeform tags to apply to all resources."
  type        = map(string)
  default     = {}
}
