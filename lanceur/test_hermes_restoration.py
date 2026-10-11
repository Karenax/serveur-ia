"""Hermes participates in encrypted Fred snapshots and durable crash recovery."""
import base64
from contextlib import closing
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import Controller
from core import ROOT, PYTHON, read_json, write_json
from hermes_accounts import HermesAccounts
from hermes_backup import HermesBackup
from restoration import atomic, recover, validate_package
from wg_crypto import protect

PHRASE = 'Hermes isolated backup recovery phrase 2026'


class FixtureFacade:
    def __init__(self, home, owner):
        self.lock = threading.RLock(); self.started = True
        def create(accounts, owner, port):
            directory = accounts.root / 'profiles' / ('fred-'+owner); directory.mkdir(parents=True, exist_ok=True)
            (directory / 'profile.yaml').write_text('description: isolated restoration fixture\n', encoding='utf-8')
        self.accounts = HermesAccounts(home, profile_factory=create)
        self.accounts.ensure(owner)
        self.accounts.gateway_key()
        self.conversations = SimpleNamespace(lock=threading.RLock(), active={}, admission_paused=False, closed=False)
        self.stops = self.starts = self.closes = 0
        self.service = SimpleNamespace(close=self.stop, start=self.start, lock=threading.RLock())

    def stop(self):
        self.stops += 1; self.accounts.clear_runtime_secrets()
    def start(self):
        self.starts += 1
        for owner in self.accounts.owners(ready_only=True): self.accounts.materialize(owner)
    def close(self):
        self.closes += 1; self.stop(); self.started = False
        self.conversations.closed = True; self.conversations.active.clear()
    def public(self, owner): return self.accounts.public(owner)
    def status(self): return {'enabled': True, 'available': self.started}


class HermesRestorationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='fred-hermes-restore-')
        self.home = Path(self.tmp.name)
        self.controller = Controller(self.home, include_legacy=False)
        c = self.controller
        c.wireguard.configure({'public_host': '127.0.0.1', 'listen_port': 51820})
        self.owner = c.wireguard.create_android('Hermes restoration fixture', 'fixture-model')['id']
        c.remote.configure({'enabled': False, 'url': 'wireguard://10.77.0.1:8766'})
        write_json(self.home / 'hermes-integration.json', {'enabled': True, 'port': 8643, 'private_port': 8768})
        self.facade = FixtureFacade(self.home, self.owner)
        c.hermes = c.remote.hermes = c.remote.workspace.hermes = self.facade
        self.root = self.home / 'hermes-fred'
        self.memory = self.root / 'profiles' / ('fred-'+self.owner) / 'memories' / 'USER.md'
        self.memory.parent.mkdir(); self.memory.write_text('Préférence enregistrée avant sauvegarde', encoding='utf-8')
        self.rebuilt = []
        def recreate(start=False):
            facade = FixtureFacade(self.home, self.owner)
            facade.started = start
            self.rebuilt.append(start)
            c.hermes = c.remote.hermes = c.remote.workspace.hermes = facade
        c.recreate_hermes = recreate

    def tearDown(self):
        self.controller.operations.backups.close(); self.controller.remote.workspace.shutdown()
        self.tmp.cleanup()

    def backup(self): return self.controller.operations.backups.create(PHRASE)
    def restore(self, archive):
        return self.controller.operations.restore({'file': archive['file'], 'password': PHRASE})

    def test_model_sharing_policy_roundtrip_and_invalid_policy_rejected(self):
        policy = {'version': 1, 'share_all': True, 'shared_accounts': [self.owner]}
        write_json(self.home / 'hermes-models.json', policy)
        archive = self.backup()
        write_json(self.home / 'hermes-models.json', {'version': 1, 'share_all': False, 'shared_accounts': []})
        self.restore(archive)
        self.assertEqual(policy, read_json(self.home / 'hermes-models.json'))
        self.assertEqual('Préférence enregistrée avant sauvegarde', self.memory.read_text(encoding='utf-8'))
        for invalid in ({'share_all': 'true'}, {'shared_accounts': ['foreign-account']},
                        {'share_all': True, 'api_key': 'must-not-be-imported'}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_package(self.controller, {'version': 1, 'files': {'hermes-models.json': invalid}})

    def test_both_encrypted_formats_capture_profile_and_portable_credentials(self):
        archive = self.backup()
        inspected = self.controller.operations.backups.inspect({'file': archive['file'], 'password': PHRASE})
        files = inspected['package']['files']
        self.assertIn('hermes', files); self.assertTrue(files['hermes-integration.json']['enabled'])
        self.assertEqual(inspected['summary']['counts']['hermes_profiles'], 1)
        self.assertEqual(self.facade.stops, 1); self.assertEqual(self.facade.starts, 1)
        self.assertFalse(self.facade.conversations.admission_paused)
        self.assertTrue((self.memory.parent.parent / '.env').exists())
        self.assertFalse(any(name.endswith('/.env') for name in files['hermes']['files']))
        token = self.facade.accounts.credentials(self.owner)['api_key']
        self.assertNotIn(token.encode(), Path(archive['file']).read_bytes())
        self.assertNotIn(token, json.dumps(self.controller.operations.backups.status()))
        legacy = self.controller.operations.backup(PHRASE)
        older = self.controller.operations.backups.inspect({'file': legacy['file'], 'password': PHRASE})
        self.assertIn('hermes', older['package']['files'])

    def test_complete_restore_rebuilds_facade_and_preserves_native_data(self):
        archive = self.backup(); credentials = self.facade.accounts.credentials(self.owner)
        self.memory.write_text('Mémoire après sauvegarde', encoding='utf-8')
        result = self.restore(archive)
        self.assertTrue(Path(result['rollback']).is_file())
        self.assertIn('avant sauvegarde', self.memory.read_text(encoding='utf-8'))
        self.assertGreaterEqual(self.facade.closes, 1)
        self.assertEqual(self.rebuilt, [True])
        self.assertEqual(self.controller.hermes.accounts.credentials(self.owner)['api_key'], credentials['api_key'])
        self.assertIsNone(self.controller.operations.hermes_pause)
        self.assertFalse(self.controller.remote.metadata()['enabled'])

    def test_failed_restore_returns_current_hermes_state(self):
        archive = self.backup()
        self.memory.write_text('État courant à conserver après échec', encoding='utf-8')
        with patch.object(self.controller.wireguard, 'save_vault', side_effect=OSError('fixture write failure')):
            with self.assertRaises(OSError): self.restore(archive)
        self.assertIn('État courant', self.memory.read_text(encoding='utf-8'))
        self.assertEqual(read_json(self.home/'securite/restauration.json')['state'], 'recovered')
        self.assertEqual(self.rebuilt, [True])

    def test_crash_journal_recovers_hermes_before_any_runtime_starts(self):
        # The actual child process dies after changing private profile files.
        with self.controller.operations.hermes_snapshot():
            snapshot = HermesBackup(self.root).export({self.owner})
        originals = {'hermes-fred': base64.b64encode(json.dumps(snapshot).encode()).decode(),
                     'acces-distants.json': base64.b64encode((self.home/'acces-distants.json').read_bytes()).decode(),
                     'hermes-integration.json': base64.b64encode((self.home/'hermes-integration.json').read_bytes()).decode()}
        atomic(self.home/'securite/retour-restauration.dpapi', protect(json.dumps(originals).encode()))
        write_json(self.home/'securite/restauration.json', {'state': 'applying', 'active': True})
        script = "import os,sys; from pathlib import Path; Path(sys.argv[1]).write_text('crashed new state',encoding='utf-8'); os._exit(47)"
        result = subprocess.run([str(PYTHON), '-c', script, str(self.memory)], capture_output=True)
        self.assertEqual(result.returncode, 47)
        self.facade.close()
        recovered = recover(self.home)
        self.assertEqual(recovered['state'], 'recovered')
        self.assertIn('avant sauvegarde', self.memory.read_text(encoding='utf-8'))
        self.assertEqual(self.facade.starts, 1)  # Recovery itself never executes an agent.

    def test_failed_recovery_can_resume_from_another_thread(self):
        archive = self.backup()
        self.memory.write_text('Keep during rollback retry', encoding='utf-8')
        with patch.object(self.controller.wireguard, 'save_vault', side_effect=OSError('fixture write failure')), \
                patch('restoration.recover', side_effect=OSError('fixture storage unavailable')):
            with self.assertRaises(OSError): self.restore(archive)
        self.assertTrue(self.controller.remote.maintenance)
        self.assertEqual(read_json(self.home/'securite/restauration.json')['state'], 'applying')
        outcome = []
        def retry():
            try: outcome.append(self.controller.operations.restorations.recover_now())
            except Exception as error: outcome.append(error)
        thread = threading.Thread(target=retry); thread.start(); thread.join(20)
        self.assertFalse(thread.is_alive()); self.assertIsInstance(outcome[0], dict, outcome)
        self.assertEqual(outcome[0]['state'], 'recovered')
        self.assertIn('Keep', self.memory.read_text(encoding='utf-8'))
        self.assertFalse(self.controller.remote.maintenance)

    def test_active_run_defers_snapshot_without_stopping_service(self):
        self.facade.conversations.active[self.owner] = {'request_id': 'fixture-active'}
        with self.assertRaises(ValueError): self.backup()
        self.assertEqual(self.facade.stops, 0)
        self.assertFalse(self.facade.conversations.admission_paused)
        self.assertIsNone(self.controller.operations.hermes_pause)

    def test_background_preparation_defers_snapshot_without_stopping_service(self):
        workspace = self.controller.remote.workspace
        workspace.running['fixture-preparing-job'] = threading.Event()
        try:
            with self.assertRaises(ValueError): self.backup()
        finally: workspace.running.clear()
        self.assertEqual(self.facade.stops, 0)
        self.assertFalse(self.facade.conversations.admission_paused)
        self.assertIsNone(self.controller.operations.hermes_pause)

    def test_snapshot_can_coexist_with_remote_revocation_lock_order(self):
        # Revocation owns remote before cancelling Workspace jobs. A snapshot
        # must never retain Workspace while waiting for that remote lock.
        waiting = threading.Event(); held = threading.Event(); release = threading.Event()
        errors = []

        class BoundedLock:
            def __init__(self, lock, observe=False): self.lock, self.observe = lock, observe
            def acquire(self):
                if self.observe and threading.current_thread().name == 'fixture-snapshot': waiting.set()
                if not self.lock.acquire(timeout=3): raise RuntimeError('Snapshot lock order is inverted')
            def release(self): self.lock.release()
            def __enter__(self): self.acquire(); return self
            def __exit__(self, *args): self.release()

        c = self.controller
        c.remote.lock = BoundedLock(c.remote.lock, observe=True)
        c.remote.workspace.lock = BoundedLock(c.remote.workspace.lock)
        self.facade.projects = SimpleNamespace(lock=threading.RLock())

        def revoke():
            try:
                with c.remote.lock:
                    held.set()
                    if not release.wait(5): raise RuntimeError('Fixture did not release revocation')
                    c.remote.workspace.cancel_owner(self.owner)
            except Exception as error: errors.append(error)

        def snapshot():
            try:
                with c.operations.hermes_snapshot(), c.remote.lock: pass
            except Exception as error: errors.append(error)

        revocation = threading.Thread(target=revoke, name='fixture-revocation')
        backup = threading.Thread(target=snapshot, name='fixture-snapshot')
        revocation.start()
        try:
            self.assertTrue(held.wait(5)); backup.start()
            self.assertTrue(waiting.wait(5))
        finally:
            release.set(); revocation.join(10)
            if backup.ident is not None: backup.join(10)
        self.assertFalse(revocation.is_alive()); self.assertFalse(backup.is_alive())
        self.assertEqual(errors, [])
        self.assertFalse(self.facade.conversations.admission_paused)

    def test_invalid_configuration_or_tampered_hermes_data_refused_without_pause(self):
        archive = self.backup()
        inspected = self.controller.operations.backups.inspect({'file': archive['file'], 'password': PHRASE})
        altered = copy.deepcopy(inspected['package'])
        altered['files']['hermes-integration.json']['private_port'] = 8643
        with self.assertRaises(ValueError): validate_package(self.controller, altered)
        altered = copy.deepcopy(inspected['package'])
        first = next(iter(altered['files']['hermes']['files'].values())); first['sha256'] = '0'*64
        with self.assertRaises(ValueError): validate_package(self.controller, altered)
        self.assertEqual(self.facade.closes, 0)

    def test_saved_running_turn_restores_as_interrupted(self):
        from hermes_conversations import SCHEMA
        with self.facade.accounts._db() as db:
            db.executescript(SCHEMA)
            db.execute('INSERT INTO agent_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (self.owner, 'a'*32, 'conversation', 'session', 'fingerprint', 'remote-run',
                        'running', '', '', '[]', '{}', '[]', 1, 1))
        archive = self.backup()
        self.restore(archive)
        with self.controller.hermes.accounts._db() as db:
            self.assertEqual(db.execute('SELECT state FROM agent_runs').fetchone()[0], 'interrupted')

    def test_preparation_failure_releases_pause_and_rebuilds_without_mutation(self):
        archive = self.backup()
        self.memory.write_text('Unchanged after stop failure', encoding='utf-8')
        with patch.object(self.facade, 'close', side_effect=RuntimeError('fixture stop failure')):
            with self.assertRaises(RuntimeError): self.restore(archive)
        self.assertEqual(self.memory.read_text(encoding='utf-8'), 'Unchanged after stop failure')
        self.assertIsNone(self.controller.operations.hermes_pause)
        self.assertFalse(self.controller.remote.maintenance)
        self.assertEqual(self.rebuilt, [True])

    def test_snapshot_restart_failure_does_not_leave_admission_frozen(self):
        with patch.object(self.facade.service, 'start', side_effect=RuntimeError('fixture restart failure')):
            with self.assertRaises(ValueError): self.backup()
        self.assertFalse(self.facade.conversations.admission_paused)
        self.assertIsNone(self.controller.operations.hermes_pause)

    def test_nested_snapshot_on_another_thread_cannot_retain_parent_locks(self):
        errors = []
        def snapshot():
            try:
                with self.controller.operations.hermes_snapshot(): pass
            except Exception as error: errors.append(error)
        with self.controller.operations.hermes_snapshot():
            # Rollback's nested snapshot on this thread remains valid.
            with self.controller.operations.hermes_snapshot(): pass
            thread = threading.Thread(target=snapshot); thread.start(); thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1); self.assertIsInstance(errors[0], ValueError)
        self.assertEqual(self.facade.stops, 1); self.assertEqual(self.facade.starts, 1)
        self.assertIsNone(self.controller.operations.hermes_pause)

    def test_controller_owned_snapshot_can_finish_while_worker_waits_for_controller(self):
        # The local legacy API owns controller before entering a snapshot.
        # Its asynchronous counterpart must wait for controller before taking
        # Hermes admission or facade, otherwise both requests wait forever.
        waiting = threading.Event(); errors = []; c = self.controller

        class ControllerLock:
            def __init__(self, lock): self.lock = lock
            def acquire(self):
                if threading.current_thread().name == 'fixture-backup-worker': waiting.set()
                if not self.lock.acquire(timeout=3): raise RuntimeError('Controller lock order is inverted')
            def release(self): self.lock.release()
            def __enter__(self): self.acquire(); return self
            def __exit__(self, *args): self.release()

        c.lock = ControllerLock(c.lock)
        def worker():
            try:
                with c.operations.hermes_snapshot(): pass
            except Exception as error: errors.append(error)
        thread = threading.Thread(target=worker, name='fixture-backup-worker')
        try:
            with c.lock:
                thread.start(); self.assertTrue(waiting.wait(5))
                with c.operations.hermes_snapshot(): pass
        finally:
            if thread.ident is not None: thread.join(10)
        self.assertFalse(thread.is_alive()); self.assertEqual(errors, [])
        self.assertEqual(self.facade.stops, 2); self.assertEqual(self.facade.starts, 2)
        self.assertIsNone(c.operations.hermes_pause)

    def test_snapshot_refuses_restore_admission_without_retaining_controller(self):
        # Restore owns Hermes admission while an active model call still needs
        # controller. A new capture must reject instead of waiting with it held.
        attempted = threading.Event(); errors = []; c = self.controller
        def worker():
            attempted.set()
            try:
                with c.operations.hermes_snapshot(): pass
            except Exception as error: errors.append(error)
        thread = threading.Thread(target=worker)
        try:
            with c.operations.hermes_lock:
                thread.start(); self.assertTrue(attempted.wait(5)); thread.join(2)
                self.assertFalse(thread.is_alive())
                self.assertTrue(c.lock.acquire(timeout=1)); c.lock.release()
        finally:
            if thread.ident is not None: thread.join(10)
        self.assertEqual(len(errors), 1); self.assertIsInstance(errors[0], ValueError)
        self.assertEqual(self.facade.stops, 0)
        self.assertIsNone(c.operations.hermes_pause)

    def test_restore_waits_for_run_without_holding_controller_or_workspace(self):
        stopped = threading.Event(); errors = []; c = self.controller
        self.facade.conversations.active[self.owner] = {'request_id': 'fixture-provider'}
        def close():
            self.facade.stop(); self.facade.started = False
            self.facade.conversations.closed = True; stopped.set()
        self.facade.close = close
        def provider():
            try:
                if not stopped.wait(5): raise RuntimeError('Restore did not stop the run')
                if not c.lock.acquire(timeout=3): raise RuntimeError('Restore retained controller')
                try:
                    if not c.remote.workspace.lock.acquire(timeout=3): raise RuntimeError('Restore retained Workspace')
                    c.remote.workspace.lock.release()
                finally: c.lock.release()
            except Exception as error: errors.append(error)
            finally:
                with self.facade.conversations.lock:
                    self.facade.conversations.active.pop(self.owner, None)
        thread = threading.Thread(target=provider); thread.start(); token = None
        try: token = c.operations.hermes_quiesce(restoring=True)
        finally:
            thread.join(10)
            if token is not None: c.operations.hermes_resume(token, restored=True)
        self.assertFalse(thread.is_alive()); self.assertEqual(errors, [])
        self.assertEqual(self.rebuilt, [True])
        self.assertIsNone(c.operations.hermes_pause)


if __name__ == '__main__': unittest.main()
