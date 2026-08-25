output "cluster_id" {
  description = "OKE cluster OCID."
  value       = oci_containerengine_cluster.this.id
}

output "cluster_name" {
  description = "OKE cluster display name."
  value       = oci_containerengine_cluster.this.name
}

output "kubernetes_version" {
  description = "Effective Kubernetes version."
  value       = oci_containerengine_cluster.this.kubernetes_version
}

output "endpoints" {
  description = "Kubernetes API endpoints (private always, public when enabled)."
  value       = oci_containerengine_cluster.this.endpoints
}

output "node_pool_ids" {
  description = "Map of pool key => OCID."
  value       = { for k, p in oci_containerengine_node_pool.this : k => p.id }
}

output "node_image_ids" {
  description = "Resolved node image OCIDs per pool."
  value       = local.pool_image_ids
}

output "is_enhanced" {
  description = "True when the cluster supports OKE Workload Identity (ENHANCED_CLUSTER)."
  value       = var.cluster_type == "ENHANCED_CLUSTER"
}
