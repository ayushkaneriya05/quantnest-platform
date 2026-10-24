# First backup and recovery setup

Do this after the chosen mode works, before you rely on its stored data. This
walkthrough uses your Windows computer as the recovery-key/off-host backup
location and the Ubuntu host for creating encrypted backups. The exact script
arguments and archive format are described in [the runbook](scripts/README.md).

## 1. Understand the three things you must retain

| Item | What it recovers | Where to keep it |
| --- | --- | --- |
| Encrypted `.tar.age` archive and checksum | Database and user media | Off the server; keep more than one recovery point |
| Original env/credential-encryption settings | Connection/configuration and decryption of stored provider credentials | Protected password manager/recovery storage |
| Matching source commit/images | Code and migrations compatible with the backup | Reviewed repository release and recorded image tag |

Redis cache/coordination and live market buffer files are not financial backups.
The archive does not include env files or the private age identity. Keep those
separately; losing the recovery identity makes its encrypted archives unreadable.

## 2. Install age on your Windows operator computer

The Ubuntu host already installed age in [Server setup](SERVER-SETUP.md).
For Windows, use the official [age releases](https://github.com/FiloSottile/age/releases)
and [usage guide](https://github.com/FiloSottile/age#usage). Download the current
Windows archive matching your computer (normally `windows-amd64` for an x64 PC).
Extract it and place `age.exe` and `age-keygen.exe` in `C:\Tools\age`.
If your extraction creates an additional nested `age` directory, use its actual
executable path or move the two files into the directory shown here.

In local PowerShell:

```powershell
& 'C:\Tools\age\age.exe' --version
New-Item -ItemType Directory -Force "$env:USERPROFILE\QuantNestRecovery"
& 'C:\Tools\age\age-keygen.exe' -o "$env:USERPROFILE\QuantNestRecovery\quantnest-public.key"
& 'C:\Tools\age\age-keygen.exe' -y "$env:USERPROFILE\QuantNestRecovery\quantnest-public.key"
```

The first key-generation command creates the private identity and prints its
public recipient; the last prints that recipient again. It begins `age1...`.
The `.key` file contains the private secret. Store a protected recovery copy in
your password manager/encrypted storage and do not send it to the server for
ordinary backups. Generate once; do not overwrite it on each backup.

For Private, repeat with a new `quantnest-private.key` filename and record that
instance's public recipient. The mode name in a filename is for your clarity;
the actual keys must match the archives they decrypt.

## 3. Create the first server backup

Use the stop/backup/start commands in your mode's guide:

- [Public backup](../public/SETUP.md#step-11-finish-recovery-preparation-before-relying-on-the-server)
- [Private backup](../private/SETUP.md#step-11-set-up-backup-and-recovery)

Replace `age1YOUR_PUBLIC_RECIPIENT` with the complete public key from Step 2.
It is safe to supply this public value to `--recipient`; do not pass the private
key contents. Review and settle active work before stopping application services.
For Live, stopping a process is not broker-side position closure.

The script prints a path similar to:

```text
/home/ubuntu/quantnest-backups/quantnest-public-TIMESTAMP.tar.age
```

Record the actual filename. A `.tar.age.sha256` sidecar accompanies it. Both
remain on the server until you copy them. The backup refuses running application
writers so the database and media are captured across the same stopped boundary.

## 4. Copy it off the server to Windows

Open **local PowerShell**, not the SSH terminal. For Public:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\QuantNestBackups\public"
scp -i "$env:USERPROFILE\.ssh\quantnest-server.key" "ubuntu@YOUR_PUBLIC_SERVER_IP:/home/ubuntu/quantnest-backups/quantnest-public-TIMESTAMP.tar.age*" "$env:USERPROFILE\QuantNestBackups\public\"
```

Replace the key path, server IP, username/home path if different, and TIMESTAMP
with the actual backup filename. The final `*` copies both that archive and its
checksum. For Private use its server/key/path, `quantnest-private-...` filename
and a `private` local directory. These are copy commands, not deletion commands.

Confirm integrity on your computer:

```powershell
Get-FileHash "$env:USERPROFILE\QuantNestBackups\public\quantnest-public-TIMESTAMP.tar.age" -Algorithm SHA256
Get-Content "$env:USERPROFILE\QuantNestBackups\public\quantnest-public-TIMESTAMP.tar.age.sha256"
```

Compare the hexadecimal hash values, ignoring letter case. Matching hashes verify
the copy, not that a restore has been proven. Keep an additional protected copy
of your recovery identity; do not keep your only identity on the same disk as your
only archives. Set a reminder for backups before upgrades and after important
changes; no automatic cloud upload/retention job is installed.

## 5. Practice recovery on a separate empty instance

This is a deliberate operator procedure, not an automatic start-of-day command.
Use a separate clean host with the correct mode/release, tools and environments.
Preserve the original credential-encryption key. Do not run deploy first:
deploy would create tables and the restore helper rejects nonempty databases.

1. Build images with that mode's `docker compose ... build` command.
2. Transfer the chosen encrypted archive and the age private identity to a private
   directory on the recovery host for this restore. Restrict its files to the
   operator (`chmod 600`). Do not post the identity in env files or logs.
3. Follow [the exact restore command](scripts/README.md#5-restore-into-an-empty-deployment),
   selecting the matching mode/archive/identity.
4. Restore starts data services and restores the database/media. Application
   services stay stopped. Inspect retained records before deciding to start work.
5. Keep provider/feed/trading services off on a drill instance while the original
   instance is active. Do not let two deployments act on the same real broker
   account or impersonate the same production callback domain.
6. Review commands/checkpoints and actual broker order state before enabling Live
   on a real recovered instance. Then use the normal deploy flow, run diagnostics,
   and check the affected ordinary-user workflows.

The helper handles Timescale pre/post-restore and application table ownership.
It does not replace a nonempty database, infer old formats, restore broker-side
state, or enable trading automatically. Format-2 archives require the older tool
that created them; the current format is 3.

After recovery, retain the private identity in your protected operator storage
and remove any temporary recovery-host copy using your normal secret-handling
procedure. Record the date, source backup and result of the recovery exercise.
