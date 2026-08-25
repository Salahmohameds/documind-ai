variable "compartment_id" {
  description = "Compartment OCID."
  type        = string
}

variable "name_prefix" {
  description = "Naming prefix."
  type        = string
}

variable "target_subnet_id" {
  description = "Subnet the bastion serves (typically oke_api for private-endpoint kubectl)."
  type        = string
}

variable "client_cidr_block_allow_list" {
  description = "Client CIDRs allowed to create bastion sessions. Never 0.0.0.0/0."
  type        = list(string)

  validation {
    condition = alltrue([
      for c in var.client_cidr_block_allow_list : can(cidrnetmask(c)) && c != "0.0.0.0/0"
    ])
    error_message = "Every allow-list entry must be a valid CIDR and not 0.0.0.0/0."
  }
}

variable "tags" {
  description = "Freeform tags."
  type        = map(string)
  default     = {}
}
