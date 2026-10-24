"""Back up PostgreSQL and user media to a local encrypted archive."""
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

from compose_config import DEPLOYMENT_MODES, compose_command, running_application_services


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def create(root, directory, recipients, mode):
    if not shutil.which('age'):
        raise RuntimeError('Install age before making encrypted backups.')
    running = running_application_services(root, mode)
    if running:
        raise RuntimeError(f'Stop application services before backing up: {", ".join(running)}')
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination = directory / f'quantnest-{mode}-{stamp}.tar.age'
    with tempfile.TemporaryDirectory(prefix='qn-backup-', dir=directory) as temporary:
        folder = Path(temporary)
        os.chmod(folder, 0o700)
        dump, media = folder / 'database.dump', folder / 'media.tar'
        command = compose_command(root, mode, 'exec', '-T', 'postgres', 'sh', '-c',
            'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-privileges')
        with dump.open('wb') as stream:
            subprocess.run(command, cwd=root, stdout=stream, check=True)
        # A one-shot container mounts media without starting the API server.
        command = compose_command(root, mode, 'run', '--rm', '--no-deps', '-T', 'api',
            'tar', '-C', '/opt/quantnest/backend/media', '-cf', '-', '.')
        with media.open('wb') as stream:
            subprocess.run(command, cwd=root, stdout=stream, check=True)
        manifest = {'format': 3, 'mode': mode, 'created_at': stamp,
                    'files': {path.name: file_hash(path) for path in (dump, media)}}
        manifest_path = folder / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        archive = folder / 'archive.tar'
        with tarfile.open(archive, 'w') as stream:
            for path in (dump, media, manifest_path):
                stream.add(path, arcname=path.name)
        partial = folder / 'encrypted.tar.age'
        command = ['age', '--encrypt', '--output', str(partial)]
        for recipient in recipients:
            command += ['--recipient', recipient]
        command.append(str(archive))
        subprocess.run(command, check=True)
        os.chmod(partial, 0o600)
        os.replace(partial, destination)
    destination.with_suffix('.age.sha256').write_text(file_hash(destination) + '\n', encoding='ascii')
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--mode', choices=DEPLOYMENT_MODES, required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--recipient', action='append', required=True, help='age public key; repeat for another recovery owner')
    args = parser.parse_args()
    path = create(args.root.resolve(), args.output.resolve(), args.recipient, args.mode)
    print(f'Encrypted backup: {path}')


if __name__ == '__main__':
    main()
