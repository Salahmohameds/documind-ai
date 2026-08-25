output "bastion_id" {
  description = "Bastion OCID — used when creating sessions."
  value       = oci_bastion_bastion.this.id
}
