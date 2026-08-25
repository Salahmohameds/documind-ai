# Remote state: native `oci` backend (Terraform >= 1.12) against the bucket
# created by ../../bootstrap-state.
#
# Backend blocks accept only literal values, so this stays an empty block and
# real values come from a local, gitignored backend.hcl:
#   cp backend.hcl.example backend.hcl   # paste the bootstrap namespace output
#   terraform init

terraform {
  backend "oci" {}
}
