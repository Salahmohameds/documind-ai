# DocuMind AI — Monitoring Module
# OCI Monitoring, Notifications, Logging

# ---------- Notification Topic ----------
resource "oci_ons_notification_topic" "alerts" {
  compartment_id = var.compartment_id
  name           = "${var.name_prefix}-alerts"
  description    = "DocuMind alerts notification topic"

  freeform_tags = var.tags
}

# Email subscription for alerts
resource "oci_ons_subscription" "email" {
  for_each = toset(var.alert_emails)

  compartment_id = var.compartment_id
  topic_id       = oci_ons_notification_topic.alerts.id
  protocol       = "EMAIL"
  endpoint       = each.value
}

# ---------- Monitoring Alarms ----------
# Alarm: OKE Node Pool — High CPU
resource "oci_monitoring_alarm" "oke_high_cpu" {
  compartment_id        = var.compartment_id
  display_name          = "${var.name_prefix}-alarm-oke-high-cpu"
  namespace             = "oci_computeagent"
  query                 = "CpuUtilization[5m]{resourceId = \"${var.oke_node_pool_id}\"}.max() > ${var.cpu_threshold}"
  severity              = "CRITICAL"
  is_enabled            = true
  pending_duration      = "PT5M"
  body                  = "OKE node pool CPU utilization exceeded ${var.cpu_threshold}%"
  message_format        = "ONS_OPTIMIZED"
  metric_compartment_id = var.compartment_id

  destinations = [oci_ons_notification_topic.alerts.id]

  freeform_tags = var.tags
}

# Alarm: OKE Node Pool — High Memory
resource "oci_monitoring_alarm" "oke_high_memory" {
  compartment_id        = var.compartment_id
  display_name          = "${var.name_prefix}-alarm-oke-high-memory"
  namespace             = "oci_computeagent"
  query                 = "MemoryUtilization[5m]{resourceId = \"${var.oke_node_pool_id}\"}.max() > ${var.memory_threshold}"
  severity              = "WARNING"
  is_enabled            = true
  pending_duration      = "PT5M"
  body                  = "OKE node pool memory utilization exceeded ${var.memory_threshold}%"
  message_format        = "ONS_OPTIMIZED"
  metric_compartment_id = var.compartment_id

  destinations = [oci_ons_notification_topic.alerts.id]

  freeform_tags = var.tags
}

# Alarm: Load Balancer — High 5xx errors
resource "oci_monitoring_alarm" "lb_5xx_errors" {
  count = var.enable_lb_monitoring ? 1 : 0

  compartment_id        = var.compartment_id
  display_name          = "${var.name_prefix}-alarm-lb-5xx"
  namespace             = "oci_lbaas"
  query                 = "HttpResponses5xx[5m]{resourceId = \"${var.lb_id}\"}.sum() > ${var.lb_error_threshold}"
  severity              = "CRITICAL"
  is_enabled            = true
  pending_duration      = "PT5M"
  body                  = "Load Balancer 5xx errors exceeded threshold"
  message_format        = "ONS_OPTIMIZED"
  metric_compartment_id = var.compartment_id

  destinations = [oci_ons_notification_topic.alerts.id]

  freeform_tags = var.tags
}

# ---------- Logging ----------
# Log Group
resource "oci_logging_log_group" "main" {
  compartment_id = var.compartment_id
  display_name   = "${var.name_prefix}-log-group"
  description    = "DocuMind AI log group"

  freeform_tags = var.tags
}

# OKE cluster log — worker node logs
resource "oci_logging_log" "oke_worker" {
  display_name = "${var.name_prefix}-log-oke-worker"
  log_group_id = oci_logging_log_group.main.id
  log_type     = "SERVICE"
  is_enabled   = true

  configuration {
    compartment_id = var.compartment_id

    source {
      category    = "all"
      resource    = var.oke_cluster_id
      service     = "oke"
      source_type = "OCISERVICE"
    }
  }

  freeform_tags = var.tags
}

# Load Balancer access log
resource "oci_logging_log" "lb_access" {
  count = var.enable_lb_monitoring ? 1 : 0

  display_name = "${var.name_prefix}-log-lb-access"
  log_group_id = oci_logging_log_group.main.id
  log_type     = "SERVICE"
  is_enabled   = true

  configuration {
    compartment_id = var.compartment_id

    source {
      category    = "access"
      resource    = var.lb_id
      service     = "loadbalancer"
      source_type = "OCISERVICE"
    }
  }

  freeform_tags = var.tags
}

# Load Balancer error log
resource "oci_logging_log" "lb_error" {
  count = var.enable_lb_monitoring ? 1 : 0

  display_name = "${var.name_prefix}-log-lb-error"
  log_group_id = oci_logging_log_group.main.id
  log_type     = "SERVICE"
  is_enabled   = true

  configuration {
    compartment_id = var.compartment_id

    source {
      category    = "error"
      resource    = var.lb_id
      service     = "loadbalancer"
      source_type = "OCISERVICE"
    }
  }

  freeform_tags = var.tags
}

# VCN Flow Logs
resource "oci_logging_log" "vcn_flow" {
  display_name = "${var.name_prefix}-log-vcn-flow"
  log_group_id = oci_logging_log_group.main.id
  log_type     = "SERVICE"
  is_enabled   = true

  configuration {
    compartment_id = var.compartment_id

    source {
      category    = "all"
      resource    = var.subnet_oke_id
      service     = "flowlogs"
      source_type = "OCISERVICE"
    }
  }

  freeform_tags = var.tags
}
