# Dynamic groups + least-privilege policies for OKE workload identity.
#
# Node principals (kubelet pulls) and pod principals (application calls) are
# deliberately separate identities with separate grants. The pod matching
# rule follows the documented OKE Workload Identity claim shape:
#   ALL {resource.type = 'pod', resource.compartment.id = '<ocid>',
#        resource.cluster.id = '<ocid>'}
# It can be overridden via workload_matching_rule if Oracle updates syntax.

locals {
  workload_rule = var.workload_matching_rule != "" ? var.workload_matching_rule : (
    var.cluster_id != "" ?
    "ALL {resource.type = 'pod', resource.compartment.id = '${var.compartment_id}', resource.cluster.id = '${var.cluster_id}'}" :
    "ALL {resource.type = 'pod', resource.compartment.id = '${var.compartment_id}'}"
  )

  nodes_group_name     = "${var.name_prefix}-dg-oke-nodes"
  workloads_group_name = "${var.name_prefix}-dg-workloads"

  # statement => {name, description, statements}
  policies = {
    "nodes-ocir-pull" = {
      description = "Node principals may pull images from OCIR in this compartment."
      statements = [
        "Allow dynamic-group ${local.nodes_group_name} to read repos in compartment id ${var.compartment_id}",
        "Allow dynamic-group ${local.nodes_group_name} to read buckets in compartment id ${var.compartment_id} where target.bucket.name = '${var.processed_bucket_name}'",
      ]
    }
    "workloads-documents" = {
      description = "Document service pods: read/write only the documents and processed buckets."
      statements = [
        "Allow dynamic-group ${local.workloads_group_name} to manage objects in compartment id ${var.compartment_id} where target.bucket.name = '${var.documents_bucket_name}'",
        "Allow dynamic-group ${local.workloads_group_name} to manage objects in compartment id ${var.compartment_id} where target.bucket.name = '${var.processed_bucket_name}'",
        "Allow dynamic-group ${local.workloads_group_name} to read buckets in compartment id ${var.compartment_id} where target.bucket.name = '${var.documents_bucket_name}'",
      ]
    }
    "workloads-generative-ai" = {
      description = "AI service pods may invoke (not administer) Generative AI models."
      statements = [
        "Allow dynamic-group ${local.workloads_group_name} to use generative-ai-family in compartment id ${var.compartment_id}",
      ]
    }
    "workloads-vault" = {
      description = "Workload pods may read secrets only."
      statements = [
        "Allow dynamic-group ${local.workloads_group_name} to read secret-family in compartment id ${var.compartment_id}",
      ]
    }
  }
}

# ------------------------------------------------------- dynamic groups ----
# OWNERSHIP: dynamic groups are tenancy-scoped IAM resources. On this
# project the tenancy administrator (not the deployment user) creates and
# owns dm-demo-dg-oke-nodes / dm-demo-dg-workloads by hand, using the exact
# names/rules generated below. Terraform only creates these resources when
# var.manage_dynamic_groups = true (default false for this project) so
# `terraform apply` never attempts to create, and never conflicts with,
# admin-managed groups. The policies further down reference the groups by
# name only, so they work identically whether Terraform or the admin owns
# the underlying dynamic-group resource.
resource "oci_identity_dynamic_group" "oke_nodes" {
  count = var.manage_dynamic_groups ? 1 : 0

  compartment_id = var.tenancy_id
  name           = local.nodes_group_name
  description    = "OKE worker node instances in ${var.compartment_id}"
  matching_rule  = "ALL {instance.compartment.id = '${var.compartment_id}'}"
  freeform_tags  = var.tags
}

resource "oci_identity_dynamic_group" "oke_workloads" {
  count = var.manage_dynamic_groups ? 1 : 0

  compartment_id = var.tenancy_id
  name           = local.workloads_group_name
  description    = "DocuMind pods running under OKE Workload Identity"
  matching_rule  = local.workload_rule
  freeform_tags  = var.tags

  lifecycle {
    precondition {
      condition     = length(var.name_prefix) <= 60 && can(regex("^[a-zA-Z][a-zA-Z0-9._-]*$", var.name_prefix))
      error_message = "Dynamic group names must be ASCII letters/digits/./_/- starting with a letter."
    }
  }
}

# ------------------------------------------------------------ policies ----
resource "oci_identity_policy" "this" {
  for_each = local.policies

  compartment_id = var.compartment_id
  name           = "${var.name_prefix}-pol-${each.key}"
  description    = each.value.description
  statements     = each.value.statements
  freeform_tags  = var.tags
}
