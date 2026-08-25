# Alerting: one ONS topic + email subs + a small set of meaningful alarms.
#
# Query design note: oci_computeagent metrics are emitted per instance, so the
# queries aggregate across all nodes in the compartment rather than filtering
# on a node-pool resourceId (pool OCIDs are not metric resourceIds).

locals {
  pending_duration = "PT${var.pending_minutes}M"
}

resource "oci_ons_notification_topic" "alerts" {
  compartment_id = var.compartment_id
  name           = "${var.name_prefix}-alerts"
  description    = "DocuMind demo alerts"
  freeform_tags  = var.tags
}

resource "oci_ons_subscription" "email" {
  for_each = var.alert_emails

  compartment_id = var.compartment_id
  topic_id       = oci_ons_notification_topic.alerts.id
  protocol       = "EMAIL"
  endpoint       = each.value
}

resource "oci_monitoring_alarm" "node_cpu_high" {
  compartment_id        = var.compartment_id
  display_name          = "${var.name_prefix}-nodes-cpu-high"
  namespace             = "oci_computeagent"
  query                 = "CpuUtilization[5m].max() > ${var.cpu_threshold_percent}"
  severity              = "WARNING"
  is_enabled            = true
  pending_duration      = local.pending_duration
  body                  = "Worker CPU above ${var.cpu_threshold_percent}% (compartment aggregate)"
  message_format        = "ONS_OPTIMIZED"
  metric_compartment_id = var.compartment_id
  destinations          = [oci_ons_notification_topic.alerts.id]
  freeform_tags         = var.tags
}

resource "oci_monitoring_alarm" "node_memory_high" {
  compartment_id        = var.compartment_id
  display_name          = "${var.name_prefix}-nodes-memory-high"
  namespace             = "oci_computeagent"
  query                 = "MemoryUtilization[5m].max() > ${var.memory_threshold_percent}"
  severity              = "CRITICAL"
  is_enabled            = true
  pending_duration      = local.pending_duration
  body                  = "Worker memory above ${var.memory_threshold_percent}% (compartment aggregate)"
  message_format        = "ONS_OPTIMIZED"
  metric_compartment_id = var.compartment_id
  destinations          = [oci_ons_notification_topic.alerts.id]
  freeform_tags         = var.tags
}

resource "oci_monitoring_alarm" "lb_5xx" {
  count = var.lb_ocid != null ? 1 : 0

  compartment_id        = var.compartment_id
  display_name          = "${var.name_prefix}-lb-5xx"
  namespace             = "oci_lbaas"
  query                 = "HttpResponses5xx[5m]{resourceId = \"${var.lb_ocid}\"}.sum() > ${var.lb_5xx_threshold}"
  severity              = "CRITICAL"
  is_enabled            = true
  pending_duration      = local.pending_duration
  body                  = "Load balancer returned more than ${var.lb_5xx_threshold} 5xx per interval"
  message_format        = "ONS_OPTIMIZED"
  metric_compartment_id = var.compartment_id
  destinations          = [oci_ons_notification_topic.alerts.id]
  freeform_tags         = var.tags

  lifecycle {
    precondition {
      condition     = can(regex("^ocid1\\.(loadbalancer)\\.", var.lb_ocid))
      error_message = "lb_ocid must be an ocid1.loadbalancer... OCID."
    }
  }
}
