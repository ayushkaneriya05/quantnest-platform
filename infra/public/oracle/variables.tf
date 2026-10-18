variable "region" {
  type = string
}
variable "tenancy_ocid" {
  type = string
}
variable "compartment_ocid" {
  type = string
}
variable "availability_domain" {
  type = string
}
variable "ubuntu_arm_image_ocid" {
  type = string
}
variable "ssh_public_key" {
  type = string
}
variable "admin_cidr" {
  type = string
  validation {
    condition     = can(cidrnetmask(var.admin_cidr)) && var.admin_cidr != "0.0.0.0/0"
    error_message = "Use your administrator IPv4 CIDR; SSH must not be open to the world."
  }
}
variable "ingress_cidrs" {
  type        = set(string)
  description = "Cloudflare proxy IP ranges from its published IP list; never default to unrestricted origin access."
  validation {
    condition     = length(var.ingress_cidrs) > 0 && alltrue([for cidr in var.ingress_cidrs : can(cidrnetmask(cidr)) && cidr != "0.0.0.0/0"])
    error_message = "Enter reviewed Cloudflare IPv4 ranges for this IPv4 VCN."
  }
}
variable "backup_retention_days" {
  type    = number
  default = 14
  validation {
    condition     = var.backup_retention_days >= 1 && floor(var.backup_retention_days) == var.backup_retention_days
    error_message = "Backup retention must be a positive whole number of days."
  }
}
variable "operations_email" {
  type        = string
  description = "Real monitored address; confirm the OCI Notifications subscription before launch."
  default     = "ayushkaneriya05@gmail.com"
}
