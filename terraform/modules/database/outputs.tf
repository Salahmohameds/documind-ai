output "db_system_id" {
  description = "PostgreSQL system OCID."
  value       = oci_psql_db_system.this.id
}

output "admin_username" {
  description = "Database administrator username."
  value       = oci_psql_db_system.this.admin_username
}

output "state" {
  description = "Database system lifecycle state."
  value       = oci_psql_db_system.this.state
}

output "instances" {
  description = "Database node details (AD, private IP)."
  value = [
    for i in oci_psql_db_system.this.instances : {
      display_name = i.display_name
      private_ip   = try(i.private_ip, null)
    }
  ]
}
