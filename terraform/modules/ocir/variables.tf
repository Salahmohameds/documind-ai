# OCIR Module — Variables

variable "compartment_id" {
  description = "OCID of the compartment."
  type        = string
}

variable "repository_prefix" {
  description = "Prefix for repository names (e.g. documind-dev)."
  type        = string
}

variable "service_names" {
  description = "List of microservice names to create repos for."
  type        = list(string)
  default = [
    "api-gateway",
    "document-service",
    "processing-service",
    "ai-service",
    "search-service",
  ]
}

variable "is_public" {
  description = "Whether the repositories are public."
  type        = bool
  default     = false
}

variable "is_immutable" {
  description = "Whether image tags are immutable."
  type        = bool
  default     = false
}
