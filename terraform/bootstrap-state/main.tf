# DocuMind AI — Terraform remote-state bootstrap
#
# Creates the ONE Object Storage bucket that holds all Terraform remote state.
# Downstacks (environments/demo) use the NATIVE `oci` backend (Terraform >= 1.12)
# pointed at this bucket — no S3-compatible endpoint, no customer secret keys,
# and state locking comes for free (lock object via If-None-Match).
#
# This stack intentionally keeps LOCAL state: the bucket cannot hold its own
# state before it exists. It is a tiny, rarely-changed stack (one bucket).

data "oci_objectstorage_namespace" "this" {
  compartment_id = var.compartment_ocid
}

resource "oci_objectstorage_bucket" "state" {
  compartment_id = var.compartment_ocid
  namespace      = data.oci_objectstorage_namespace.this.namespace
  name           = var.state_bucket_name
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
  versioning     = "Enabled" # required safety net for state recovery

  freeform_tags = merge(var.tags, { Component = "terraform-state" })

  lifecycle {
    precondition {
      condition     = !strcontains(var.state_bucket_name, " ")
      error_message = "state_bucket_name must not contain spaces."
    }
  }
}
