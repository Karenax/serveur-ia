"""Lots 1–2: real isolated SQLite, Windows DPAPI and encrypted-file evidence."""
import base64
import copy
import datetime as dt
import errno
import hashlib
import io
import json
from pathlib import Path
import secrets
import sqlite3
import struct
import tempfile
import threading
import time
import unittest
import zipfile
from unittest.mock import patch
import psutil

from app import Controller
from backups import BackupManager, HEADER, _canonical, _manifest
from core import read_json, write_json
from operations import cipher
from wg_crypto import protect

PHRASE = 'phrase de récupération de test uniquement 2026'


class BackupsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='fred-backups-')
        self.home = Path(self.tmp.name)
        self.c = Controller(self.home, include_legacy=False)
        self.b = self.c.operations.backups if hasattr(self.c.operations, 'backups') else BackupManager(self.c)
        self.c.wireguard.configure({'public_host': '127.0.0.1', 'listen_port': 51820})
        self.access = self.c.remote.issue('Appareil de test')
        self.owner = self.access['id']
        self.profile = self.c.wireguard.new_peer(self.access)
        saved = self.c.wireguard.directory / 'profils-restaures.dpapi'
        saved.write_bytes(protect(json.dumps({self.owner: self.profile}).encode()))
        self.c.remote.accounts.configure({'id': self.owner, 'username': 'test', 'password': 'mot de passe test uniquement'},
                                         self.c.remote.metadata()['clients'])
        self.w = self.c.remote.workspace
        self.project = secrets.token_hex(16)
        self.document = secrets.token_hex(16)
        self.original = 'Document original UTF-8 café été'.encode()
        self.history = {'conversations': [{'id': 'test-histoire', 'title': 'Privé',
                        'messages': [{'role': 'user', 'content': 'conversations et réglages confidentiels'}]}],
                        'currentId': 'test-histoire'}
        with self.w.db() as db:
            db.execute('INSERT INTO projects(id,owner,title,instructions,revision,updated) VALUES(?,?,?,?,?,?)',
                       (self.project, self.owner, 'Projet', 'Instructions privées', 1, time.time()))
            db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?)',
                       (self.document, self.owner, self.project, 'Original', self.original.decode(), self.original, 'txt', 1, time.time()))
            db.execute('INSERT INTO client_histories VALUES(?,?,?,?)', (self.owner, json.dumps(self.history), 1, time.time()))
            db.execute('INSERT INTO policies VALUES(?,?)', (self.owner, json.dumps({'enabled': True})))
        write_json(self.home / 'derniers-reglages-valides.json', self.c.settings())
        write_json(self.home / 'appareils-activite.json', {self.owner: {'platform': 'android', 'version': '1.0.0'}})

    def tearDown(self):
        self.b.close()
        self.c.remote.workspace.shutdown()
        self.tmp.cleanup()

    def backup(self, **kwargs):
        return self.b.create(PHRASE, **kwargs)

    def join(self):
        self.assertIsNotNone(self.b.thread)
        self.b.thread.join(15)
        self.assertFalse(self.b.thread.is_alive(), 'Le travail serveur doit se terminer.')

    def test_complete_encrypted_snapshot_and_public_catalogue(self):
        result = self.backup()
        path = Path(result['file'])
        raw = path.read_bytes()
        self.assertTrue(raw.startswith(HEADER))
        for secret in (PHRASE, self.profile['token'], self.profile['wireguard']['private_key'], self.original.decode()):
            self.assertNotIn(secret.encode(), raw)
            self.assertNotIn(secret, json.dumps(self.b.status()))
            self.assertNotIn(secret, self.b.path.read_text())
        prepared = self.b.inspect({'id': result['id'], 'password': PHRASE})
        files = prepared['package']['files']
        self.assertEqual(files['profiles'][self.owner], self.profile)
        self.assertEqual(files['comptes.json'][0]['username'], 'test')
        self.assertEqual(files['reglages.json'], self.c.settings())
        memory = sqlite3.connect(':memory:')
        try:
            memory.deserialize(base64.b64decode(files['workspace']))
            self.assertEqual(memory.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(memory.execute('SELECT original FROM documents').fetchone()[0], self.original)
            self.assertEqual(json.loads(memory.execute('SELECT history FROM client_histories').fetchone()[0]), self.history)
            self.assertEqual(memory.execute('SELECT COUNT(*) FROM policies').fetchone()[0], 1)
        finally: memory.close()
        counts = prepared['summary']['counts']
        self.assertEqual(counts['documents'], 1); self.assertEqual(counts['client_histories'], 1)
        self.assertEqual(counts['document_original_bytes'], len(self.original))
        self.assertEqual(prepared['extras']['appareils-activite.json'][self.owner]['platform'], 'android')
        self.assertEqual(self.b.status()['catalog'][0]['sha256'], hashlib.sha256(raw).hexdigest())

    def test_legacy_backup_can_be_inspected_and_registered_as_protected_return_point(self):
        result = self.c.operations.backup(PHRASE)
        prepared = self.b.inspect({'file': result['file'], 'password': PHRASE})
        self.assertEqual(prepared['summary']['version'], 1)
        self.assertEqual(prepared['package']['files']['profiles'][self.owner], self.profile)
        record = self.b.register_legacy(result['file'], password=PHRASE)
        self.assertTrue(record['protected']); self.assertTrue(record['verified'])
        self.assertEqual(self.b.prune(), [])

    def test_tampered_token_and_wrong_phrase_are_refused_without_mutation(self):
        result = self.backup(); path = Path(result['file']); before = self.w.backup()
        with self.assertRaisesRegex(ValueError, 'phrase incorrecte'):
            self.b.inspect({'id': result['id'], 'password': 'phrase incorrecte suffisamment longue'})
        raw = bytearray(path.read_bytes()); raw[-6] ^= 1; path.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'phrase incorrecte'):
            self.b.inspect({'id': result['id'], 'password': PHRASE})
        self.assertEqual(self.w.backup(), before)

    def test_authenticated_but_bad_manifest_is_refused(self):
        result = self.backup(); path = Path(result['file']); blob = path.read_bytes()
        key = cipher(PHRASE, blob[11:27]); document = json.loads(key.decrypt(blob[27:]))
        document['package']['files']['reglages.json']['context'] = 8192
        path.write_bytes(blob[:27] + key.encrypt(_canonical(document)))
        with self.assertRaisesRegex(ValueError, 'Manifeste'):
            self.b.inspect({'id': result['id'], 'password': PHRASE})

    def test_unrecognised_extra_configuration_is_refused(self):
        result = self.backup(); path = Path(result['file']); blob = path.read_bytes()
        key = cipher(PHRASE, blob[11:27]); document = json.loads(key.decrypt(blob[27:]))
        document['extras']['securite/generation.json'] = {'malicious': True}
        document['manifest'] = _manifest(document['package'], document['extras'], document['security'])
        path.write_bytes(blob[:27] + key.encrypt(_canonical(document)))
        with self.assertRaisesRegex(ValueError, 'inconnue'):
            self.b.inspect({'id': result['id'], 'password': PHRASE})

    def test_automation_phrase_is_real_dpapi_and_portable_phrase_still_reads_archive(self):
        self.b.configure({'enabled': True, 'password': PHRASE})
        protected = self.b.secret_path.read_bytes()
        self.assertNotIn(PHRASE.encode(), protected)
        self.assertEqual(protect(protected, decrypt=True).decode(), PHRASE)
        self.assertTrue(self.b.status()['config']['secret_configured'])
        result = self.backup()
        self.assertEqual(self.b.inspect({'id': result['id']})['summary']['counts']['documents'], 1)
        self.b.secret_path.unlink()
        self.assertEqual(self.b.inspect({'id': result['id'], 'password': PHRASE})['summary']['counts']['documents'], 1)

    def test_explicit_automatic_setup_generates_private_portable_recovery_without_response_secret(self):
        result = self.b.setup_automatic()
        recovery = Path(result['recovery_file'])
        phrase = recovery.read_text(encoding='utf-8')
        self.assertGreaterEqual(len(phrase), 40)
        self.assertNotIn(phrase, json.dumps(result)); self.assertNotIn(phrase, self.b.path.read_text())
        self.assertEqual(protect(self.b.secret_path.read_bytes(), decrypt=True).decode(), phrase)
        self.assertTrue(result['config']['enabled'])
        archive = self.b.create(phrase)
        self.b.secret_path.unlink()
        self.assertTrue(self.b.inspect({'id': archive['id'], 'password': phrase})['summary']['verified'])
        restored_setup = self.b.setup_automatic()
        self.assertEqual(Path(restored_setup['recovery_file']).read_text(encoding='utf-8'), phrase)

    def test_automatic_setup_does_not_overwrite_a_mismatched_recovery_phrase(self):
        self.b.configure({'password': PHRASE})
        recovery = self.b.directory / 'phrase-recuperation.txt'
        recovery.write_text('different manual recovery phrase for testing', encoding='utf-8')
        before = recovery.read_bytes()
        with self.assertRaisesRegex(ValueError, 'ne correspond pas'): self.b.setup_automatic()
        self.assertEqual(recovery.read_bytes(), before)

    def test_schedule_missed_deadline_catches_up_once_after_restart(self):
        self.b.configure({'enabled': True, 'password': PHRASE})
        with self.b.lock:
            self.b.data['next_due'] = time.time() - 7 * 86400
            self.b._save()
        self.b.close(); self.b = BackupManager(self.c)
        self.assertTrue(self.b.tick())
        self.join()
        self.assertEqual(self.b.status()['job']['state'], 'succeeded')
        self.assertEqual(len(self.b.status()['catalog']), 1)
        self.assertFalse(self.b.tick())
        self.assertGreater(self.b.data['next_due'], time.time())

    def test_interrupted_automatic_job_is_durable_and_retried(self):
        self.b.configure({'enabled': True, 'password': PHRASE})
        with self.b.lock:
            self.b.data['job'] = {'state': 'running', 'kind': 'automatic', 'message': ''}
            self.b._save()
        self.b.close(); self.b = BackupManager(self.c)
        self.assertEqual(self.b.status()['job']['state'], 'failed')
        self.assertTrue(self.b.tick()); self.join()
        self.assertEqual(self.b.status()['job']['state'], 'succeeded')

    def test_bad_dpapi_secret_does_not_start_or_leak_error_and_retries_are_bounded(self):
        self.b.configure({'enabled': True, 'password': PHRASE})
        self.b.secret_path.write_bytes(b'broken-secret-private-test')
        self.b.data['next_due'] = time.time() - 1
        self.assertFalse(self.b.tick())
        self.assertEqual(self.b.status()['catalog'], [])
        self.assertGreater(self.b.data['retry_due'], time.time() + 200)
        self.assertNotIn('broken-secret', json.dumps(self.b.status()))

    def test_next_due_daily_and_weekly_local_time(self):
        stamp = dt.datetime(2026, 10, 10, 4, 0).timestamp()
        cfg = {**self.b.data['config'], 'time': '03:00'}
        next_day = dt.datetime.fromtimestamp(self.b.next_due(cfg, stamp))
        self.assertEqual(next_day, dt.datetime(2026, 10, 11, 3, 0))
        cfg.update(frequency='weekly', weekday=0)
        self.assertEqual(dt.datetime.fromtimestamp(self.b.next_due(cfg, stamp)), dt.datetime(2026, 10, 12, 3, 0))

    def test_schedule_validation_and_no_secret_activation(self):
        for values in ({'enabled': True}, {'time': '25:02'}, {'time': '3:00'}, {'frequency': 'hourly'},
                       {'weekday': True}, {'destination': 'relative'}, {'retention': {'daily': -1, 'weekly': 4, 'monthly': 6}},
                       {'enabled': 1}):
            with self.subTest(values=values), self.assertRaises(ValueError): self.b.configure(values)
        self.assertFalse(self.b.status()['config']['enabled'])

    def test_secondary_copy_success_and_retry_preserves_local_success(self):
        second = self.home / 'second'
        self.b.configure({'secondary_destination': str(second)})
        result = self.backup()
        copied = Path(result['secondary']['file'])
        self.assertEqual(copied.read_bytes(), Path(result['file']).read_bytes())
        blocked = self.home / 'blocked'; blocked.write_bytes(b'not a directory')
        self.b.configure({'secondary_destination': str(blocked)})
        other = self.backup(kind='automatic')
        self.assertEqual(other['secondary']['status'], 'error')
        self.assertTrue(Path(other['file']).exists()); self.assertTrue(self.b.status()['last_success'])
        blocked.unlink(); blocked.mkdir()
        retry = next(r for r in self.b.data['catalog'] if r['id'] == other['id'])
        retry['secondary']['next_retry'] = 0
        self.assertTrue(self.b.tick()); self.join()
        self.assertEqual(retry['secondary']['status'], 'copied')
        self.assertEqual(Path(retry['secondary']['file']).read_bytes(), Path(other['file']).read_bytes())

    def test_disk_full_has_no_partial_archive_and_keeps_previous(self):
        before = self.backup(); good = Path(before['file']).read_bytes()
        with patch('backups.shutil.disk_usage', return_value=type('Space', (), {'free': 0})()):
            with self.assertRaisesRegex(ValueError, 'Espace disque insuffisant'): self.backup()
        self.assertEqual(Path(before['file']).read_bytes(), good)
        self.assertEqual(len(self.b.status()['catalog']), 1)
        self.assertEqual(list(self.b.directory.glob('*.tmp')), [])

    def test_publish_failure_has_no_partial_archive_and_no_exception_secret(self):
        self.b.start({'password': PHRASE})
        self.join()
        before = len(self.b.status()['catalog'])
        with patch('backups._atomic_bytes', side_effect=OSError('secret-token-from-operating-system')):
            self.b.start({'password': PHRASE}); self.join()
        self.assertEqual(self.b.status()['job']['state'], 'failed')
        self.assertEqual(len(self.b.status()['catalog']), before)
        self.assertNotIn('secret-token', json.dumps(self.b.status()))
        self.assertEqual(list(self.b.directory.glob('*.tmp')), [])

    def test_single_worker_and_controller_locks_released_during_encryption(self):
        entered = threading.Event(); release = threading.Event()
        original = self.b._decode
        def slow(*args, **kwargs):
            entered.set()
            if not release.wait(10): raise TimeoutError('test')
            return original(*args, **kwargs)
        with patch.object(self.b, '_decode', side_effect=slow):
            try:
                self.b.start({'password': PHRASE})
                self.assertTrue(entered.wait(10))
                self.assertEqual(self.b.status()['job']['phase'], 'verify')
                for lock in (self.c.lock, self.c.wireguard.lock, self.c.remote.lock, self.w.lock):
                    self.assertTrue(lock.acquire(blocking=False)); lock.release()
                with self.assertRaisesRegex(ValueError, 'déjà en cours'): self.b.start({'password': PHRASE})
                with self.assertRaises(ValueError): self.b.configure({'time': '04:00'})
            finally: release.set(); self.join()
        self.assertEqual(self.b.status()['job']['state'], 'succeeded')

    def test_restoration_exclusivity_rejects_backup_without_reentrant_deadlock(self):
        with self.b.exclusive():
            with self.assertRaisesRegex(ValueError, 'déjà en cours'): self.backup()
            self.assertFalse(self.b.tick())
        self.assertTrue(self.backup())

    def test_retention_calendar_buckets_latest_manual_and_return_points_survive(self):
        example = self.backup()
        base = copy.deepcopy(self.b.data['catalog'][0]); self.b.data['catalog'] = []
        now = dt.datetime(2026, 10, 10, 3).timestamp()
        records = []
        for days in range(100):
            stamp = now - days * 86400; identity = secrets.token_hex(12)
            target = self.b.directory / ('fred-' + dt.datetime.fromtimestamp(stamp).strftime('%Y%m%d-%H%M%S') + '-' + identity + '.qwenbackup')
            target.write_bytes(b'valid-calendar-fixture')
            record = {**copy.deepcopy(base), 'id': identity, 'file': str(target), 'timestamp': stamp, 'kind': 'automatic',
                      'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'size': target.stat().st_size}
            records.append(record)
        records[-1]['protected'] = True
        manual = copy.deepcopy(records[-2]); manual.update(id=base['id'], file=example['file'], kind='manual')
        self.b.data['catalog'] = records + [manual]
        removed = self.b.prune()
        remaining = self.b.data['catalog']
        self.assertTrue(removed); self.assertLess(len(remaining), 25)
        self.assertIn(records[0], remaining); self.assertIn(records[-1], remaining); self.assertIn(manual, remaining)
        self.assertTrue(all(Path(r['file']).exists() for r in remaining))

    def test_failed_secondary_and_tampered_archive_are_not_deleted_by_retention(self):
        result = self.backup(kind='automatic')
        old = copy.deepcopy(self.b.data['catalog'][0]); old['id'] = secrets.token_hex(12)
        old['timestamp'] -= 10 * 86400
        path = self.b.directory / ('fred-20260101-030000-' + old['id'] + '.qwenbackup')
        path.write_bytes(b'unexpected modification'); old['file'] = str(path)
        self.b.data['catalog'].append(old)
        self.b.data['config']['retention'] = {'daily': 0, 'weekly': 0, 'monthly': 0}
        self.assertEqual(self.b.prune(), [])
        old['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        old['secondary'] = {'status': 'error', 'attempts': 1, 'file': ''}
        self.assertEqual(self.b.prune(), [])
        self.assertTrue(path.exists()); self.assertTrue(Path(result['file']).exists())

    def test_recovered_unpublished_catalog_entry_requires_explicit_verification(self):
        result = self.backup()
        self.b.data['catalog'] = []; self.b._save(); self.b.close()
        self.b = BackupManager(self.c)
        self.assertEqual(len(self.b.status()['catalog']), 1)
        record = self.b.status()['catalog'][0]
        self.assertFalse(record['verified']); self.assertTrue(record['protected'])
        self.b.inspect({'id': record['id'], 'password': PHRASE})
        self.assertTrue(self.b.status()['catalog'][0]['verified'])
        self.assertTrue(Path(result['file']).exists())

    def test_revocation_ledger_snapshot_is_separate_from_restore_files(self):
        ledger = self.home / 'securite' / 'revocations.json'
        write_json(ledger, {'version': 1, 'revocations': {self.owner: {'epoch': time.time(), 'reason': 'test'}}})
        result = self.backup()
        prepared = self.b.inspect({'id': result['id'], 'password': PHRASE})
        self.assertIn(self.owner, prepared['security']['revocations.json']['revocations'])
        self.assertNotIn('revocations.json', prepared['package']['files'])
        self.assertNotIn('revocations.json', prepared['extras'])
        self.assertTrue(prepared['summary']['revocation_ledger'])

    def test_restore_failure_after_schedule_mutation_restores_previous_policy(self):
        archive = self.backup()
        self.b.configure({'enabled': True, 'password': PHRASE, 'time': '18:27'})
        before = copy.deepcopy(self.b.status()['config'])
        with patch.object(self.c.remote.revocations, 'merge', side_effect=OSError('simulated ledger write failure')):
            with self.assertRaises(OSError): self.c.operations.restore({'file': archive['file'], 'password': PHRASE})
        self.assertEqual(self.b.status()['config'], before)
        self.assertFalse(self.c.remote.maintenance)

    def test_failed_rollback_keeps_maintenance_and_requires_explicit_recovery(self):
        archive = self.backup()
        before = self.c.settings(); self.c.save({**before, 'context': 8192})
        changed = self.c.settings()
        with (patch.object(self.c.wireguard, 'save_vault', side_effect=OSError('simulated mutation failure')),
              patch('restoration.recover', side_effect=RuntimeError('simulated rollback write failure'))):
            with self.assertRaises(RuntimeError): self.c.operations.restore({'file': archive['file'], 'password': PHRASE})
        self.assertTrue(self.c.remote.maintenance); self.assertTrue(self.w.maintenance)
        self.assertEqual(read_json(self.home / 'securite' / 'restauration.json')['state'], 'applying')
        self.assertFalse(self.b.tick())
        with self.assertRaisesRegex(ValueError, 'maintenance'): self.backup()
        with self.assertRaisesRegex(ValueError, 'maintenance'): self.b.start({'password': PHRASE})
        recovered = self.c.operations.restorations.recover_now()
        self.assertEqual(recovered['state'], 'recovered'); self.assertFalse(self.c.remote.maintenance)
        self.assertEqual(self.c.settings(), changed)

    def test_foreign_backup_suspends_devices_even_if_destination_already_has_an_access(self):
        archive = self.backup()
        with tempfile.TemporaryDirectory(prefix='fred-foreign-backup-') as destination:
            fresh = Controller(destination, include_legacy=False)
            try:
                fresh.wireguard.configure({'public_host': '127.0.0.1', 'listen_port': 51820})
                fresh.wireguard.create_android('Unrelated existing device', 'fixture-model')
                fresh.operations.restore({'file': archive['file'], 'password': PHRASE})
                self.assertTrue(all(row['suspended'] for row in fresh.remote.metadata()['clients']))
                self.assertFalse(fresh.remote.valid_owner(self.owner))
            finally: fresh.operations.backups.close(); fresh.remote.workspace.shutdown()

    def test_restore_then_backup_ignores_orphan_windows_exe_and_preserves_registered_profile(self):
        archive_a = self.backup()
        access_b = self.c.remote.issue('PC créé après sauvegarde A')
        profile_b = self.c.wireguard.new_peer(access_b)
        directory = self.home / 'clients'
        from wg_crypto import private_directory
        private_directory(directory)
        exe_b = directory / (access_b['id'] + '.exe')
        raw_profile = json.dumps(profile_b).encode('utf-8')
        # Exercise the actual personal EXE footer contract; no executable is launched.
        exe_b.write_bytes(b'MZ-isolated-Windows-client-fixture' + raw_profile + struct.pack('<I', len(raw_profile)) + b'QWENPROFILE1')
        original_exe = exe_b.read_bytes()
        before = self.backup()
        self.assertIn(access_b['id'], self.b.inspect({'id': before['id'], 'password': PHRASE})['package']['files']['profiles'])
        self.c.operations.restore({'file': archive_a['file'], 'password': PHRASE})
        self.assertNotIn(access_b['id'], {row['id'] for row in self.c.remote.metadata()['clients']})
        self.assertEqual(exe_b.read_bytes(), original_exe)
        # Recovered maps can also contain a profile outside the restored registry.
        saved = self.c.wireguard.directory / 'profils-restaures.dpapi'
        restored_profiles = json.loads(protect(saved.read_bytes(), decrypt=True))
        restored_profiles[access_b['id']] = profile_b
        saved.write_bytes(protect(json.dumps(restored_profiles).encode()))
        after = self.backup()
        profiles = self.b.inspect({'id': after['id'], 'password': PHRASE})['package']['files']['profiles']
        self.assertEqual(profiles, {self.owner: self.profile})
        legacy = self.c.operations.backup(PHRASE)
        legacy_profiles = self.b.inspect({'file': legacy['file'], 'password': PHRASE})['package']['files']['profiles']
        self.assertEqual(legacy_profiles, {self.owner: self.profile})
        self.assertEqual(exe_b.read_bytes(), original_exe)
        self.assertIn(access_b['id'], json.loads(protect(saved.read_bytes(), decrypt=True)))

    def test_archived_registered_profile_is_kept_while_invalid_orphan_files_are_ignored(self):
        from wg_crypto import private_directory
        directory = self.home / 'clients'; private_directory(directory)
        orphan = secrets.token_hex(8)
        exe = directory / (orphan + '.exe'); exe.write_bytes(b'tiny malformed orphan')
        android = directory / (orphan + '.fred-android'); android.write_bytes(b'not JSON')
        self.c.wireguard.delete(self.owner)
        archive = self.backup()
        profiles = self.b.inspect({'id': archive['id'], 'password': PHRASE})['package']['files']['profiles']
        self.assertEqual(profiles, {self.owner: self.profile})
        self.assertEqual(exe.read_bytes(), b'tiny malformed orphan'); self.assertEqual(android.read_bytes(), b'not JSON')

    def test_16_mib_original_document_backup_restore_volume_and_resource_evidence(self):
        # Eight valid DOCX imports respect the existing 2 MiB/file and 20 MiB/owner limits.
        from docx import Document
        document = Document(); document.add_paragraph('Original à conserver : été, café et données privées.')
        stream = io.BytesIO(); document.save(stream); template = stream.getvalue()
        measured = io.BytesIO(template)
        with zipfile.ZipFile(measured, 'a', compression=zipfile.ZIP_STORED) as archive:
            archive.writestr('word/media/proof.bin', b'')
        original_stream = io.BytesIO(template)
        with zipfile.ZipFile(original_stream, 'a', compression=zipfile.ZIP_STORED) as archive:
            archive.writestr('word/media/proof.bin', b'\x7f' * (2 * 1024 * 1024 - len(measured.getvalue())))
        original = original_stream.getvalue()
        self.assertEqual(len(original), 2 * 1024 * 1024)
        ids = []
        for index in range(8):
            imported = self.w.action(self.owner, {'action': 'document_upload', 'project': self.project,
                'title': 'Original-' + str(index) + '.docx', 'data': base64.b64encode(original).decode()})
            ids.append(imported['id'])
        baseline = psutil.Process().memory_info().rss
        peak = [baseline]; stop = threading.Event(); capture_seconds = []
        def sample():
            while not stop.wait(.01): peak[0] = max(peak[0], psutil.Process().memory_info().rss)
        sampler = threading.Thread(target=sample, daemon=True); sampler.start()
        capture = self.b._capture
        def measured_capture():
            start = time.monotonic()
            try: return capture()
            finally: capture_seconds.append(time.monotonic() - start)
        started = time.monotonic()
        try:
            with patch.object(self.b, '_capture', side_effect=measured_capture): archive = self.backup()
            backup_seconds = time.monotonic() - started
            with self.w.db() as db:
                for identity in ids: db.execute('UPDATE documents SET original=? WHERE id=?', (b'changed after snapshot', identity))
            started = time.monotonic()
            self.c.operations.restore({'file': archive['file'], 'password': PHRASE})
            restore_seconds = time.monotonic() - started
            total = 0
            with self.w.db() as db:
                for identity in ids:
                    restored = db.execute('SELECT original FROM documents WHERE id=?', (identity,)).fetchone()[0]
                    self.assertEqual(hashlib.sha256(restored).digest(), hashlib.sha256(original).digest())
                    total += len(restored)
            self.assertEqual(total, 16 * 1024 * 1024)
            self.assertLess(backup_seconds, 30); self.assertLess(restore_seconds, 30)
            self.assertLess(peak[0] - baseline, 1024 * 1024 * 1024)
            print('\nVOLUME_PROOF ' + json.dumps({'document_count': len(ids), 'original_bytes': total, 'archive_bytes': Path(archive['file']).stat().st_size,
                  'backup_seconds': round(backup_seconds, 3), 'restore_seconds': round(restore_seconds, 3),
                  'snapshot_lock_seconds': round(capture_seconds[0], 3), 'peak_rss_bytes': peak[0],
                  'rss_increase_bytes': peak[0] - baseline, 'sha256_match': True}))
        finally: stop.set(); sampler.join(2)


if __name__ == '__main__': unittest.main(verbosity=2)
