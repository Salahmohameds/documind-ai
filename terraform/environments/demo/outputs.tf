output "vcn_id" {
  description = "Demo VCN OCID."
  value       = module.networking.vcn_id
}

output "subnet_ids" {
  description = "Subnet OCIDs by logical key."
  value       = module.networking.subnet_ids
}

output "nsg_ids" {
  description = "Workload NSG OCIDs by key."
  value       = module.networking.nsg_ids
}

output "service_gateway_id" {
  description = "Service Gateway OCID when enabled."
  value       = module.networking.service_gateway_id
}

output "oke_cluster_id" {
  description = "OKE cluster OCID (null while enable_oke is false)."
  value       = try(module.oke[0].cluster_id, null)
}

output "oke_endpoints" {
  description = "Kubernetes API endpoints."
  value       = try(module.oke[0].endpoints, null)
}

output "oke_kubernetes_version" {
  description = "Effective Kubernetes version."
  value       = try(module.oke[0].kubernetes_version, null)
}

output "node_pool_ids" {
  description = "Node pool OCIDs by key."
  value       = try(module.oke[0].node_pool_ids, null)
}

output "workload_identity" {
  description = "Dynamic-group names backing OKE workload identity."
  value = {
    nodes     = module.iam.nodes_dynamic_group_name
    workloads = module.iam.workloads_dynamic_group_name
    rule      = module.iam.workload_matching_rule
  }
}

output "bucket_names" {
  description = "Application bucket names."
  value       = module.object_storage.bucket_names
}

output "container_repositories" {
  description = "Fully qualified OCIR image paths per service."
  value       = module.ocir.repositories
}

output "database" {
  description = "PostgreSQL system summary (null while disabled)."
  value = var.enable_database ? {
    id       = module.database[0].db_system_id
    username = module.database[0].admin_username
    state    = module.database[0].state
  } : null
}

output "bastion_id" {
  description = "OCI Bastion OCID when enabled."
  value       = try(module.bastion[0].bastion_id, null)
}

output "alert_topic_id" {
  description = "ONS alert topic OCID when monitoring enabled."
  value       = try(module.monitoring[0].topic_id, null)
}

output "kubeconfig_hint" {
  description = "Command to write kubeconfig once the cluster is ACTIVE."
  value = try(format(
    "oci ce cluster create-kubeconfig --cluster-id %s --file $HOME/.kube/config --region %s --token-version 2.0.0 --kube-endpoint %s",
    module.oke[0].cluster_id,
    var.region,
    var.oke_endpoint_public ? "PUBLIC_ENDPOINT" : "PRIVATE_ENDPOINT",
  ), null)
}
