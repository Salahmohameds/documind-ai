# Derived naming, security-list profiles and the flattened NSG rule map.
# Every rule carries a description â€” OCI console readability is a requirement.

locals {
  osn = try(data.oci_core_services.all_osn.services[0].cidr_block, null)

  # Numeric CIDR ranges (no cidrcontains before Terraform 1.16): first and
  # last address of every subnet as integers, via explicit octet math.
  ip_int = { for k, s in var.subnets : k => [
    tonumber(element(split(".", cidrhost(s.cidr, 0)), 0)) * 16777216 + tonumber(element(split(".", cidrhost(s.cidr, 0)), 1)) * 65536 + tonumber(element(split(".", cidrhost(s.cidr, 0)), 2)) * 256 + tonumber(element(split(".", cidrhost(s.cidr, 0)), 3)),
    tonumber(element(split(".", cidrhost(s.cidr, -1)), 0)) * 16777216 + tonumber(element(split(".", cidrhost(s.cidr, -1)), 1)) * 65536 + tonumber(element(split(".", cidrhost(s.cidr, -1)), 2)) * 256 + tonumber(element(split(".", cidrhost(s.cidr, -1)), 3)),
  ] }

  vcn_start = (
    tonumber(element(split(".", cidrhost(var.vcn_cidr, 0)), 0)) * 16777216
    + tonumber(element(split(".", cidrhost(var.vcn_cidr, 0)), 1)) * 65536
    + tonumber(element(split(".", cidrhost(var.vcn_cidr, 0)), 2)) * 256
    + tonumber(element(split(".", cidrhost(var.vcn_cidr, 0)), 3))
  )

  vcn_end = (
    tonumber(element(split(".", cidrhost(var.vcn_cidr, -1)), 0)) * 16777216
    + tonumber(element(split(".", cidrhost(var.vcn_cidr, -1)), 1)) * 65536
    + tonumber(element(split(".", cidrhost(var.vcn_cidr, -1)), 2)) * 256
    + tonumber(element(split(".", cidrhost(var.vcn_cidr, -1)), 3))
  )

  subnets_within_vcn = alltrue([
    for r in values(local.ip_int) : r[0] >= local.vcn_start && r[1] <= local.vcn_end
  ])

  subnets_disjoint = alltrue([
    for pair in setproduct(keys(var.subnets), keys(var.subnets)) :
    pair[0] >= pair[1] ? true : (
      local.ip_int[pair[0]][1] < local.ip_int[pair[1]][0] ||
      local.ip_int[pair[1]][1] < local.ip_int[pair[0]][0]
    )
  ])

  # ------------------------------------------------------------------ naming
  subnet_names   = { for k, s in var.subnets : k => "${var.name_prefix}-sn-${k}" }
  route_tables   = { for k, s in var.subnets : k => "${var.name_prefix}-rt-${k}" }
  sec_lists      = { for k, s in var.subnets : k => "${var.name_prefix}-sl-${k}" }
  log_group_name = "${var.name_prefix}-flow-logs"

  # --------------------------------------------------------- security lists
  # Subnet-level defaults. Workload-specific control lives in NSGs; these
  # profiles only encode sane defaults per subnet role.
  sl_ingress_profiles = {
    public_lb = concat([
      { protocol = "6", source = "0.0.0.0/0", min = var.https_port, max = var.https_port, description = "HTTPS from internet" },
      { protocol = "6", source = "0.0.0.0/0", min = var.http_port, max = var.http_port, description = "HTTP from internet (redirect only)" },
    ], [local.icmp_pmtu])
    private_oke = concat([
      { protocol = "all", source = var.vcn_cidr, description = "All intra-VCN (nodes/pods/control plane)" },
    ], [local.icmp_pmtu])
    data = concat([
      { protocol = "6", source = var.subnets["oke_workers"].cidr, min = var.database_port, max = var.database_port, description = "PostgreSQL from worker subnet" },
      { protocol = "6", source = var.subnets["oke_pods"].cidr, min = var.database_port, max = var.database_port, description = "PostgreSQL from pod subnet" },
    ], [local.icmp_pmtu])
    bastion = [
      { protocol = "6", source = "0.0.0.0/0", min = 22, max = 22, description = "SSH via OCI Bastion sessions (session auth gates access)" },
      local.icmp_pmtu,
    ]
    locked = [local.icmp_pmtu]
  }

  sl_egress_profiles = {
    public_lb = [{ protocol = "all", destination = "0.0.0.0/0", description = "All egress" }]
    private_oke = concat([
      { protocol = "all", destination = "0.0.0.0/0", description = "All egress (NAT)" },
    ], local.sgw_enabled ? [{ protocol = "all", destination = local.osn, destination_type = "SERVICE_CIDR_BLOCK", description = "Oracle Services Network" }] : [])
    data = local.sgw_enabled ? [{
      protocol         = "6"
      destination      = local.osn
      destination_type = "SERVICE_CIDR_BLOCK"
      min              = 443
      max              = 443
      description      = "HTTPS to Oracle Services Network (backups)"
      }] : [{
      protocol         = "6"
      destination      = "0.0.0.0/0"
      destination_type = "CIDR_BLOCK"
      min              = 443
      max              = 443
      description      = "HTTPS out (backups via NAT)"
    }]
    bastion = []
    locked = local.sgw_enabled ? [{
      protocol         = "6"
      destination      = local.osn
      destination_type = "SERVICE_CIDR_BLOCK"
      min              = 443
      max              = 443
      description      = "HTTPS to Oracle Services Network only"
    }] : []
  }

  icmp_pmtu = { protocol = "1", source = "0.0.0.0/0", icmp_type = 3, icmp_code = 4, description = "ICMP type 3 code 4 (path MTU discovery)" }

  sgw_enabled = var.enable_service_gateway && local.osn != null

  sl_profile_keys = {
    public_lb   = "public_lb"
    oke_api     = "private_oke"
    oke_workers = "private_oke"
    oke_pods    = "private_oke"
    data        = "data"
    bastion     = "bastion"
  }

  # Kubelet traffic always originates from the API endpoint subnet, whether
  # that subnet is IGW-routed (public endpoint) or NAT-routed (private).
  api_path_cidrs = [var.subnets["oke_api"].cidr]

  # ------------------------------------------------------------- NSG rules
  # One flattened map drives a single for_each rule resource.
  # src_kind: cidr | nsg | service ; ports: [min, max] or null for all/icmp.
  nsg_rules = merge(
    {
      "lb-in-https"            = { nsg = "lb", direction = "INGRESS", protocol = "6", src_kind = "cidr", src = "0.0.0.0/0", ports = [var.https_port, var.https_port], description = "HTTPS from internet" }
      "lb-in-http"             = { nsg = "lb", direction = "INGRESS", protocol = "6", src_kind = "cidr", src = "0.0.0.0/0", ports = [var.http_port, var.http_port], description = "HTTP from internet" }
      "lb-eg-nodeports"        = { nsg = "lb", direction = "EGRESS", protocol = "6", src_kind = "nsg", src = "workers", dst_kind = "nsg", dst = "workers", ports = [var.node_port_min, var.node_port_max], description = "Load balancer to backend NodePorts" }
      "lb-eg-kubeproxy-health" = { nsg = "lb", direction = "EGRESS", protocol = "6", src_kind = "nsg", src = "workers", dst_kind = "nsg", dst = "workers", ports = [var.kubelet_health_port, var.kubelet_health_port], description = "Load balancer health checks to kube-proxy" }
      "lb-eg-pmtu"             = { nsg = "lb", direction = "EGRESS", protocol = "1", src_kind = "cidr", src = "0.0.0.0/0", icmp_type = 3, icmp_code = 4, description = "Path MTU discovery" }

      "api-eg-all" = { nsg = "oke_api", direction = "EGRESS", protocol = "all", src_kind = "cidr", src = "0.0.0.0/0", ports = null, description = "API endpoint egress" }
    },
    { for i, c in var.admin_cidrs : format("api-in-admin-%02d", i) => {
      nsg   = "oke_api", direction = "INGRESS", protocol = "6", src_kind = "cidr", src = c,
      ports = [var.kubernetes_api_port, var.kubernetes_api_port], description = "kubectl from admin CIDR ${c}"
    } },
    {
      "api-in-workers" = { nsg = "oke_api", direction = "INGRESS", protocol = "6", src_kind = "nsg", src = "workers", ports = [var.kubernetes_api_port, var.kubernetes_api_port], description = "Workers to Kubernetes API" }
      "api-in-pods"    = { nsg = "oke_api", direction = "INGRESS", protocol = "6", src_kind = "nsg", src = "pods", ports = [var.kubernetes_api_port, var.kubernetes_api_port], description = "Pods to Kubernetes API" }
      "api-in-control" = { nsg = "oke_api", direction = "INGRESS", protocol = "6", src_kind = "nsg", src = "workers", ports = [var.oke_control_port, var.oke_control_port], description = "OKE control channel from workers" }

      "workers-in-self"        = { nsg = "workers", direction = "INGRESS", protocol = "all", src_kind = "cidr", src = var.subnets["oke_workers"].cidr, ports = null, description = "Inter-worker traffic" }
      "workers-in-pods"        = { nsg = "workers", direction = "INGRESS", protocol = "all", src_kind = "nsg", src = "pods", ports = null, description = "Pod-to-host traffic (VCN-native CNI)" }
      "workers-eg-all"         = { nsg = "workers", direction = "EGRESS", protocol = "all", src_kind = "cidr", src = "0.0.0.0/0", ports = null, description = "Worker egress (NAT / SGW / API)" }
      "workers-in-pmtu"        = { nsg = "workers", direction = "INGRESS", protocol = "1", src_kind = "cidr", src = "0.0.0.0/0", icmp_type = 3, icmp_code = 4, description = "Path MTU discovery" }
      "workers-in-lb-np"       = { nsg = "workers", direction = "INGRESS", protocol = "6", src_kind = "nsg", src = "lb", ports = [var.node_port_min, var.node_port_max], description = "Service LB to NodePort range" }
      "workers-in-api-kubelet" = { nsg = "workers", direction = "INGRESS", protocol = "6", src_kind = "cidr", src = local.api_path_cidrs[0], ports = [10250, 10250], description = "Kubernetes API to kubelet" }
    },
    { for i, c in var.admin_cidrs : format("workers-in-ssh-%02d", i) => {
      nsg   = "workers", direction = "INGRESS", protocol = "6", src_kind = "cidr", src = c,
      ports = [22, 22], description = "SSH from admin CIDR ${c}"
    } },
    {
      "pods-in-workers" = { nsg = "pods", direction = "INGRESS", protocol = "all", src_kind = "nsg", src = "workers", ports = null, description = "Host-to-pod traffic" }
      "pods-in-self"    = { nsg = "pods", direction = "INGRESS", protocol = "all", src_kind = "cidr", src = var.subnets["oke_pods"].cidr, ports = null, description = "Inter-pod traffic" }
      "pods-eg-all"     = { nsg = "pods", direction = "EGRESS", protocol = "all", src_kind = "cidr", src = "0.0.0.0/0", ports = null, description = "Pod egress (NAT / SGW / API)" }

      "data-in-pg-workers" = { nsg = "data", direction = "INGRESS", protocol = "6", src_kind = "nsg", src = "workers", ports = [var.database_port, var.database_port], description = "PostgreSQL from workers" }
      "data-in-pg-pods"    = { nsg = "data", direction = "INGRESS", protocol = "6", src_kind = "nsg", src = "pods", ports = [var.database_port, var.database_port], description = "PostgreSQL from pods" }
    },
    merge(
      local.sgw_enabled ? {
        "data-eg-osn" = { nsg = "data", direction = "EGRESS", protocol = "6", src_kind = "service", src = tostring(local.osn), ports = [443, 443], description = "Backups to Oracle Services Network" }
      } : {},
      local.sgw_enabled ? {} : {
        "data-eg-https" = { nsg = "data", direction = "EGRESS", protocol = "6", src_kind = "cidr", src = "0.0.0.0/0", ports = [443, 443], description = "Backups via NAT" }
      }
    )
  )

  nsg_display_names = {
    lb      = "${var.name_prefix}-nsg-lb"
    oke_api = "${var.name_prefix}-nsg-oke-api"
    workers = "${var.name_prefix}-nsg-workers"
    pods    = "${var.name_prefix}-nsg-pods"
    data    = "${var.name_prefix}-nsg-data"
  }

  logged_subnets = { for k, s in var.subnets : k => s if s.enable_logs && var.enable_flow_logs }
}
