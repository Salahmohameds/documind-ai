
# DocuMind AI — Networking Module
# Creates VCN, Subnets (4), Gateways (3), Route Tables (3), NSGs (4),
# Security Lists (3)
#
# Architecture (from diagram):
#   VCN — dm-vcn (10.20.0.0/16)
#   ├── Public Subnet  — 10.20.1.0/24   (Load Balancer)
#   ├── Private Subnet — 10.20.10.0/24  (OKE workers)
#   ├── Private Subnet — 10.20.11.0/24  (OKE pods, VCN-native)
#   └── Private Subnet — 10.20.30.0/24  (Data: DB, Redis, etc.)
#
#   Gateways: IGW (public ingress), NAT (private egress), SGW (OCI services)
#   Route Tables: public (IGW), private (NAT+SGW), data (SGW only)
#   NSGs: dm-nsg-lb, dm-nsg-oke-api, dm-nsg-workers, dm-nsg-data


# ---------- Data Sources ----------
data "oci_core_services" "all_services" {
  filter {
    name   = "name"
    values = ["All .* Services In Oracle Services Network"]
    regex  = true
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# VCN
# ═══════════════════════════════════════════════════════════════════════════════
resource "oci_core_vcn" "main" {
  compartment_id = var.compartment_id
  display_name   = "${var.name_prefix}-vcn"
  cidr_blocks    = [var.vcn_cidr]
  dns_label      = var.vcn_dns_label

  freeform_tags = var.tags
}

# ═══════════════════════════════════════════════════════════════════════════════
# GATEWAYS
# ═══════════════════════════════════════════════════════════════════════════════

# Internet Gateway — public ingress
resource "oci_core_internet_gateway" "igw" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.name_prefix}-igw"
  enabled        = true

  freeform_tags = var.tags
}

# NAT Gateway — private egress (patches, pulls, etc.)
resource "oci_core_nat_gateway" "natgw" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.name_prefix}-natgw"
  block_traffic  = false

  freeform_tags = var.tags
}

# Service Gateway — OCI services (OCIR, Object Storage, GenAI) without internet
resource "oci_core_service_gateway" "sgw" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.name_prefix}-sgw"

  services {
    service_id = data.oci_core_services.all_services.services[0].id
  }

  freeform_tags = var.tags
}

# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE TABLES (3)
# ═══════════════════════════════════════════════════════════════════════════════

# Public route table — outbound via IGW
resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.name_prefix}-rt-public"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.igw.id
  }

  freeform_tags = var.tags
}

# Private route table — outbound via NAT, OCI services via SGW
# Used by: OKE workers subnet, OKE pods subnet
resource "oci_core_route_table" "private" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.name_prefix}-rt-private"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_nat_gateway.natgw.id
  }

  route_rules {
    destination       = data.oci_core_services.all_services.services[0].cidr_block
    destination_type  = "SERVICE_CIDR_BLOCK"
    network_entity_id = oci_core_service_gateway.sgw.id
  }

  freeform_tags = var.tags
}

# Data route table — SGW only, NO internet route (zero-trust)
# Used by: data subnet (DB, Redis)
resource "oci_core_route_table" "data" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.name_prefix}-rt-data"

  route_rules {
    destination       = data.oci_core_services.all_services.services[0].cidr_block
    destination_type  = "SERVICE_CIDR_BLOCK"
    network_entity_id = oci_core_service_gateway.sgw.id
  }

  freeform_tags = var.tags
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY LISTS (3) — subnet-level defaults
# ═══════════════════════════════════════════════════════════════════════════════

# Public security list (Load Balancer subnet)
resource "oci_core_security_list" "public" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.name_prefix}-sl-public"

  # Ingress: HTTPS from internet
  ingress_security_rules {
    protocol  = "6" # TCP
    source    = "0.0.0.0/0"
    stateless = false
    tcp_options {
      min = 443
      max = 443
    }
  }

  # Ingress: HTTP from internet (redirect to HTTPS)
  ingress_security_rules {
    protocol  = "6"
    source    = "0.0.0.0/0"
    stateless = false
    tcp_options {
      min = 80
      max = 80
    }
  }

  # Egress: all
  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
    stateless   = false
  }

  freeform_tags = var.tags
}

# Private security list (OKE workers + pods)
resource "oci_core_security_list" "private_oke" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.name_prefix}-sl-private-oke"

  # Ingress: all from VCN (inter-node, pod-to-pod)
  ingress_security_rules {
    protocol  = "all"
    source    = var.vcn_cidr
    stateless = false
  }

  # Ingress: ICMP path discovery
  ingress_security_rules {
    protocol  = "1" # ICMP
    source    = "0.0.0.0/0"
    stateless = false
    icmp_options {
      type = 3
      code = 4
    }
  }

  # Egress: all
  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
    stateless   = false
  }

  freeform_tags = var.tags
}

# Data security list (Database, Redis) — zero-trust
resource "oci_core_security_list" "data" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.name_prefix}-sl-data"

  # Ingress: PostgreSQL from OKE workers only
  ingress_security_rules {
    protocol  = "6"
    source    = var.subnet_cidrs["oke_workers"]
    stateless = false
    tcp_options {
      min = 5432
      max = 5432
    }
  }

  # Ingress: Redis from OKE workers only
  ingress_security_rules {
    protocol  = "6"
    source    = var.subnet_cidrs["oke_workers"]
    stateless = false
    tcp_options {
      min = 6379
      max = 6379
    }
  }

  # Egress: OCI services only (via SGW)
  egress_security_rules {
    protocol         = "6"
    destination      = data.oci_core_services.all_services.services[0].cidr_block
    stateless        = false
    destination_type = "SERVICE_CIDR_BLOCK"
  }

  freeform_tags = var.tags
}

# ═══════════════════════════════════════════════════════════════════════════════
# SUBNETS (4)
# ═══════════════════════════════════════════════════════════════════════════════

# Public subnet — Load Balancer (10.20.1.0/24)
resource "oci_core_subnet" "public_lb" {
  compartment_id             = var.compartment_id
  vcn_id                     = oci_core_vcn.main.id
  display_name               = "${var.name_prefix}-sn-public"
  cidr_block                 = var.subnet_cidrs["public"]
  dns_label                  = "pub"
  prohibit_public_ip_on_vnic = false
  route_table_id             = oci_core_route_table.public.id
  security_list_ids          = [oci_core_security_list.public.id]

  freeform_tags = var.tags
}

# Private subnet — OKE Worker Nodes (10.20.10.0/24)
resource "oci_core_subnet" "private_oke_workers" {
  compartment_id             = var.compartment_id
  vcn_id                     = oci_core_vcn.main.id
  display_name               = "${var.name_prefix}-sn-private-oke-workers"
  cidr_block                 = var.subnet_cidrs["oke_workers"]
  dns_label                  = "okeworkers"
  prohibit_public_ip_on_vnic = true
  route_table_id             = oci_core_route_table.private.id
  security_list_ids          = [oci_core_security_list.private_oke.id]

  freeform_tags = var.tags
}

# Private subnet — OKE Pods / VCN-native (10.20.11.0/24)
resource "oci_core_subnet" "private_oke_pods" {
  compartment_id             = var.compartment_id
  vcn_id                     = oci_core_vcn.main.id
  display_name               = "${var.name_prefix}-sn-private-oke-pods"
  cidr_block                 = var.subnet_cidrs["oke_pods"]
  dns_label                  = "okepods"
  prohibit_public_ip_on_vnic = true
  route_table_id             = oci_core_route_table.private.id
  security_list_ids          = [oci_core_security_list.private_oke.id]

  freeform_tags = var.tags
}

# Private subnet — Data tier (10.20.30.0/24) — NO internet route
resource "oci_core_subnet" "private_data" {
  compartment_id             = var.compartment_id
  vcn_id                     = oci_core_vcn.main.id
  display_name               = "${var.name_prefix}-sn-private-data"
  cidr_block                 = var.subnet_cidrs["data"]
  dns_label                  = "data"
  prohibit_public_ip_on_vnic = true
  route_table_id             = oci_core_route_table.data.id
  security_list_ids          = [oci_core_security_list.data.id]

  freeform_tags = var.tags
}

# ═══════════════════════════════════════════════════════════════════════════════
# NETWORK SECURITY GROUPS (4)
# ═══════════════════════════════════════════════════════════════════════════════

# ─── NSG: Load Balancer (dm-nsg-lb) ──────────────────────────────────────────
resource "oci_core_network_security_group" "lb" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.name_prefix}-nsg-lb"

  freeform_tags = var.tags
}

# LB: ingress HTTPS 443 from internet
resource "oci_core_network_security_group_security_rule" "lb_ingress_https" {
  network_security_group_id = oci_core_network_security_group.lb.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = "0.0.0.0/0"
  source_type               = "CIDR_BLOCK"
  stateless                 = false

  tcp_options {
    destination_port_range {
      min = 443
      max = 443
    }
  }
}

# LB: ingress HTTP 80 from internet (redirect)
resource "oci_core_network_security_group_security_rule" "lb_ingress_http" {
  network_security_group_id = oci_core_network_security_group.lb.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = "0.0.0.0/0"
  source_type               = "CIDR_BLOCK"
  stateless                 = false

  tcp_options {
    destination_port_range {
      min = 80
      max = 80
    }
  }
}

# LB: egress to OKE workers (NodePort range)
resource "oci_core_network_security_group_security_rule" "lb_egress_to_workers" {
  network_security_group_id = oci_core_network_security_group.lb.id
  direction                 = "EGRESS"
  protocol                  = "6"
  destination               = var.subnet_cidrs["oke_workers"]
  destination_type          = "CIDR_BLOCK"
  stateless                 = false

  tcp_options {
    destination_port_range {
      min = 30000
      max = 32767
    }
  }
}

# LB: egress to OKE workers (app ports 8080-8090 for health checks)
resource "oci_core_network_security_group_security_rule" "lb_egress_healthcheck" {
  network_security_group_id = oci_core_network_security_group.lb.id
  direction                 = "EGRESS"
  protocol                  = "6"
  destination               = var.subnet_cidrs["oke_workers"]
  destination_type          = "CIDR_BLOCK"
  stateless                 = false

  tcp_options {
    destination_port_range {
      min = 10256
      max = 10256
    }
  }
}

# ─── NSG: OKE API Endpoint (dm-nsg-oke-api) ─────────────────────────────────
resource "oci_core_network_security_group" "oke_api" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.name_prefix}-nsg-oke-api"

  freeform_tags = var.tags
}

# OKE API: ingress 6443 (kubectl access)
resource "oci_core_network_security_group_security_rule" "oke_api_ingress_6443" {
  network_security_group_id = oci_core_network_security_group.oke_api.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = "0.0.0.0/0"
  source_type               = "CIDR_BLOCK"
  stateless                 = false

  tcp_options {
    destination_port_range {
      min = 6443
      max = 6443
    }
  }
}

# OKE API: ingress 12250 from workers (control plane communication)
resource "oci_core_network_security_group_security_rule" "oke_api_ingress_12250" {
  network_security_group_id = oci_core_network_security_group.oke_api.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.subnet_cidrs["oke_workers"]
  source_type               = "CIDR_BLOCK"
  stateless                 = false

  tcp_options {
    destination_port_range {
      min = 12250
      max = 12250
    }
  }
}

# OKE API: egress all
resource "oci_core_network_security_group_security_rule" "oke_api_egress_all" {
  network_security_group_id = oci_core_network_security_group.oke_api.id
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
  stateless                 = false
}

# ─── NSG: OKE Workers (dm-nsg-workers) ───────────────────────────────────────
resource "oci_core_network_security_group" "workers" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.name_prefix}-nsg-workers"

  freeform_tags = var.tags
}

# Workers: ingress from LB (NodePort range) — dm-nsg-lb only
resource "oci_core_network_security_group_security_rule" "workers_ingress_nodeport" {
  network_security_group_id = oci_core_network_security_group.workers.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = oci_core_network_security_group.lb.id
  source_type               = "NETWORK_SECURITY_GROUP"
  stateless                 = false

  tcp_options {
    destination_port_range {
      min = 30000
      max = 32767
    }
  }
}

# Workers: ingress all from worker subnet (inter-node)
resource "oci_core_network_security_group_security_rule" "workers_ingress_internal" {
  network_security_group_id = oci_core_network_security_group.workers.id
  direction                 = "INGRESS"
  protocol                  = "all"
  source                    = var.subnet_cidrs["oke_workers"]
  source_type               = "CIDR_BLOCK"
  stateless                 = false
}

# Workers: ingress all from pods subnet (VCN-native pod traffic)
resource "oci_core_network_security_group_security_rule" "workers_ingress_pods" {
  network_security_group_id = oci_core_network_security_group.workers.id
  direction                 = "INGRESS"
  protocol                  = "all"
  source                    = var.subnet_cidrs["oke_pods"]
  source_type               = "CIDR_BLOCK"
  stateless                 = false
}

# Workers: ingress kubelet (10250) from API
resource "oci_core_network_security_group_security_rule" "workers_ingress_kubelet" {
  network_security_group_id = oci_core_network_security_group.workers.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = "0.0.0.0/0"
  source_type               = "CIDR_BLOCK"
  stateless                 = false

  tcp_options {
    destination_port_range {
      min = 10250
      max = 10250
    }
  }
}

# Workers: ingress ICMP path discovery
resource "oci_core_network_security_group_security_rule" "workers_ingress_icmp" {
  network_security_group_id = oci_core_network_security_group.workers.id
  direction                 = "INGRESS"
  protocol                  = "1"
  source                    = "0.0.0.0/0"
  source_type               = "CIDR_BLOCK"
  stateless                 = false

  icmp_options {
    type = 3
    code = 4
  }
}

# Workers: egress all (NAT for patches, SGW for OCI services)
resource "oci_core_network_security_group_security_rule" "workers_egress_all" {
  network_security_group_id = oci_core_network_security_group.workers.id
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
  stateless                 = false
}

# ─── NSG: Data tier (dm-nsg-data) ───────────────────────────────────────────
resource "oci_core_network_security_group" "data" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.name_prefix}-nsg-data"

  freeform_tags = var.tags
}

# Data: ingress PostgreSQL 5432 from dm-nsg-workers ONLY
resource "oci_core_network_security_group_security_rule" "data_ingress_pg" {
  network_security_group_id = oci_core_network_security_group.data.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = oci_core_network_security_group.workers.id
  source_type               = "NETWORK_SECURITY_GROUP"
  stateless                 = false

  tcp_options {
    destination_port_range {
      min = 5432
      max = 5432
    }
  }
}

# Data: ingress Redis 6379 from dm-nsg-workers ONLY
resource "oci_core_network_security_group_security_rule" "data_ingress_redis" {
  network_security_group_id = oci_core_network_security_group.data.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = oci_core_network_security_group.workers.id
  source_type               = "NETWORK_SECURITY_GROUP"
  stateless                 = false

  tcp_options {
    destination_port_range {
      min = 6379
      max = 6379
    }
  }
}

# Data: egress to OCI services only (backups, etc.)
resource "oci_core_network_security_group_security_rule" "data_egress_services" {
  network_security_group_id = oci_core_network_security_group.data.id
  direction                 = "EGRESS"
  protocol                  = "6"
  destination               = data.oci_core_services.all_services.services[0].cidr_block
  destination_type          = "SERVICE_CIDR_BLOCK"
  stateless                 = false
}
