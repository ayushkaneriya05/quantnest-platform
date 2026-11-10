"""Initialize or upgrade one Compose deployment with stopped application services."""
import argparse
import base64
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

from compose_config import DATA_SERVICES, DEPLOYMENT_MODES, DEVELOPMENT_PROFILES, compose_command, compose_configuration


def require_configured(environment, *names):
    """Catch copied examples before stopping a working deployment; never log values."""
    for name in names:
        value = environment.get(name, "")
        if not value or "replace-with-" in value:
            raise ValueError(f"Configure {name} before deploying")


def validate_configuration(configuration, mode):
    """Check operator inputs once, outside application startup and execution."""
    services = configuration["services"]
    backend = services["api"]["environment"]
    scopes = {value.strip() for value in backend["EXECUTION_ENABLED_SCOPES"].split(",")}
    if ("live" in scopes) != ("broker-events" in services):
        raise ValueError("Live scope and broker-events must be enabled together; use the development live profile")
    if mode != "development":
        require_configured(backend, "SECRET_KEY", "CREDENTIAL_ENCRYPTION_KEYS", "DB_PASSWORD",
                           "QUANTNEST_PROXY_TOKEN", "FYERS_CLIENT_ID", "FYERS_SECRET",
                           "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD", "DEFAULT_FROM_EMAIL")
        database = services["postgres"]["environment"]
        require_configured(database, "POSTGRES_PASSWORD")
        if backend["DB_USER"] == database["POSTGRES_USER"] or backend["DB_PASSWORD"] == database["POSTGRES_PASSWORD"]:
            raise ValueError("Use separate application and administrator database credentials")
        for key in backend["CREDENTIAL_ENCRYPTION_KEYS"].split(","):
            try:
                valid = len(base64.b64decode(key.strip(), altchars=b"-_", validate=True)) == 32
            except ValueError:
                valid = False
            if not valid:
                raise ValueError("CREDENTIAL_ENCRYPTION_KEYS must contain generated Fernet keys")
        origin = urlsplit(backend["FRONTEND_URL"])
        if (origin.scheme != "https" or not origin.hostname or origin.username or origin.password
                or origin.path not in ("", "/") or origin.query or origin.fragment
                or backend["BACKEND_URL"].rstrip("/") != backend["FRONTEND_URL"].rstrip("/")):
            raise ValueError("FRONTEND_URL and BACKEND_URL must use the same HTTPS browser origin")
        if services["ingress"]["environment"]["PUBLIC_HOSTNAME"] != origin.netloc:
            raise ValueError("PUBLIC_HOSTNAME must match the browser origin")
        if "replace-with-" in backend["REDIS_URL"]:
            raise ValueError("Configure REDIS_PASSWORD before deploying")
    if "research" in services:
        research = services["research"]["environment"]
        if research.get("RESEARCH_PROVIDER", "gemini") == "gemini":
            require_configured(research, "GEMINI_API_KEY")
        require_configured(backend, "RESEARCH_SERVICE_TOKEN")
        if backend["RESEARCH_SERVICE_TOKEN"] != research.get("RESEARCH_SERVICE_TOKEN"):
            raise ValueError("RESEARCH_SERVICE_TOKEN must match in backend.env and research.env")


def deploy(root, mode, *, build=False, profiles=()):
    root = Path(root).resolve()
    command = compose_command(root, mode, profiles=profiles)
    configuration = compose_configuration(root, mode, profiles=profiles)
    validate_configuration(configuration, mode)

    def run(*values):
        return subprocess.run([*command, *values], cwd=root, check=True)

    if build:
        run("build")
    run("run", "--rm", "--no-deps", "api", "python", "manage.py", "check", *(["--deploy", "--fail-level", "WARNING"] if mode != "development" else []))
    run("up", "-d", "--wait", *DATA_SERVICES)
    # Include previously enabled development profiles, even if this run disables them.
    all_services = subprocess.run(
        [*command, "--profile", "*", "config", "--services"],
        cwd=root, capture_output=True, text=True, timeout=30, check=True,
    ).stdout.split()
    producers = sorted(set(all_services) - set(DATA_SERVICES))
    run("stop", *producers)
    run("run", "--rm", "--no-deps", "api", "python", "manage.py", "migrate", "--noinput")
    run("run", "--rm", "--no-deps", "api", "python", "manage.py", "setup_timescale")
    run("run", "--rm", "--no-deps", "api", "python", "manage.py", "configure_site")
    run("run", "--rm", "--no-deps", "api", "python", "manage.py", "collectstatic", "--noinput")
    run("up", "-d", "--wait", "--wait-timeout", "180", "--remove-orphans")
    print("Stack started. Run diagnostics and review execution sessions.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--mode", choices=DEPLOYMENT_MODES, required=True)
    parser.add_argument("--build", action="store_true", help="Build application images before stopping services")
    parser.add_argument("--profile", choices=DEVELOPMENT_PROFILES, action="append", default=[], help="Development only; repeat for optional services")
    args = parser.parse_args()
    if args.profile and args.mode != "development":
        parser.error("--profile is only supported for development")
    deploy(args.root, args.mode, build=args.build, profiles=args.profile)


if __name__ == "__main__":
    main()
