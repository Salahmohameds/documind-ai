# DocuMind AI — Prod Environment — Outputs

output "vcn_id" {
  value = module.networking.vcn_id
}

output "oke_cluster_id" {
  value = module.oke.cluster_id
}

output "oke_cluster_name" {
  value = module.oke.cluster_name
}

output "oke_cluster_endpoints" {
  value = module.oke.cluster_endpoints
}

output "lb_public_ip" {
  value = module.load_balancer.lb_ip
}

output "db_endpoint" {
  value = module.database.db_system_fqdn
}

output "documents_bucket" {
  value = module.object_storage.documents_bucket_name
}

output "ocir_repositories" {
  value = module.ocir.repository_paths
}

output "deployment_summary" {
  value = {
    environment = var.environment
    region      = var.region
    vcn_id      = module.networking.vcn_id
    oke_cluster = module.oke.cluster_name
    lb_ip       = module.load_balancer.lb_ip
    db_endpoint = module.database.db_system_fqdn
    doc_bucket  = module.object_storage.documents_bucket_name
  }
}
