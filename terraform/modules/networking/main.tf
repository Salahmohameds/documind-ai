# VCN, gateways, per-subnet route tables / security lists / flow logs,
# and workload NSGs. Everything is driven by locals maps — no copy-pasted
# rule blocks. See locals.tf for the rule payloads.

data "oci_core_services" "all_osn" {
  filter {
    name   = "name"
    values = ["All .* Services In Oracle Services Network"]
    regex  = true
  }
}

# ------------------------------------------------------------------- core --
resource "oci_core_vcn" "this" {
  compartment_id = var.compartment_id
  display_name   = "${var.name_prefix}-vcn"
  cidr_blocks    = [var.vcn_cidr]
  dns_label      = var.vcn_dns_label
  freeform_tags  = var.tags

  lifecycle {
    precondition {
      condition     = local.subnets_within_vcn
      error_message = "Every subnet CIDR must sit inside vcn_cidr."
    }

    precondition {
      condition     = local.subnets_disjoint
      error_message = "Subnet CIDRs must not overlap each other."
    }
  }
}

resource "oci_core_internet_gateway" "this" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name_prefix}-igw"
  enabled        = true
  freeform_tags  = var.tags
}

resource "oci_core_nat_gateway" "this" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name_prefix}-nat"
  freeform_tags  = var.tags
}

# Private access to OCIR / Object Storage / GenAI without internet hairpins.
resource "oci_core_service_gateway" "this" {
  count = local.sgw_enabled ? 1 : 0

  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name_prefix}-sgw"
  freeform_tags  = var.tags

  services {
    service_id = data.oci_core_services.all_osn.services[0].id
  }
}

# --------------------------------------------------------- route tables ----
resource "oci_core_route_table" "this" {
  for_each = var.subnets

  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.this.id
  display_name   = local.route_tables[each.key]
  freeform_tags  = var.tags

  dynamic "route_rules" {
    for_each = each.value.route == "igw" ? [1] : []
    content {
      destination       = "0.0.0.0/0"
      destination_type  = "CIDR_BLOCK"
      network_entity_id = oci_core_internet_gateway.this.id
      description       = "Default route to Internet Gateway"
    }
  }

  dynamic "route_rules" {
    for_each = each.value.route == "nat" ? [1] : []
    content {
      destination       = "0.0.0.0/0"
      destination_type  = "CIDR_BLOCK"
      network_entity_id = oci_core_nat_gateway.this.id
      description       = "Default route to NAT Gateway"
    }
  }

  dynamic "route_rules" {
    for_each = local.sgw_enabled && each.value.route != "igw" ? [1] : []
    content {
      destination       = data.oci_core_services.all_osn.services[0].cidr_block
      destination_type  = "SERVICE_CIDR_BLOCK"
      network_entity_id = oci_core_service_gateway.this[0].id
      description       = "Oracle Services Network via Service Gateway"
    }
  }
}

# -------------------------------------------------------- security lists ---
resource "oci_core_security_list" "this" {
  for_each = var.subnets

  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.this.id
  display_name   = local.sec_lists[each.key]
  freeform_tags  = var.tags

  dynamic "ingress_security_rules" {
    for_each = local.sl_ingress_profiles[try(local.sl_profile_keys[each.key], "locked")]
    content {
      protocol    = ingress_security_rules.value.protocol
      source      = ingress_security_rules.value.source
      source_type = "CIDR_BLOCK"
      description = ingress_security_rules.value.description
      stateless   = false

      dynamic "tcp_options" {
        for_each = ingress_security_rules.value.protocol == "6" && try(ingress_security_rules.value.min, null) != null ? [1] : []
        content {
          min = ingress_security_rules.value.min
          max = ingress_security_rules.value.max
        }
      }

      dynamic "icmp_options" {
        for_each = ingress_security_rules.value.protocol == "1" && try(ingress_security_rules.value.icmp_type, null) != null ? [1] : []
        content {
          type = ingress_security_rules.value.icmp_type
          code = try(ingress_security_rules.value.icmp_code, null)
        }
      }
    }
  }

  dynamic "egress_security_rules" {
    for_each = local.sl_egress_profiles[try(local.sl_profile_keys[each.key], "locked")]
    content {
      protocol         = egress_security_rules.value.protocol
      destination      = egress_security_rules.value.destination
      destination_type = try(egress_security_rules.value.destination_type, "CIDR_BLOCK")
      description      = egress_security_rules.value.description
      stateless        = false

      dynamic "tcp_options" {
        for_each = egress_security_rules.value.protocol == "6" && try(egress_security_rules.value.min, null) != null ? [1] : []
        content {
          min = egress_security_rules.value.min
          max = egress_security_rules.value.max
        }
      }
    }
  }
}

# -------------------------------------------------------------- subnets ----
resource "oci_core_subnet" "this" {
  for_each = var.subnets

  compartment_id             = var.compartment_id
  vcn_id                     = oci_core_vcn.this.id
  display_name               = local.subnet_names[each.key]
  cidr_block                 = each.value.cidr
  dns_label                  = each.value.dns_label
  prohibit_public_ip_on_vnic = each.value.private
  route_table_id             = oci_core_route_table.this[each.key].id
  security_list_ids          = [oci_core_security_list.this[each.key].id]
  freeform_tags              = merge(var.tags, { Component = each.key })
}

# ------------------------------------------------------------------ NSGs ---
resource "oci_core_network_security_group" "this" {
  for_each = local.nsg_display_names

  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.this.id
  display_name   = each.value
  freeform_tags  = var.tags
}

resource "oci_core_network_security_group_security_rule" "this" {
  for_each = local.nsg_rules

  network_security_group_id = oci_core_network_security_group.this[each.value.nsg].id
  direction                 = each.value.direction
  protocol                  = each.value.protocol
  description               = each.value.description
  stateless                 = false

  source           = each.value.direction == "INGRESS" ? (each.value.src_kind == "nsg" ? oci_core_network_security_group.this[each.value.src].id : each.value.src) : null
  source_type      = each.value.direction == "INGRESS" ? (each.value.src_kind == "nsg" ? "NETWORK_SECURITY_GROUP" : "CIDR_BLOCK") : null
  destination      = each.value.direction == "EGRESS" ? (each.value.dst_kind == "nsg" ? oci_core_network_security_group.this[each.value.dst].id : each.value.src) : null
  destination_type = each.value.direction == "EGRESS" ? (each.value.dst_kind == "nsg" ? "NETWORK_SECURITY_GROUP" : (each.value.src_kind == "service" ? "SERVICE_CIDR_BLOCK" : "CIDR_BLOCK")) : null

  dynamic "tcp_options" {
    for_each = each.value.protocol == "6" && try(each.value.ports, null) != null ? [1] : []
    content {
      destination_port_range {
        min = each.value.ports[0]
        max = each.value.ports[1]
      }
    }
  }

  dynamic "icmp_options" {
    for_each = each.value.protocol == "1" && try(each.value.icmp_type, null) != null ? [1] : []
    content {
      type = each.value.icmp_type
      code = try(each.value.icmp_code, null)
    }
  }

  lifecycle {
    precondition {
      condition     = each.value.direction != "INGRESS" || each.value.src_kind != "service"
      error_message = "INGRESS service-CIDR sources are not used in this design; use cidr or nsg."
    }
  }
}

# ------------------------------------------------------------ flow logs ----
resource "oci_logging_log_group" "flow" {
  count = length(local.logged_subnets) > 0 ? 1 : 0

  compartment_id = var.compartment_id
  display_name   = local.log_group_name
  description    = "VCN flow logs for ${var.name_prefix}"
  freeform_tags  = var.tags
}

resource "oci_core_capture_filter" "flow" {
  count = length(local.logged_subnets) > 0 ? 1 : 0

  compartment_id = var.compartment_id
  display_name   = "${var.name_prefix}-flow-filter"
  filter_type    = "FLOWLOG"
  freeform_tags  = var.tags

  flow_log_capture_filter_rules {
    is_enabled    = true
    priority      = 1
    sampling_rate = 10
    flow_log_type = "ALL"
  }
}

resource "oci_logging_log" "flow" {
  for_each = local.logged_subnets

  display_name       = "${local.subnet_names[each.key]}-flow-log"
  log_group_id       = oci_logging_log_group.flow[0].id
  log_type           = "SERVICE"
  is_enabled         = true
  retention_duration = var.log_retention_days
  freeform_tags      = var.tags

  configuration {
    compartment_id = var.compartment_id

    source {
      category    = "all"
      resource    = oci_core_subnet.this[each.key].id
      service     = "flowlogs"
      source_type = "OCISERVICE"

      parameters = {
        capture_filter = oci_core_capture_filter.flow[0].id
      }
    }
  }
}
