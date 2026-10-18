# Private release and installer tools

There are two roles: **QuantNest packages/signs** software on its authorized central Oracle host; **the customer verifies/installs** it on their own Linux host. Private keys never go to the customer.

Read [the complete Private setup](../README.md) for host preparation, configuration, contract provisioning and activation. Read [shared operations](../../shared/scripts/README.md) for deployment, backups and recovery.

## 1. Files and dependencies

| Tool | Location and purpose |
| --- | --- |
| `release.py create` | Central authorized host; assemble a source/static archive and sign its integrity with the release key in OCI Vault |
| `release.py verify` | Customer/operator; verify ES256 signature, issuer/audience, archive hash/size, signed member list and each file hash |
| `release.py unpack` | Operator; verify then safely extract to a new release directory, without deployment |
| `install.py` | Customer Linux host; verify/unpack, validate config/public keys, build and deploy, then change the current symlink |

Central host dependencies are locked in `infra/public/requirements.lock` and installed by its bootstrap. Customer host verification dependencies are the much smaller `infra/private/requirements.lock`. Application runtime dependencies remain inside the Docker images.

## 2. Build the customer's frontend before signing

In a complete reviewed source checkout, set the customer's actual HTTPS origin and public widget/support values in frontend/.env using private/frontend.env.example. Then:

```sh
npm ci --prefix frontend
npm run build --prefix frontend
```

Confirm frontend/dist contains index.html, routes.caddy, security.caddy and the generated assets. The customer's installation will serve this exact build. The archive contains frontend/dist rather than Node/source dependencies.

The packager includes backend, research_service, infra/shared, infra/private, frontend/dist and selected deployment/runtime documentation, plus root build/runtime metadata. Plans, support labels and builder metadata are served by the installation's backend; no separate JSON exports are packaged. It excludes Public/Development deployment infrastructure, internal business/implementation plans, local secrets, media, caches, virtual environments, logs, scheduler state and private keys. Do not place operator secrets in source files with disguised names.

## 3. Prepare separate release-signing trust

The Public Oracle Terraform provisions a P-256 **release** key separate from the licence key. Put these operator-only inputs in /etc/quantnest/operations.env:

```dotenv
OCI_RELEASE_KEY_ID=the-release-key-ocid
OCI_RELEASE_KEY_VERSION=the-release-key-version-ocid
OCI_RELEASE_SIGNING_ENDPOINT=the-vault-crypto-endpoint
```

Use real values from Terraform/OCI Console. The signing host authenticates with its instance principal. No user API private key is needed in the environment. The licence service continues to use its different OCI_LICENSE_* values in the Public backend environment.

Export the release version's public PEM from OCI and distribute an out-of-band trusted JSON mapping of its version ID to PEM. Distribute the licence version's mapping separately for local lease verification. Keep the private keys centrally in Vault. Record fingerprints and rotation dates.

## 4. Create a signed artifact

Run on the authorized central Oracle host, from the complete reviewed checkout:

```sh
/opt/quantnest/operations/bin/python infra/private/scripts/release.py create --release YOUR_RELEASE --output /secure-delivery/releases --architecture aarch64 --environment /etc/quantnest/operations.env
```

Use the exact reviewed release identifier. Repeat `--architecture x86_64` only if that release was qualified on x86_64 as well. Signing does not perform architecture qualification.

The environment flag reads only the selected signing configuration; it does not rely on a developer's backend/.env, start Django, query PostgreSQL or copy those secrets into the archive. It signs via OCI KMS and writes:

- YOUR_RELEASE.tar.gz: software/static artifact;
- YOUR_RELEASE.jws: ES256 signed hash, size, issuer/audience and manifest.

The issuer is quantnest-releases and audience is quantnest-private. Customers cannot substitute a licence token for a release signature.

Deliver both files plus a separately authenticated trust mapping. Do not include activation tokens or the backup decryption identity in a release archive. For a new key, deliver/verify the new public key before requiring that version. Never remove old verification keys while deployed artifacts/leases still depend on them.

## 5. Verify or unpack without deployment

On the customer/recovery host:

```sh
/opt/quantnest/operations/bin/python infra/private/scripts/release.py verify --archive /secure-delivery/YOUR_RELEASE.tar.gz --signature /secure-delivery/YOUR_RELEASE.jws --trusted-keys /etc/quantnest/trust/release-public-keys.json
```

A verification failure exits nonzero. Do not ignore it or edit the signature/manifest. Obtain a correct artifact/trust mapping from the accepted delivery channel.

To extract only:

```sh
/opt/quantnest/operations/bin/python infra/private/scripts/release.py unpack --archive /secure-delivery/YOUR_RELEASE.tar.gz --signature /secure-delivery/YOUR_RELEASE.jws --trusted-keys /etc/quantnest/trust/release-public-keys.json --releases /opt/quantnest/releases
```

This refuses an existing destination. It does not start containers, import a licence or change the current symlink. The installer can reuse that extraction after rechecking its complete signed content; it never blindly overwrites application files.

## 6. Install or upgrade

The configuration directory must contain:

```text
/etc/quantnest/private/
  backend.env                 owner-only, mode 600
  research.env                owner-only, mode 600
  license/public-keys.json    nonempty P-256 public mapping; not group/world writable
```

Set QUANTNEST_RELEASE to the signed artifact identifier. Never copy the central licence/release private key onto the customer host.

First installation:

```sh
/opt/quantnest/operations/bin/python infra/private/scripts/install.py --archive /secure-delivery/YOUR_RELEASE.tar.gz --signature /secure-delivery/YOUR_RELEASE.jws --trusted-keys /etc/quantnest/trust/release-public-keys.json --releases /opt/quantnest/releases --configuration /etc/quantnest/private --current /opt/quantnest/current
```

Upgrade: use the next signed artifact and also supply `--backup-directory /mnt/quantnest-data/backups --backup-recipient age1YOUR_PUBLIC_RECIPIENT`. Repeat the recipient flag if needed.

Flags:

| Flag | Meaning |
| --- | --- |
| --archive / --signature | Matching delivered files |
| --trusted-keys | Independently authenticated release public-key mapping |
| --releases | Parent of immutable per-release directories |
| --configuration | Protected customer environment/licence-public-key directory |
| --current | Stable symlink; a regular directory is refused |
| --backup-directory | Encrypted local recovery artifacts; required for upgrades |
| --backup-recipient | Public age recipient; required for upgrades |

The installer uses project quantnest-private consistently so an update keeps the same database/Redis/media volumes. It validates permissions and public key format/curve, rejects unsupported host architecture and builds before the service replacement. The shared deploy flow stops application services, backs up on upgrade, runs migrations and starts the services. It changes current only after startup succeeds.

Builds, configuration checks and service replacement use the shared deploy function once. On an upgrade, its backup callback runs after application services stop and before migrations. A failed preflight/build/check leaves the running application untouched; a failed backup leaves application services stopped without applying migrations.

Unlike the unpack-only command, installer retry may reuse an existing extraction **only after** validating its exact manifest, source/static member list, paths and checksums. This permits retry after a transient build failure without blindly overwriting files. Configuration is then recopied from the protected directory; do not edit signed application files in place. An already active release is refused by the installer: use the shared deploy command for configuration changes. Run one installer/deploy operation at a time.

The installer does not roll schema changes back. If a deployment fails after migrations, retaining the old symlink does not imply the old schema was restored. Diagnose and use matching isolated recovery if needed. Saved session states persist, and execution services can recover sessions left Running.

## 7. After installation

1. Create/enrol the staff administrator as described in the Private guide.
2. Refresh/import the signed installation licence and verify the supported release, validity and Live qualification.
3. Run diagnostics and inspect source/broker reconciliation and session states.
4. Deploy/resume qualified sessions through the workspace as needed. Saved Running sessions can recover when services start.
5. Verify encrypted recovery and monitoring on the customer's accepted infrastructure.

The installer starts the configured runtime, including broker observations. It does not create a strategy session or authorize a trade. Contract expiry blocks new user-initiated licensed work. Already running strategies have no background commercial-expiry gate; stopping/pausing them and handling financial obligations remain explicit.
