"""Physical per-client isolation, updates, recovery, safe paths and private profiles."""
import base64
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from app import Controller
from core import read_json, write_json
from wg_crypto import protect
from workspace import HISTORY_RESET_ID


class ClientStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fred-client-folders-')
        self.home = Path(self.temp.name); self.c = Controller(self.home, include_legacy=False)
        self.store = self.c.remote; self.w = self.store.workspace; self.storage = self.c.client_storage
        self.a = self.store.issue('Alice'); self.b = self.store.issue('Bob')
        self.p = self.action('project_create', title='Projet Alice')['id']
        self.document = self.action('document_upload', project=self.p, title='original.txt',
            data=base64.b64encode('Original privé Alice'.encode()).decode())['id']
        self.action('personal_memory_create', text='Souvenir personnel Alice')
        self.w.history_write(self.a['id'], {'revision': 0, 'reset_id': HISTORY_RESET_ID,
            'history': {'currentId': 'a', 'conversations': [{'id': 'a', 'title': 'Alice', 'messages': [{'role': 'user', 'content': 'Historique privé Alice'}]}]}})
        self.w.history_write(self.b['id'], {'revision': 0, 'reset_id': HISTORY_RESET_ID,
            'history': {'currentId': 'b', 'conversations': [{'id': 'b', 'title': 'Bob', 'messages': [{'role': 'user', 'content': 'Secret exclusif Bob'}]}]}})

    def tearDown(self):
        self.storage.close(); self.c.operations.backups.close(); self.w.shutdown(); self.temp.cleanup()

    def action(self, action, **values): return self.w.action(self.a['id'], {'action': action, **values})
    def folder(self): return self.storage.directory(self.a['id'])

    def test_folder_database_and_readable_exports_are_owner_isolated(self):
        self.storage.synchronize(); folder = self.folder()
        with closing(sqlite3.connect(folder / 'donnees.sqlite3')) as db:
            self.assertEqual({r[0] for r in db.execute('SELECT owner FROM client_histories')}, {self.a['id']})
            self.assertEqual(db.execute('SELECT COUNT(*) FROM documents').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT text FROM personal_memories').fetchone()[0], 'Souvenir personnel Alice')
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        text = '\n'.join(p.read_text(encoding='utf-8') for p in folder.rglob('*.json'))
        self.assertIn('Historique privé Alice', text); self.assertNotIn('Secret exclusif Bob', text)
        self.assertNotIn(self.a['token'], text); self.assertNotIn(read_json(self.store.path)['clients'][0]['hash'], text)
        original = folder / 'projets' / self.p / 'documents' / self.document / 'original.txt'
        self.assertEqual(original.read_bytes(), 'Original privé Alice'.encode())
        validated = self.w.validate_backup(base64.b64encode((folder / 'donnees.sqlite3').read_bytes()).decode(), {self.a['id']})
        self.assertTrue(validated.startswith(b'SQLite format 3'))
        self.assertEqual(self.store.metadata()['clients'][0]['storage']['path'], str(folder.resolve()))

    def test_unchanged_snapshot_is_not_rewritten_and_manual_files_survive(self):
        self.storage.synchronize(); folder = self.folder()
        stamp = (folder / 'donnees.sqlite3').stat().st_mtime_ns
        (folder / 'note-administrateur.txt').write_text('À conserver', encoding='utf-8')
        self.storage.synchronize()
        self.assertEqual(stamp, (folder / 'donnees.sqlite3').stat().st_mtime_ns)
        self.assertTrue((folder / 'note-administrateur.txt').is_file())

    def test_document_delete_removes_only_managed_files(self):
        self.storage.synchronize()
        self.action('document_delete', id=self.document, revision=1)
        self.storage.synchronize()
        self.assertFalse((self.folder() / 'projets' / self.p / 'documents' / self.document / 'original.txt').exists())
        with closing(sqlite3.connect(self.folder() / 'donnees.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM documents').fetchone()[0], 0)

    def test_rename_and_archiving_keep_stable_folder_and_history(self):
        self.storage.synchronize(); folder = self.folder()
        self.store.rename(self.a['id'], 'Alice renommée'); self.storage.synchronize()
        self.assertEqual(self.folder(), folder); self.assertEqual(read_json(folder / 'client.json')['name'], 'Alice renommée')
        self.store.delete(self.a['id']); self.storage.synchronize()
        self.assertTrue(read_json(folder / 'client.json')['archived'])
        self.assertTrue(read_json(folder / 'client.json')['revoked'])
        self.assertIn('Historique privé Alice', (folder / 'historique.json').read_text(encoding='utf-8'))

    def test_missing_or_corrupt_generated_file_is_rebuilt(self):
        self.storage.synchronize(); folder = self.folder()
        (folder / 'historique.json').unlink(); (folder / 'configuration.json').write_text('corrompu')
        self.storage.synchronize()
        self.assertEqual(read_json(folder / 'historique.json')['revision'], 1)
        self.assertIn('limites', read_json(folder / 'configuration.json'))

    def test_automatic_committed_update_and_restore_refresh(self):
        before = base64.b64decode(self.w.backup()); self.storage.start()
        self.action('personal_memory_create', text='Nouveau souvenir automatique')
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if (self.folder() / 'dossier.json').is_file() and 'Nouveau souvenir automatique' in (self.folder() / 'memoires.json').read_text(encoding='utf-8'): break
            time.sleep(.1)
        self.assertIn('Nouveau souvenir automatique', (self.folder() / 'memoires.json').read_text(encoding='utf-8'))
        self.storage.close(); self.storage.dirty.clear(); self.w.restore(before)
        self.assertTrue(self.storage.dirty.is_set()); self.storage.synchronize()
        self.assertNotIn('Nouveau souvenir automatique', (self.folder() / 'memoires.json').read_text(encoding='utf-8'))

    def test_unsafe_names_and_linked_directories_are_refused(self):
        with self.assertRaises(ValueError): self.storage.directory('../autre')
        with self.assertRaises(ValueError): self.storage.safe(self.folder() / '..' / '..' / 'autre')
        # Directory junctions do not require the symlink privilege on Windows.
        import subprocess
        outside = self.home / 'autre'; outside.mkdir()
        self.storage.root.mkdir()
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(self.folder()), str(outside)], capture_output=True)
        self.assertEqual(result.returncode, 0)
        try:
            with self.assertRaises(ValueError): self.storage.synchronize()
            self.assertEqual(list(outside.iterdir()), [])
        finally:
            # Remove only the verified junction itself, never recurse into its target.
            link = self.storage.root / self.a['id']; link.rmdir()

    def test_connection_profile_is_stored_encrypted_not_in_readable_exports(self):
        self.c.wireguard.configure({'public_host': '127.0.0.1', 'listen_port': 51820})
        device = self.c.wireguard.create_android('Android synthétique', 'fixture-model')
        self.storage.synchronize(); folder = self.storage.directory(device['id'])
        encrypted = (folder / 'profil-connexion.dpapi').read_bytes()
        profile = json.loads(protect(encrypted, decrypt=True))
        self.assertNotIn(profile['token'].encode(), encrypted)
        self.assertEqual(profile['token'].split('_')[1], device['id'])
        for path in folder.rglob('*.json'): self.assertNotIn(profile['token'], path.read_text(encoding='utf-8'))

    def test_snapshot_before_restoration_cannot_be_published_after_generation_changes(self):
        snapshot = self.storage.snapshot()[0]
        from server_state import new_generation
        new_generation(self.home)
        self.assertFalse(self.storage.publish(snapshot))
        self.assertFalse((self.folder() / 'dossier.json').exists())


if __name__ == '__main__': unittest.main()
