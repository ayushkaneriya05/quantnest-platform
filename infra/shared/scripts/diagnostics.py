"""Report deployment health without printing environment values or credentials."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from compose_config import DEPLOYMENT_MODES, DEVELOPMENT_PROFILES, compose_command, compose_configuration

READINESS_CHECKS = ("compose_valid", "services_ready", "application_checks", "worker_checks", "task_workers")


def service_status(root, mode, profiles=()):
    command = compose_command(root, mode, profiles=profiles)
    required = set(compose_configuration(root, mode, profiles=profiles)["services"])
    result = subprocess.run(
        [*command, "ps", "--all", "--format", "json"],
        cwd=root, capture_output=True, text=True, timeout=20, check=True,
    )
    rows = json.loads(result.stdout) if result.stdout.strip().startswith("[") else [
        json.loads(line) for line in result.stdout.splitlines() if line
    ]
    services = [{key: row.get(key) for key in ("Service", "State", "Health")} for row in rows]
    missing = sorted(required - {row["Service"] for row in services})
    ready = not missing and all(
        row["State"] == "running" and row["Health"] not in {"unhealthy", "starting"}
        for row in services if row["Service"] in required
    )
    return {"services": services, "missing_services": missing, "services_ready": ready}


def diagnose(root, mode, *, profiles=()):
    """Share the same read-only checks with the one-command Development launcher."""
    root = Path(root).resolve()
    command = compose_command(root, mode, profiles=profiles)
    services = compose_configuration(root, mode, profiles=profiles)["services"]
    expected_queues = {
        name: next(value.removeprefix("--queues=") for value in services[name]["command"]
                   if value.startswith("--queues=")).split(",")
        for name in ("background", "compute")
    }
    # A running container can still contain a Celery process that is failing to
    # initialize. This is an operator check, not a periodic hot-path probe.
    task_probe = f"""
from backend.celery import app
workers = app.control.inspect(timeout=5).active_queues() or {{}}
expected = {expected_queues!r}
for service, required in expected.items():
    observed = [{{queue['name'] for queue in queues}}
                for name, queues in workers.items() if name.startswith(service + '@')]
    assert any(set(required) <= queues for queues in observed), service + ' is not consuming its configured queues'
"""

    def check(*arguments):
        return subprocess.run(
            [*command, *arguments], cwd=root, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=45,
        ).returncode == 0

    report = {
        "disk_free_bytes": shutil.disk_usage(root).free,
        "compose_valid": check("config", "--quiet"),
        **service_status(root, mode, profiles),
        "application_checks": check(
            "exec", "-T", "api", "python", "manage.py", "check",
            *(["--deploy", "--fail-level", "WARNING"] if mode != "development" else []),
        ),
        "worker_checks": check(
            "exec", "-T", "api", "python", "manage.py", "deployment_health",
            "--require-mode", mode, "--workers",
        ),
        "task_workers": check("exec", "-T", "api", "python", "-c", task_probe),
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--mode", choices=DEPLOYMENT_MODES, required=True)
    parser.add_argument("--profile", choices=DEVELOPMENT_PROFILES, action="append", default=[])
    args = parser.parse_args()
    if args.profile and args.mode != "development":
        parser.error("--profile belongs only to development")
    report = diagnose(args.root, args.mode, profiles=args.profile)
    print(json.dumps(report, indent=2))
    if not all(report[key] for key in READINESS_CHECKS):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
