output "nodes_dynamic_group_name" {
  description = <<-EOT
    Dynamic group matching worker node instances. Always resolves to the
    expected name (dm-demo-dg-oke-nodes) whether Terraform created the
    group (manage_dynamic_groups=true) or an admin created it out of band
    (manage_dynamic_groups=false, the default here).
  EOT
  value       = local.nodes_group_name
}

output "workloads_dynamic_group_name" {
  description = <<-EOT
    Dynamic group matching OKE workload pods. Always resolves to the
    expected name (dm-demo-dg-workloads) regardless of who owns the
    underlying dynamic-group resource; see nodes_dynamic_group_name.
  EOT
  value       = local.workloads_group_name
}

output "workload_matching_rule" {
  description = "Effective dynamic-group matching rule for workload identity."
  value       = local.workload_rule
}

output "policy_names" {
  description = "Created policy names."
  value       = [for p in oci_identity_policy.this : p.name]
}
