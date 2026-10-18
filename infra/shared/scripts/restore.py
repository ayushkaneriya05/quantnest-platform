"""Restore only into an empty database in an isolated Compose project."""
import argparse
import json
import os
import re
import uuid
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time
from contextlib import contextmanager
from backup import file_hash
from compose_config import DEPLOYMENT_MODES, compose_configuration


@contextmanager
def recovery_stack(root, mode, project):
    """Render an isolated state-only stack, without origin ports or fixed subnets."""
    config = compose_configuration(root, mode)
    config["name"] = project
    retained = {"postgres", "redis", "redis-runtime", "redis-cache", "api"}
    config["services"] = {name: service for name, service in config["services"].items() if name in retained}
    used_volumes = {mount["source"] for service in config["services"].values()
                    for mount in service.get("volumes", []) if mount["type"] == "volume"}
    config["volumes"] = {name: volume for name, volume in config.get("volumes", {}).items() if name in used_volumes}
    for service in config["services"].values():
        service.pop("ports", None)
        if any(mount.get("type") == "bind" and not mount.get("read_only") for mount in service.get("volumes", [])):
            raise ValueError("Recovery refuses writable host bind mounts; use isolated local named volumes")
        for key, value in service.get("environment", {}).items():
            if isinstance(value, str):
                service["environment"][key] = value.replace("$", "$$")
        for network in service.get("networks", {}).values():
            if network:
                network.pop("ipv4_address", None)
    for network in config.get("networks", {}).values():
        if network.get("external"):
            raise ValueError("Recovery refuses shared external networks")
        network.pop("name", None)
        network.pop("ipam", None)
    for volume in config.get("volumes", {}).values():
        if volume.get("external") or volume.get("driver_opts") or volume.get("driver", "local") != "local":
            raise ValueError("Recovery requires isolated local Docker volumes")
        volume.pop("name", None)
    # Commands/health checks already retain Compose's $$ shell-variable escapes;
    # only resolved environment values need escaping for a second rendering.
    config = {key: value for key, value in config.items() if not key.startswith("x-")}
    encoded = json.dumps(config)
    with tempfile.TemporaryDirectory(prefix="qn-recovery-config-") as temporary:
        folder = Path(temporary)
        os.chmod(folder, 0o700)
        path = folder / "compose.json"
        path.write_text(encoded, encoding="utf-8")
        os.chmod(path, 0o600)
        yield ["docker", "compose", "--project-name", project, "-f", str(path)]


def redis_ready(name, *, durable=False):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        result = subprocess.run(["docker", "exec", name, "redis-cli", "INFO", "persistence"], capture_output=True)
        info = result.stdout
        if result.returncode == 0 and b"loading:0" in info:
            if not durable or (b"aof_enabled:1" in info and b"aof_rewrite_in_progress:0" in info and b"aof_rewrite_scheduled:0" in info and b"aof_last_bgrewrite_status:ok" in info):
                return
        time.sleep(.5)
    raise RuntimeError("Redis recovery did not reach its durable ready state")


def safe_extract(archive, folder):
    with tarfile.open(archive) as stream:
        for member in stream.getmembers():
            destination = (folder/member.name).resolve()
            if not destination.is_relative_to(folder.resolve()) or not member.isfile():
                raise ValueError("Backup contains an unsafe member")
        stream.extractall(folder, filter="data")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--mode", choices=DEPLOYMENT_MODES, required=True)
    parser.add_argument("--backup", required=True, type=Path)
    parser.add_argument("--identity", required=True, type=Path)
    parser.add_argument("--project", required=True, help="New isolated project name: quantnest-recovery-<unique-name>")
    parser.add_argument("--confirm-empty-database", action="store_true", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    project = args.project
    if not re.fullmatch(r"quantnest-recovery-[a-z0-9][a-z0-9_-]*", project):
        raise ValueError("Use --project quantnest-recovery-<unique-name>; restoration must use isolated volumes")
    with recovery_stack(root, args.mode, project) as command:
        restore(args, root, project, command)


def restore(args, root, project, command):
    def compose(*values, capture=False, **kwargs):
        return subprocess.run([*command, *values], cwd=root, check=True,
            stdout=subprocess.PIPE if capture else None, **kwargs)

    compose("up", "-d", "--wait", "postgres", "redis", "redis-runtime", "redis-cache")
    count = compose("exec", "-T", "postgres", "sh", "-c", 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema=\'public\' AND table_name NOT LIKE \'_timescaledb%\'"', capture=True)
    if int(count.stdout.strip() or b"0"):
        raise RuntimeError("Refusing to overwrite a non-empty database. Use a separate restore project first.")
    for service in ("redis", "redis-runtime"):
        info = compose("exec", "-T", service, "redis-cli", "INFO", "keyspace", capture=True).stdout
        if any(line.startswith(b"db") for line in info.splitlines()):
            raise RuntimeError("Restore requires empty isolated Redis stores")
    with tempfile.TemporaryDirectory(prefix="qn-restore-", dir=root) as temporary:
        folder = Path(temporary)
        os.chmod(folder, 0o700)
        archive = folder/"archive.tar"
        subprocess.run(["age", "--decrypt", "--identity", str(args.identity), "--output", str(archive), str(args.backup)], check=True)
        safe_extract(archive, folder)
        manifest = json.loads((folder/"manifest.json").read_text())
        if manifest.get("format") != 2 or manifest.get("mode") != args.mode or set(manifest.get("files", {})) != {"database.dump", "media.tar", "redis.rdb", "redis-runtime.rdb"}:
            raise ValueError("Backup format or deployment mode does not match the recovery stack")
        for name, checksum in manifest["files"].items():
            if file_hash(folder/name) != checksum:
                raise ValueError("Backup integrity verification failed")
        compose("exec", "-T", "postgres", "sh", "-c", 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT timescaledb_pre_restore()"')
        with (folder/"database.dump").open("rb") as stream:
            compose("exec", "-T", "postgres", "sh", "-c",
                    'exec pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges --exit-on-error', stdin=stream)
        # Restoring as the bootstrap administrator preserves Timescale catalogs;
        # application tables must then belong to the non-superuser app role.
        ownership_sql = """
SELECT timescaledb_post_restore();
SELECT format('ALTER %s %I.%I OWNER TO %I',
  CASE c.relkind WHEN 'S' THEN 'SEQUENCE' WHEN 'v' THEN 'VIEW' WHEN 'm' THEN 'MATERIALIZED VIEW' ELSE 'TABLE' END,
  n.nspname, c.relname, :'app_user')
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r','p','S','v','m')
  AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.deptype = 'e')
ORDER BY CASE WHEN c.relkind = 'S' THEN 1 ELSE 0 END
\\gexec
"""
        compose("exec", "-T", "postgres", "sh", "-c",
            'exec psql -v ON_ERROR_STOP=1 --set=app_user="$DB_USER" -U "$POSTGRES_USER" -d "$POSTGRES_DB"', input=ownership_sql.encode())
        with tarfile.open(folder/"media.tar") as stream:
            if any(not (folder/member.name).resolve().is_relative_to(folder.resolve()) or not (member.isfile() or member.isdir()) for member in stream.getmembers()):
                raise ValueError("Unsafe restored file path")
        with (folder/"media.tar").open("rb") as stream:
            compose("run", "--rm", "--no-deps", "-T", "api", "tar", "-C", "/opt/quantnest/backend/media", "-xf", "-", stdin=stream)
        for service in ("redis", "redis-runtime"):
            info = compose("exec", "-T", service, "redis-cli", "INFO", "keyspace", capture=True).stdout
            if any(line.startswith(b"db") for line in info.splitlines()):
                raise RuntimeError("Restore requires empty isolated Redis stores")
            compose("stop", service)
            with (folder/(service+".rdb")).open("rb") as stream:
                compose("run", "--rm", "--no-deps", "--user", "root", "-T", service, "sh", "-c",
                    "test -d /data && rm -rf /data/appendonlydir && cat > /data/dump.rdb && chown redis:redis /data/dump.rdb", stdin=stream)
            # Load the RDB with AOF off once, then turn AOF on to recreate its base.
            container = project + "-" + service + "-" + uuid.uuid4().hex[:8]
            compose("run", "--rm", "--no-deps", "--detach", "--name", container, service, "sh", "-c", 'exec redis-server --dir /data --appendonly no --requirepass "$REDISCLI_AUTH"')
            try:
                redis_ready(container)
                subprocess.run(["docker", "exec", container, "redis-cli", "CONFIG", "SET", "appendonly", "yes"], check=True)
                redis_ready(container, durable=True)
            finally:
                subprocess.run(["docker", "stop", container], check=True)
            compose("up", "-d", service)
    print("Restore completed. Only isolated data services are running. Review licensing, outbox records and broker state before starting the application.")


if __name__ == "__main__":
    main()
