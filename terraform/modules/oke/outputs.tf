# OKE Module — Outputs

output "cluster_id" {
  description = "OCID of the OKE cluster."
  value       = oci_containerengine_cluster.main.id
}

output "cluster_name" {
  description = "Display name of the OKE cluster."
  value       = oci_containerengine_cluster.main.name
}

output "cluster_kubernetes_version" {
  description = "Kubernetes version running on the cluster."
  value       = oci_containerengine_cluster.main.kubernetes_version
}

output "cluster_endpoints" {
  description = "Cluster API endpoints."
  value       = oci_containerengine_cluster.main.endpoints
}

output "node_pool_id" {
  description = "OCID of the node pool."
  value       = oci_containerengine_node_pool.workers.id
}

output "node_pool_size" {
  description = "Number of nodes in the pool."
  value       = var.node_pool_size
}
