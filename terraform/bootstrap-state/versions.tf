terraform {
  # The native oci backend used by environments/* requires Terraform >= 1.12.
  required_version = ">= 1.12.0"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 8.0"
    }
  }
}
