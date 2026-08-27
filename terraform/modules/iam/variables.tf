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

variable "manage_dynamic_groups" {
  description = <<-EOT
    Whether Terraform should create the two tenancy-scoped dynamic groups
    (oke_nodes/oke_workloads) itself.

    OCI dynamic groups are tenancy-scoped resources. On this project the
    deployment user only has compartment-level access to
    shared-group-b-cmp and cannot create, list, or manage dynamic groups
    (confirmed via `oci iam dynamic-group list` returning 404). The
    tenancy administrator creates and owns these two groups by hand,
    using the exact names/rules this module would otherwise generate
    (see locals.nodes_group_name / locals.workload_rule).

    Leave this false for this project. The IAM policies below reference
    the dynamic groups by name only (plain strings), so they attach
    correctly to the admin-created groups without Terraform ever owning
    the group resources. Set to true only in an environment where the
    deployment identity genuinely has tenancy-level dynamic-group
    management rights.
  EOT
  type        = bool
  default     = false
}
