# DocuMind AI — Database Module
# PostgreSQL-compatible database on OCI
# Uses OCI Database System (PostgreSQL) in a private subnet


resource "oci_psql_db_system" "main" {
  compartment_id = var.compartment_id
  display_name   = "${var.name_prefix}-postgres"
  db_version     = var.db_version
  shape          = var.db_shape

  credentials {
    username = var.db_admin_username
    password_details {
      password_type = "PLAIN_TEXT"
      password      = var.db_admin_password
    }
  }

  network_details {
    subnet_id = var.subnet_db_id
    nsg_ids   = var.nsg_ids
  }

  storage_details {
    system_type           = "OCI_OPTIMIZED_STORAGE"
    is_regionally_durable = false
    availability_domain   = var.availability_domain
  }

  instance_count              = var.instance_count
  instance_memory_size_in_gbs = var.instance_memory_gbs
  instance_ocpu_count         = var.instance_ocpus

  freeform_tags = var.tags
}

