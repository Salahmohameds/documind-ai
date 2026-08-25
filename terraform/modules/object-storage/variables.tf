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

variable "tags" {
  description = "Freeform tags."
  type        = map(string)
  default     = {}
}
