"""Regression checks for deployment sequencing and destructive-operation guards."""
from pathlib import Path
import io
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import backup
import compose_config
import deploy
import restore


class DeploymentTests(unittest.TestCase):
    def configuration(self):
        return {'services': {'api': {'environment': {'EXECUTION_ENABLED_SCOPES': 'paper'}},
                             'execution': {}, 'postgres': {}, 'redis': {}, 'redis-cache': {}}}

    def test_live_scope_requires_broker_events(self):
        config = self.configuration()
        config['services']['api']['environment']['EXECUTION_ENABLED_SCOPES'] = 'paper,live'
        with patch.object(deploy, 'compose_configuration', return_value=config), patch.object(deploy, 'compose_command', return_value=['compose']), patch.object(deploy.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'broker-events'):
                deploy.deploy(Path('.'), 'development')
            run.assert_not_called()

    def test_failed_migration_does_not_start_execution(self):
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            if 'migrate' in command:
                raise subprocess.CalledProcessError(1, command)
            return subprocess.CompletedProcess(command, 0, stdout='api execution postgres redis redis-cache')
        with patch.object(deploy, 'compose_configuration', return_value=self.configuration()), patch.object(deploy, 'compose_command', return_value=['compose']), patch.object(deploy.subprocess, 'run', side_effect=run):
            with self.assertRaises(subprocess.CalledProcessError):
                deploy.deploy(Path('.'), 'development')
        self.assertTrue(any('stop' in command and 'execution' in command for command in calls))
        self.assertFalse(any('--remove-orphans' in command for command in calls))

    def test_timescale_setup_precedes_startup(self):
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, stdout='api execution postgres redis redis-cache')
        with patch.object(deploy, 'compose_configuration', return_value=self.configuration()), patch.object(deploy, 'compose_command', return_value=['compose']), patch.object(deploy.subprocess, 'run', side_effect=run):
            deploy.deploy(Path('.'), 'development')
        positions = {value: next(i for i, command in enumerate(calls) if value in command) for value in ('migrate', 'setup_timescale', 'configure_site', '--remove-orphans')}
        self.assertLess(positions['migrate'], positions['setup_timescale'])
        self.assertLess(positions['setup_timescale'], positions['configure_site'])
        self.assertLess(positions['configure_site'], positions['--remove-orphans'])

    def test_backup_refuses_running_api(self):
        with patch.object(backup.shutil, 'which', return_value='age'), patch.object(backup, 'running_application_services', return_value=['api']), patch.object(backup.subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'Stop application'):
                backup.create(Path('.'), Path('unused'), ['age1test'], 'public')
            run.assert_not_called()

    def test_restore_refuses_running_worker(self):
        with patch.object(restore.shutil, 'which', return_value='age'), patch.object(restore, 'running_application_services', return_value=['execution']), patch.object(restore.subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'Stop application'):
                restore.restore(Path('.'), 'private', Path('unused'), Path('unused'))
            run.assert_not_called()

    def test_archive_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            archive = folder / 'unsafe.tar'
            with tarfile.open(archive, 'w') as stream:
                member = tarfile.TarInfo('../outside.txt')
                member.size = 1
                stream.addfile(member, io.BytesIO(b'x'))
            with self.assertRaises(ValueError):
                restore.safe_extract(archive, folder)

    def test_archive_link_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            archive = folder / 'unsafe.tar'
            with tarfile.open(archive, 'w') as stream:
                member = tarfile.TarInfo('database.dump')
                member.type = tarfile.SYMTYPE
                member.linkname = '/etc/passwd'
                stream.addfile(member)
            with self.assertRaises(ValueError):
                restore.safe_extract(archive, folder)

    def test_data_services_are_not_counted_as_writers(self):
        with patch.object(compose_config, 'compose_command', return_value=['compose']), patch.object(compose_config.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout='postgres\nredis\nredis-cache\napi\n')):
            self.assertEqual(compose_config.running_application_services(Path('.'), 'public'), ['api'])


if __name__ == '__main__':
    unittest.main()
