output "topic_id" {
  description = "Alert notification topic OCID."
  value       = oci_ons_notification_topic.alerts.id
}

output "topic_name" {
  description = "Alert topic name."
  value       = oci_ons_notification_topic.alerts.name
}

output "alarm_names" {
  description = "Created alarms (empty entries when inputs were absent)."
  value       = concat([for a in [oci_monitoring_alarm.node_cpu_high, oci_monitoring_alarm.node_memory_high] : a.display_name], [for a in oci_monitoring_alarm.lb_5xx : a.display_name])
}
