# OCI Database with PostgreSQL in the private data subnet.
# Password handling follows the provider's VaultSecretPasswordDetails /
# PlainTextPasswordDetails contract.

resource "oci_psql_db_system" "this" {
  compartment_id = var.compartment_id
  display_name   = "${var.name_prefix}-postgres"
  db_version     = var.db_version
  shape          = var.shape

  credentials {
    username = var.admin_username

    password_details {
      password_type  = var.password_mode == "VAULT_SECRET" ? "VAULT_SECRET" : "PLAIN_TEXT"
      password       = var.password_mode == "PLAIN_TEXT" ? var.db_admin_password : null
      secret_id      = var.password_mode == "VAULT_SECRET" ? var.db_password_secret_id : null
      secret_version = var.password_mode == "VAULT_SECRET" ? var.secret_version : null
    }
  }

  network_details {
    subnet_id = var.subnet_id
    nsg_ids   = var.nsg_ids
  }

  storage_details {
    system_type           = "OCI_OPTIMIZED_STORAGE"
    is_regionally_durable = false
    availability_domain   = var.availability_domain
    iops                  = var.storage_iops
  }

  instance_count              = var.instance_count
  instance_ocpu_count         = var.instance_ocpus
  instance_memory_size_in_gbs = var.instance_memory_gbs

  dynamic "management_policy" {
    for_each = var.enable_daily_backups ? [1] : []
    content {
      maintenance_window_start = "sun 02:00"

      backup_policy {
        kind           = "DAILY"
        retention_days = 7
        backup_start   = "02:30"
      }
    }
  }

  freeform_tags = merge(var.tags, { Component = "database" })

  lifecycle {
    precondition {
      condition     = var.password_mode != "VAULT_SECRET" || length(var.db_password_secret_id) > 0
      error_message = "password_mode VAULT_SECRET requires db_password_secret_id."
    }

    precondition {
      condition     = var.password_mode != "PLAIN_TEXT" || (length(var.db_admin_password) >= 12 && can(regex("[A-Z]", var.db_admin_password)) && can(regex("[a-z]", var.db_admin_password)) && can(regex("[0-9]", var.db_admin_password)))
      error_message = "PLAIN_TEXT admin password must be >= 12 chars with upper, lower and digit."
    }

    precondition {
      condition     = length(var.availability_domain) > 0
      error_message = "availability_domain is required for AD-local storage."
    }
  }
}
