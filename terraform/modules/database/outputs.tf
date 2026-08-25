# Database Module — Outputs

output "db_system_id" {
  description = "OCID of the PostgreSQL DB System."
  value       = oci_psql_db_system.main.id
}

output "db_system_fqdn" {
  description = "FQDN of the database endpoint."
  value       = oci_psql_db_system.main.network_details[0].primary_db_endpoint_private_ip
}

output "db_system_port" {
  description = "Database port."
  value       = 5432
}

output "db_admin_username" {
  description = "Admin username."
  value       = var.db_admin_username
}
