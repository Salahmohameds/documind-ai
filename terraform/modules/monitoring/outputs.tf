# Monitoring Module — Outputs

output "notification_topic_id" {
  description = "OCID of the notification topic."
  value       = oci_ons_notification_topic.alerts.id
}

output "log_group_id" {
  description = "OCID of the log group."
  value       = oci_logging_log_group.main.id
}

output "alarm_oke_cpu_id" {
  description = "OCID of the OKE high CPU alarm."
  value       = oci_monitoring_alarm.oke_high_cpu.id
}

output "alarm_oke_memory_id" {
  description = "OCID of the OKE high memory alarm."
  value       = oci_monitoring_alarm.oke_high_memory.id
}
