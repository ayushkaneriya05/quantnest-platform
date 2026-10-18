# Public Oracle host operations

These tools belong to the **Public Oracle host**. They are not customer Private scripts and are not application runtime supervisors. See [Public deployment](../README.md) first.

## 1. bootstrap_host.sh: run once on a fresh host

Prerequisites:

1. Ubuntu 24.04, root/sudo access and the reviewed release directory.
2. The correct data disk has already been verified and mounted at /mnt/quantnest-data.
3. Docker has no existing data to migrate. The script refuses a populated /var/lib/docker.
4. /opt/quantnest/current points to the intended release; it must contain the operations lock and host units.

```sh
sudo bash infra/public/scripts/bootstrap_host.sh /mnt/quantnest-data /opt/quantnest/current
```

The two positional arguments are absolute data-mount and release paths. It checks the mount/OS, installs Docker/Compose, Python venv support and age, creates the quantnest operator, sets Docker data on the mounted volume, configures bounded JSON logs, installs hashed operations dependencies and copies the public host systemd units.

It never formats a disk or migrates an existing Docker installation. Review/migrate existing storage separately instead of deleting it to force the bootstrap. Application startup and timer activation are later steps.

The bootstrap also writes `/etc/systemd/system/docker.service.d/quantnest-storage.conf`: Docker requires the data filesystem to be mounted before it starts. This prevents a reboot with a missing disk from creating a new empty installation on the boot filesystem. Persist the correct mount in `/etc/fstab` first. A custom data path must have no whitespace; if it changes later, update Docker's data-root, this drop-in, mounts and operations.env together during a backed-up maintenance window.

Make the reviewed release/config paths readable by quantnest. The public deployment guide uses that service account for scripts; it is a non-login account, so use sudo -u quantnest rather than a password login.

## 2. operations.env: host-only configuration

```sh
sudo install -m 600 -o quantnest -g quantnest infra/public/operations.env.example /etc/quantnest/operations.env
sudoedit /etc/quantnest/operations.env
```

| Input | Where to get it / meaning |
| --- | --- |
| QUANTNEST_DATA_DIRECTORY | Mounted data filesystem, default /mnt/quantnest-data |
| QUANTNEST_BACKUP_DIRECTORY | Protected local backup directory on that filesystem |
| OCI_COMPARTMENT_OCID / OCI_INSTANCE_OCID | Configured compartment / instance_ocid output or OCI Console details |
| OCI_OBJECT_NAMESPACE / OCI_BACKUP_BUCKET | backup_namespace / backup_bucket outputs; namespace is not your tenancy display name |
| BACKUP_AGE_RECIPIENT | Public age recipient generated on a separate recovery computer |
| OCI_RELEASE_KEY_ID / OCI_RELEASE_KEY_VERSION / OCI_RELEASE_SIGNING_ENDPOINT | Optional central release packaging, using the distinct release key |

This is a systemd EnvironmentFile. Keep one NAME=value per line; no shell commands or export statements. It is separate from backend.env/research.env and is not passed to application containers. Do not put an age private recovery identity in it.

## 3. Backup service and timer

The service runs shared backup.py --mode public with the operations interpreter, encrypted recipient and scoped OCI Object Storage upload. The timer runs at **01:30 UTC daily** and catches a missed schedule after reboot.

Before enabling:

1. Finish application setup and migrations.
2. Store the offline age identity securely; only its public recipient is on the VM.
3. Confirm bucket, namespace, IAM and backup-directory capacity.
4. Run once:

```sh
sudo systemctl start quantnest-backup.service
sudo systemctl status quantnest-backup.service --no-pager
sudo journalctl -u quantnest-backup.service -n 100 --no-pager
```

A successful oneshot is normally inactive/dead after finishing, with Result=success; it is not a daemon. Confirm archive, checksum and uploaded marker in the backup directory, then download/restore an archive on isolated stores.

```sh
sudo systemctl enable --now quantnest-backup.timer
```

For an immediate pre-upgrade backup, start the service again or use the complete command in [the shared guide](../../shared/scripts/README.md). Local cleanup removes only aged successfully uploaded archives, retaining at least two. OCI lifecycle independently expires remote artifacts; budget storage for both archive and checksum/version retention.

## 4. monitor.py: health and host metrics

The monitor service supplies the required environment and runs:

```text
monitor.py --root /opt/quantnest/current --compartment-ocid <configured compartment> --instance-ocid <configured instance>
```

Use its service for a complete configured invocation:

```sh
sudo systemctl start quantnest-monitor.service
sudo systemctl status quantnest-monitor.service --no-pager
sudo journalctl -u quantnest-monitor.service -n 100 --no-pager
```

It reads host CPU/memory/disk, age of successful backup uploads, Compose/application/worker diagnostics, Redis persistence, and bounded database/outbox/order metrics. It sends content-free metric values to OCI's quantnest namespace under the instanceId dimension. No customer/broker content is a metric label.

The VM principal needs the scoped metric permission. Confirm the Oracle Notifications email subscription. Alarms cover unavailable/missing deployment metrics, low disk/memory, high CPU, Redis persistence, stale execution workers, old outbox/order work and backup uploads older than 30 hours.

If OCI rejects metric delivery, the process fails. The missing-metric alarm reports a stopped monitor or unreachable host; confirm its notification delivery before launch.

After the manual run succeeds:

```sh
sudo systemctl enable --now quantnest-monitor.timer
sudo systemctl list-timers --all
```

The timer starts about two minutes after boot and repeats one minute after each run finishes, so a slow run cannot overlap the next one. It does not replace broker acceptance, source freshness checks or independent external website probes.

## 5. Understand and maintain the units

| File | Role |
| --- | --- |
| quantnest-backup.service | One-shot encrypted backup/upload, up to 30 minutes |
| quantnest-backup.timer | Daily UTC schedule |
| quantnest-monitor.service | One-shot host/deployment metrics, up to three minutes |
| quantnest-monitor.timer | Repeated host metrics schedule |

Units run as quantnest, require Docker, use /opt/quantnest/current and /etc/quantnest/operations.env, and restrict temporary/home access. They do not start duplicate execution or Celery services.

If the reviewed unit definitions change, install those files and reload systemd:

```sh
sudo install -m 644 infra/public/systemd/quantnest-* /etc/systemd/system/
sudo systemctl daemon-reload
```

Then inspect/run the affected service before relying on its timer. Updating operations.env takes effect on the next oneshot invocation. Application env changes still require container recreation.

Do not run the fresh-host bootstrap again to update units on a populated Docker host; it correctly refuses that situation. Use the explicit install/reload commands.

## 6. Dependencies and signing

The operations requirements lock is separate from the application. It installs OCI SDK plus the small verification/configuration dependencies used by central signed release packaging. To update it after an intentional dependency change:

```sh
uv pip compile infra/public/requirements.txt --constraint backend/requirements.lock --python-version 3.12 --universal --generate-hashes --output-file infra/public/requirements.lock
```

Reinstall the reviewed lock into the operations venv during maintenance of host tools. Do not pip-upgrade production operator dependencies without updating the lock. Private customer host tools use their own smaller lock and do not receive the OCI SDK/private signing role.
