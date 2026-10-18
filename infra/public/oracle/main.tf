resource "oci_core_vcn" "app" {
  compartment_id = var.compartment_ocid
  cidr_block     = "10.24.0.0/16"
  display_name   = "quantnest"
  dns_label      = "quantnest"
}
resource "oci_core_internet_gateway" "app" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.app.id
  display_name   = "quantnest-ingress"
}
resource "oci_core_route_table" "app" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.app.id
  route_rules {
    destination       = "0.0.0.0/0"
    network_entity_id = oci_core_internet_gateway.app.id
  }
}
resource "oci_core_security_list" "app" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.app.id
  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }
  ingress_security_rules {
    protocol = "6"
    source   = var.admin_cidr
    tcp_options {
      min = 22
      max = 22
    }
  }
  dynamic "ingress_security_rules" {
    for_each = var.ingress_cidrs
    content {
      protocol = "6"
      source   = ingress_security_rules.value
      tcp_options {
        min = 443
        max = 443
      }
    }
  }
}
resource "oci_core_subnet" "app" {
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.app.id
  cidr_block        = "10.24.1.0/24"
  route_table_id    = oci_core_route_table.app.id
  security_list_ids = [oci_core_security_list.app.id]
  dns_label         = "app"
}
resource "oci_core_instance" "app" {
  availability_domain = var.availability_domain
  compartment_id      = var.compartment_ocid
  display_name        = "quantnest-a1"
  shape               = "VM.Standard.A1.Flex"
  shape_config {
    ocpus         = 2
    memory_in_gbs = 12
  }
  create_vnic_details {
    subnet_id        = oci_core_subnet.app.id
    assign_public_ip = false
  }
  source_details {
    source_type             = "image"
    source_id               = var.ubuntu_arm_image_ocid
    boot_volume_size_in_gbs = 50
  }
  metadata = { ssh_authorized_keys = var.ssh_public_key }
  lifecycle { prevent_destroy = true }
}
data "oci_core_vnic_attachments" "app" {
  compartment_id = var.compartment_ocid
  instance_id    = oci_core_instance.app.id
}
data "oci_core_private_ips" "app" {
  vnic_id = data.oci_core_vnic_attachments.app.vnic_attachments[0].vnic_id
}
resource "oci_core_public_ip" "app" {
  compartment_id = var.compartment_ocid
  display_name   = "quantnest-origin"
  lifetime       = "RESERVED"
  private_ip_id  = data.oci_core_private_ips.app.private_ips[0].id
  lifecycle { prevent_destroy = true }
}
resource "oci_core_volume" "data" {
  compartment_id      = var.compartment_ocid
  availability_domain = var.availability_domain
  display_name        = "quantnest-data"
  size_in_gbs         = 150
  vpus_per_gb         = 10
  lifecycle { prevent_destroy = true }
}
resource "oci_core_volume_attachment" "data" {
  attachment_type = "paravirtualized"
  instance_id     = oci_core_instance.app.id
  volume_id       = oci_core_volume.data.id
}
resource "oci_kms_vault" "app" {
  compartment_id = var.compartment_ocid
  display_name   = "quantnest-standard"
  vault_type     = "DEFAULT"
  lifecycle { prevent_destroy = true }
}
resource "oci_kms_key" "license" {
  compartment_id      = var.compartment_ocid
  display_name        = "quantnest-es256"
  management_endpoint = oci_kms_vault.app.management_endpoint
  protection_mode     = "HSM"
  key_shape {
    algorithm = "ECDSA"
    curve_id  = "NIST_P256"
    length    = 32
  }
  lifecycle { prevent_destroy = true }
}
data "oci_objectstorage_namespace" "app" { compartment_id = var.compartment_ocid }
resource "oci_kms_key" "release" {
  compartment_id      = var.compartment_ocid
  display_name        = "quantnest-release-es256"
  management_endpoint = oci_kms_vault.app.management_endpoint
  protection_mode     = "HSM"
  key_shape {
    algorithm = "ECDSA"
    curve_id  = "NIST_P256"
    length    = 32
  }
  lifecycle { prevent_destroy = true }
}
resource "oci_objectstorage_bucket" "backups" {
  compartment_id = var.compartment_ocid
  namespace      = data.oci_objectstorage_namespace.app.namespace
  name           = "quantnest-encrypted-backups"
  access_type    = "NoPublicAccess"
  versioning     = "Enabled"
  lifecycle { prevent_destroy = true }
}
resource "oci_objectstorage_object_lifecycle_policy" "backups" {
  namespace = data.oci_objectstorage_namespace.app.namespace
  bucket    = oci_objectstorage_bucket.backups.name
  rules {
    name        = "expire-backups"
    action      = "DELETE"
    is_enabled  = true
    time_amount = var.backup_retention_days
    time_unit   = "DAYS"
    target      = "objects"
  }
  rules {
    name        = "expire-old-versions"
    action      = "DELETE"
    is_enabled  = true
    time_amount = var.backup_retention_days
    time_unit   = "DAYS"
    target      = "previous-object-versions"
  }
}
resource "oci_identity_dynamic_group" "runtime" {
  compartment_id = var.tenancy_ocid
  name           = "quantnest-runtime"
  description    = "Only the approved QuantNest host"
  matching_rule  = "ALL {instance.id = '${oci_core_instance.app.id}'}"
}
resource "oci_identity_policy" "runtime" {
  compartment_id = var.compartment_ocid
  name           = "quantnest-runtime-scoped"
  description    = "Dedicated signing, metrics and encrypted backups"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.runtime.name} to use metrics in compartment id ${var.compartment_ocid} where target.metrics.namespace = 'quantnest'",
    "Allow dynamic-group ${oci_identity_dynamic_group.runtime.name} to use keys in compartment id ${var.compartment_ocid} where target.key.id = '${oci_kms_key.license.id}'",
    "Allow dynamic-group ${oci_identity_dynamic_group.runtime.name} to use keys in compartment id ${var.compartment_ocid} where target.key.id = '${oci_kms_key.release.id}'",
    "Allow dynamic-group ${oci_identity_dynamic_group.runtime.name} to read buckets in compartment id ${var.compartment_ocid} where target.bucket.name = '${oci_objectstorage_bucket.backups.name}'",
    "Allow dynamic-group ${oci_identity_dynamic_group.runtime.name} to manage objects in compartment id ${var.compartment_ocid} where all {target.bucket.name = '${oci_objectstorage_bucket.backups.name}', request.permission = 'OBJECT_CREATE'}"
  ]
}
resource "oci_identity_policy" "backup_lifecycle" {
  compartment_id = var.tenancy_ocid
  name           = "quantnest-backup-lifecycle"
  description    = "Permit regional Object Storage lifecycle cleanup without giving the VM delete permissions"
  statements = [
    "Allow service objectstorage-${var.region} to read buckets in compartment id ${var.compartment_ocid}",
    "Allow service objectstorage-${var.region} to manage objects in compartment id ${var.compartment_ocid} where all {target.bucket.name = '${oci_objectstorage_bucket.backups.name}', any {request.permission = 'OBJECT_INSPECT', request.permission = 'OBJECT_DELETE', request.permission = 'OBJECT_VERSION_DELETE'}}"
  ]
}
