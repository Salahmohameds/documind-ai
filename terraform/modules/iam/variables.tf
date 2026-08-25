variable "tenancy_id" {
  description = "Tenancy OCID (dynamic groups live at tenancy scope)."
  type        = string
}

variable "compartment_id" {
  description = "Compartment OCID the policies and resource claims target."
  type        = string
}

variable "name_prefix" {
  description = "Naming prefix (e.g. dm-demo)."
  type        = string
}

variable "cluster_id" {
  description = <<-EOT
    OKE cluster OCID. When set, the workload dynamic group matches pods of
    THIS cluster only; otherwise it matches every pod in the compartment.
  EOT
  type        = string
  default     = ""
}

variable "workload_matching_rule" {
  description = "Override the generated OKE workload-identity dynamic-group rule entirely if OCI docs update the claim syntax."
  type        = string
  default     = ""
}

variable "documents_bucket_name" {
  description = "Bucket holding raw uploaded documents."
  type        = string
}

variable "processed_bucket_name" {
  description = "Bucket holding processed/derived artifacts."
  type        = string
}

variable "tags" {
  description = "Freeform tags."
  type        = map(string)
  default     = {}
}
