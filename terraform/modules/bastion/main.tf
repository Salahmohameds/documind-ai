# OCI Bastion for operational access to private targets (kubectl through a
# private API endpoint, SSH to workers, DB psql). Sessions are created ad hoc:
#   oci bastion session create-port-forwarding ...
# The bastion itself is IAM-gated; target subnets must accept port traffic
# from the Bastion service (the networking module's bastion SL profile does).

resource "oci_bastion_bastion" "this" {
  bastion_type                 = "standard"
  compartment_id               = var.compartment_id
  name                         = "${var.name_prefix}-bastion"
  target_subnet_id             = var.target_subnet_id
  max_session_ttl_in_seconds   = 10800 # 3h ops sessions
  client_cidr_block_allow_list = var.client_cidr_block_allow_list
  freeform_tags                = merge(var.tags, { Component = "bastion" })
}
