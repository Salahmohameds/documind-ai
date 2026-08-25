# DocuMind AI — OCIR Module
# Container repositories for each microservice

resource "oci_artifacts_container_repository" "services" {
  for_each = toset(var.service_names)

  compartment_id = var.compartment_id
  display_name   = "${var.repository_prefix}/${each.value}"
  is_public      = var.is_public
  is_immutable   = var.is_immutable

  dynamic "readme" {
    for_each = []
    content {
      content = ""
      format  = "TEXT_PLAIN"
    }
  }
}
