"""Initialize or upgrade one Compose deployment with stopped application services."""
import argparse
from pathlib import Path
import subprocess

from compose_config import DATA_SERVICES, DEPLOYMENT_MODES, DEVELOPMENT_PROFILES, compose_command, compose_configuration


def deploy(root, mode, *, build=False, profiles=()):
    root = Path(root).resolve()
    command = compose_command(root, mode, profiles=profiles)
    configuration = compose_configuration(root, mode, profiles=profiles)
    services = configuration["services"]
    backend_environment = services["api"]["environment"]
    live_enabled = "live" in {value.strip() for value in backend_environment["EXECUTION_ENABLED_SCOPES"].split(",")}
    if live_enabled != ("broker-events" in services):
        raise ValueError("Live scope and the broker-events service must be enabled together; use the development live profile")
    if "research" in services:
        research_environment = services["research"]["environment"]
        if not research_environment.get("GEMINI_API_KEY") or research_environment["GEMINI_API_KEY"].startswith("replace-with-"):
            raise ValueError("Configure GEMINI_API_KEY before enabling the research service")
        if not backend_environment.get("RESEARCH_SERVICE_TOKEN") or backend_environment["RESEARCH_SERVICE_TOKEN"] != research_environment.get("RESEARCH_SERVICE_TOKEN"):
            raise ValueError("RESEARCH_SERVICE_TOKEN must match in backend.env and research.env")

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
