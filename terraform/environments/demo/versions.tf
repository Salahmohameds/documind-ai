terraform {
  # >= 1.12 for the native oci backend and cidrcontains().
  required_version = ">= 1.12.0"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 8.0"
    }
  }
}
