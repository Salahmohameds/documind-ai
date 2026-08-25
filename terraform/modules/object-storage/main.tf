# DocuMind AI — Object Storage Module
# Buckets for documents and processed data

resource "oci_objectstorage_bucket" "documents" {
  compartment_id = var.compartment_id
  namespace      = var.object_storage_namespace
  name           = "${var.name_prefix}-documents"
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
  versioning     = "Enabled"

  freeform_tags = var.tags
}

resource "oci_objectstorage_bucket" "processed" {
  compartment_id = var.compartment_id
  namespace      = var.object_storage_namespace
  name           = "${var.name_prefix}-processed"
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
  versioning     = "Disabled"

  freeform_tags = var.tags
}

# Lifecycle rule — auto-delete incomplete multipart uploads after 7 days
resource "oci_objectstorage_object_lifecycle_policy" "documents_lifecycle" {
  namespace = var.object_storage_namespace
  bucket    = oci_objectstorage_bucket.documents.name

  rules {
    name        = "abort-incomplete-multipart"
    action      = "ABORT"
    time_amount = 7
    time_unit   = "DAYS"
    is_enabled  = true

    target = "multipart-uploads"
  }
}

# Optional: Terraform state bucket (if managing state in same project)
resource "oci_objectstorage_bucket" "terraform_state" {
  count = var.create_state_bucket ? 1 : 0

  compartment_id = var.compartment_id
  namespace      = var.object_storage_namespace
  name           = "${var.name_prefix}-terraform-state"
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
  versioning     = "Enabled"

  freeform_tags = var.tags
}
