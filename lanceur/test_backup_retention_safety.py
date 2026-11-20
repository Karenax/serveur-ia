"""Retention safety checks using only small, isolated fixture files."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from backups import BackupManager


class RetentionSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='kiara-retention-test-')
        self.manager = BackupManager(SimpleNamespace(home=self.tmp.name))
        self.primary = Path(self.tmp.name) / 'primary'
        self.secondary = Path(self.tmp.name) / 'secondary'
        self.primary.mkdir()
        self.secondary.mkdir()
        name = 'fred-20261116-030000-' + 'a' * 24 + '.qwenbackup'
        self.main = self.primary / name
        self.copy = self.secondary / name
        self.agent = self.main.with_suffix('.kiara-agent')
        self.agent_copy = self.copy.with_suffix('.kiara-agent')
        self.contents = {self.main: b'main fixture', self.copy: b'main fixture',
                         self.agent: b'projects fixture', self.agent_copy: b'projects fixture'}
        for path, data in self.contents.items():
            path.write_bytes(data)
        sha = lambda data: hashlib.sha256(data).hexdigest()
        self.old = {'id': 'a' * 24, 'file': str(self.main), 'timestamp': 10,
                    'kind': 'automatic', 'verified': True, 'sha256': sha(self.contents[self.main]),
                    'agent': {'file': str(self.agent), 'sha256': sha(self.contents[self.agent])},
                    'secondary': {'status': 'copied', 'file': str(self.copy)}}
        self.new = {'id': 'b' * 24, 'file': 'new-fixture', 'timestamp': 20,
                    'kind': 'automatic', 'verified': True}
        self.manager.data['catalog'] = [self.new, self.old]
        self.manager.data['config']['retention'] = {'daily': 0, 'weekly': 0, 'monthly': 0}

    def tearDown(self):
        self.manager.close()
        self.tmp.cleanup()

    def assert_preserved(self):
        self.assertEqual(self.manager.prune(), [])
        self.assertEqual(self.manager.data['catalog'], [self.new, self.old])
        for path, data in self.contents.items():
            self.assertEqual(path.read_bytes(), data)

    def test_corrupted_secondary_preserves_both_project_pairs(self):
        self.contents[self.copy] = b'corrupted fixture'
        self.copy.write_bytes(self.contents[self.copy])
        self.assert_preserved()

    def test_missing_secondary_projects_preserves_the_other_files(self):
        self.agent_copy.unlink()
        del self.contents[self.agent_copy]
        self.assert_preserved()

    def test_missing_local_main_preserves_the_other_files(self):
        self.main.unlink()
        del self.contents[self.main]
        self.assert_preserved()

    def test_removed_local_projects_preserves_complete_secondary_pair(self):
        self.agent.unlink()
        del self.contents[self.agent]
        self.assert_preserved()
        self.assertIn('Nettoyage incomplet', self.manager.data['last_error'])

    def test_verified_pairs_are_still_removed_by_retention(self):
        self.assertEqual(self.manager.prune(), [self.old['id']])
        self.assertEqual(self.manager.data['catalog'], [self.new])
        self.assertTrue(all(not path.exists() for path in self.contents))

    def test_denied_secondary_read_keeps_files_and_persists_warning(self):
        from backups import _hash_file
        def selective_hash(path):
            if path == self.copy:
                raise PermissionError('fixture path must not be exposed')
            return _hash_file(path)
        with patch('backups._hash_file', selective_hash):
            self.assert_preserved()
        self.assertIn('Nettoyage incomplet', self.manager.data['last_error'])
        self.assertNotIn('fixture path', self.manager.data['last_error'])
        import json
        saved = json.loads(self.manager.path.read_text(encoding='utf-8'))
        self.assertEqual(saved['last_error'], self.manager.data['last_error'])

    def test_copy_pointing_to_primary_does_not_remove_the_source(self):
        self.old['secondary']['file'] = str(self.main)
        self.assert_preserved()

    def test_interrupted_preparation_restores_the_complete_pair_on_restart(self):
        real_rename = os.rename
        for fail_at in range(1, 5):
            with self.subTest(interruption_before_move=fail_at):
                self.manager._save()
                calls = 0
                def interrupt_move(source, destination):
                    nonlocal calls
                    calls += 1
                    if calls == fail_at:
                        raise SystemExit('simulated process interruption')
                    return real_rename(source, destination)
                with patch('backup_retention.os.rename', interrupt_move):
                    with self.assertRaises(SystemExit):
                        self.manager.prune()
                self.manager.close()
                self.manager = BackupManager(SimpleNamespace(home=self.tmp.name))
                self.assertEqual([item['id'] for item in self.manager.data['catalog']], [self.new['id'], self.old['id']])
                for path, contents in self.contents.items():
                    self.assertEqual(path.read_bytes(), contents)
                self.assertFalse((self.manager.directory / 'retention-en-cours.json').exists())

    def test_interruption_after_commit_finishes_cleanup_without_touching_new_backup(self):
        newest = self.primary / ('fred-20261117-030000-' + 'b' * 24 + '.qwenbackup')
        newest.write_bytes(b'newest fixture')
        self.new['file'] = str(newest)
        self.manager._save()
        real_unlink = Path.unlink
        calls = 0
        def interrupt_cleanup(path, *args, **kwargs):
            nonlocal calls
            if '.kiara-prune-' in path.name:
                calls += 1
                if calls == 2:
                    raise SystemExit('simulated process interruption')
            return real_unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', interrupt_cleanup):
            with self.assertRaises(SystemExit):
                self.manager.prune()
        self.manager.close()
        self.manager = BackupManager(SimpleNamespace(home=self.tmp.name))
        self.assertEqual([item['id'] for item in self.manager.data['catalog']], [self.new['id']])
        self.assertEqual(newest.read_bytes(), b'newest fixture')
        self.assertTrue(all(not path.exists() for path in self.contents))
        self.assertFalse((self.manager.directory / 'retention-en-cours.json').exists())
        self.assertFalse(list(Path(self.tmp.name).rglob('*.kiara-prune-*')))

    def test_conflicting_original_blocks_recovery_without_overwriting_either_copy(self):
        self.manager._save()
        real_rename = os.rename
        calls = 0
        def interrupt_move(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2: raise SystemExit('simulated process interruption')
            return real_rename(source, destination)
        with patch('backup_retention.os.rename', interrupt_move):
            with self.assertRaises(SystemExit): self.manager.prune()
        staged = list(self.primary.glob('*.kiara-prune-*'))
        self.assertEqual(len(staged), 1)
        self.main.write_bytes(b'new file at original path')
        self.manager.close()
        self.manager = BackupManager(SimpleNamespace(home=self.tmp.name))
        self.assertEqual(self.main.read_bytes(), b'new file at original path')
        self.assertEqual(staged[0].read_bytes(), self.contents[self.main])
        self.assertTrue(self.manager.data['retention_warning'])
        self.assertEqual(self.manager.prune(), [])
        self.assertTrue(staged[0].exists())

    def test_invalid_journal_blocks_cleanup_and_preserves_files(self):
        journal = self.manager.directory / 'retention-en-cours.json'
        journal.write_text('{invalid fixture', encoding='utf-8')
        self.assert_preserved()
        self.assertTrue(self.manager.data['retention_warning'])
        self.assertTrue(journal.exists())

    def test_catalogue_commit_failure_restores_files_at_next_start(self):
        self.manager._save()
        real_save = self.manager._save
        calls = 0
        def fail_commit_once():
            nonlocal calls
            calls += 1
            if calls == 2: raise OSError('simulated catalogue write failure')
            return real_save()
        with patch.object(self.manager, '_save', fail_commit_once):
            self.assertEqual(self.manager.prune(), [])
        self.assertTrue(self.manager.data['retention_warning'])
        self.manager.close()
        self.manager = BackupManager(SimpleNamespace(home=self.tmp.name))
        self.assertEqual([item['id'] for item in self.manager.data['catalog']], [self.new['id'], self.old['id']])
        for path, contents in self.contents.items():
            self.assertEqual(path.read_bytes(), contents)
        self.assertFalse((self.manager.directory / 'retention-en-cours.json').exists())

    def test_disconnected_copy_blocks_recovery_until_access_returns(self):
        self.manager._save()
        real_rename = os.rename
        calls = 0
        def interrupt_move(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2: raise SystemExit('simulated interruption')
            return real_rename(source, destination)
        with patch('backup_retention.os.rename', interrupt_move):
            with self.assertRaises(SystemExit): self.manager.prune()
        real_scandir = os.scandir
        def deny_secondary(path):
            if Path(path) == self.secondary: raise PermissionError('simulated disconnected share')
            return real_scandir(path)
        self.manager.close()
        with patch('backup_retention.os.scandir', deny_secondary):
            self.manager = BackupManager(SimpleNamespace(home=self.tmp.name))
        self.assertTrue(self.manager.data['retention_warning'])
        self.assertTrue((self.manager.directory / 'retention-en-cours.json').exists())
        self.manager.close()
        self.manager = BackupManager(SimpleNamespace(home=self.tmp.name))
        self.assertEqual(self.manager.data['retention_warning'], '')
        for path, contents in self.contents.items():
            self.assertEqual(path.read_bytes(), contents)

    def test_actual_process_exit_during_preparation_restores_all_files(self):
        self.manager._save()
        self.manager.close()
        script = '''
import os, sys
from types import SimpleNamespace
import backup_retention
from backups import BackupManager
manager = BackupManager(SimpleNamespace(home=sys.argv[1]))
original = os.rename
calls = 0
def interrupted(source, destination):
    global calls
    calls += 1
    if calls == 3: os._exit(79)
    return original(source, destination)
backup_retention.os.rename = interrupted
manager.prune()
'''
        child = subprocess.run([sys.executable, '-c', script, self.tmp.name], capture_output=True, timeout=30)
        self.assertEqual(child.returncode, 79, child.stderr.decode(errors='replace'))
        self.manager = BackupManager(SimpleNamespace(home=self.tmp.name))
        self.assertEqual([item['id'] for item in self.manager.data['catalog']], [self.new['id'], self.old['id']])
        for path, contents in self.contents.items():
            self.assertEqual(path.read_bytes(), contents)

    def test_actual_process_exit_after_commit_finishes_deletion(self):
        self.manager._save()
        self.manager.close()
        script = '''
import os, sys
from pathlib import Path
from types import SimpleNamespace
from backups import BackupManager
manager = BackupManager(SimpleNamespace(home=sys.argv[1]))
original = Path.unlink
calls = 0
def interrupted(path, *args, **kwargs):
    global calls
    if '.kiara-prune-' in path.name:
        calls += 1
        if calls == 2: os._exit(79)
    return original(path, *args, **kwargs)
Path.unlink = interrupted
manager.prune()
'''
        child = subprocess.run([sys.executable, '-c', script, self.tmp.name], capture_output=True, timeout=30)
        self.assertEqual(child.returncode, 79, child.stderr.decode(errors='replace'))
        self.manager = BackupManager(SimpleNamespace(home=self.tmp.name))
        self.assertEqual([item['id'] for item in self.manager.data['catalog']], [self.new['id']])
        self.assertTrue(all(not path.exists() for path in self.contents))
        self.assertFalse((self.manager.directory / 'retention-en-cours.json').exists())

    def test_modified_staged_file_blocks_cleanup_of_every_copy(self):
        self.manager._save()
        real_unlink = Path.unlink
        def stop_before_cleanup(path, *args, **kwargs):
            if '.kiara-prune-' in path.name: raise SystemExit('simulated interruption')
            return real_unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', stop_before_cleanup):
            with self.assertRaises(SystemExit): self.manager.prune()
        stages = list(Path(self.tmp.name).rglob('*.kiara-prune-*'))
        self.assertEqual(len(stages), 4)
        stages[-1].write_bytes(b'modified staged fixture')
        self.manager.close()
        self.manager = BackupManager(SimpleNamespace(home=self.tmp.name))
        self.assertTrue(self.manager.data['retention_warning'])
        self.assertTrue(all(path.exists() for path in stages))
        self.assertEqual(stages[-1].read_bytes(), b'modified staged fixture')
        self.assertTrue((self.manager.directory / 'retention-en-cours.json').exists())

    def test_interrupted_rollback_resumes_on_following_start(self):
        self.manager._save()
        real_rename = os.rename
        calls = 0
        def interrupt_third_move(source, destination):
            nonlocal calls
            calls += 1
            if calls == 3: raise SystemExit('simulated preparation interruption')
            return real_rename(source, destination)
        with patch('backup_retention.os.rename', interrupt_third_move):
            with self.assertRaises(SystemExit): self.manager.prune()
        self.manager.close()
        calls = 0
        def interrupt_second_restore(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2: raise SystemExit('simulated recovery interruption')
            return real_rename(source, destination)
        with patch('backup_retention.os.rename', interrupt_second_restore):
            with self.assertRaises(SystemExit): BackupManager(SimpleNamespace(home=self.tmp.name))
        self.manager = BackupManager(SimpleNamespace(home=self.tmp.name))
        for path, contents in self.contents.items():
            self.assertEqual(path.read_bytes(), contents)
        self.assertFalse((self.manager.directory / 'retention-en-cours.json').exists())
