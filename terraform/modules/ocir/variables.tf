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
    "frontend",
  ]
}

variable "is_immutable" {
  description = <<-EOT
    Immutable repositories reject overwriting an existing tag. CI pushes
    git-SHA tags, so immutability is safe and prevents accidental :latest
    drift -- however, `CreateContainerRepository` in this region/tenancy
    currently rejects the isImmutable field outright (confirmed: 400
    BAD_REQUEST "Setting isImmutable is not currently supported" on first
    apply), so this defaults to false for now. Tag discipline is still
    enforced independently: no Kubernetes manifest or CI workflow in this
    repo ever references ':latest'. Flip to true once OCI supports it here.
  EOT
  type        = bool
  default     = false
}

variable "is_public" {
  description = "Public pull access. Keep false — images are pulled with node principals."
  type        = bool
  default     = false
}
