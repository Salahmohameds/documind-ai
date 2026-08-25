# IAM Module — Outputs

output "dg_oke_workers_id" {
  description = "OCID of the OKE workers dynamic group."
  value       = oci_identity_dynamic_group.oke_workers.id
}

output "dg_oke_workers_name" {
  description = "Name of the OKE workers dynamic group."
  value       = oci_identity_dynamic_group.oke_workers.name
}

output "dg_document_service_id" {
  description = "OCID of the document service dynamic group."
  value       = oci_identity_dynamic_group.document_service.id
}

output "dg_ai_service_id" {
  description = "OCID of the AI service dynamic group."
  value       = oci_identity_dynamic_group.ai_service.id
}

output "policy_oke_workers_id" {
  description = "OCID of the OKE workers policy."
  value       = oci_identity_policy.oke_workers.id
}

output "policy_object_storage_id" {
  description = "OCID of the Object Storage policy."
  value       = oci_identity_policy.object_storage.id
}

output "policy_generative_ai_id" {
  description = "OCID of the Generative AI policy."
  value       = oci_identity_policy.generative_ai.id
}

output "policy_vault_secrets_id" {
  description = "OCID of the Vault secrets policy."
  value       = oci_identity_policy.vault_secrets.id
}

output "policy_ocir_pull_id" {
  description = "OCID of the OCIR pull policy."
  value       = oci_identity_policy.ocir_pull.id
}
