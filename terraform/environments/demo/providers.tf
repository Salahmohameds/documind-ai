# Authentication prefers ~/.oci/config profiles locally. In CI set
# config_file_profile = null via TF_VAR_config_file_profile and supply the
# OCI_* credential environment variables instead — never commit keys.

provider "oci" {
  region              = var.region
  config_file_profile = var.config_file_profile == "" ? null : var.config_file_profile

  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path

  # Intern tenancies auto-inject Oracle-Tags.CreatedBy/CreatedOn; without this
  # ignore-list every plan tries to strip them and fails on tag policy.
  ignore_defined_tags = ["Oracle-Tags.CreatedBy", "Oracle-Tags.CreatedOn"]
}
