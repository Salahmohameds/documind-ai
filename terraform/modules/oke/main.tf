# OKE cluster + node pools. VCN-native pod networking, private workers,
# dedicated API-endpoint subnet, per-role NSGs. Node pools are a map driven
# by for_each — add/remove pools without touching resource addresses.

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_id
}

data "oci_containerengine_cluster_option" "all" {
  cluster_option_id = "all"
}

# May return empty on restricted compartments; pin node_image_id in tfvars then.
data "oci_containerengine_node_pool_option" "all" {
  node_pool_option_id = "all"
  compartment_id      = var.compartment_id
}

resource "oci_containerengine_cluster" "this" {
  compartment_id     = var.compartment_id
  kubernetes_version = local.version_effective
  name               = "${var.name_prefix}-oke"
  vcn_id             = var.vcn_id
  type               = var.cluster_type
  freeform_tags      = var.tags

  cluster_pod_network_options {
    cni_type = var.cni_type
  }

  endpoint_config {
    is_public_ip_enabled = var.endpoint_public
    subnet_id            = var.endpoint_subnet_id
    nsg_ids              = [var.nsg_api_id]
  }

  options {
    service_lb_subnet_ids = [var.lb_subnet_id]

    # Lets Service load balancers reach backends when rule management is
    # set to NSG mode via service annotations.
    service_lb_config {
      backend_nsg_ids = distinct(compact([var.nsg_workers_id, var.nsg_pods_id]))
    }

    add_ons {
      is_kubernetes_dashboard_enabled = var.dashboard_enabled
      is_tiller_enabled               = false
    }

    kubernetes_network_config {
      services_cidr = var.services_cidr
      pods_cidr     = local.is_native ? null : var.pods_cidr
    }
  }

  lifecycle {
    precondition {
      condition     = local.version_effective != ""
      error_message = "kubernetes_version is empty and the region catalog returned no versions; pin it explicitly."
    }

    precondition {
      condition     = !local.is_native || length(var.pod_subnet_ids) > 0
      error_message = "OCI_VCN_IP_NATIVE requires at least one pod subnet."
    }
  }
}

resource "oci_containerengine_node_pool" "this" {
  for_each = var.node_pools

  cluster_id         = oci_containerengine_cluster.this.id
  compartment_id     = var.compartment_id
  kubernetes_version = local.version_effective
  name               = "${var.name_prefix}-np-${each.key}"
  node_shape         = each.value.shape
  ssh_public_key     = var.ssh_public_key != "" ? var.ssh_public_key : null
  freeform_tags      = var.tags

  dynamic "node_shape_config" {
    for_each = strcontains(upper(each.value.shape), "FLEX") ? [1] : []
    content {
      ocpus         = each.value.ocpus
      memory_in_gbs = each.value.memory_in_gbs
    }
  }

  node_config_details {
    size                                = each.value.size
    nsg_ids                             = [var.nsg_workers_id]
    is_pv_encryption_in_transit_enabled = true

    placement_configs {
      availability_domain = local.availability_domain
      subnet_id           = var.worker_subnet_id
    }

    node_pool_pod_network_option_details {
      cni_type          = var.cni_type
      max_pods_per_node = local.is_native ? var.max_pods_per_node : null
      pod_subnet_ids    = local.is_native ? var.pod_subnet_ids : null
      pod_nsg_ids       = local.pod_nsg_ids
    }
  }

  dynamic "initial_node_labels" {
    for_each = local.pool_labels[each.key]
    content {
      key   = initial_node_labels.key
      value = initial_node_labels.value
    }
  }

  node_source_details {
    image_id                = local.pool_image_ids[each.key]
    source_type             = "IMAGE"
    boot_volume_size_in_gbs = each.value.boot_volume_gb
  }

  lifecycle {
    precondition {
      condition     = local.pool_image_ids[each.key] != ""
      error_message = "No OKE node image resolved for pool '${each.key}'. Pin node_image_id or check node_pool_option availability."
    }

    precondition {
      condition     = length(var.worker_subnet_id) > 0
      error_message = "worker_subnet_id is required."
    }
  }
}
