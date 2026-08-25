variable "compartment_id" {
  description = "Compartment OCID for the PostgreSQL system."
  type        = string
}

variable "name_prefix" {
  description = "Naming prefix."
  type        = string
}

variable "subnet_id" {
  description = "Private data subnet OCID. The database has no public access by design."
  type        = string
}

variable "nsg_ids" {
  description = "NSGs attached to the database VNICs."
  type        = list(string)
}

variable "availability_domain" {
  description = "Availability domain for AD-local storage (required when storage is not regionally durable)."
  type        = string
}

variable "db_version" {
  description = "PostgreSQL major version offered by OCI Database with PostgreSQL (e.g. 16). Adjust to the versions your region offers."
  type        = string
  default     = "16"

  validation {
    condition     = can(regex("^[0-9]+$", var.db_version))
    error_message = "db_version must be a major version number such as '16'."
  }
}

variable "shape" {
  description = "Database shape (VM.Standard.E4.Flex family)."
  type        = string
  default     = "VM.Standard.E4.Flex"

  validation {
    condition     = can(regex("^VM\\.Standard\\.E[0-9]\\.Flex$", var.shape))
    error_message = "shape must be an elastic compute shape like VM.Standard.E4.Flex."
  }
}

variable "instance_ocpus" {
  description = "OCPUs per database node."
  type        = number
  default     = 1

  validation {
    condition     = var.instance_ocpus >= 1
    error_message = "instance_ocpus must be >= 1."
  }
}

variable "instance_memory_gbs" {
  description = "Memory (GB) per database node."
  type        = number
  default     = 8

  validation {
    condition     = var.instance_memory_gbs >= 1
    error_message = "instance_memory_gbs must be >= 1."
  }
}

variable "instance_count" {
  description = "Number of database nodes (1 for the demo burst)."
  type        = number
  default     = 1

  validation {
    condition     = var.instance_count >= 1 && var.instance_count <= 5
    error_message = "instance_count must be between 1 and 5."
  }
}

variable "storage_iops" {
  description = "Optional guaranteed IOPS tier for OCI Optimized Storage. Null uses the service default."
  type        = number
  default     = null
}

# ---------------------------------------------------------------------------
# Credentials — prefer Vault; plaintext exists only for throwaway bursts and
# still ends up in state, which is why the state bucket must stay private.
# ---------------------------------------------------------------------------

variable "password_mode" {
  description = "VAULT_SECRET (recommended) reads the admin password from Vault; PLAIN_TEXT takes db_admin_password directly."
  type        = string
  default     = "VAULT_SECRET"

  validation {
    condition     = contains(["VAULT_SECRET", "PLAIN_TEXT"], var.password_mode)
    error_message = "password_mode must be VAULT_SECRET or PLAIN_TEXT."
  }
}

variable "admin_username" {
  description = "Database administrator username."
  type        = string
  default     = "documindadmin"

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]{3,62}$", var.admin_username))
    error_message = "admin_username: start with a letter, then letters/digits/underscore (4-63 chars)."
  }
}

variable "db_admin_password" {
  description = "Admin password when password_mode = PLAIN_TEXT. Sensitive; stored in Terraform state."
  type        = string
  default     = ""
  sensitive   = true
}

variable "db_password_secret_id" {
  description = "Vault secret OCID holding the admin password when password_mode = VAULT_SECRET."
  type        = string
  default     = ""
}

variable "secret_version" {
  description = "Vault secret version to consume (required by the API in VAULT_SECRET mode). Use the stage name or numeric version per your tenancy conventions."
  type        = string
  default     = "1"
}

variable "enable_daily_backups" {
  description = "Create a daily backup policy (small extra cost). Keep on unless quota-blocked."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Freeform tags."
  type        = map(string)
  default     = {}
}
