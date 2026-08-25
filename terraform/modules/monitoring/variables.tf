variable "compartment_id" {
  description = "Compartment OCID for topics, subscriptions and alarms."
  type        = string
}

variable "name_prefix" {
  description = "Naming prefix."
  type        = string
}

variable "alert_emails" {
  description = "Email addresses subscribed to the alert topic (confirm opt-in from inbox)."
  type        = set(string)
  default     = []
}

variable "cpu_threshold_percent" {
  description = "Aggregate worker-node CPU threshold (%)."
  type        = number
  default     = 85

  validation {
    condition     = var.cpu_threshold_percent > 0 && var.cpu_threshold_percent <= 100
    error_message = "cpu_threshold_percent must be 1-100."
  }
}

variable "memory_threshold_percent" {
  description = "Aggregate worker-node memory threshold (%)."
  type        = number
  default     = 90

  validation {
    condition     = var.memory_threshold_percent > 0 && var.memory_threshold_percent <= 100
    error_message = "memory_threshold_percent must be 1-100."
  }
}

variable "lb_5xx_threshold" {
  description = "LB 5xx responses per 5 minutes before alarming. Requires lb_ocid."
  type        = number
  default     = 5
}

variable "lb_ocid" {
  description = <<-EOT
    OCID of a Terraform-managed load balancer for LB alarms. Kubernetes-owned
    Service LBs are unknown to Terraform — leave null and add the OCID to
    tfvars after first deploy if you want LB alarms.
  EOT
  type        = string
  default     = null
}

variable "pending_minutes" {
  description = "Minutes a metric must breach before the alarm fires."
  type        = number
  default     = 5

  validation {
    condition     = contains([1, 5, 15], var.pending_minutes)
    error_message = "pending_minutes must be 1, 5 or 15 (PT1M/PT5M/PT15M)."
  }
}

variable "tags" {
  description = "Freeform tags."
  type        = map(string)
  default     = {}
}
