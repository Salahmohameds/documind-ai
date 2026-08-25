# Networking Module — Outputs

# ─── VCN ─────────────────────────────────────────────────────────────────────
output "vcn_id" {
  description = "OCID of the VCN."
  value       = oci_core_vcn.main.id
}

output "vcn_cidr" {
  description = "CIDR block of the VCN."
  value       = oci_core_vcn.main.cidr_blocks[0]
}

# ─── Subnets ─────────────────────────────────────────────────────────────────
output "subnet_public_id" {
  description = "OCID of the public subnet (Load Balancer)."
  value       = oci_core_subnet.public_lb.id
}

output "subnet_oke_workers_id" {
  description = "OCID of the private OKE workers subnet."
  value       = oci_core_subnet.private_oke_workers.id
}

output "subnet_oke_pods_id" {
  description = "OCID of the private OKE pods subnet (VCN-native)."
  value       = oci_core_subnet.private_oke_pods.id
}

output "subnet_data_id" {
  description = "OCID of the private data subnet (DB, Redis)."
  value       = oci_core_subnet.private_data.id
}

# ─── Gateways ────────────────────────────────────────────────────────────────
output "internet_gateway_id" {
  description = "OCID of the Internet Gateway."
  value       = oci_core_internet_gateway.igw.id
}

output "nat_gateway_id" {
  description = "OCID of the NAT Gateway."
  value       = oci_core_nat_gateway.natgw.id
}

output "service_gateway_id" {
  description = "OCID of the Service Gateway."
  value       = oci_core_service_gateway.sgw.id
}

# ─── NSGs ────────────────────────────────────────────────────────────────────
output "nsg_lb_id" {
  description = "OCID of the Load Balancer NSG (dm-nsg-lb)."
  value       = oci_core_network_security_group.lb.id
}

output "nsg_oke_api_id" {
  description = "OCID of the OKE API endpoint NSG (dm-nsg-oke-api)."
  value       = oci_core_network_security_group.oke_api.id
}

output "nsg_workers_id" {
  description = "OCID of the OKE workers NSG (dm-nsg-workers)."
  value       = oci_core_network_security_group.workers.id
}

output "nsg_data_id" {
  description = "OCID of the data tier NSG (dm-nsg-data)."
  value       = oci_core_network_security_group.data.id
}

# ─── Route Tables ────────────────────────────────────────────────────────────
output "route_table_public_id" {
  description = "OCID of the public route table."
  value       = oci_core_route_table.public.id
}

output "route_table_private_id" {
  description = "OCID of the private route table (NAT + SGW)."
  value       = oci_core_route_table.private.id
}

output "route_table_data_id" {
  description = "OCID of the data route table (SGW only, no internet)."
  value       = oci_core_route_table.data.id
}
