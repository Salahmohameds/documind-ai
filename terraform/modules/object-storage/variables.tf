variable "compartment_id" {
  description = "Compartment OCID."
  type        = string
}

variable "name_prefix" {
  description = "Naming prefix (bucket names become <prefix>-documents etc.)."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.name_prefix))
    error_message = "name_prefix must keep bucket names lowercase (letters/digits/hyphens)."
  }
}

variable "namespace" {
  description = "Object Storage namespace."
  type        = string
}

variable "enable_versioning" {
  description = "Enable bucket versioning (recommended; cheap insurance against deletes)."
  type        = bool
  default     = true
}

variable "multipart_abort_days" {
  description = "Abort incomplete multipart uploads after N days."
  type        = number
  default     = 7

  validation {
    condition     = var.multipart_abort_days >= 1 && var.multipart_abort_days <= 30
    error_message = "multipart_abort_days must be between 1 and 30."
  }
}

variable "enable_lifecycle_policy" {
  description = <<-EOT
    Whether to create the abort-incomplete-multipart-upload lifecycle rule.
    Default false: applying it requires the Object Storage service
    principal (objectstorage-<region>) to already have management
    permission on the bucket, which is a tenancy/root-level policy grant
    this compartment-scoped deployment identity does not have (confirmed:
    400 InsufficientServicePermissions on first apply). This is cost
    hygiene, not a functional requirement for the demo -- set true once an
    admin confirms/grants that service-principal permission.
  EOT
  type        = bool
  default     = false
}

variable "tags" {
  description = "Freeform tags."
  type        = map(string)
  default     = {}
}
