output "vcn_id" {
  description = "OCID of the VCN."
  value       = oci_core_vcn.this.id
}

output "subnet_ids" {
  description = "Map of logical subnet key => OCID (public_lb, oke_api, oke_workers, oke_pods, data, [bastion])."
  value       = { for k, s in oci_core_subnet.this : k => s.id }
}

output "subnet_cidrs" {
  description = "Map of logical subnet key => CIDR."
  value       = { for k, s in var.subnets : k => s.cidr }
}

output "nsg_ids" {
  description = "Map of NSG key => OCID (lb, oke_api, workers, pods, data)."
  value       = { for k, g in oci_core_network_security_group.this : k => g.id }
}

output "internet_gateway_id" {
  description = "Internet Gateway OCID."
  value       = oci_core_internet_gateway.this.id
}

output "nat_gateway_id" {
  description = "NAT Gateway OCID."
  value       = oci_core_nat_gateway.this.id
}

output "service_gateway_id" {
  description = "Service Gateway OCID (null when disabled)."
  value       = try(oci_core_service_gateway.this[0].id, null)
}

output "osn_cidr" {
  description = "Region-wide Oracle Services Network service CIDR."
  value       = local.osn
}

output "log_group_id" {
  description = "Flow-log group OCID (null when flow logs are off)."
  value       = try(oci_logging_log_group.flow[0].id, null)
}
