"""Resolve an explicit QuantNest deployment-mode Compose stack."""
from pathlib import Path
import os
import json
import subprocess

DEPLOYMENT_MODES = ("development", "public", "private")
DEVELOPMENT_PROFILES = ("market-data", "research", "live")


def compose_command(root, mode, *arguments, profiles=()):
    if mode not in DEPLOYMENT_MODES:
        raise ValueError(f"mode must be one of: {', '.join(DEPLOYMENT_MODES)}")
    project = os.environ.get("COMPOSE_PROJECT_NAME", "")
    if project and project != f"quantnest-{mode}":
        raise ValueError(f"Unset COMPOSE_PROJECT_NAME or use quantnest-{mode}; never reuse another mode's volumes")
    if profiles and (mode != "development" or not set(profiles) <= set(DEVELOPMENT_PROFILES)):
        raise ValueError("Only development supports the market-data, research and live profiles")
    directory = Path(root).resolve() / "infra" / mode
    compose_file = directory / "compose.yaml"
    environment_file = directory / "backend.env"
    if not compose_file.is_file():
        raise FileNotFoundError(f"Missing {mode} Compose file: {compose_file}")
    if not environment_file.is_file():
        raise FileNotFoundError(f"Copy {mode}/backend.env.example to {environment_file} and configure it")
    command = ["docker", "compose", "--project-name", f"quantnest-{mode}", "--env-file", str(environment_file), "-f", str(compose_file)]
    for profile in profiles:
        command += ["--profile", profile]
    return [*command, *arguments]


def compose_configuration(root, mode, *, profiles=()):
    """Read effective configuration privately; never print its resolved secrets."""
    result = subprocess.run(
        compose_command(root, mode, "config", "--format", "json", profiles=profiles),
        cwd=root, capture_output=True, text=True, timeout=30, check=True,
    )
    return json.loads(result.stdout)
