"""Encrypted, streamed PostgreSQL/media backup with optional scoped OCI upload."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time
from compose_config import DEPLOYMENT_MODES, compose_command


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def compose(root, *arguments, mode="private", capture=False):
    command = compose_command(root, mode, *arguments)
    return subprocess.run(command, cwd=root, check=True, stdout=subprocess.PIPE if capture else None)


def encrypt(source, destination, recipients):
    command = ["age", "--encrypt", "--output", str(destination)]
    for recipient in recipients:
        command += ["--recipient", recipient]
    with source.open("rb") as stream:
        subprocess.run(command, stdin=stream, check=True)


def create(root, directory, recipients, mode="private"):
    if not shutil.which("age"):
        raise RuntimeError("Install age and configure an offline-held recovery identity")
    directory.mkdir(parents=True, exist_ok=True)
    identity = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = directory / f"quantnest-{identity}.tar.age"
    if destination.exists():
        raise FileExistsError("A backup already exists for this timestamp; wait a second before starting another")
    with tempfile.TemporaryDirectory(prefix="qn-backup-", dir=directory) as temporary:
        folder = Path(temporary)
        os.chmod(folder, 0o700)
        dump = folder / "database.dump"
        command = compose_command(root, mode, "exec", "-T", "postgres",
                   "sh", "-c", 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-privileges')
        with dump.open("wb") as stream:
            subprocess.run(command, cwd=root, stdout=stream, check=True)
        media = folder / "media.tar"
        with media.open("wb") as stream:
            subprocess.run(compose_command(root, mode, "run", "--rm", "--no-deps", "-T", "api",
                            "tar", "-C", "/opt/quantnest/backend/media", "-cf", "-", "."), cwd=root, stdout=stream, check=True)
        redis_files = []
        for service in ("redis", "redis-runtime"):
            reply = compose(root, "exec", "-T", service, "redis-cli", "BGSAVE", mode=mode, capture=True).stdout
            if b"Background saving started" not in reply and b"already in progress" not in reply:
                raise RuntimeError("Redis refused the backup snapshot")
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                info = compose(root, "exec", "-T", service, "redis-cli", "INFO", "persistence", mode=mode, capture=True).stdout
                if b"rdb_bgsave_in_progress:0" in info:
                    if b"rdb_last_bgsave_status:ok" not in info:
                        raise RuntimeError("Redis snapshot failed")
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError("Redis snapshot exceeded its deadline")
            path = folder/(service+".rdb")
            with path.open("wb") as stream:
                subprocess.run(compose_command(root, mode, "exec", "-T", service, "cat", "/data/dump.rdb"), cwd=root, stdout=stream, check=True)
            redis_files.append(path)
        # Highest accepted revisions and installation identity are in the database dump.
        # Redis projections/queues are recovered from durable DB intents and outbox records.
        manifest = {"format": 2, "mode": mode, "created_at": identity, "files": {p.name: file_hash(p) for p in (dump, media, *redis_files)}}
        (folder/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        archive = folder / "archive.tar"
        with tarfile.open(archive, "w") as stream:
            for path in (dump, media, *redis_files, folder/"manifest.json"):
                stream.add(path, arcname=path.name)
        partial = folder / "encrypted.tar.age"
        try:
            encrypt(archive, partial, recipients)
            os.replace(partial, destination)
        finally:
            partial.unlink(missing_ok=True)
    os.chmod(destination, 0o600)
    checksum = file_hash(destination)
    destination.with_suffix(destination.suffix+".sha256").write_text(checksum+"\n", encoding="ascii")
    return destination


def upload(path, namespace, bucket):
    import oci
    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    client = oci.object_storage.ObjectStorageClient({}, signer=signer, timeout=(5, 120))
    with path.open("rb") as stream:
        client.put_object(namespace, bucket, path.name, stream, content_type="application/octet-stream", if_none_match="*")
    with path.with_suffix(path.suffix+".sha256").open("rb") as stream:
        client.put_object(namespace, bucket, path.name+".sha256", stream, if_none_match="*")
    path.with_suffix(path.suffix+".uploaded").write_text(datetime.now(timezone.utc).isoformat(), encoding="ascii")


def prune_uploaded(directory, days):
    """Only prune our confirmed-uploaded backups; failed uploads stay recoverable."""
    import re
    paths = sorted(directory.glob("quantnest-*.tar.age"), reverse=True)
    cutoff = time.time() - days * 86400
    for path in paths[2:]:
        if not re.fullmatch(r"quantnest-\d{8}T\d{6,12}Z\.tar\.age", path.name) or path.is_symlink():
            continue
        if path.stat().st_mtime >= cutoff or not path.with_suffix(path.suffix+".uploaded").is_file():
            continue
        for target in (path, path.with_suffix(path.suffix+".sha256"), path.with_suffix(path.suffix+".uploaded")):
            if target.resolve().parent != directory.resolve():
                raise ValueError("Backup cleanup escaped its configured directory")
            target.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--mode", choices=DEPLOYMENT_MODES, required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--recipient", action="append", required=True)
    parser.add_argument("--namespace")
    parser.add_argument("--bucket")
    parser.add_argument("--local-retention-days", type=int, default=3)
    args = parser.parse_args()
    if bool(args.bucket) != bool(args.namespace):
        parser.error("Provide namespace and bucket together")
    if args.bucket and args.mode != "public":
        parser.error("OCI upload belongs to public mode; customer backups use their own storage workflow")
    if args.local_retention_days < 1:
        parser.error("Local retention must be at least one day")
    path = create(args.root.resolve(), args.output.resolve(), args.recipient, mode=args.mode)
    if args.bucket:
        upload(path, args.namespace, args.bucket)
        prune_uploaded(args.output.resolve(), args.local_retention_days)
    print(json.dumps({"backup": str(path), "encrypted_bytes": path.stat().st_size, "uploaded": bool(args.bucket)}))


if __name__ == "__main__":
    main()
