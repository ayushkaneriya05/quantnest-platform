# Deployment and recovery scripts

These are operator tools, not running application services. Use Python 3.12 and Docker Compose v2. Run commands from the repository/release root. Every application operation selects **one** mode: `development`, `public` or `private`.

## 1. Before using a script

1. Follow the selected mode's README and create its `backend.env` and `research.env` files.
2. Docker must be running, and your operator must have permission to access it.
3. On Linux restrict environment files to their operator: `chmod 600 infra/<mode>/*.env`. Docker group membership grants administrative power on that host.
4. Use a reviewed release. Keep configuration, signing/encryption keys and backup identities outside source control.
5. Before an upgrade, use the workspace to stop or pause strategies and settle open orders/positions. The deploy script stops application services while applying the update.

Production scripts run on the Linux host, **outside** the API container. The container runs `manage.py` commands on their behalf. `--root .` means the current directory is the complete release; it does not mean `backend/`.

Normal operations use the selected mode's project name, quantnest-development/public/private. The helpers reject an inherited COMPOSE_PROJECT_NAME from another mode, protecting against accidental reuse of its volumes. Leave that variable unset. Helpers pass the selected project name explicitly; recovery uses its own --project argument.

| Script | When to use it | Dependencies |
| --- | --- | --- |
| `compose_config.py` | Imported by the other scripts; not a command to run | Python standard library |
| `deploy.py` | First installation or reviewed application upgrade | Python, Docker/Compose |
| `diagnostics.py` | After startup, after upgrades, or when investigating an incident | Python, Docker/Compose |
| `backup.py` | Encrypted backups; optionally upload Public backups to OCI | Python, Docker/Compose, `age`; OCI SDK only for upload |
| `restore.py` | Disaster recovery into a new isolated state-only project | Python, Docker/Compose, `age`, matching backend image |

`compose_config.py` owns valid mode/profile names, resolves the selected mode's file paths, fixes its project identity and privately reads effective Compose configuration. Deploy and diagnostics derive service names from that configuration rather than maintaining separate service lists. The helper's standard-library code does not require Django or a host application virtual environment.

## 2. Initialize or upgrade

Examples for each mode:

```sh
python3 infra/shared/scripts/deploy.py --root . --mode development --build
python3 infra/shared/scripts/deploy.py --root . --mode public --build
python3 infra/shared/scripts/deploy.py --root . --mode private --build
```

Run **only the line for your mode**. `--build` rebuilds the backend and research images. Omit it only when those exact release images have already been built or loaded.

The sequence is:

1. Resolve Compose privately. Validate Live scope/broker-events consistency, matching research tokens, enabled AI credentials, and required TLS/frontend/licence files.
2. Build images and run Django configuration checks before stopping the application. Production configuration warnings fail the deployment at this stage.
3. Start/check the database and Redis services.
4. Stop application producers, scheduler, frontend/ingress and workers. Database and Redis services remain available.
5. For a Private installer upgrade, create the required encrypted backup of the stopped application state.
6. Run migrations, configure the Django Site from FRONTEND_URL, and collect static assets.
7. Start the services and wait up to 180 seconds for configured health checks.

A failure exits nonzero; it does not silently undo schema changes. Read the reported error and use the recovery procedure if necessary. A failure after services are stopped leaves them stopped until the update/recovery is completed.

Development supports optional profiles:

```sh
python3 infra/shared/scripts/deploy.py --root . --mode development --build --profile market-data --profile research
```

`--profile live` starts broker observations only for intentionally configured Development Live execution. Set `EXECUTION_ENABLED_SCOPES=paper,live` and the execution app credentials first. Live sends real broker orders even though the deployment is called Development.

After startup, run diagnostics for the selected mode and inspect your sessions.
Deploying preserves saved session statuses. A session left Running can recover
when execution services restart; stop or pause it in the workspace before an
update if it must remain inactive. Resume or redeploy through the normal UI.

## 3. Diagnose startup and services

```sh
python3 infra/shared/scripts/diagnostics.py --root . --mode development
python3 infra/shared/scripts/diagnostics.py --root . --mode public
python3 infra/shared/scripts/diagnostics.py --root . --mode private
```

The report contains disk free space, Compose validity, service state/health, missing required services, application configuration checks and fresh execution-worker heartbeats. Exit code `0` means these checks passed. It does not certify source entitlement, broker fills, AI output, email delivery, payment settlement or customer capacity.

Pass the same Development `--profile` flags when those services are required. `ps --all` includes exited containers so a dead process cannot disappear from the report.

For a failing Public report:

```sh
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml ps --all
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml logs --tail 100 api execution orders outbox background compute research
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py check --deploy --fail-level WARNING
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py deployment_health --require-mode public --workers
```

Use the corresponding mode paths and `--require-mode` in the other modes. Do not publish raw environment output or OAuth callback query strings in support messages. `docker compose config --quiet` checks configuration without displaying secret values; plain `config` displays resolved secrets.

## 4. Prepare backup encryption once

On a separate trusted recovery computer install [age](https://github.com/FiloSottile/age#installation), then run:

```sh
age-keygen -o quantnest-recovery.key
```

The command prints the **public recipient** (`age1...`). Put that public value on the server. Store `quantnest-recovery.key` offline in at least two protected locations; do not store your only decryption identity on the VM being backed up. Without the identity an encrypted backup cannot be restored.

Backup requires available disk for temporary unencrypted dump/media/RDB files, the assembled archive and the encrypted result. Temporary files are restricted to the operator and removed when the command exits normally. Keep the backup directory on the protected data volume.

## 5. Run a backup

Local encryption works for all modes. Here is a Private example:

```sh
python3 infra/shared/scripts/backup.py --root . --mode private --output /mnt/quantnest-data/backups --recipient age1YOUR_PUBLIC_RECIPIENT
```

Replace the recipient with your actual public value. Select `--mode public` or `--mode development` with the respective deployment root to back up those modes. Repeat `--recipient` to encrypt for more than one recovery identity.

A rejected Redis snapshot or failed encryption exits nonzero. The encrypted archive is published only after encryption succeeds. Filenames include UTC microseconds to separate independently started backups.

The archive contains a PostgreSQL custom dump, private media, durable general/runtime Redis RDB snapshots and a checksum manifest. It does not contain environment files, encryption keys, TLS keys, frontend builds, local market buffers or the offline recovery identity. Keep those configuration/release records separately. Analytical caches and runtime files rebuild from authoritative data; they are not backup artifacts.

The snapshots are sequential, not one distributed transaction. Online backups can have a recovery gap between the database and Redis captures. Recovery stays in an isolated data-only project; reconcile database intents/outbox records and, for Live, broker activity since the backup before starting the application.

Public optional OCI upload, run on the authorized Oracle VM with the operations interpreter:

```sh
/opt/quantnest/operations/bin/python infra/shared/scripts/backup.py --root . --mode public --output /mnt/quantnest-data/backups --recipient age1YOUR_PUBLIC_RECIPIENT --namespace YOUR_OCI_NAMESPACE --bucket quantnest-encrypted-backups
```

`--namespace` and `--bucket` must be supplied together. The host's instance principal needs scoped Object Storage access. The uploaded marker is written only after both archive and checksum uploads succeed. `--local-retention-days` defaults to three: cleanup removes only older confirmed-uploaded backups, retaining at least the two newest local archives. Unuploaded backups remain local; investigate failed uploads before they fill disk.

Verify the `.tar.age`, `.sha256` and (for OCI) `.uploaded` files. Copy/download the archive and checksum to the recovery computer. Keep archives from different modes separate: restore checks the recorded mode.

## 6. Restore without touching the active installation

Use a complete compatible release directory and its mode environment files. Preserve the original credential encryption key and signing key where existing encrypted credentials/signed records require them. Changing a database password for the **new** recovery database is possible; changing the credential encryption key loses access to encrypted application secrets.

Ensure Docker has the matching backend image (or build it before recovery). Choose an unused recovery project name, then run on Linux:

```sh
python3 infra/shared/scripts/restore.py --root . --mode private --backup /secure/backups/quantnest-TIMESTAMP.tar.age --identity /secure/quantnest-recovery.key --project quantnest-recovery-review-20261015 --confirm-empty-database
```

The same command works in PowerShell with `python` instead of `python3` and local file paths. No recovery environment variable is needed.

Use the archive's actual filename and matching mode. `--confirm-empty-database` does not bypass the empty-store checks. The script renders a temporary protected Compose configuration with:

- only PostgreSQL, Redis and an API utility container;
- no published host ports;
- separate project volumes/networks and no production subnet;
- no feed, execution, order, broker, frontend, ingress or scheduler service.

It decrypts and checks the manifest, uses TimescaleDB pre/post restore hooks, restores ownership to the non-superuser application role and rebuilds durable Redis AOF from RDB. The temporary configuration containing resolved secrets is then deleted. Only recovered volumes and data services remain running for inspection; the API, scheduler and execution workers are not started.

Recovery refuses writable host bind mounts, external/shared networks and external/custom-driver volumes. Those need an explicitly reviewed provider/storage recovery procedure. Standard mode stacks use local named volumes; generated recovery drops resolved resource names so it cannot accidentally reuse a production volume/network.

Inspect them without starting the normal stack:

```sh
docker ps --all --filter label=com.docker.compose.project=quantnest-recovery-review-20261015
docker volume ls --filter label=com.docker.compose.project=quantnest-recovery-review-20261015
```

**Do not run a normal mode `up` command with the recovery project name**: it would introduce application producers and the mode's regular ports/subnet. The shared helpers reject a foreign COMPOSE_PROJECT_NAME. The restore script passes its protected, temporary configuration explicitly and deletes it afterwards. Promotion requires a separate reviewed migration/cutover on the destination host. Reconcile broker orders/fills, licence revision/renewal, pending intents, payment events and records created after the backup. Account-wide broker totals must not overwrite individual strategy positions.

## 7. Recover an earlier release

```sh
python3 infra/shared/scripts/restore.py --root /opt/quantnest/releases/PREVIOUS_RELEASE --mode private --backup /secure/backups/quantnest-TIMESTAMP.tar.age --identity /secure/quantnest-recovery.key --project quantnest-recovery-previous-release --confirm-empty-database
```

This is restore with an explicitly selected previous release. It does not reverse Django migrations against active financial data and does not switch ingress or start trading. An old backup may omit later fills/payments/contract revisions; reconcile them before a cutover. Recover the old **matching** schema/release together.

## 8. Configuration changes and scaling

Changing a file does not change running containers. `restart` also does not reload Compose environment values; a reviewed deployment recreates affected containers. Back up before changing encryption keys, schema, topology or resource allocation.

Scale on measured CPU, RSS, worker queue age, PostgreSQL locks/connections, Redis memory/persistence and receipt-to-order latency. Keep execution/order partition and node settings consistent. When changing topology, stop financial producers, run `python manage.py rebuild_execution_assignments` in an API utility container, then restart the complete topology. Calculation child count is `EXECUTION_WORKERS × CALCULATION_WORKERS` per node. Do not use `docker compose --scale execution`: this stack has one local runtime directory and a fixed notification address and requires explicit ownership/topology changes for another execution node.

See [shared architecture](../README.md) and each mode's capacity/launch requirements before raising admission limits.
