# Load Balancer Module — Variables

variable "compartment_id" {
  description = "OCID of the compartment."
  type        = string
}

variable "name_prefix" {
  description = "Prefix for resource names."
  type        = string
}

variable "subnet_lb_id" {
  description = "OCID of the public Load Balancer subnet."
  type        = string
}

variable "nsg_lb_id" {
  description = "OCID of the Load Balancer NSG."
  type        = string
}

variable "lb_shape" {
  description = "Shape of the Load Balancer (flexible or fixed)."
  type        = string
  default     = "flexible"
}

variable "lb_min_bandwidth" {
  description = "Minimum bandwidth in Mbps (flexible shape only)."
  type        = number
  default     = 10
}

variable "lb_max_bandwidth" {
  description = "Maximum bandwidth in Mbps (flexible shape only)."
  type        = number
  default     = 100
}

variable "backend_port" {
  description = "Port on the backend nodes (OKE NodePort)."
  type        = number
  default     = 30080
}

variable "health_check_path" {
  description = "Health check URL path."
  type        = string
  default     = "/health"
}

variable "backend_ips" {
  description = "Map of backend IPs to register. Empty = managed by OKE."
  type        = map(string)
  default     = {}
}

variable "ssl_certificate_id" {
  description = "OCID of an SSL certificate. Empty = no HTTPS listener."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Freeform tags."
  type        = map(string)
  default     = {}
}
