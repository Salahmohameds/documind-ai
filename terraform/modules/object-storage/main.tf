# Application buckets. The Terraform state bucket is NOT here — it is created
# once by ../bootstrap-state so state never manages the bucket holding it.

locals {
  buckets = {
    documents = { versioning = var.enable_versioning }
    processed = { versioning = var.enable_versioning }
  }
}

resource "oci_objectstorage_bucket" "this" {
  for_each = local.buckets

  compartment_id = var.compartment_id
  namespace      = var.namespace
  name           = "${var.name_prefix}-${each.key}"
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
  versioning     = each.value.versioning ? "Enabled" : "Disabled"

  freeform_tags = merge(var.tags, { Component = each.key })
}

resource "oci_objectstorage_object_lifecycle_policy" "abort_multipart" {
  for_each = local.buckets

  namespace = var.namespace
  bucket    = oci_objectstorage_bucket.this[each.key].name

  rules {
    name        = "abort-incomplete-multipart"
    action      = "ABORT"
    time_amount = var.multipart_abort_days
    time_unit   = "DAYS"
    is_enabled  = true
    target      = "multipart-uploads"
  }
}
