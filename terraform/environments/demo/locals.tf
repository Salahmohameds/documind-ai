locals {
  name_prefix = "dm-${var.environment}"

  tags = {
    Project     = "DocuMind-AI"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Owner       = var.owner
  }

  # Availability domain resolved from the region catalog — never hardcoded.
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[
    min(var.availability_domain_index, length(data.oci_identity_availability_domains.ads.availability_domains) - 1)
  ].name

  # The Kubernetes endpoint subnet route follows the endpoint mode: public
  # endpoint needs the IGW path, private endpoint rides NAT. This invariant
  # is constructed here so it cannot drift.
  oke_api_base = try(var.subnets["oke_api"], null)

  oke_api_cidr = try(local.oke_api_base.cidr, "10.20.2.0/28")
  oke_api_dns  = try(local.oke_api_base.dns_label, "okeapi")
  oke_api_logs = try(local.oke_api_base.enable_logs, false)

  subnets = merge(
    { for k, s in var.subnets : k => s if k != "oke_api" },
    {
      oke_api = {
        cidr        = local.oke_api_cidr
        dns_label   = local.oke_api_dns
        enable_logs = local.oke_api_logs
        private     = !var.oke_endpoint_public
        route       = var.oke_endpoint_public ? "igw" : "nat"
      }
    },
  )
}

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_id
}
