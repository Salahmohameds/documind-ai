# Object Storage Module — Outputs

output "documents_bucket_name" {
  description = "Name of the documents bucket."
  value       = oci_objectstorage_bucket.documents.name
}

output "documents_bucket_id" {
  description = "OCID of the documents bucket (namespace/bucket)."
  value       = oci_objectstorage_bucket.documents.bucket_id
}

output "processed_bucket_name" {
  description = "Name of the processed data bucket."
  value       = oci_objectstorage_bucket.processed.name
}

output "processed_bucket_id" {
  description = "OCID of the processed data bucket."
  value       = oci_objectstorage_bucket.processed.bucket_id
}

output "state_bucket_name" {
  description = "Name of the Terraform state bucket (if created)."
  value       = var.create_state_bucket ? oci_objectstorage_bucket.terraform_state[0].name : ""
}
