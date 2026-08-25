locals {
  is_native         = var.cni_type == "OCI_VCN_IP_NATIVE"
  k8s_numeric       = replace(local.version_effective, "v", "")
  version_effective = var.kubernetes_version != "" ? var.kubernetes_version : try(reverse(sort(data.oci_containerengine_cluster_option.all.kubernetes_versions))[0], "")

  # OKE images filtered by Kubernetes version, split by CPU architecture so
  # each pool resolves an image matching its own shape.
  images_for_version = {
    for s in try(data.oci_containerengine_node_pool_option.all.sources, []) : s.source_name => s.image_id
    if length(regexall("OKE", s.source_name)) > 0 &&
    (local.k8s_numeric == "" || length(regexall(replace(local.k8s_numeric, ".", "\\."), s.source_name)) > 0)
  }
  arm_images = [for name, id in local.images_for_version : id if length(regexall("aarch64", name)) > 0]
  x86_images = [for name, id in local.images_for_version : id if length(regexall("aarch64", name)) == 0]

  # Per-pool resolved image: explicit override wins, else newest matching arch.
  pool_image_ids = {
    for key, pool in var.node_pools : key =>
    var.node_image_id != "" ? var.node_image_id : (
      strcontains(upper(pool.shape), "A1") ? try(local.arm_images[0], "") : try(local.x86_images[0], "")
    )
  }

  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[
    min(var.availability_domain_index, length(data.oci_identity_availability_domains.ads.availability_domains) - 1)
  ].name

  pool_labels = {
    for key, pool in var.node_pools : key => merge(
      { "app" = "documind", "environment" = var.environment, "pool" = key },
      pool.labels,
    )
  }

  pod_nsg_ids = local.is_native ? [var.nsg_pods_id] : null
}
