"""Start the local Docker workspace, including configured data and AI services.

Run with the repository's Python: python infra/development/dev.py
This helper uses only the standard library; application packages stay in Docker.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "infra" / "development"
sys.path.insert(0, str(ROOT / "infra" / "shared" / "scripts"))

from compose_config import compose_command  # noqa: E402
from deploy import deploy  # noqa: E402
from diagnostics import READINESS_CHECKS, diagnose  # noqa: E402


def read_environment(path):
    """Read our flat key=value files without executing values or using host env."""
    if not path.is_file():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[name.strip()] = value
    return values


def write_environment(path, values):
    """Create secrets locally once. Single quotes prevent Compose interpolation."""
    if any("\n" in value or "\r" in value for value in values.values()):
        raise ValueError("Environment settings must be single-line values")
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("# Local Docker Development settings. Do not commit or share this file.\n")
        for name, value in values.items():
            stream.write(f"{name}='" + value.replace("'", "\\'") + "'\n")
    path.chmod(0o600)
    print(f"Created {path.relative_to(ROOT)} (values hidden).")


def prepare_environment():
    """Reuse local provider credentials; isolate Docker DB, Redis and runtime."""
    native = read_environment(ROOT / "backend" / ".env")
    backend_path = DIRECTORY / "backend.env"
    if not backend_path.exists():
        backend = read_environment(DIRECTORY / "backend.env.example")
        for name in ("FYERS_CLIENT_ID", "FYERS_SECRET",
                     "EMAIL_HOST", "EMAIL_PORT", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD",
                     "EMAIL_USE_TLS", "EMAIL_USE_SSL", "DEFAULT_FROM_EMAIL"):
            if native.get(name):
                backend[name] = native[name]
        backend["SECRET_KEY"] = secrets.token_urlsafe(64)
        # Native Development derives its encryption key from SECRET_KEY when no
        # explicit key exists. Preserve it so an imported DB stays decryptable.
        backend["CREDENTIAL_ENCRYPTION_KEYS"] = native.get("CREDENTIAL_ENCRYPTION_KEYS") or (
            base64.urlsafe_b64encode(hashlib.sha256((native.get("SECRET_KEY") or backend["SECRET_KEY"]).encode()).digest()).decode()
        )
        for name in ("POSTGRES_ADMIN_PASSWORD", "DB_PASSWORD", "REDIS_PASSWORD",
                     "RESEARCH_SERVICE_TOKEN", "QUANTNEST_PROXY_TOKEN"):
            backend[name] = secrets.token_hex(32)
        write_environment(backend_path, backend)
    backend = read_environment(backend_path)

    research_path = DIRECTORY / "research.env"
    if not research_path.exists():
        research = read_environment(DIRECTORY / "research.env.example")
        native_research = read_environment(ROOT / "research_service" / ".env")
        for name in research:
            if native_research.get(name):
                research[name] = native_research[name]
        research["RESEARCH_SERVICE_TOKEN"] = backend["RESEARCH_SERVICE_TOKEN"]
        write_environment(research_path, research)
    frontend_path = DIRECTORY / "frontend.env"
    if not frontend_path.exists():
        frontend = read_environment(DIRECTORY / "frontend.env.example")
        native_frontend = read_environment(ROOT / "frontend" / ".env")
        for name in ("VITE_SITE_URL", "VITE_TURNSTILE_SITE_KEY"):
            if native_frontend.get(name):
                frontend[name] = native_frontend[name]
        write_environment(frontend_path, frontend)


def selected_profiles():
    """Enable integrations with configured credentials; Live remains opt-in."""
    backend = read_environment(DIRECTORY / "backend.env")
    research = read_environment(DIRECTORY / "research.env")
    profiles = []
    if backend.get("FYERS_CLIENT_ID") and backend.get("FYERS_SECRET"):
        profiles.append("market-data")
    if research.get("GEMINI_API_KEY"):
        profiles.append("research")
    if "live" in {scope.strip() for scope in backend.get("EXECUTION_ENABLED_SCOPES", "paper").split(",")}:
        profiles.append("live")
    return profiles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=("start", "stop", "status", "logs"), default="start")
    parser.add_argument("--no-build", action="store_true", help="Reuse installed image dependencies")
    parser.add_argument("--prepare-only", action="store_true", help="Create missing local env files without starting Docker")
    args = parser.parse_args()
    prepare_environment()
    if args.prepare_only:
        return
    result = subprocess.run(["docker", "info", "--format", "{{.OSType}}"], capture_output=True, text=True)
    if result.returncode or result.stdout.strip() != "linux":
        raise RuntimeError("Start/unpause Docker Desktop with its Linux engine, then run this command again.")
    profiles = selected_profiles()
    print(f"Development profiles: {', '.join(profiles) or 'base services only'}.")
    if args.action == "start":
        deploy(ROOT, "development", build=not args.no_build, profiles=profiles)
        report = diagnose(ROOT, "development", profiles=profiles)
        print(json.dumps(report, indent=2))
        if not all(report[name] for name in READINESS_CHECKS):
            raise RuntimeError("Development started but readiness failed; inspect dev.py logs.")
        print("Website: http://localhost:5173\nAdmin: http://localhost:8000/admin/")
    elif args.action == "status":
        report = diagnose(ROOT, "development", profiles=profiles)
        print(json.dumps(report, indent=2))
        if not all(report[name] for name in READINESS_CHECKS):
            raise SystemExit(1)
    else:
        arguments = ("stop",) if args.action == "stop" else ("logs", "--follow", "--tail", "80")
        # Include a previously enabled service even after its key/scope is removed.
        subprocess.run(compose_command(ROOT, "development", "--profile", "*", *arguments), cwd=ROOT, check=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Development setup failed: {error}", file=sys.stderr)
        raise SystemExit(1)
