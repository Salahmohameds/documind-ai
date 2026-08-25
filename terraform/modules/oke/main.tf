# DocuMind AI — OKE Module
# Creates OKE Cluster + Node Pool
#   - VCN-native pod networking (OCI_VCN_IP_NATIVE)
#   - Private workers (no public IPs)
#   - Pods get IPs from dedicated pods subnet
#   - Cluster name: dm-oke

# ---------- Data Sources ----------
data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_id
}

# ---------- OKE Cluster ----------
resource "oci_containerengine_cluster" "main" {
  compartment_id     = var.compartment_id
  kubernetes_version = var.kubernetes_version
  name               = "${var.name_prefix}-oke"
  vcn_id             = var.vcn_id
  type               = "BASIC_CLUSTER"

  # VCN-native pod networking
  cluster_pod_network_options {
    cni_type = "OCI_VCN_IP_NATIVE"
  }

  endpoint_config {
    is_public_ip_enabled = var.cluster_endpoint_public
    subnet_id            = var.subnet_oke_workers_id
    nsg_ids              = [var.nsg_oke_api_id]
  }

  options {
    service_lb_subnet_ids = [var.subnet_lb_id]

    add_ons {
      is_kubernetes_dashboard_enabled = false
      is_tiller_enabled               = false
    }

    kubernetes_network_config {
      services_cidr = var.services_cidr
    }
  }

  freeform_tags = var.tags
}

# ---------- Node Pool ----------
resource "oci_containerengine_node_pool" "workers" {
  compartment_id     = var.compartment_id
  cluster_id         = oci_containerengine_cluster.main.id
  kubernetes_version = var.kubernetes_version
  name               = "${var.name_prefix}-node-pool"

  node_shape = var.node_shape

  dynamic "node_shape_config" {
    for_each = var.node_shape_config != null ? [var.node_shape_config] : []
    content {
      ocpus         = node_shape_config.value.ocpus
      memory_in_gbs = node_shape_config.value.memory_in_gbs
    }
  }

  node_config_details {
    size = var.node_pool_size

    placement_configs {
      availability_domain = var.availability_domain != "" ? var.availability_domain : data.oci_identity_availability_domains.ads.availability_domains[0].name
      subnet_id           = var.subnet_oke_workers_id
    }

    nsg_ids                             = [var.nsg_workers_id]
    is_pv_encryption_in_transit_enabled = false

    # VCN-native pod networking configuration
    node_pool_pod_network_option_details {
      cni_type          = "OCI_VCN_IP_NATIVE"
      pod_subnet_ids    = [var.subnet_oke_pods_id]
      max_pods_per_node = var.max_pods_per_node
      pod_nsg_ids       = [var.nsg_workers_id]
    }
  }

  node_source_details {
    source_type = "IMAGE"
    image_id    = var.node_image_id
  }

  initial_node_labels {
    key   = "app"
    value = "documind"
  }

  initial_node_labels {
    key   = "env"
    value = var.environment
  }

  ssh_public_key = var.ssh_public_key != "" ? var.ssh_public_key : null

  freeform_tags = var.tags
}
