# DocuMind AI — Dev Environment — Remote State Backend
#
# USAGE:
# 1. Copy backend.hcl.example → backend.hcl and fill in values
# 2. Run: terraform init -backend-config=backend.hcl
#
# The state bucket must exist BEFORE init. Create it manually or with the
# object-storage module's create_state_bucket option first.


terraform {
  backend "s3" {
    # All values come from backend.hcl (gitignored) 
    # See backend.hcl.example for the required keys
  }
}
