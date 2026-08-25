output "namespace" {
  description = "Object Storage namespace — required by every environment's backend.hcl."
  value       = data.oci_objectstorage_namespace.this.namespace
}

output "bucket_name" {
  description = "Remote-state bucket name."
  value       = oci_objectstorage_bucket.state.name
}

output "bucket_ocid" {
  description = "OCID of the state bucket."
  value       = oci_objectstorage_bucket.state.id
}
