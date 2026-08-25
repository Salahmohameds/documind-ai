output "nodes_dynamic_group_name" {
  description = "Dynamic group matching worker node instances."
  value       = oci_identity_dynamic_group.oke_nodes.name
}

output "workloads_dynamic_group_name" {
  description = "Dynamic group matching OKE workload pods."
  value       = oci_identity_dynamic_group.oke_workloads.name
}

output "workload_matching_rule" {
  description = "Effective dynamic-group matching rule for workload identity."
  value       = local.workload_rule
}

output "policy_names" {
  description = "Created policy names."
  value       = [for p in oci_identity_policy.this : p.name]
}
