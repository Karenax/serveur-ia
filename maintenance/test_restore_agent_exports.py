"""Checks for importing Agent exports without trusting captured paths."""

import hashlib
import json
import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path

from import_agent import import_exports
from restore_agent_exports import configure_restored_copy, prepare_manifest


class RestoreAgentExportsTests(unittest.TestCase):
    def test_import_preserves_eg2_and_leaves_legacy_index_in_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            downloads = root / 'exports'
            downloads.mkdir()
            for name in ('minipilot.db', 'project_brain.db'):
                with closing(sqlite3.connect(downloads / name)) as db:
                    db.execute('VACUUM')
            archive = downloads / 'storage.zip'
            with zipfile.ZipFile(archive, 'w') as bundle:
                bundle.writestr('storage/MultiModal/index.db', b'obsolete')
                bundle.writestr('storage/eg2/index.db', b'EG2')
                bundle.writestr('storage/mail/original.eml', b'original')
            before = archive.read_bytes()

            destination = root / 'import'
            result = import_exports(downloads, destination)

            self.assertEqual(result['files_extracted'], 2)
            self.assertFalse((destination / 'storage/MultiModal').exists())
            self.assertEqual((destination / 'storage/eg2/index.db').read_bytes(), b'EG2')
            self.assertEqual((destination / 'storage/mail/original.eml').read_bytes(), b'original')
            self.assertEqual(archive.read_bytes(), before)

    def test_manifest_checks_capture_and_can_be_repeated(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('brain', 'erp', 'storage/meeting-sessions'):
                (root / name).mkdir(parents=True)
            fragment = root / 'storage/meeting-sessions/part.wav'
            fragment.write_bytes(b'audio')
            sha = hashlib.sha256(b'audio').hexdigest()
            brain = root / 'brain/project_brain.db'
            with closing(sqlite3.connect(brain)) as db:
                db.execute('CREATE TABLE meeting_session_chunks (id TEXT, storage_path TEXT, sha256 TEXT, size_bytes INTEGER)')
                db.execute('INSERT INTO meeting_session_chunks VALUES (?,?,?,?)',
                           ('id', r'C:\Agent\storage\meeting-sessions\part.wav', sha, 5))
                db.commit()
            erp = root / 'erp/minipilot.db'
            erp.write_bytes(b'erp')
            marker = {'format': 'agent-export-staging-v1', 'status': 'staged', 'inputs': {
                'minipilot.db': {'sha256': hashlib.sha256(erp.read_bytes()).hexdigest()},
                'project_brain.db': {'sha256': hashlib.sha256(brain.read_bytes()).hexdigest()}}}
            (root / 'import.json').write_text(json.dumps(marker), encoding='utf-8')
            self.assertEqual(prepare_manifest(root), 1)
            self.assertEqual(prepare_manifest(root), 1)
            fragment.write_bytes(b'other')
            with self.assertRaises(ValueError):
                prepare_manifest(root)

    def test_configuration_disables_imported_automation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'brain').mkdir()
            index = root / 'storage/eg2/profile/index.db'
            index.parent.mkdir(parents=True)
            index.touch()
            brain = root / 'brain/project_brain.db'
            with closing(sqlite3.connect(brain)) as db:
                db.execute('CREATE TABLE app_settings (key TEXT PRIMARY KEY,value TEXT)')
                db.executemany('INSERT INTO app_settings VALUES (?,?)', [
                    ('memory', json.dumps({'index_path': r'C:\Agent\storage\eg2\profile\index.db'})),
                    ('mail', json.dumps({'auto_scan': True})),
                    ('ai', json.dumps({'enabled': True, 'api_key': 'dpapi:old'})),
                ])
                db.commit()
            configure_restored_copy(root)
            with closing(sqlite3.connect(brain)) as db:
                settings = {key: json.loads(value) for key, value in db.execute('SELECT key,value FROM app_settings')}
            self.assertEqual(Path(settings['memory']['index_path']), index)
            self.assertFalse(settings['mail']['auto_scan'])
            self.assertFalse(settings['ai']['enabled'])
            self.assertEqual(settings['ai']['api_key'], '')


if __name__ == '__main__':
    unittest.main()
