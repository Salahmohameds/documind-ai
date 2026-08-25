variable "compartment_id" {
  description = "Compartment OCID owning the repositories."
  type        = string
}

variable "region" {
  description = "Region key used to build full registry paths (e.g. me-jeddah-1)."
  type        = string
}

variable "repository_prefix" {
  description = "Repository path prefix, conventionally the tenancy namespace (e.g. <namespace>/documind)."
  type        = string

  validation {
    condition     = var.repository_prefix != "" && !strcontains(var.repository_prefix, "//")
    error_message = "repository_prefix must be non-empty and free of double slashes."
  }
}

variable "service_names" {
  description = "One immutable-tag repository per microservice."
  type        = set(string)
  default = [
    "api-gateway",
    "document-service",
    "processing-service",
    "ai-service",
    "search-service",
  ]
}

variable "is_immutable" {
  description = <<-EOT
    Immutable repositories reject overwriting an existing tag. CI pushes
    git-SHA tags, so immutability is safe and prevents accidental :latest
    drift. Set false only for throwaway experiments.
  EOT
  type        = bool
  default     = true
}

variable "is_public" {
  description = "Public pull access. Keep false — images are pulled with node principals."
  type        = bool
  default     = false
}
