# OCIR Module — Outputs

output "repository_ids" {
  description = "Map of service name to repository OCID."
  value       = { for k, v in oci_artifacts_container_repository.services : k => v.id }
}

output "repository_paths" {
  description = "Map of service name to full repository path."
  value       = { for k, v in oci_artifacts_container_repository.services : k => v.display_name }
}
