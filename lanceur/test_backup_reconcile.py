"""Catalogue recovery with isolated files and simulated access failures."""
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from backups import BackupManager, HEADER


class ReconcileTests(unittest.TestCase):
    def test_unreadable_directory_keeps_catalogue_and_existing_error(self):
        with tempfile.TemporaryDirectory(prefix='kiara-catalogue-test-') as directory:
            manager = BackupManager(SimpleNamespace(home=directory))
            try:
                existing = {'id': 'existing', 'file': 'known-fixture', 'timestamp': 1}
                manager.data['catalog'] = [existing.copy()]
                manager.data['last_error'] = 'Earlier failure'
                with patch('backups.os.listdir', side_effect=PermissionError('private directory')):
                    manager._reconcile()
                self.assertEqual(manager.data['catalog'], [existing])
                self.assertEqual(manager.data['last_error'], 'Earlier failure')
                self.assertTrue(manager.data['reconcile_warning'])
                self.assertNotIn('private directory', manager.data['reconcile_warning'])
            finally:
                manager.close()

    def test_one_unreadable_archive_does_not_block_other_recovery(self):
        with tempfile.TemporaryDirectory(prefix='kiara-catalogue-test-') as directory:
            controller = SimpleNamespace(home=directory)
            manager = BackupManager(controller)
            folder = Path(directory) / 'sauvegardes'
            denied = folder / ('fred-20261116-030000-' + 'a' * 24 + '.qwenbackup')
            readable = folder / ('fred-20261117-030000-' + 'b' * 24 + '.qwenbackup')
            denied.write_bytes(HEADER + b'restricted fixture')
            readable.write_bytes(HEADER + b'recoverable fixture')
            original = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (denied, readable)}
            manager.close()
            real_open = Path.open

            def selective_open(path, *args, **kwargs):
                if path == denied:
                    raise PermissionError('simulated private path')
                return real_open(path, *args, **kwargs)

            with patch.object(Path, 'open', selective_open):
                resumed = BackupManager(controller)
            try:
                self.assertEqual([entry['id'] for entry in resumed.data['catalog']], ['b' * 24])
                self.assertFalse(resumed.data['catalog'][0]['verified'])
                self.assertTrue(resumed.data['catalog'][0]['protected'])
                warning = resumed.data['reconcile_warning']
                self.assertTrue(warning)
                self.assertEqual(resumed.status()['reconcile_warning'], warning)
                self.assertNotIn('simulated private path', warning)
                self.assertNotIn(str(denied), warning)
                self.assertEqual(original, {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in original})

                resumed._reconcile()
                self.assertEqual({entry['id'] for entry in resumed.data['catalog']}, {'a' * 24, 'b' * 24})
                self.assertEqual(resumed.data['reconcile_warning'], '')
            finally:
                resumed.close()

    def test_failed_hash_does_not_register_partial_record(self):
        with tempfile.TemporaryDirectory(prefix='kiara-catalogue-test-') as directory:
            manager = BackupManager(SimpleNamespace(home=directory))
            try:
                target = Path(directory) / 'sauvegardes' / ('fred-20261116-030000-' + 'c' * 24 + '.qwenbackup')
                content = HEADER + b'fixture preserved after hash failure'
                target.write_bytes(content)
                with patch('backups._hash_file', side_effect=OSError('simulated read failure')):
                    manager._reconcile()
                self.assertEqual(manager.data['catalog'], [])
                self.assertTrue(manager.data['reconcile_warning'])
                self.assertEqual(target.read_bytes(), content)
                manager._reconcile()
                self.assertEqual([item['id'] for item in manager.data['catalog']], ['c' * 24])
                self.assertEqual(manager.data['reconcile_warning'], '')
            finally:
                manager.close()
