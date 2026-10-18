resource "oci_ons_notification_topic" "operations" {
  compartment_id = var.compartment_ocid
  name           = "quantnest-operations"
  description    = "Reviewed infrastructure alerts, without customer or broker content"
}

resource "oci_ons_subscription" "operations" {
  compartment_id = var.compartment_ocid
  endpoint       = var.operations_email
  protocol       = "EMAIL"
  topic_id       = oci_ons_notification_topic.operations.id
}

resource "oci_monitoring_alarm" "operations" {
  for_each = {
    unavailable = "deployment_ready[1m]{instanceId = \"${oci_core_instance.app.id}\"}.min() < 1"
    missing     = "deployment_ready[1m]{instanceId = \"${oci_core_instance.app.id}\"}.absent()"
    disk        = "disk_free_bytes[1m]{instanceId = \"${oci_core_instance.app.id}\"}.min() < 2147483648"
    memory      = "memory_available_bytes[1m]{instanceId = \"${oci_core_instance.app.id}\"}.min() < 536870912"
    cpu         = "cpu_busy_pct[1m]{instanceId = \"${oci_core_instance.app.id}\"}.mean() > 90"
    persistence = "redis_persistence_ok[1m]{instanceId = \"${oci_core_instance.app.id}\"}.min() < 1"
    worker      = "execution_workers_ok[1m]{instanceId = \"${oci_core_instance.app.id}\"}.min() < 1"
    outbox      = "outbox_oldest_seconds[1m]{instanceId = \"${oci_core_instance.app.id}\"}.max() > 120"
    orders      = "order_pending_idle_seconds[1m]{instanceId = \"${oci_core_instance.app.id}\"}.max() > 120"
    backup      = "backup_upload_age_seconds[1m]{instanceId = \"${oci_core_instance.app.id}\"}.max() > 108000"
    database    = "database_ok[1m]{instanceId = \"${oci_core_instance.app.id}\"}.min() < 1"
  }
  compartment_id               = var.compartment_ocid
  metric_compartment_id        = var.compartment_ocid
  display_name                 = "quantnest-${each.key}"
  namespace                    = "quantnest"
  query                        = each.value
  severity                     = "CRITICAL"
  is_enabled                   = true
  pending_duration             = "PT5M"
  repeat_notification_duration = "PT1H"
  destinations                 = [oci_ons_notification_topic.operations.id]
  body                         = "Check the QuantNest deployment diagnostics and incident runbook. Do not resume financial execution without reviewing retained state."
}
