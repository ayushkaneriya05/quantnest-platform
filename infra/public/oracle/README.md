# Oracle provisioning: Public mode

This Terraform directory provisions the infrastructure for the **Public QuantNest service**. It does not provision a customer Private installation or your developer stack. Applying it creates real OCI resources; review your tenancy's capacity, cost estimate and quotas first.

It targets the agreed A1 profile: 2 OCPUs / 12 GB on Ubuntu 24.04 ARM64. The [Public software guide](../README.md) starts after this provisioning/host-storage preparation.

## 1. Know what Terraform creates

| Resource | Purpose |
| --- | --- |
| VCN/subnet/Internet Gateway/routes | Public host networking with a controlled inbound policy |
| Security list | SSH only from administrator IPv4; HTTPS only from reviewed Cloudflare IPv4 ranges |
| A1 instance and 50 GB boot volume | Application host |
| 150 GB paravirtualized data volume | Persistent Docker/application/backup storage |
| Reserved public address | Stable Cloudflare origin address |
| Standard Vault and two HSM P-256 keys | Separate licence/release signing |
| Private versioned backup bucket/lifecycle | Encrypted backups and remote retention |
| Instance dynamic group/scoped IAM | Metrics, approved signing keys and append-only backup uploads |
| Regional lifecycle service policy | Permit Object Storage to expire old backup versions; the VM does not receive deletion rights |
| Notification topic/email subscription and alarms | Operational readiness/capacity/persistence/backup alerts |

State protection prevents accidental destruction of important host/storage/Vault/key/bucket resources. It is not a backup and does not protect every network resource. Do not use terraform destroy against an active trading installation.

Files in this directory:

| File | Purpose |
| --- | --- |
| versions.tf | Supported Terraform range, OCI provider constraint and region selection |
| .terraform.lock.hcl | Committed provider version/checksums; keep it with the template and do not edit hashes manually |
| variables.tf / terraform.tfvars.example | Declared inputs / copy-and-edit example with no secrets |
| main.tf | Compute, network, storage, signing keys and scoped IAM |
| monitoring.tf | OCI Notifications subscription and operational metric alarms |
| outputs.tf | Host/operator and signing identifiers used by subsequent steps |

Intentional provider upgrade: run `terraform -chdir=infra/public/oracle init -upgrade`, review the lock/resource changes, then validate and review a new plan. Ordinary initialization should retain the committed provider version.

## 2. Prepare OCI access

1. Sign into OCI and enable MFA.
2. Use the actual tenancy home region; confirm A1 Always Free capacity/eligibility there.
3. Create/select a dedicated QuantNest compartment.
4. Record tenancy OCID, compartment OCID and region identifier.
5. Record an availability domain name that supports A1 in that region.
6. Choose an **Ubuntu 24.04 ARM64** platform image OCID for that region, not an x86 image.
7. Create an SSH key on your trusted computer. Keep the private key there; only the public key goes into metadata.
8. Find your administrator public IPv4 and use its /32 CIDR, or an accepted restricted administrator network.
9. Confirm budget alerts and available compute, block-volume, Vault, Object Storage and monitoring allowances.

The template uses a standard shared Vault. It creates two asymmetric signing versions; review Oracle's actual allowance and rotation/storage/backup-version growth before adding resources. Application environment files are operator-managed and are not uploaded into Terraform or Vault bundles.

Primary provider guidance: [Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), [instance principals](https://docs.oracle.com/en-us/iaas/Content/Identity/Tasks/callingservicesfrominstances.htm). Free capacity and idle-instance reclamation are operational risks; do not generate artificial load to avoid reclamation.

## 3. Choose one Terraform execution method

### Option A: OCI Resource Manager

1. In OCI Console open Resource Manager → Stacks → Create stack.
2. Upload a zip containing this directory's Terraform files and provider lock.
3. Select the intended compartment/region.
4. Enter all required variables from the next section.
5. Run **Plan**, review it, then run **Apply** only after confirming resources/costs.
6. Save outputs and monitor the work request for failures.

Do not upload app environment files, OCI API private keys or age identities with this stack.

### Option B: local Terraform

Install Terraform 1.8+ below 2.0 and configure an authenticated OCI profile on your trusted operator computer. Keep the OCI API private key in the protected OCI config directory, outside the repository. This provisioning identity needs rights for the declared compute/network/Vault/storage resources plus root-level dynamic-group/service-policy administration.

From the repository root:

```sh
cp infra/public/oracle/terraform.tfvars.example infra/public/oracle/terraform.tfvars
terraform -chdir=infra/public/oracle init
terraform -chdir=infra/public/oracle fmt -check
terraform -chdir=infra/public/oracle validate
terraform -chdir=infra/public/oracle plan -out=quantnest.tfplan
```

On PowerShell use Copy-Item for the copy. Edit terraform.tfvars before planning. Review the plan privately; Terraform state/plan files contain infrastructure identifiers. After approval:

```sh
terraform -chdir=infra/public/oracle apply quantnest.tfplan
terraform -chdir=infra/public/oracle output
```

Do not apply an old plan after changing inputs/resources. Keep state access restricted and backed up. The repository ignores .tfvars/state/plan artifacts; state is not shared through Git. For team operations use a separately secured Terraform state backend rather than copying competing local states.

## 4. Fill the variables

| Variable | Value |
| --- | --- |
| region | OCI region identifier, such as the actual home region |
| tenancy_ocid | Tenancy details OCID |
| compartment_ocid | Dedicated application compartment |
| availability_domain | Exact accepted availability-domain name |
| ubuntu_arm_image_ocid | Region-specific Ubuntu 24.04 ARM64 platform image |
| ssh_public_key | Entire single-line public key; never the private key |
| admin_cidr | Your restricted administrator IPv4 CIDR |
| ingress_cidrs | Complete reviewed Cloudflare IPv4 proxy ranges |
| operations_email | Real monitored address; confirm the notification email |
| backup_retention_days | Positive integer; default 14, subject to storage budget |

The example includes the IPv4 list reviewed on 15 October 2026. Compare with [Cloudflare's current published ranges](https://www.cloudflare.com/ips-v4/) before applying. This VCN is IPv4; do not copy IPv6 CIDRs into its security-list inputs.

All replace-me/example identifiers must be changed. The documentation IPv4 203.0.113.10/32 is not your administrator address. No secret values belong in Terraform variables/state.

## 5. Existing resources and repeat deployments

If you already own the VM, volume, Vault, key or bucket, import/adapt it rather than making a duplicate. Terraform import requires the correct resource address and actual OCI resource ID. Import one accepted resource, run a plan and reconcile all attributes before applying.

A plan proposing replacement/deletion of the active host, disk, reserved address, key or bucket needs investigation. prevent_destroy intentionally blocks destructive changes; do not remove it just to make a plan pass. Dynamic-group/policy/bucket display names must not collide with a different deployment.

The template assumes one Public stack in the selected compartment. Development and customer Private do not use it.

## 6. Record outputs

| Output | Used for |
| --- | --- |
| instance_ocid | operations.env monitoring dimension |
| public_ip | Cloudflare proxied origin A record |
| data_volume_ocid / data_volume_device | Disk verification/attachment inventory |
| vault_ocid | Console signing-key management |
| vault_management_endpoint | Key-version public-key retrieval |
| signing_endpoint | OCI cryptographic signing calls |
| license_key_ocid / license_key_version_ocid | Public backend OCI_LICENSE_* |
| release_key_ocid / release_key_version_ocid | Host operations OCI_RELEASE_* |
| backup_namespace / backup_bucket | Backup upload configuration |
| operations_topic_ocid | Notification/incident inventory |

There are no exported private keys. Export the appropriate **public** PEM for each signing version and distribute it with a verified trust mapping.

## 7. Verify and mount the data disk

1. SSH to the reserved public address using your private SSH key: `ssh -i PATH_TO_PRIVATE_KEY ubuntu@YOUR_RESERVED_PUBLIC_IP`. On Windows this works from PowerShell with the Windows OpenSSH client; use the real local key path and keep the key private.
2. Compare OCI attachment metadata/device output with lsblk -f and the OS device identity.
3. If it is a new empty disk, prepare a filesystem only after verifying that exact device contains no data.
4. Mount it at /mnt/quantnest-data.
5. Persist its filesystem UUID in /etc/fstab with appropriate boot behavior.
6. Verify mountpoint /mnt/quantnest-data and df -h /mnt/quantnest-data.

No format command is automated because choosing the wrong disk destroys data. Do not assume a device name from another VM or use the boot disk. The fresh-host bootstrap refuses to use an unmounted directory.

Then follow [Public software deployment](../README.md): reviewed release, host bootstrap, protected env files, TLS, Cloudflare frontend, initial database/admin and source setup.

## 8. Backups, lifecycle and monitoring

VM backup uploads are create-only within the dedicated bucket. They cannot overwrite/delete old backups. OCI's regional Object Storage service has the separate scoped permissions to apply lifecycle expiration.

Confirm actual retention in Console and ensure an older good backup remains within your recovery needs. Versioned storage, checksums and growing candle data all consume quota. [Oracle lifecycle permissions](https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/usinglifecyclepolicies.htm) explain the service-policy requirement.

Confirm the Oracle Notifications subscription by email before relying on alarms. Public host monitoring publishes the quantnest namespace and instanceId dimension. Alarms include missing/unready deployment, disk/memory/CPU, Redis persistence, execution heartbeats, old order/outbox work and backup uploads older than 30 hours.

Provisioning an alarm does not produce metrics; run/configure the host monitor/timers after deploying the application. Validate a controlled operational alert through your accepted incident process.

## 9. Ongoing operation

- Watch resource usage and provider budgets rather than assuming all future usage is free.
- Review Cloudflare ranges and update the security list when they change.
- Keep administrator CIDR current; preserve a recovery access path before changing SSH rules.
- Retain trusted public keys for still-valid releases/leases; rotate private signing versions centrally.
- Recover data into isolated projects; never use Terraform replacement as a database restore.
- Recheck the plan and host health after each reviewed infrastructure change.

This stack does not grant data redistribution, securities activity approval or broker qualification. Those are separate operational prerequisites enforced by the application.
