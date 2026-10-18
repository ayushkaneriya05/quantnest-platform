"""Prepare a source/static release and verify its OCI-signed integrity before extraction."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[3]
EXCLUDED = {"node_modules", ".venv", ".cache", ".terraform", "__pycache__", ".git", "logs", "staticfiles", "media"}


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def allowed(path):
    return not (set(path.parts) & EXCLUDED
                or path.name.endswith((".pyc", ".log", ".sqlite3", ".age", ".dump", ".rdb", ".pem", ".key", ".jws", ".tar.gz", ".tar")) or (path.name.startswith(".env") and not path.name.endswith(".example"))
                or path.name.endswith(".env")
                or path.name.startswith("celerybeat-schedule") or ".log." in path.name
                or path.name in {"public-keys.json", "origin.pem", "origin-key.pem"})


def create(output, release, architectures, environment):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", release):
        raise ValueError("Invalid release identifier")
    if not (ROOT/"frontend/dist/index.html").exists():
        raise ValueError("Build and verify the React frontend before packaging")
    from decouple import RepositoryEnv
    config = RepositoryEnv(str(environment.resolve(strict=True)))
    required = ("OCI_RELEASE_KEY_ID", "OCI_RELEASE_KEY_VERSION", "OCI_RELEASE_SIGNING_ENDPOINT")
    if not all(config.data.get(name) for name in required):
        raise ValueError("Configure the central OCI signing key/version/endpoint in the selected environment")
    files = []
    for name in ("backend", "research_service", "infra/shared", "infra/private", "frontend/dist"):
        files.extend(path for path in (ROOT/name).rglob("*") if path.is_file() and not path.is_symlink() and allowed(path.relative_to(ROOT)))
    files.extend(ROOT / name for name in (
        "README.md", "infra/README.md", ".dockerignore", ".gitattributes", ".python-version", "pyproject.toml",
        "docs/backend-runtime.md", "docs/execution-technical-reference.md", "docs/commercial-operations.md",
        "docs/authentication.md", "docs/third-party-setup.md", "docs/strategy-configuration.md", "docs/execution-review.md",
    ))
    files = sorted(set(files))
    manifest = {"release": release, "created_at": datetime.now(timezone.utc).isoformat(), "architectures": architectures,
        "files": {str(path.relative_to(ROOT)).replace(os.sep,"/"): file_hash(path) for path in files}}
    output.mkdir(parents=True, exist_ok=True)
    archive = output/(release+".tar.gz")
    with tarfile.open(archive, "w:gz") as stream:
        for path in files:
            stream.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
    # Signing is an explicit operator action. OCI private signing keys never leave the Vault.
    import sys
    sys.path.insert(0,str(ROOT/"backend"))
    from installations.signing import sign_licence
    claims = {"iss":"quantnest-releases","aud":"quantnest-private","iat":int(datetime.now(timezone.utc).timestamp()),
        "artifact_sha256":file_hash(archive),"artifact_bytes":archive.stat().st_size,
        "manifest":manifest}
    signature = output/(release+".jws")
    signature.write_text(sign_licence(claims, key_id=config[required[0]], key_version=config[required[1]], endpoint=config[required[2]]),encoding="ascii")
    return archive, signature


def verify(archive, signature, trusted_keys):
    import jwt
    token=signature.read_text(encoding="ascii").strip()
    header=jwt.get_unverified_header(token)
    keys=json.loads(trusted_keys.read_text(encoding="utf-8"))
    if header.get("alg")!="ES256" or header.get("kid") not in keys:
        raise ValueError("Unknown release signing key")
    claims=jwt.decode(token,keys[header["kid"]],algorithms=["ES256"],issuer="quantnest-releases",audience="quantnest-private",
                      options={"require":["iss","aud","iat","artifact_sha256","artifact_bytes","manifest"]})
    if archive.stat().st_size!=claims["artifact_bytes"] or file_hash(archive)!=claims["artifact_sha256"]:
        raise ValueError("Release artifact integrity verification failed")
    manifest=claims["manifest"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}",manifest["release"]):
        raise ValueError("Invalid release identity")
    with tarfile.open(archive) as stream:
        members=stream.getmembers()
        if len(members)>20000 or len(members)!=len(manifest["files"]) or set(member.name for member in members)!=set(manifest["files"]):
            raise ValueError("Release content differs from its signed manifest")
        for member in members:
            path=Path(member.name)
            if not member.isfile() or path.is_absolute() or ".." in path.parts or not allowed(path):
                raise ValueError("Unsafe release member")
            with stream.extractfile(member) as source:
                if hashlib.file_digest(source,"sha256").hexdigest()!=manifest["files"][member.name]:
                    raise ValueError("Release file checksum mismatch")
    return manifest


def unpack(archive, signature, trusted_keys, releases, *, expected_release=None, reuse=False):
    manifest=verify(archive,signature,trusted_keys)
    if expected_release is not None and manifest["release"] != expected_release:
        raise ValueError("QUANTNEST_RELEASE must match the signed artifact identifier")
    releases=releases.resolve()
    target=releases/manifest["release"]
    if target.exists():
        if reuse and target.is_dir() and not target.is_symlink():
            existing = json.loads((target/"release-manifest.json").read_text(encoding="utf-8"))
            actual = {path.relative_to(target).as_posix() for path in target.rglob("*")
                      if path.is_file() and allowed(path.relative_to(target)) and path != target/"release-manifest.json"}
            if existing != manifest or actual != set(manifest["files"]):
                raise ValueError("Existing release content differs from the signed manifest; use a new verified destination")
            for name, checksum in manifest["files"].items():
                path = target/name
                if path.is_symlink() or not path.resolve().is_relative_to(target.resolve()) or file_hash(path) != checksum:
                    raise ValueError("Existing release checksum/path differs from the signed manifest")
            return target
        raise ValueError("Release destination already exists")
    releases.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="qn-release-",dir=releases) as temporary:
        folder=Path(temporary)
        with tarfile.open(archive) as stream:
            stream.extractall(folder,filter="data")
        (folder/"release-manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        folder.rename(target)
    return target


def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="action",required=True)
    build=sub.add_parser("create");build.add_argument("--release",required=True);build.add_argument("--output",type=Path,required=True)
    build.add_argument("--environment", type=Path, required=True, help="Reviewed central release-signing environment, normally /etc/quantnest/operations.env")
    build.add_argument("--architecture",choices=["aarch64","x86_64"],action="append",required=True)
    for name in ("verify","unpack"):
        command=sub.add_parser(name);command.add_argument("--archive",type=Path,required=True);command.add_argument("--signature",type=Path,required=True)
        command.add_argument("--trusted-keys",type=Path,required=True)
        if name=="unpack":command.add_argument("--releases",type=Path,required=True)
    args=parser.parse_args()
    if args.action=="create":
        archive,signature=create(args.output,args.release,args.architecture,args.environment);print(json.dumps({"archive":str(archive),"signature":str(signature)}))
    elif args.action=="verify":print(json.dumps(verify(args.archive,args.signature,args.trusted_keys),indent=2))
    else:print(unpack(args.archive,args.signature,args.trusted_keys,args.releases))


if __name__=="__main__":main()
