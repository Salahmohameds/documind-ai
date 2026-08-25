# DocuMind AI — Prod Environment — Main
# Same module wiring as dev; sizing differences come from variables

locals {
  name_prefix = "dm"

  tags = {
    Project   = "DocuMind"
    Env       = var.environment
    Owner     = "cloud-lead"
    ManagedBy = "terraform"
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 1. NETWORKING
# ═══════════════════════════════════════════════════════════════════════════════
module "networking" {
  source = "../../modules/networking"

  compartment_id = var.compartment_id
  name_prefix    = local.name_prefix
  vcn_cidr       = var.vcn_cidr
  vcn_dns_label  = var.vcn_dns_label
  subnet_cidrs   = var.subnet_cidrs
  tags           = local.tags
}

# ═══════════════════════════════════════════════════════════════════════════════
# 2. IAM
# ═══════════════════════════════════════════════════════════════════════════════
module "iam" {
  source = "../../modules/iam"

  tenancy_id            = var.tenancy_ocid
  compartment_id        = var.compartment_id
  name_prefix           = local.name_prefix
  documents_bucket_name = module.object_storage.documents_bucket_name
  processed_bucket_name = module.object_storage.processed_bucket_name
  tags                  = local.tags
}

# ═══════════════════════════════════════════════════════════════════════════════
# 3. OBJECT STORAGE
# ═══════════════════════════════════════════════════════════════════════════════
module "object_storage" {
  source = "../../modules/object-storage"

  compartment_id           = var.compartment_id
  name_prefix              = local.name_prefix
  object_storage_namespace = var.object_storage_namespace
  create_state_bucket      = true
  tags                     = local.tags
}

# ═══════════════════════════════════════════════════════════════════════════════
# 4. OCIR
# ═══════════════════════════════════════════════════════════════════════════════
module "ocir" {
  source = "../../modules/ocir"

  compartment_id    = var.compartment_id
  repository_prefix = var.ocir_repo_prefix
}

# ═══════════════════════════════════════════════════════════════════════════════
# 5. DATABASE
# ═══════════════════════════════════════════════════════════════════════════════
module "database" {
  source = "../../modules/database"

  compartment_id      = var.compartment_id
  name_prefix         = local.name_prefix
  subnet_db_id        = module.networking.subnet_data_id
  nsg_ids             = [module.networking.nsg_data_id]
  availability_domain = var.availability_domain
  db_admin_password   = var.db_admin_password
  db_shape            = var.db_shape
  tags                = local.tags
}

# ═══════════════════════════════════════════════════════════════════════════════
# 6. OKE
# ═══════════════════════════════════════════════════════════════════════════════
module "oke" {
  source = "../../modules/oke"

  compartment_id        = var.compartment_id
  name_prefix           = local.name_prefix
  environment           = var.environment
  vcn_id                = module.networking.vcn_id
  subnet_oke_workers_id = module.networking.subnet_oke_workers_id
  subnet_oke_pods_id    = module.networking.subnet_oke_pods_id
  subnet_lb_id          = module.networking.subnet_public_id
  nsg_oke_api_id        = module.networking.nsg_oke_api_id
  nsg_workers_id        = module.networking.nsg_workers_id
  kubernetes_version    = var.kubernetes_version
  node_shape            = var.node_shape
  node_shape_config = {
    ocpus         = var.node_ocpus
    memory_in_gbs = var.node_memory_gbs
  }
  node_pool_size      = var.node_pool_size
  max_pods_per_node   = var.max_pods_per_node
  node_image_id       = var.node_image_id
  availability_domain = var.availability_domain
  ssh_public_key      = var.ssh_public_key
  tags                = local.tags
}

# ═══════════════════════════════════════════════════════════════════════════════
# 7. LOAD BALANCER
# ═══════════════════════════════════════════════════════════════════════════════
module "load_balancer" {
  source = "../../modules/load-balancer"

  compartment_id   = var.compartment_id
  name_prefix      = local.name_prefix
  subnet_lb_id     = module.networking.subnet_public_id
  nsg_lb_id        = module.networking.nsg_lb_id
  lb_shape         = "flexible"
  lb_min_bandwidth = var.lb_min_bandwidth
  lb_max_bandwidth = var.lb_max_bandwidth
  tags             = local.tags
}

# ═══════════════════════════════════════════════════════════════════════════════
# 8. MONITORING
# ═══════════════════════════════════════════════════════════════════════════════
module "monitoring" {
  source = "../../modules/monitoring"

  compartment_id   = var.compartment_id
  name_prefix      = local.name_prefix
  alert_emails     = var.alert_emails
  oke_cluster_id   = module.oke.cluster_id
  oke_node_pool_id = module.oke.node_pool_id
  subnet_oke_id    = module.networking.subnet_oke_workers_id
  lb_id            = module.load_balancer.lb_id
  tags             = local.tags
}
