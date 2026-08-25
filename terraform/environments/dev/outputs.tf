# DocuMind AI — Dev Environment — Outputs

# ─── Networking ──────────────────────────────────────────────────────────────
output "vcn_id" {
  description = "OCID of the VCN."
  value       = module.networking.vcn_id
}

output "subnet_public_id" {
  description = "OCID of the public subnet."
  value       = module.networking.subnet_public_id
}

output "subnet_oke_workers_id" {
  description = "OCID of the OKE workers subnet."
  value       = module.networking.subnet_oke_workers_id
}

output "subnet_oke_pods_id" {
  description = "OCID of the OKE pods subnet (VCN-native)."
  value       = module.networking.subnet_oke_pods_id
}

output "subnet_data_id" {
  description = "OCID of the data subnet."
  value       = module.networking.subnet_data_id
}

# ─── OKE ─────────────────────────────────────────────────────────────────────
output "oke_cluster_id" {
  description = "OCID of the OKE cluster."
  value       = module.oke.cluster_id
}

output "oke_cluster_name" {
  description = "Name of the OKE cluster."
  value       = module.oke.cluster_name
}

output "oke_cluster_endpoints" {
  description = "OKE cluster API endpoints."
  value       = module.oke.cluster_endpoints
}

output "oke_node_pool_id" {
  description = "OCID of the OKE node pool."
  value       = module.oke.node_pool_id
}

# ─── Object Storage ─────────────────────────────────────────────────────────
output "documents_bucket" {
  description = "Name of the documents bucket."
  value       = module.object_storage.documents_bucket_name
}

output "processed_bucket" {
  description = "Name of the processed data bucket."
  value       = module.object_storage.processed_bucket_name
}

# ─── Database ────────────────────────────────────────────────────────────────
output "db_endpoint" {
  description = "PostgreSQL database private endpoint."
  value       = module.database.db_system_fqdn
}

# ─── Load Balancer ───────────────────────────────────────────────────────────
output "lb_public_ip" {
  description = "Public IP of the Load Balancer."
  value       = module.load_balancer.lb_ip
}

# ─── OCIR ────────────────────────────────────────────────────────────────────
output "ocir_repositories" {
  description = "Map of OCIR repository paths."
  value       = module.ocir.repository_paths
}

# ─── Monitoring ──────────────────────────────────────────────────────────────
output "notification_topic_id" {
  description = "OCID of the alerts notification topic."
  value       = module.monitoring.notification_topic_id
}

# ─── Summary ─────────────────────────────────────────────────────────────────
output "deployment_summary" {
  description = "Quick-reference summary of deployed resources."
  value = {
    environment = var.environment
    region      = var.region
    vcn_id      = module.networking.vcn_id
    oke_cluster = module.oke.cluster_name
    lb_ip       = module.load_balancer.lb_ip
    db_endpoint = module.database.db_system_fqdn
    doc_bucket  = module.object_storage.documents_bucket_name
  }
}
