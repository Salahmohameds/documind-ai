# DocuMind demo environment â€” single root wiring every module.
# Feature flags keep the burst footprint small and teardown cheap.

# 1 â”€â”€ NETWORKING â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
module "networking" {
  source = "../../modules/networking"

  compartment_id         = var.compartment_id
  name_prefix            = local.name_prefix
  vcn_cidr               = var.vcn_cidr
  vcn_dns_label          = var.vcn_dns_label
  subnets                = local.subnets
  admin_cidrs            = var.admin_cidrs
  enable_service_gateway = var.enable_service_gateway
  enable_flow_logs       = var.enable_flow_logs
  tags                   = local.tags
}

# Optional operational access (private endpoint kubectl, worker SSH, psql).
module "bastion" {
  count = var.enable_bastion ? 1 : 0

  source = "../../modules/bastion"

  compartment_id               = var.compartment_id
  name_prefix                  = local.name_prefix
  target_subnet_id             = module.networking.subnet_ids["oke_api"]
  client_cidr_block_allow_list = var.admin_cidrs
  tags                         = local.tags
}

# 2 â”€â”€ STORAGE & REGISTRY (no cluster dependency) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
data "oci_objectstorage_namespace" "this" {}

module "object_storage" {
  source = "../../modules/object-storage"

  compartment_id = var.compartment_id
  name_prefix    = local.name_prefix
  namespace      = data.oci_objectstorage_namespace.this.namespace
  tags           = local.tags
}

module "ocir" {
  source = "../../modules/ocir"

  compartment_id    = var.compartment_id
  region            = var.region
  repository_prefix = var.ocir_namespace != "" ? var.ocir_namespace : data.oci_objectstorage_namespace.this.namespace
}

# 3 â”€â”€ OKE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
module "oke" {
  count = var.enable_oke ? 1 : 0

  source = "../../modules/oke"

  compartment_id            = var.compartment_id
  name_prefix               = local.name_prefix
  environment               = var.environment
  vcn_id                    = module.networking.vcn_id
  endpoint_public           = var.oke_endpoint_public
  endpoint_subnet_id        = module.networking.subnet_ids["oke_api"]
  worker_subnet_id          = module.networking.subnet_ids["oke_workers"]
  pod_subnet_ids            = [module.networking.subnet_ids["oke_pods"]]
  lb_subnet_id              = module.networking.subnet_ids["public_lb"]
  nsg_api_id                = module.networking.nsg_ids["oke_api"]
  nsg_workers_id            = module.networking.nsg_ids["workers"]
  nsg_pods_id               = module.networking.nsg_ids["pods"]
  cluster_type              = var.oke_cluster_type
  kubernetes_version        = var.kubernetes_version
  node_pools                = var.node_pools
  node_image_id             = var.node_image_id
  availability_domain_index = var.availability_domain_index
  ssh_public_key            = var.ssh_public_key
  max_pods_per_node         = var.max_pods_per_node
  services_cidr             = var.services_cidr
  tags                      = local.tags

  depends_on = [module.networking]
}

# 4 â”€â”€ IAM (workload identity) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
module "iam" {
  source = "../../modules/iam"

  tenancy_id            = var.tenancy_ocid
  compartment_id        = var.compartment_id
  name_prefix           = local.name_prefix
  cluster_id            = try(module.oke[0].cluster_id, "")
  documents_bucket_name = module.object_storage.documents_bucket_name
  processed_bucket_name = module.object_storage.processed_bucket_name
  tags                  = local.tags
}

# Integer-range overlap check for the Kubernetes Service CIDR vs the VCN
# (no cidrcontains before TF 1.16; explicit octet math instead).
locals {
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

  svc_start = (
    tonumber(element(split(".", cidrhost(var.services_cidr, 0)), 0)) * 16777216
    + tonumber(element(split(".", cidrhost(var.services_cidr, 0)), 1)) * 65536
    + tonumber(element(split(".", cidrhost(var.services_cidr, 0)), 2)) * 256
    + tonumber(element(split(".", cidrhost(var.services_cidr, 0)), 3))
  )

  svc_end = (
    tonumber(element(split(".", cidrhost(var.services_cidr, -1)), 0)) * 16777216
    + tonumber(element(split(".", cidrhost(var.services_cidr, -1)), 1)) * 65536
    + tonumber(element(split(".", cidrhost(var.services_cidr, -1)), 2)) * 256
    + tonumber(element(split(".", cidrhost(var.services_cidr, -1)), 3))
  )
}

check "services_cidr_disjoint_from_vcn" {
  assert {
    condition     = !(local.vcn_end < local.svc_start || local.svc_end < local.vcn_start)
    error_message = "Kubernetes services_cidr (${var.services_cidr}) must not overlap vcn_cidr (${var.vcn_cidr})."
  }
}

# 5 â”€â”€ DATABASE (optional â€” costs and quota) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
module "database" {
  count = var.enable_database ? 1 : 0

  source = "../../modules/database"

  compartment_id        = var.compartment_id
  name_prefix           = local.name_prefix
  subnet_id             = module.networking.subnet_ids["data"]
  nsg_ids               = [module.networking.nsg_ids["data"]]
  availability_domain   = local.availability_domain
  db_version            = var.db_version
  shape                 = var.db_shape
  instance_ocpus        = var.db_instance_ocpus
  instance_memory_gbs   = var.db_instance_memory_gbs
  instance_count        = var.db_instance_count
  password_mode         = var.db_password_mode
  db_admin_password     = var.db_admin_password
  db_password_secret_id = var.db_password_secret_id
  enable_daily_backups  = var.db_enable_daily_backups
  tags                  = local.tags
}

# 6 â”€â”€ MONITORING (optional) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
module "monitoring" {
  count = var.enable_monitoring ? 1 : 0

  source = "../../modules/monitoring"

  compartment_id           = var.compartment_id
  name_prefix              = local.name_prefix
  alert_emails             = var.alert_emails
  cpu_threshold_percent    = var.cpu_threshold_percent
  memory_threshold_percent = var.memory_threshold_percent
  lb_5xx_threshold         = var.lb_5xx_threshold
  lb_ocid                  = var.lb_ocid
  tags                     = local.tags
}
