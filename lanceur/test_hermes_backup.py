"""Dedicated-root snapshots, committed WAL, portable DPAPI and safe restore."""
import base64
import copy
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hermes_backup import HermesBackup

OWNER = 'a' * 16


def machine_protection(machine):
    def protection(raw, decrypt=False):
        if decrypt:
            if not raw.startswith(machine + b':'):
                raise ValueError('Clé machine incorrecte.')
            return raw[len(machine)+1:]
        return machine + b':' + raw
    return protection


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='fred-hermes-backup-')
        self.base = Path(self.tmp.name)
        self.root = self.base / 'source' / 'hermes-fred'
        self.root.mkdir(parents=True)
        self.profile = self.root / 'profiles' / ('fred-' + OWNER)
        self.profile.mkdir(parents=True)
        (self.root / 'config.yaml').write_text('model: local-qwen\n', encoding='utf-8')
        (self.profile / 'profile.yaml').write_text('name: client\n', encoding='utf-8')
        (self.profile / 'memories').mkdir()
        (self.profile / 'memories' / 'USER.md').write_text('Préférer les euros', encoding='utf-8')
        (self.profile / '.env').write_text('PRIVATE_RUNTIME_TOKEN=secret', encoding='utf-8')
        (self.profile / 'cron').mkdir()
        (self.profile / 'cron' / 'jobs.json').write_text('{"jobs":["never replay"]}', encoding='utf-8')
        self.db = sqlite3.connect(self.profile / 'state.db')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE messages(text)'); self.db.commit()
        self.db.execute('INSERT INTO messages VALUES(?)', ('Committed WAL message',)); self.db.commit()
        with closing(sqlite3.connect(self.root / 'fred-integration.db')) as registry:
            registry.executescript('CREATE TABLE hermes_bindings(owner TEXT PRIMARY KEY, secrets BLOB);'
                                  'CREATE TABLE hermes_settings(name TEXT PRIMARY KEY, secret BLOB);'
                                  'CREATE TABLE runs(owner TEXT, state TEXT);')
            registry.execute('INSERT INTO hermes_bindings VALUES(?,?)', (OWNER, b'old:profile-private-secret'))
            registry.execute('INSERT INTO hermes_settings VALUES(?,?)', ('api', b'old:gateway-private-secret'))
            registry.execute('INSERT INTO runs VALUES(?,?)', (OWNER, 'completed')); registry.commit()
        self.backup = HermesBackup(self.root)

    def tearDown(self):
        self.db.close(); self.tmp.cleanup()

    def export(self):
        with patch('hermes_backup.protect', side_effect=machine_protection(b'old')):
            return self.backup.export({OWNER})

    def test_export_includes_committed_wal_and_excludes_runtime_and_jobs(self):
        package = self.export()
        names = set(package['files'])
        prefix = 'profiles/fred-' + OWNER + '/'
        self.assertIn(prefix + 'memories/USER.md', names)
        self.assertNotIn(prefix + '.env', names)
        self.assertNotIn(prefix + 'cron/jobs.json', names)
        self.assertFalse(any(name.endswith(('-wal', '-shm')) for name in names))
        decoded = self.backup.validate(package, {OWNER})
        with closing(sqlite3.connect(':memory:')) as snapshot:
            snapshot.deserialize(decoded[prefix+'state.db'])
            self.assertEqual(snapshot.execute('SELECT text FROM messages').fetchone()[0], 'Committed WAL message')
        with closing(sqlite3.connect(':memory:')) as registry:
            registry.deserialize(decoded['fred-integration.db'])
            self.assertEqual(registry.execute('SELECT secrets FROM hermes_bindings').fetchone()[0], b'profile-private-secret')

    def test_isolated_restore_rewraps_secrets_and_replaces_previous_data(self):
        package = self.export()
        target = self.base / 'destination' / 'hermes-fred'
        target.mkdir(parents=True)
        (target / 'old-not-retained.txt').write_text('old')
        restored = HermesBackup(target)
        with patch('hermes_backup.protect', side_effect=machine_protection(b'new')):
            result = restored.restore(package, {OWNER})
        self.assertEqual(result['files'], len(package['files']))
        self.assertFalse((target / 'old-not-retained.txt').exists())
        self.assertIn('euros', (target / 'profiles' / ('fred-'+OWNER) / 'memories' / 'USER.md').read_text(encoding='utf-8'))
        with closing(sqlite3.connect(target / 'fred-integration.db')) as registry:
            self.assertEqual(registry.execute('SELECT secrets FROM hermes_bindings').fetchone()[0], b'new:profile-private-secret')
            self.assertEqual(registry.execute('SELECT secret FROM hermes_settings').fetchone()[0], b'new:gateway-private-secret')
        self.assertTrue((self.root / 'config.yaml').exists())
        self.assertFalse(list(target.parent.glob('.hermes-fred-restore-*')))

    def test_rejects_unknown_owner_tamper_sidecars_paths_and_personal_root(self):
        package = self.export()
        with self.assertRaises(ValueError): self.backup.validate(package, {'b' * 16})
        for name in ['../.hermes/config.yaml', 'profiles/fred-'+OWNER+'/state.db-wal',
                     'profiles/fred-'+OWNER+'/.env', 'profiles/fred-'+OWNER+'/workspace/../secret',
                     'profiles/fred-'+OWNER+'/workspace/CON.txt', 'D:/outside', 'config.yaml:stream',
                     'profiles/default/config.yaml']:
            altered = copy.deepcopy(package)
            altered['files'][name] = altered['files']['config.yaml']
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.backup.validate(altered, {OWNER})
        altered = copy.deepcopy(package); altered['files']['config.yaml']['data'] = base64.b64encode(b'tampered').decode()
        with self.assertRaises(ValueError): self.backup.validate(altered, {OWNER})
        with self.assertRaises(ValueError): HermesBackup(self.base / '.hermes')

    def test_registry_ownership_and_database_integrity(self):
        package = self.export()
        with closing(sqlite3.connect(':memory:')) as registry:
            registry.deserialize(base64.b64decode(package['files']['fred-integration.db']['data']))
            registry.execute('INSERT INTO runs VALUES(?,?)', ('b'*16, 'running')); registry.commit()
            raw = registry.serialize()
        package['files']['fred-integration.db'].update(data=base64.b64encode(raw).decode(),
                                                       bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError): self.backup.validate(package, {OWNER})
        package = self.export(); raw = b'invalid sqlite'; name = 'profiles/fred-'+OWNER+'/state.db'
        package['files'][name].update(data=base64.b64encode(raw).decode(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError): self.backup.validate(package, {OWNER})

    def test_failed_restore_preserves_existing_root(self):
        package = self.export()
        target = self.base / 'destination' / 'hermes-fred'; target.mkdir(parents=True)
        (target / 'keep.txt').write_text('preserved')
        with patch('hermes_backup.protect', side_effect=ValueError('Machine refuses protection')):
            with self.assertRaises(ValueError): HermesBackup(target).restore(package, {OWNER})
        self.assertEqual((target / 'keep.txt').read_text(), 'preserved')
        self.assertFalse(list(target.parent.glob('.hermes-fred-restore-*')))

    def test_restoring_runtime_junction_never_deletes_shared_dependencies(self):
        from hermes_service import prepare_runtime
        dependencies = self.base / 'installed-runtime'
        dependencies.mkdir()
        sentinel = dependencies / 'keep-installed-library.txt'; sentinel.write_text('preserve runtime')
        runtime = {'dependencies': dependencies}
        prepare_runtime(self.root, runtime)
        package = self.export()
        self.assertFalse(any(name.startswith('installs/') for name in package['files']))
        target = self.base / 'destination' / 'hermes-fred'; target.mkdir(parents=True)
        prepare_runtime(target, runtime)
        with patch('hermes_backup.protect', side_effect=machine_protection(b'new')):
            HermesBackup(target).restore(package, {OWNER})
        self.assertEqual(sentinel.read_text(), 'preserve runtime')
        self.assertEqual((self.root / 'installs').resolve(), dependencies.resolve())
        self.assertFalse((target / 'installs').exists())


if __name__ == '__main__': unittest.main()
