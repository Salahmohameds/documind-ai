output "registry" {
  description = "Registry host for docker login/push."
  value       = "${var.region}.ocir.io"
}

output "namespace" {
  description = "Object Storage / OCIR namespace."
  value       = data.oci_objectstorage_namespace.this.namespace
}

output "repositories" {
  description = "Map of service name => fully qualified image path."
  value       = { for k, r in oci_artifacts_container_repository.services : k => "${var.region}.ocir.io/${var.repository_prefix}/${k}" }
}
