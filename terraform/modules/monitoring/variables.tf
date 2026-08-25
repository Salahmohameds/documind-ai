# Monitoring Module — Variables

variable "compartment_id" {
  description = "OCID of the compartment."
  type        = string
}

variable "name_prefix" {
  description = "Prefix for resource names."
  type        = string
}

variable "alert_emails" {
  description = "List of email addresses for alert notifications."
  type        = list(string)
  default     = []
}

variable "oke_cluster_id" {
  description = "OCID of the OKE cluster."
  type        = string
}

variable "oke_node_pool_id" {
  description = "OCID of the OKE node pool."
  type        = string
}

variable "subnet_oke_id" {
  description = "OCID of the OKE subnet (for VCN flow logs)."
  type        = string
}

variable "enable_lb_monitoring" {
  description = "Whether to enable Load Balancer alarms and access logs."
  type        = bool
  default     = true
}

variable "lb_id" {
  description = "OCID of the Load Balancer. Empty = skip LB monitoring."
  type        = string
  default     = ""
}

variable "cpu_threshold" {
  description = "CPU utilization threshold (%) for alarm."
  type        = number
  default     = 80
}

variable "memory_threshold" {
  description = "Memory utilization threshold (%) for alarm."
  type        = number
  default     = 85
}

variable "lb_error_threshold" {
  description = "5xx error count threshold for LB alarm."
  type        = number
  default     = 10
}

variable "tags" {
  description = "Freeform tags."
  type        = map(string)
  default     = {}
}
