"""Restore an encrypted backup into an empty deployment with applications stopped."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

from backup import file_hash
from compose_config import DATA_SERVICES, DEPLOYMENT_MODES, compose_command, running_application_services


def safe_extract(archive, folder):
    with tarfile.open(archive) as stream:
        for member in stream.getmembers():
            if not (folder / member.name).resolve().is_relative_to(folder.resolve()) or not member.isfile():
                raise ValueError('Unexpected backup member or unsafe archive path.')
        stream.extractall(folder, filter='data')


def restore(root, mode, backup, identity):
    if not shutil.which('age'):
        raise RuntimeError('Install age before restoring a backup.')
    running = running_application_services(root, mode)
    if running:
        raise RuntimeError(f'Stop application services before restoring: {", ".join(running)}')
    command = compose_command(root, mode)

    def compose(*arguments, **kwargs):
        return subprocess.run([*command, *arguments], cwd=root, check=True, **kwargs)

    with tempfile.TemporaryDirectory(prefix='qn-restore-') as temporary:
        folder = Path(temporary)
        os.chmod(folder, 0o700)
        archive = folder / 'archive.tar'
        subprocess.run(['age', '--decrypt', '--identity', str(identity), '--output', str(archive), str(backup)], check=True)
        safe_extract(archive, folder)
        manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
        if manifest.get('format') != 3 or manifest.get('mode') != mode or set(manifest.get('files', {})) != {'database.dump', 'media.tar'}:
            raise ValueError('Backup format/mode mismatch. Older backup formats require their original restore tool.')
        for name, checksum in manifest['files'].items():
            if file_hash(folder / name) != checksum:
                raise ValueError('Backup integrity verification failed.')
        # Even a valid backup must never overwrite an existing application database.
        compose('up', '-d', '--wait', *DATA_SERVICES)
        result = compose('exec', '-T', 'postgres', 'sh', '-c',
            'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema=\'public\'"',
            capture_output=True, text=True)
        if int(result.stdout.strip()):
            raise RuntimeError('Database is not empty. Use a new server/empty deployment; existing data was not overwritten.')
        compose('exec', '-T', 'postgres', 'sh', '-c',
            'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT timescaledb_pre_restore()"')
        with (folder / 'database.dump').open('rb') as stream:
            compose('exec', '-T', 'postgres', 'sh', '-c',
                'exec pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges --exit-on-error', stdin=stream)
        # Restore runs as the bootstrap administrator for Timescale catalogs.
        # Return application tables to the non-superuser role before API startup.
        ownership_sql = r"""
SELECT timescaledb_post_restore();
SELECT format('ALTER %s %I.%I OWNER TO %I',
  CASE c.relkind WHEN 'S' THEN 'SEQUENCE' WHEN 'v' THEN 'VIEW' WHEN 'm' THEN 'MATERIALIZED VIEW' ELSE 'TABLE' END,
  n.nspname, c.relname, :'app_user')
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r','p','S','v','m')
  AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.deptype = 'e')
ORDER BY CASE WHEN c.relkind = 'S' THEN 1 ELSE 0 END
\gexec
"""
        compose('exec', '-T', 'postgres', 'sh', '-c',
            'exec psql -v ON_ERROR_STOP=1 --set=app_user="$DB_USER" -U "$POSTGRES_USER" -d "$POSTGRES_DB"', input=ownership_sql.encode())
        with tarfile.open(folder / 'media.tar') as stream:
            for member in stream.getmembers():
                if not (folder / member.name).resolve().is_relative_to(folder.resolve()) or not (member.isfile() or member.isdir()):
                    raise ValueError('Unsafe media archive member.')
        # New recovery volumes inherit the application UID from the image.
        with (folder / 'media.tar').open('rb') as stream:
            compose('run', '--rm', '--no-deps', '-T', 'api', 'tar', '-C', '/opt/quantnest/backend/media', '-xf', '-', stdin=stream)
    print('Database and media restored. Application services remain stopped. Review recovered sessions/broker state before deploying.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--mode', choices=DEPLOYMENT_MODES, required=True)
    parser.add_argument('--backup', required=True, type=Path)
    parser.add_argument('--identity', required=True, type=Path, help='age private recovery key')
    args = parser.parse_args()
    restore(args.root.resolve(), args.mode, args.backup.resolve(strict=True), args.identity.resolve(strict=True))


if __name__ == '__main__':
    main()
