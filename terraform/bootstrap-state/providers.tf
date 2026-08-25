provider "oci" {
  region              = var.region
  config_file_profile = var.config_file_profile

  # Intern tenancies inject Oracle-Tags.CreatedBy/CreatedOn; without this the
  # next plan tries to strip them and fails on policy.
  ignore_defined_tags = ["Oracle-Tags.CreatedBy", "Oracle-Tags.CreatedOn"]
}
