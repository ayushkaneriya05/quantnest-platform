# Deployment, diagnostics, backup and restore

Run these Python 3.12 scripts from the repository root. They are one-shot operator
tools, not extra servers. Docker runs application processes. All helpers select
one of `development`, `public` or `private`, and preserve its project/volume name.

## 1. Common arguments and files

| Argument/file | Meaning |
| --- | --- |
| `--root .` | Repository/release root, containing `backend`, `frontend`, `research_service` and `infra`. |
| `--mode <mode>` | Selects exactly one mode's `compose.yaml` and `backend.env`. |
| `--profile market-data`, `--profile research`, `--profile live` | Development only; repeat for each provider service needed. Production has a fixed complete topology. |
| `backend.env` | Both Compose interpolation inputs and backend runtime settings. Never print resolved `docker compose config` to a shared log. |
| `research.env` | AI provider key/token; needed as a file even when Development's research profile is off. |
| `frontend.env` | Development public Vite inputs. Public has a separate Pages build configuration; Private builds from backend public URL/widget inputs. |

The mode must match the data you intend to operate on. Unset stale
`COMPOSE_PROJECT_NAME`/`COMPOSE_PROFILES` and shell exports from another mode.
Shell environment values override `--env-file` interpolation. Helpers explicitly
use `quantnest-<mode>`; a conflicting `COMPOSE_PROJECT_NAME` is rejected.

## 2. Initialize or upgrade

```sh
python3 infra/shared/scripts/deploy.py --root . --mode development --build
python3 infra/shared/scripts/deploy.py --root . --mode public --build
python3 infra/shared/scripts/deploy.py --root . --mode private --build
```

Run only the command for your selected mode. `--build` builds that mode's backend,
research and, for Private, frontend images. Omit it only when the matching tagged
images are already installed. No package installation runs inside production API
containers at startup.

Deployment performs these actions in order:

1. Resolve the effective Compose model without printing secrets. Reject a Live
   scope without broker-events, or broker-events without Live scope.
2. If research is enabled, verify that its key is configured and its token matches
   Django's token. This is a configuration check, not a provider API request.
3. Build requested images. A build failure happens before stopping the old app.
4. Run Django checks. Production uses `check --deploy --fail-level WARNING`.
5. Start/wait for PostgreSQL, Redis and research-cache Redis.
6. Stop all application services, including previously selected Development profiles.
7. Run `migrate --noinput`, `setup_timescale`, `configure_site` and
   `collectstatic --noinput` as one-shot API-image commands.
8. Start selected services with `up -d --wait --wait-timeout 180 --remove-orphans`.

`--rm` deletes a completed one-shot container, not its named volumes. `--no-deps`
prevents management commands from implicitly starting the API or trading services.
`--wait` is a readiness wait where healthchecks exist, and a running-state check
for other services. Readiness does not prove broker/provider connectivity.

Before an upgrade, stop/settle active strategy work through the workspace, take
a backup, retain the old release tag/code and then run deployment. If a migration
or Timescale setup fails, the helper stops there with applications stopped. Fix
the reported issue and rerun; do not skip a failed schema operation.

### Development profiles

```sh
python3 infra/shared/scripts/deploy.py --root . --mode development --build --profile market-data
python3 infra/shared/scripts/deploy.py --root . --mode development --build --profile market-data --profile research
```

For intentional Live development, set `EXECUTION_ENABLED_SCOPES=paper,live` in
Development's backend.env and also add `--profile live`. It uses real broker access.
One execution container still handles Paper, Live and Terminal together.

## 3. Diagnostics and everyday commands

```sh
python3 infra/shared/scripts/diagnostics.py --root . --mode public
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml ps
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml logs --tail=100 execution
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py deployment_health --require-mode public --workers
```

Replace both `public` path segments and the mode value for another mode. Pass your
Development profiles to diagnostics so it knows which optional services to expect.

Diagnostics reports free disk bytes, configuration validity, missing/unhealthy
containers, Django checks and execution-worker readiness. Nonzero exit means a
required check failed. It does not publish metrics to an external service.
The plain `ps` and bounded `logs` commands help identify which process failed.
The management command checks database/runtime Redis and the reported worker count.

To stop all application processes while retaining data services:

```sh
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml stop api feed execution background compute beat research ingress
```

For Private add `broker-events`. For Development omit `ingress`, add `frontend`,
and add any active `feed`, `research`, `broker-events` services using the same
`--profile` flags. `stop` preserves containers and volumes. Do not use `down -v`
as routine maintenance. Reuse the deployment helper to start the reviewed stack.

## 4. Encrypted local backup

For first-time Windows setup, file copying and a beginner recovery drill, follow
[the recovery setup walkthrough](../RECOVERY-SETUP.md). The steps below are the
command/format reference.

Install `age` and generate a recovery identity once, on a protected operator machine:

```sh
age-keygen -o /secure/quantnest-backup.key
age-keygen -y /secure/quantnest-backup.key
```

The first command creates the private decryption key and prints its public recipient.
The second prints the public recipient again. Keep the private key away from the
deployment host; the backup command needs only its `age1...` public value.

After stopping application services, with PostgreSQL still running:

```sh
python3 infra/shared/scripts/backup.py --root . --mode public --output /secure/backups --recipient age1YOUR_PUBLIC_RECIPIENT
```

| Argument | Meaning |
| --- | --- |
| `--output` | Local destination directory; make sure there is room for temporary plaintext and final encrypted files. |
| `--recipient` | Public encryption key. Repeat to allow another recovery owner. No private key is used for encryption. |

The helper refuses to run while application services are running. It takes a
custom-format `pg_dump`, archives media from its named volume, hashes both files
into a format-3 manifest, creates a tar archive, encrypts it with age and atomically
moves the completed archive to `quantnest-<mode>-<UTC timestamp>.tar.age`.
A `.sha256` sidecar contains the encrypted archive's hash. Plaintext temporary
files are removed on normal completion/error; they must not be on shared storage.

Copy the encrypted archive and checksum off-host, for example with your existing
SSH/SCP backup procedure. No cloud credentials, automatic deletion or upload SDK
is included. Verify recovery regularly using a separate empty deployment. A backup
stored only on the same failed disk is not a recovery copy.

Retain the corresponding code/image tag, protected environments, Django key and
credential encryption keys separately. They are deliberately not bundled into
the database/media archive. Redis queues/cache/leases and market buffers are not
financial backups and are not restored by this tool.

## 5. Restore into an empty deployment

Use a separate clean server or empty mode/project volumes. Configure the same
mode's environment, preserving the original credential encryption key, and build
the backend image without running `deploy.py` first (deployment would create tables):

```sh
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml build
python3 infra/shared/scripts/restore.py --root . --mode public --backup /secure/backups/quantnest-public-TIMESTAMP.tar.age --identity /secure/quantnest-backup.key
```

| Argument | Meaning |
| --- | --- |
| `--backup` | Existing format-3 encrypted archive matching the selected mode. |
| `--identity` | Existing age private recovery key; never put its contents in environment files or command arguments. |

Restore refuses running applications. It decrypts in a private temporary directory,
checks allowed archive members, mode, manifest and hashes, then starts data services.
It refuses any existing public-schema tables rather than replacing a working DB.
The Timescale pre/post restore hooks preserve extension metadata; application table
ownership is reassigned to `DB_USER`. Media paths are checked before extraction.
Failures exit nonzero and leave applications stopped for inspection. A partially
restored database is not retried over itself; use a new empty recovery deployment.

After restore, review recovered execution commands/checkpoints and reconcile real
broker orders before enabling Live execution. Once reviewed, run the normal deploy
helper to apply any later migrations, configure Site/static assets and start services.
Recovery does not start execution automatically and does not restore old provider
leases. Supply the backed-up encryption keys to decrypt stored broker credentials.

Format-2 backups used the former Redis snapshot machinery. Restore them with the
matching older release's tools, then upgrade. This tool does not guess formats.

## 6. Internal methods and responsibilities

| Method/module | Why it exists |
| --- | --- |
| `compose_command()` | Builds one explicit argument list with mode/project/env-file/profile paths; no shell-built commands. |
| `compose_configuration()` | Reads Compose JSON privately so consumers see the same effective topology. |
| `running_application_services()` | Prevents backup/restore while API, workers or provider services can change state. |
| `deploy()` | Owns the stopped-service upgrade sequence. It does not start hidden native processes. |
| `service_status()` | Compares configured services against Docker's running/health state. |
| `backup.create()` | Owns the consistent database/media snapshot and encrypted archive. |
| `backup.file_hash()` | Streamed SHA-256 for archive/manifest integrity checks. |
| `restore.safe_extract()` | Rejects unexpected file types and paths outside the private recovery directory. |
| `restore.restore()` | Empty-database validation, Timescale restore, ownership and media recovery. |

Python script arguments use `Path` for filesystem values and strings for mode/profile
names. Docker receives argument arrays; quoted shell snippets are limited to commands
that expand container-owned PostgreSQL environment variables.
