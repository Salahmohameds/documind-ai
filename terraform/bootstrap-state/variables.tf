variable "region" {
  description = "OCI region where the state bucket lives."
  type        = string
}

variable "config_file_profile" {
  description = "Profile in ~/.oci/config used for authentication (never commit real keys)."
  type        = string
  default     = "DEFAULT"
}

variable "compartment_ocid" {
  description = "Compartment that owns the state bucket."

  type = string
  validation {
    condition     = startswith(var.compartment_ocid, "ocid1.compartment.")
    error_message = "compartment_ocid must be a compartment OCID (ocid1.compartment.<region>..)."
  }
}

variable "state_bucket_name" {
  description = "Name of the single remote-state bucket."
  type        = string
  default     = "documind-tfstate"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-_.]{2,254}$", var.state_bucket_name))
    error_message = "Bucket names: 3-255 chars, lowercase letters/digits/hyphen/dot/underscore."
  }
}

variable "tags" {
  description = "Freeform tags applied to the bucket."
  type        = map(string)
  default = {
    Project   = "DocuMind-AI"
    ManagedBy = "Terraform"
  }
}
