output "bucket_names" {
  description = "Map of logical bucket key => name."
  value       = { for k, b in oci_objectstorage_bucket.this : k => b.name }
}

output "documents_bucket_name" {
  description = "Raw uploaded documents bucket."
  value       = oci_objectstorage_bucket.this["documents"].name
}

output "processed_bucket_name" {
  description = "Processed artifacts bucket."
  value       = oci_objectstorage_bucket.this["processed"].name
}
