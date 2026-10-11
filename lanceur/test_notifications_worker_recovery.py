"""Real worker/restart/HTTP contracts on disposable storage, without inference."""
import base64
import json
import secrets
import sqlite3
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import Mock, patch

from notifications import JOB_ATTEMPT_PREFIX, Notifications, job_attempt
from workspace import Workspace


class NotificationWorkerRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='fred-notification-recovery-')
        self.workspace = Workspace(self.directory.name)
        self.inbox = Notifications(self.workspace)
        self.owner = 'a' * 16
        self.project = self.workspace.action(self.owner, {'action': 'project_create', 'title': 'Isolated recovery'})['id']
        self.workspace.generation = Mock(side_effect=RuntimeError('private fixture error'))
        self.restarted = []

    def tearDown(self):
        self.workspace.shutdown()
        for workspace in self.restarted:
            workspace.shutdown()
        self.directory.cleanup()

    def job(self):
        return self.workspace.action(self.owner, {'action': 'job_create', 'project': self.project,
            'prompt': 'private fixture prompt', 'request_key': secrets.token_hex(16)})['id']

    def state(self, identity):
        return self.workspace.action(self.owner, {'action': 'job_get', 'id': identity})['state']

    def restart(self):
        workspace = Workspace(self.directory.name)
        self.restarted.append(workspace)
        return workspace, Notifications(workspace)

    def retry(self, identity):
        return self.workspace.action(self.owner, {'action': 'job_retry', 'id': identity})

    def test_second_failed_attempt_is_new_unread_after_first_was_read(self):
        identity = self.job()
        self.assertTrue(self.workspace.run_one())
        first = self.inbox.snapshot(self.owner)['items'][0]
        self.inbox.action(self.owner, {'action': 'read', 'ids': [first['id']]})
        self.retry(identity)
        self.assertTrue(self.workspace.run_one())
        state = self.inbox.snapshot(self.owner)
        self.assertEqual(['job_failed', 'job_failed'], [row['type'] for row in state['items']])
        self.assertNotEqual(first['id'], state['items'][1]['id'])
        self.assertIsNotNone(state['items'][0]['read_at'])
        self.assertIsNone(state['items'][1]['read_at'])
        self.assertEqual(1, state['unread_count'])
        self.assertEqual(2, self.workspace.generation.call_count)
        with self.workspace.db() as db:
            keys = [row[0] for row in db.execute('SELECT source_key FROM notifications ORDER BY seq')]
        self.assertEqual(['job_failed:' + identity, 'job_failed:' + identity + ':attempt:1'], keys)

    def test_same_attempt_failure_and_success_events_remain_idempotent(self):
        identity = self.job()
        self.workspace.run_one()
        self.retry(identity)
        self.workspace.generation = Mock(return_value='isolated success')
        self.workspace.run_one()
        before = self.inbox.snapshot(self.owner)
        for unused in range(3):
            with self.workspace.db() as db:
                self.workspace.event(db, self.owner, 'job_completed', identity)
        self.assertEqual(before, self.inbox.snapshot(self.owner))
        self.assertEqual('job_completed', before['items'][-1]['type'])
        self.assertEqual('completed', self.state(identity))
        self.assertEqual(1, self.workspace.generation.call_count)
        with self.workspace.db() as db:
            key = db.execute("SELECT source_key FROM notifications WHERE type='job_completed'").fetchone()[0]
        self.assertEqual('job_completed:' + identity + ':attempt:1', key)

    def test_retry_number_survives_clock_rollback_event_pruning_and_restart(self):
        identity = self.job()
        self.workspace.run_one()
        first = self.inbox.snapshot(self.owner)['items'][0]['id']
        self.inbox.action(self.owner, {'action': 'read', 'ids': [first]})
        backwards = time.time() - 60
        with patch('workspace.time.time', return_value=backwards):
            self.retry(identity)
            self.workspace.run_one()
        with self.workspace.db() as db:
            db.execute('DELETE FROM events')
            self.assertEqual(1, job_attempt(db, identity))
        workspace, inbox = self.restart()
        workspace.action(self.owner, {'action': 'job_retry', 'id': identity})
        workspace.generation = Mock(side_effect=RuntimeError('isolated later failure'))
        workspace.run_one()
        self.assertEqual(3, len(inbox.snapshot(self.owner)['items']))
        self.assertEqual(2, inbox.snapshot(self.owner)['unread_count'])
        with workspace.db() as db:
            self.assertEqual(2, job_attempt(db, identity))
        self.assertEqual(1, workspace.generation.call_count)

    def test_duplicate_failure_event_after_reconnection_keeps_same_read_id(self):
        identity = self.job()
        self.workspace.run_one()
        self.retry(identity)
        self.workspace.run_one()
        before = self.inbox.snapshot(self.owner)
        ids = [row['id'] for row in before['items']]
        self.inbox.action(self.owner, {'action': 'read', 'ids': ids})
        for unused in range(3):
            with self.workspace.db() as db:
                self.workspace.event(db, self.owner, 'job_failed', identity)
        after = self.inbox.snapshot(self.owner, before['cursor'])
        self.assertEqual([], after['items'])
        self.assertEqual(ids, after['read_ids'])
        self.assertEqual(0, after['unread_count'])

    def test_interrupted_running_job_notifies_once_without_replaying_inference(self):
        identity = self.job()
        with self.workspace.db() as db:
            db.execute("UPDATE jobs SET state='running' WHERE id=?", (identity,))
            db.execute("INSERT OR REPLACE INTO settings VALUES('worker','malformed lease')")
        workspace, inbox = self.restart()
        workspace.generation = Mock(side_effect=AssertionError('inference must not replay'))
        self.assertFalse(workspace.run_one())
        state = inbox.snapshot(self.owner)
        self.assertEqual(1, state['unread_count'])
        self.assertEqual(identity, state['items'][0]['target']['id'])
        self.assertEqual('job_failed', state['items'][0]['type'])
        self.assertEqual('failed', self.state(identity))
        workspace.generation.assert_not_called()
        second, second_inbox = self.restart()
        self.assertEqual(state, second_inbox.snapshot(self.owner))
        with second.db() as db:
            self.assertEqual(1, db.execute("SELECT COUNT(*) FROM events WHERE action='job_failed'").fetchone()[0])

    def test_restart_failure_state_event_and_notification_roll_back_together(self):
        identity = self.job()
        with self.workspace.db() as db:
            db.execute("UPDATE jobs SET state='running' WHERE id=?", (identity,))
        with patch('notifications.publish', side_effect=RuntimeError('isolated database failure')):
            with self.assertRaisesRegex(RuntimeError, 'database failure'):
                Workspace(self.directory.name)
        self.assertEqual('running', self.state(identity))
        with self.workspace.db() as db:
            self.assertEqual(0, db.execute("SELECT COUNT(*) FROM events WHERE action='job_failed'").fetchone()[0])
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM notifications').fetchone()[0])
        unused, inbox = self.restart()
        self.assertEqual(1, inbox.snapshot(self.owner)['unread_count'])

    def test_live_worker_lease_prevents_another_constructor_from_failing_job(self):
        import psutil
        identity = self.job()
        process = psutil.Process()
        with self.workspace.db() as db:
            db.execute("UPDATE jobs SET state='running' WHERE id=?", (identity,))
            db.execute("INSERT OR REPLACE INTO settings VALUES('worker',?)",
                       (json.dumps({'pid': process.pid, 'created': process.create_time(), 'instance': self.workspace.instance}),))
        unused, inbox = self.restart()
        self.assertEqual('running', self.state(identity))
        self.assertEqual([], inbox.snapshot(self.owner)['items'])

    def test_old_cancelled_worker_cannot_fail_or_remove_new_running_attempt(self):
        identity = self.job()
        old_entered = threading.Event(); old_release = threading.Event()
        new_entered = threading.Event(); new_release = threading.Event()
        def old_generation(*unused):
            old_entered.set()
            if not old_release.wait(10):
                raise TimeoutError('old fixture not released')
            raise RuntimeError('old attempt failure')
        def new_generation(*unused):
            new_entered.set()
            if not new_release.wait(10):
                raise TimeoutError('new fixture not released')
            raise RuntimeError('new attempt failure')
        self.workspace.generation = old_generation
        old_worker = threading.Thread(target=self.workspace.run_one)
        old_worker.start()
        new_worker = None
        try:
            self.assertTrue(old_entered.wait(5))
            self.workspace.action(self.owner, {'action': 'job_pause', 'id': identity})
            self.retry(identity)
            self.workspace.generation = new_generation
            new_worker = threading.Thread(target=self.workspace.run_one)
            new_worker.start()
            self.assertTrue(new_entered.wait(5))
            current_cancel = self.workspace.running[identity]
            old_release.set(); old_worker.join(5)
            self.assertFalse(old_worker.is_alive())
            self.assertEqual('running', self.state(identity))
            self.assertIs(current_cancel, self.workspace.running[identity])
            self.assertEqual([], self.inbox.snapshot(self.owner)['items'])
            new_release.set(); new_worker.join(5)
            self.assertFalse(new_worker.is_alive())
            self.assertEqual('failed', self.state(identity))
            self.assertEqual(1, self.inbox.snapshot(self.owner)['unread_count'])
        finally:
            old_release.set(); new_release.set(); old_worker.join(10)
            if new_worker:
                new_worker.join(10)

    def test_attempt_counter_is_accounted_and_removed_when_job_is_pruned(self):
        identity = self.job()
        self.workspace.run_one()
        with self.workspace.db() as db:
            before = self.workspace.usage(db, self.owner)
        self.retry(identity)
        with self.workspace.db() as db:
            self.assertGreaterEqual(self.workspace.usage(db, self.owner) - before, 120)
            db.execute("UPDATE jobs SET state='failed',created=1 WHERE id=?", (identity,))
            for index in range(100):
                token = secrets.token_hex(16)
                db.execute("INSERT INTO jobs(id,owner,project,title,prompt,kind,url,state,created,due,repeat_hours,request_key) "
                           "SELECT ?,owner,project,title,prompt,kind,url,'completed',?,due,repeat_hours,? FROM jobs WHERE id=?",
                           (token, 100 + index, token, identity))
            self.workspace.prune(db, self.owner)
            self.assertIsNone(db.execute('SELECT id FROM jobs WHERE id=?', (identity,)).fetchone())
            self.assertIsNone(db.execute('SELECT value FROM settings WHERE key=?', (JOB_ATTEMPT_PREFIX + identity,)).fetchone())

    def test_backup_roundtrip_preserves_attempt_counter_and_rejects_corruption(self):
        identity = self.job()
        self.workspace.run_one(); self.retry(identity); self.workspace.run_one()
        backup = self.workspace.backup()
        validated = self.workspace.validate_backup(backup, {self.owner})
        with tempfile.TemporaryDirectory(prefix='fred-attempt-restore-') as directory:
            restored = Workspace(directory)
            try:
                restored.restore(validated)
                restored.action(self.owner, {'action': 'job_retry', 'id': identity})
                restored.generation = Mock(side_effect=RuntimeError('isolated restored failure'))
                restored.run_one()
                self.assertEqual(3, Notifications(restored).snapshot(self.owner)['unread_count'])
                with restored.db() as db:
                    self.assertEqual(2, job_attempt(db, identity))
            finally:
                restored.shutdown()
        for bad in ('0', '01', '-1', '9223372036854775808', '1' * 100):
            with self.subTest(counter=bad):
                memory = sqlite3.connect(':memory:')
                try:
                    memory.deserialize(base64.b64decode(backup))
                    memory.execute('UPDATE settings SET value=? WHERE key=?', (bad, JOB_ATTEMPT_PREFIX + identity))
                    memory.commit()
                    encoded = base64.b64encode(memory.serialize()).decode()
                    with self.assertRaises(ValueError):
                        self.workspace.validate_backup(encoded, {self.owner})
                finally:
                    memory.close()
        memory = sqlite3.connect(':memory:')
        try:
            memory.deserialize(base64.b64decode(backup))
            memory.execute('INSERT INTO settings VALUES(?,?)', (JOB_ATTEMPT_PREFIX + 'b' * 32, '1'))
            memory.commit()
            with self.assertRaises(ValueError):
                self.workspace.validate_backup(base64.b64encode(memory.serialize()).decode(), {self.owner})
        finally:
            memory.close()

    def test_revoked_access_recovered_after_crash_stays_inaccessible_and_isolated(self):
        from remote import AccessStore, serve_gateway
        with tempfile.TemporaryDirectory(prefix='fred-revoked-recovery-http-') as directory:
            store = AccessStore(directory)
            first = store.issue('Isolated phone'); other = store.issue('Isolated tablet')
            store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
            project = store.workspace.action(first['id'], {'action': 'project_create', 'title': 'private project'})['id']
            identity = store.workspace.action(first['id'], {'action': 'job_create', 'project': project,
                'prompt': 'private prompt', 'request_key': secrets.token_hex(16)})['id']
            store.notifications.action(first['id'], {'action': 'subscribe', 'enabled': True})
            with store.workspace.db() as db:
                db.execute("UPDATE jobs SET state='running' WHERE id=?", (identity,))
            # Simulate the crash after committing the monotonic revoke ledger,
            # before the best-effort cancellation of the running database row.
            store.revocations.revoke(first['id'])
            store.notifications.revoke(first['id'])
            recovered = AccessStore(directory)
            with recovered.workspace.db() as db:
                self.assertEqual('failed', db.execute('SELECT state FROM jobs WHERE id=?', (identity,)).fetchone()[0])
                notification = db.execute('SELECT id FROM notifications WHERE owner=?', (first['id'],)).fetchone()[0]
                self.assertEqual(0, db.execute('SELECT COUNT(*) FROM notification_subscriptions').fetchone()[0])
            backend = Mock(side_effect=AssertionError('backend must not be called'))
            gateway = serve_gateway(recovered, backend, 0)
            thread = threading.Thread(target=gateway.serve_forever, daemon=True); thread.start()
            url = 'http://127.0.0.1:' + str(gateway.server_port)
            def request(access, body=None):
                path = '/v1/notifications/action' if body is not None else '/v1/notifications'
                data = json.dumps(body).encode() if body is not None else None
                headers = {'Authorization': 'Bearer ' + access['token'], 'Content-Type': 'application/json'}
                with urllib.request.urlopen(urllib.request.Request(url + path, data, headers), timeout=5) as response:
                    return json.load(response)
            try:
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    request(first)
                self.assertEqual(401, denied.exception.code); denied.exception.close()
                self.assertEqual([], request(other)['items'])
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    request(other, {'action': 'get', 'id': notification})
                self.assertEqual(403, denied.exception.code); denied.exception.close()
                self.assertFalse(recovered.workspace.run_one())
                backend.assert_not_called()
            finally:
                gateway.shutdown(); gateway.server_close(); thread.join(5)
                store.workspace.shutdown()


if __name__ == '__main__':
    unittest.main()
