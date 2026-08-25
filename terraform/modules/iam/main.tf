# DocuMind AI — IAM Module
# Dynamic Groups + Least-Privilege Policies


# ---------- Dynamic Groups ----------

# OKE Worker Nodes — all instances in the OKE node pool
resource "oci_identity_dynamic_group" "oke_workers" {
  compartment_id = var.tenancy_id
  name           = "${var.name_prefix}-dg-oke-workers"
  description    = "Dynamic group for DocuMind OKE worker nodes"
  matching_rule  = "ALL {instance.compartment.id = '${var.compartment_id}'}"

  freeform_tags = var.tags
}

# Document Service workload — pods that access Object Storage
resource "oci_identity_dynamic_group" "document_service" {
  compartment_id = var.tenancy_id
  name           = "${var.name_prefix}-dg-document-svc"
  description    = "Dynamic group for DocuMind document service workloads"
  matching_rule  = "ALL {resource.type = 'cluster', resource.compartment.id = '${var.compartment_id}'}"

  freeform_tags = var.tags
}

# AI Service workload — pods that access OCI Generative AI
resource "oci_identity_dynamic_group" "ai_service" {
  compartment_id = var.tenancy_id
  name           = "${var.name_prefix}-dg-ai-svc"
  description    = "Dynamic group for DocuMind AI service workloads"
  matching_rule  = "ALL {resource.type = 'cluster', resource.compartment.id = '${var.compartment_id}'}"

  freeform_tags = var.tags
}

# ---------- IAM Policies ----------

# OKE worker node policy — pull images from OCIR, access networking
resource "oci_identity_policy" "oke_workers" {
  compartment_id = var.compartment_id
  name           = "${var.name_prefix}-pol-oke-workers"
  description    = "Policy for OKE worker nodes to operate"

  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.oke_workers.name} to use instances in compartment id ${var.compartment_id}",
    "Allow dynamic-group ${oci_identity_dynamic_group.oke_workers.name} to use subnets in compartment id ${var.compartment_id}",
    "Allow dynamic-group ${oci_identity_dynamic_group.oke_workers.name} to use vnics in compartment id ${var.compartment_id}",
    "Allow dynamic-group ${oci_identity_dynamic_group.oke_workers.name} to use network-security-groups in compartment id ${var.compartment_id}",
  ]

  freeform_tags = var.tags
}

# Object Storage policy — document service can manage document buckets
resource "oci_identity_policy" "object_storage" {
  compartment_id = var.compartment_id
  name           = "${var.name_prefix}-pol-object-storage"
  description    = "Policy for document/processing services to access Object Storage"

  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.document_service.name} to manage objects in compartment id ${var.compartment_id} where target.bucket.name = '${var.documents_bucket_name}'",
    "Allow dynamic-group ${oci_identity_dynamic_group.document_service.name} to manage objects in compartment id ${var.compartment_id} where target.bucket.name = '${var.processed_bucket_name}'",
    "Allow dynamic-group ${oci_identity_dynamic_group.document_service.name} to read buckets in compartment id ${var.compartment_id}",
  ]

  freeform_tags = var.tags
}

# OCI Generative AI policy — AI service can invoke models
resource "oci_identity_policy" "generative_ai" {
  compartment_id = var.compartment_id
  name           = "${var.name_prefix}-pol-generative-ai"
  description    = "Policy for AI service to use OCI Generative AI"

  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.ai_service.name} to manage generative-ai-family in compartment id ${var.compartment_id}",
  ]

  freeform_tags = var.tags
}

# Vault policy — all services can read secrets
resource "oci_identity_policy" "vault_secrets" {
  compartment_id = var.compartment_id
  name           = "${var.name_prefix}-pol-vault-secrets"
  description    = "Policy for workloads to read secrets from OCI Vault"

  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.oke_workers.name} to read secret-family in compartment id ${var.compartment_id}",
    "Allow dynamic-group ${oci_identity_dynamic_group.oke_workers.name} to use keys in compartment id ${var.compartment_id}",
  ]

  freeform_tags = var.tags
}

# OCIR pull policy — worker nodes can pull container images
resource "oci_identity_policy" "ocir_pull" {
  compartment_id = var.compartment_id
  name           = "${var.name_prefix}-pol-ocir-pull"
  description    = "Policy for OKE workers to pull images from OCIR"

  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.oke_workers.name} to read repos in compartment id ${var.compartment_id}",
    "Allow dynamic-group ${oci_identity_dynamic_group.oke_workers.name} to read compartments in compartment id ${var.compartment_id}",
  ]

  freeform_tags = var.tags
}
