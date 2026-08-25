# Object Storage Module — Variables

variable "compartment_id" {
  description = "OCID of the compartment."
  type        = string
}

variable "name_prefix" {
  description = "Prefix for bucket names."
  type        = string
}

variable "object_storage_namespace" {
  description = "OCI Object Storage namespace."
  type        = string
}

variable "create_state_bucket" {
  description = "Whether to create a Terraform state bucket."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Freeform tags."
  type        = map(string)
  default     = {}
}
