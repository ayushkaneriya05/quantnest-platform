"""Install a verified Private release and back up existing installations."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import uuid

from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey, SECP256R1
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from decouple import RepositoryEnv

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "infra" / "shared" / "scripts"))

from release import unpack
from backup import create as backup
from deploy import deploy


def validate_configuration(directory):
    directory = directory.resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("Configuration path must be a directory")

    files = {}
    for name in ("backend.env", "research.env"):
        source = directory / name
        if not source.is_file():
            raise ValueError(f"Missing required configuration file: {name}")
        if source.stat().st_mode & 0o077:
            raise ValueError("Environment files must have owner-only permissions")
        files[name] = source

    public_keys = directory / "license" / "public-keys.json"
    if not public_keys.is_file():
        raise ValueError("Missing license/public-keys.json in the configuration directory")
    if public_keys.stat().st_mode & 0o022:
        raise ValueError("The public verification key file must not be group/world writable")
    try:
        keys = json.loads(public_keys.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("The public verification key file must contain valid JSON") from error
    if not isinstance(keys, dict) or not keys:
        raise ValueError("The public verification key file must be a non-empty key-id to PEM mapping")
    for key_id, pem in keys.items():
        if not isinstance(key_id, str) or not key_id or not isinstance(pem, str):
            raise ValueError("Public verification keys must map non-empty key IDs to PEM strings")
        try:
            key = load_pem_public_key(pem.encode("utf-8"))
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid public verification key: {key_id}") from error
        if not isinstance(key, EllipticCurvePublicKey) or not isinstance(key.curve, SECP256R1):
            raise ValueError(f"Public verification key {key_id} must use P-256")
    files["public-keys.json"] = public_keys
    return files


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--archive",type=Path,required=True);parser.add_argument("--signature",type=Path,required=True)
    parser.add_argument("--trusted-keys",type=Path,required=True);parser.add_argument("--releases",type=Path,required=True)
    parser.add_argument("--configuration",type=Path,required=True,help="Private config directory containing backend.env, research.env, and license/public-keys.json")
    parser.add_argument("--current",type=Path,required=True,help="Stable symbolic link to the active release")
    parser.add_argument("--backup-directory",type=Path);parser.add_argument("--backup-recipient",action="append")
    args=parser.parse_args()
    if platform.system()!="Linux" or not shutil.which("docker"):
        raise RuntimeError("The supported installer requires a Linux Docker Compose host")
    if args.current.exists() and not args.current.is_symlink():
        raise ValueError("The current path must be a symbolic link")
    configuration_files = validate_configuration(args.configuration)
    configured_release = RepositoryEnv(str(configuration_files["backend.env"])).data.get("QUANTNEST_RELEASE")
    if not configured_release:
        raise ValueError("Configure QUANTNEST_RELEASE before installing the signed artifact")
    target=unpack(args.archive,args.signature,args.trusted_keys,args.releases,expected_release=configured_release,reuse=True)
    manifest=json.loads((target/"release-manifest.json").read_text())
    if platform.machine() not in manifest["architectures"]:
        raise RuntimeError("This release was not qualified for the host architecture")
    configuration_directory = target/"infra"/"private"
    configuration_directory.mkdir(parents=True, exist_ok=True)
    for name in ("backend.env", "research.env"):
        destination = configuration_directory / name
        shutil.copyfile(configuration_files[name], destination)
        os.chmod(destination, 0o600)
    license_directory = configuration_directory / "license"
    license_directory.mkdir(parents=True, exist_ok=True)
    public_keys_destination = license_directory / "public-keys.json"
    shutil.copyfile(configuration_files["public-keys.json"], public_keys_destination)
    os.chmod(public_keys_destination, 0o644)
    previous=args.current.resolve() if args.current.is_symlink() else None
    if previous == target:
        raise ValueError("This release is already active; use the shared deploy command for configuration changes")
    if previous:
        if not args.backup_directory or not args.backup_recipient:
            raise RuntimeError("An upgrade requires an encrypted recovery backup")
    before_migrate = (lambda: backup(previous,args.backup_directory,args.backup_recipient,mode="private")) if previous else None
    deploy(target, "private", build=True, before_migrate=before_migrate)
    temporary=args.current.with_name(args.current.name+"."+uuid.uuid4().hex+".next")
    temporary.symlink_to(target);os.replace(temporary,args.current)
    print("Release installed. Import/refresh the licence, run diagnostics and review execution sessions.")


if __name__=="__main__":main()
