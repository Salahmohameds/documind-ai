# One OCIR repository per microservice. Tagging strategy lives in CI:
#   <service>:<git-sha>   deployable artifact
#   <service>:vX.Y.Z      release alias pushed once (immutability enforced)
# Never rely on :latest for deploys.

data "oci_objectstorage_namespace" "this" {
  compartment_id = var.compartment_id
}

resource "oci_artifacts_container_repository" "services" {
  for_each = var.service_names

  compartment_id = var.compartment_id
  display_name   = "${var.repository_prefix}/${each.value}"
  is_public      = var.is_public
  is_immutable   = var.is_immutable

  lifecycle {
    precondition {
      condition     = length("${var.repository_prefix}/${each.value}") <= 256
      error_message = "Full repository path exceeds the 256-character limit."
    }
  }
}
