# Database Module — Variables

variable "compartment_id" {
  description = "OCID of the compartment."
  type        = string
}

variable "name_prefix" {
  description = "Prefix for resource names."
  type        = string
}

variable "subnet_db_id" {
  description = "OCID of the private database subnet."
  type        = string
}

variable "nsg_ids" {
  description = "List of NSG OCIDs to attach to the database."
  type        = list(string)
  default     = []
}

variable "availability_domain" {
  description = "Availability domain for the database."
  type        = string
}

variable "db_version" {
  description = "PostgreSQL version."
  type        = string
  default     = "14"
}

variable "db_shape" {
  description = "Shape for the PostgreSQL DB System."
  type        = string
  default     = "PostgreSQL.VM.Standard.E4.Flex.2.32GB"
}

variable "db_admin_username" {
  description = "Admin username for the database."
  type        = string
  default     = "documind_admin"
}

variable "db_admin_password" {
  description = "Admin password for the database. Should come from OCI Vault in production."
  type        = string
  sensitive   = true
}

variable "instance_count" {
  description = "Number of database instances."
  type        = number
  default     = 1
}

variable "instance_memory_gbs" {
  description = "Memory in GBs per instance."
  type        = number
  default     = 32
}

variable "instance_ocpus" {
  description = "OCPUs per instance."
  type        = number
  default     = 2
}

variable "tags" {
  description = "Freeform tags."
  type        = map(string)
  default     = {}
}
