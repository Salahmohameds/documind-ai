# Load Balancer Module — Outputs

output "lb_id" {
  description = "OCID of the Load Balancer."
  value       = oci_load_balancer_load_balancer.main.id
}

output "lb_ip" {
  description = "Public IP address of the Load Balancer."
  value       = oci_load_balancer_load_balancer.main.ip_address_details[0].ip_address
}

output "lb_shape" {
  description = "Shape of the Load Balancer."
  value       = oci_load_balancer_load_balancer.main.shape
}

output "backend_set_name" {
  description = "Name of the API backend set."
  value       = oci_load_balancer_backend_set.api.name
}
