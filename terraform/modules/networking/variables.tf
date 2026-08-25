# Networking module inputs. Values come from the environment root;
# this module never hardcodes environment-specific OCIDs or names.

variable "compartment_id" {
  description = "Compartment OCID that owns every network resource."
  type        = string
}

variable "name_prefix" {
  description = "Display-name prefix, usually '<project>-<env>' (e.g. dm-demo)."
  type        = string
}

variable "vcn_cidr" {
  description = "VCN CIDR block."
  type        = string
  default     = "10.20.0.0/16"

  validation {
    condition     = can(cidrnetmask(var.vcn_cidr))
    error_message = "vcn_cidr must be valid IPv4 CIDR notation."
  }

  validation {
    condition     = tonumber(split("/", var.vcn_cidr)[1]) >= 16 && tonumber(split("/", var.vcn_cidr)[1]) <= 30
    error_message = "vcn_cidr prefix must be between /16 and /30."
  }
}

variable "vcn_dns_label" {
  description = "VCN DNS label (letters/digits, starts with a letter, max 15)."
  type        = string
  default     = "dmvcn"

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9]{0,14}$", var.vcn_dns_label))
    error_message = "vcn_dns_label must start with a letter and be 1-15 letters/digits."
  }
}

variable "subnets" {
  description = <<-EOT
    Subnets to create, keyed by stable logical name. Recognized keys get a
    matching security-list profile; unknown keys fall back to the locked-down
    'locked' profile. route: igw | nat | none (none = no default route).
    Required keys: public_lb, oke_api, oke_workers, oke_pods, data.
  EOT
  type = map(object({
    cidr        = string
    dns_label   = string
    private     = bool
    route       = string
    enable_logs = optional(bool, false)
  }))

  validation {
    condition = alltrue([
      contains(keys(var.subnets), "public_lb"),
      contains(keys(var.subnets), "oke_api"),
      contains(keys(var.subnets), "oke_workers"),
      contains(keys(var.subnets), "oke_pods"),
      contains(keys(var.subnets), "data"),
    ])
    error_message = "subnets must define public_lb, oke_api, oke_workers, oke_pods and data."
  }

  validation {
    condition     = alltrue([for s in values(var.subnets) : contains(["igw", "nat", "none"], s.route)])
    error_message = "Each subnet route must be igw, nat, or none."
  }

  validation {
    condition     = alltrue([for s in values(var.subnets) : can(cidrnetmask(s.cidr))])
    error_message = "Every subnet CIDR must be valid IPv4 CIDR notation (containment/overlap enforced at plan time)."
  }
}

variable "admin_cidrs" {
  description = <<-EOT
    CIDRs allowed to reach the Kubernetes API (6443), worker SSH (22) and the
    bastion. NEVER use 0.0.0.0/0 — validation rejects it on purpose.
  EOT
  type        = list(string)

  validation {
    condition     = length(var.admin_cidrs) > 0
    error_message = "Provide at least one admin CIDR (your laptop IP /32)."
  }

  validation {
    condition     = alltrue([for c in var.admin_cidrs : can(cidrnetmask(c))])
    error_message = "admin_cidrs entries must be valid IPv4 CIDR notation."
  }

  validation {
    condition     = !contains(var.admin_cidrs, "0.0.0.0/0")
    error_message = "admin_cidrs must not contain 0.0.0.0/0 (Kubernetes API would be world-open)."
  }
}

variable "enable_service_gateway" {
  description = "Create the Service Gateway and route Oracle Services Network traffic privately."
  type        = bool
  default     = true
}

variable "enable_flow_logs" {
  description = "Enable VCN flow logs on subnets whose enable_logs = true (cost: log ingestion)."
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "Retention (days) for flow logs."
  type        = number
  default     = 30

  validation {
    condition     = var.log_retention_days >= 1 && var.log_retention_days <= 365
    error_message = "log_retention_days must be between 1 and 365."
  }
}

# ---------------------------------------------------------------------------
# Ports used by the generated security rules
# ---------------------------------------------------------------------------

variable "https_port" {
  description = "Public HTTPS port on load balancers."
  type        = number
  default     = 443
}

variable "http_port" {
  description = "Public HTTP port on load balancers (redirect to HTTPS)."
  type        = number
  default     = 80
}

variable "kubernetes_api_port" {
  description = "OKE Kubernetes API TCP port."
  type        = number
  default     = 6443
}

variable "oke_control_port" {
  description = "OKE control-plane/proxy TCP port."
  type        = number
  default     = 12250
}

variable "kubelet_health_port" {
  description = "Kube-proxy health-check TCP port used by load balancer probes."
  type        = number
  default     = 10256
}

variable "node_port_min" {
  description = "NodePort range start for Service load balancer backends."
  type        = number
  default     = 30000
}

variable "node_port_max" {
  description = "NodePort range end for Service load balancer backends."
  type        = number
  default     = 32767

  validation {
    condition     = var.node_port_max >= var.node_port_min && var.node_port_max <= 65535
    error_message = "node_port_max must be >= node_port_min and <= 65535."
  }
}

variable "database_port" {
  description = "PostgreSQL TCP port allowed into the data subnet."
  type        = number
  default     = 5432
}

variable "tags" {
  description = "Freeform tags applied to every resource."
  type        = map(string)
  default     = {}
}
