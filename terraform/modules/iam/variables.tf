# IAM Module — Variables

variable "tenancy_id" {
  description = "OCID of the tenancy (dynamic groups must be at tenancy level)."
  type        = string
}

variable "compartment_id" {
  description = "OCID of the compartment for policies."
  type        = string
}

variable "name_prefix" {
  description = "Prefix for all resource names."
  type        = string
}

variable "documents_bucket_name" {
  description = "Name of the documents Object Storage bucket."
  type        = string
}

variable "processed_bucket_name" {
  description = "Name of the processed data Object Storage bucket."
  type        = string
}

variable "tags" {
  description = "Freeform tags."
  type        = map(string)
  default     = {}
}
