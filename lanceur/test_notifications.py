"""Notification durability, owner isolation and connected-delivery contracts."""
import json
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from notifications import (Notifications, ADMIN_TYPES, CLIENT_TYPES, MAX_OWNER,
                           RETENTION_DAYS, migrate, publish, validate)
from workspace import Workspace, Conflict, Denied


class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.workspace = Workspace(self.directory.name)
        self.inbox = Notifications(self.workspace)
        self.owner = 'a' * 16
        self.other = 'b' * 16

    def tearDown(self):
        self.workspace.shutdown()
        self.directory.cleanup()

    def publish(self, key='result:1', owner=None, kind='job_completed'):
        return self.inbox.publish(owner or self.owner, kind, key)['id']

    def test_notification_survives_restart_and_deduplicates(self):
        identity = self.publish()
        restarted = Notifications(Workspace(self.directory.name))
        repeated = restarted.publish(self.owner, 'job_completed', 'result:1')
        self.assertEqual(repeated, {'id': identity, 'created': False})
        self.assertEqual([identity], [row['id'] for row in restarted.snapshot(self.owner)['items']])
        restarted.workspace.shutdown()

    def test_order_uses_durable_sequence_even_if_clock_moves_back(self):
        with self.workspace.db() as db:
            first = publish(db, self.owner, 'job_completed', 'first', now=time.time())['id']
            second = publish(db, self.owner, 'job_completed', 'second', now=time.time()-30)['id']
        rows = self.inbox.snapshot(self.owner)['items']
        self.assertEqual([first, second], [row['id'] for row in rows])
        self.assertLess(rows[0]['sequence'], rows[1]['sequence'])

    def test_reconnection_catches_all_pages_and_network_retry_has_same_ids(self):
        identities = [self.publish('page:' + str(index)) for index in range(105)]
        first = self.inbox.action(self.owner, {'action': 'list', 'after': 0, 'limit': 100})
        retry = self.inbox.action(self.owner, {'action': 'list', 'after': 0, 'limit': 100})
        self.assertEqual(first, retry)
        self.assertTrue(first['has_more'])
        second = self.inbox.action(self.owner, {'action': 'list', 'after': first['cursor']})
        self.assertFalse(second['has_more'])
        self.assertEqual(identities, [row['id'] for row in first['items'] + second['items']])

    def test_read_is_idempotent_and_synchronized_even_after_cursor(self):
        identity = self.publish()
        before = self.inbox.snapshot(self.owner)
        read = self.inbox.action(self.owner, {'action': 'read', 'ids': [identity, identity]})
        again = self.inbox.action(self.owner, {'action': 'read', 'ids': [identity]})
        self.assertEqual(read['items'][0]['read_at'], again['items'][0]['read_at'])
        after = self.inbox.snapshot(self.owner, before['cursor'])
        self.assertEqual([], after['items'])
        self.assertEqual([identity], after['read_ids'])
        self.assertEqual(0, after['unread_count'])

    def test_two_owners_cannot_read_get_ack_or_deliver_each_other(self):
        private = self.publish()
        own = self.publish('other', self.other)
        self.assertEqual([own], [row['id'] for row in self.inbox.snapshot(self.other)['items']])
        for action in ('read', 'delivered'):
            with self.assertRaises(Denied):
                self.inbox.action(self.other, {'action': action, 'ids': [own, private]})
        with self.assertRaises(Denied):
            self.inbox.action(self.other, {'action': 'get', 'id': private})
        self.assertEqual(1, self.inbox.snapshot(self.other)['unread_count'])
        with self.workspace.db() as db:
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM notification_deliveries').fetchone()[0])

    def test_preferences_persist_and_disable_delivery_without_hiding_inbox(self):
        identity = self.publish()
        updated = self.inbox.action(self.owner, {'action': 'preferences', 'revision': 0,
                                                'types': {'job_completed': False}, 'discreet': True})
        self.assertEqual(1, updated['preferences']['revision'])
        self.assertFalse(updated['items'][0]['enabled'])
        self.inbox.action(self.owner, {'action': 'delivered', 'ids': [identity]})
        with self.workspace.db() as db:
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM notification_deliveries').fetchone()[0])
        restarted = Notifications(Workspace(self.directory.name))
        self.assertFalse(restarted.snapshot(self.owner)['preferences']['types']['job_completed'])
        with self.assertRaises(Conflict):
            restarted.action(self.owner, {'action': 'preferences', 'revision': 0, 'types': {}})
        restarted.workspace.shutdown()

    def test_subscription_off_suppresses_receipts_and_revoke_removes_it(self):
        identity = self.publish()
        self.inbox.action(self.owner, {'action': 'subscribe', 'enabled': True, 'discreet': True})
        self.inbox.action(self.owner, {'action': 'delivered', 'ids': [identity]})
        self.inbox.action(self.owner, {'action': 'delivered', 'ids': [identity]})
        with self.workspace.db() as db:
            self.assertEqual(1, db.execute('SELECT COUNT(*) FROM notification_deliveries').fetchone()[0])
        self.inbox.action(self.owner, {'action': 'subscribe', 'enabled': False})
        another = self.publish('off')
        self.inbox.action(self.owner, {'action': 'delivered', 'ids': [another]})
        self.inbox.revoke(self.owner)
        self.workspace.valid = lambda owner: owner != self.owner
        with self.assertRaises(Denied):
            self.inbox.snapshot(self.owner)
        with self.assertRaises(Denied):
            self.inbox.action(self.owner, {'action': 'subscribe', 'enabled': True})
        with self.workspace.db() as db:
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM notification_subscriptions').fetchone()[0])
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM notification_deliveries').fetchone()[0])
            self.assertEqual(2, db.execute('SELECT COUNT(*) FROM notifications WHERE owner=?', (self.owner,)).fetchone()[0])

    def test_admin_alerts_are_isolated_and_clients_cannot_set_admin_types(self):
        alert = self.inbox.publish('admin', 'backup_failed', 'backup:1')['id']
        self.publish()
        self.assertEqual([alert], [row['id'] for row in self.inbox.admin()['items']])
        self.assertNotIn(alert, [row['id'] for row in self.inbox.snapshot(self.owner)['items']])
        with self.assertRaises(ValueError):
            self.inbox.publish(self.owner, 'backup_failed', 'forge')
        with self.assertRaises(ValueError):
            self.inbox.action(self.owner, {'action': 'preferences', 'revision': 0, 'types': {'backup_failed': True}})

    def test_only_server_can_publish_and_no_target_can_select_another_owner(self):
        for body in ({'action': 'publish', 'owner': self.other},
                     {'action': 'read', 'ids': [], 'owner': self.other},
                     {'action': 'subscribe', 'enabled': True, 'device': self.other}):
            with self.assertRaises(ValueError):
                self.inbox.action(self.owner, body)
        with self.assertRaises(Denied):
            self.inbox.snapshot(self.owner, device=self.other)
        with self.assertRaises(ValueError):
            self.inbox.publish(self.owner, 'job_completed', 'url', {'kind': 'url', 'url': 'https://example.org'})

    def test_job_and_document_notifications_publish_atomically_without_private_text(self):
        project = self.workspace.action(self.owner, {'action': 'project_create', 'title': 'Titre secret'})['id']
        document = self.workspace.action(self.owner, {'action': 'document_create', 'project': project,
                                                      'title': 'Document secret', 'text': 'Texte confidentiel'})['id']
        rows = self.inbox.snapshot(self.owner)['items']
        self.assertEqual('document_indexed', rows[0]['type'])
        self.assertEqual({'kind': 'document', 'id': document, 'project': project}, rows[0]['target'])
        self.assertNotIn('secret', json.dumps(rows).lower())
        self.assertNotIn('confidentiel', json.dumps(rows).lower())
        self.workspace.action(self.owner, {'action': 'document_save', 'id': document, 'project': project,
                                          'title': 'Document secret', 'text': 'Révision suivante', 'revision': 1})
        self.assertEqual(2, len(self.inbox.snapshot(self.owner)['items']))
        job = self.workspace.action(self.owner, {'action': 'job_create', 'project': project,
                                                'title': 'Question privée', 'prompt': 'Répondre secret',
                                                'kind': 'analysis', 'request_key': 'c' * 32})['id']
        self.workspace.generation = lambda *args: 'Résultat privé'
        self.workspace.run_one()
        completed = self.inbox.snapshot(self.owner)['items'][-1]
        self.assertEqual('job_completed', completed['type'])
        self.assertEqual(job, completed['target']['id'])
        self.assertNotIn('privé', json.dumps(completed))

    def test_transaction_rolls_back_notification_with_failed_document_write(self):
        with self.assertRaises(RuntimeError):
            with self.workspace.db() as db:
                publish(db, self.owner, 'job_completed', 'rolled-back')
                raise RuntimeError('simulated transaction failure')
        result = self.inbox.snapshot(self.owner)
        self.assertEqual([], result['items'])
        self.assertEqual([], result['retained_ids'])

    def test_migration_is_additive_and_never_resets_existing_data(self):
        db = sqlite3.connect(':memory:')
        db.execute('CREATE TABLE existing_history(value TEXT)')
        db.execute('INSERT INTO existing_history VALUES(?)', ('conversation conservée',))
        migrate(db); migrate(db)
        self.assertEqual('conversation conservée', db.execute('SELECT value FROM existing_history').fetchone()[0])
        self.assertEqual(4, db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE 'notification%'").fetchone()[0])
        db.close()

    def test_notifications_and_read_preferences_restore_with_workspace_backup(self):
        identity = self.publish()
        self.inbox.action(self.owner, {'action': 'read', 'ids': [identity]})
        self.inbox.action(self.owner, {'action': 'preferences', 'revision': 0, 'types': {'job_failed': False}})
        saved = self.workspace.backup()
        raw = self.workspace.validate_backup(saved, {self.owner})
        self.publish('after-snapshot')
        self.workspace.restore(raw)
        restored = self.inbox.snapshot(self.owner)
        self.assertEqual([identity], [row['id'] for row in restored['items']])
        self.assertEqual([identity], restored['read_ids'])
        self.assertFalse(restored['preferences']['types']['job_failed'])

    def test_validation_rejects_foreign_owner_and_invalid_preferences_with_tuple_db(self):
        self.publish()
        with self.workspace.db() as source:
            raw = source.serialize()
            raw = raw[:18] + b'\x01\x01' + raw[20:]
        db = sqlite3.connect(':memory:'); db.deserialize(raw)
        with self.assertRaises(ValueError):
            validate(db, {self.other})
        self.assertIsNone(db.row_factory)
        validate(db, {self.owner})
        db.execute('INSERT INTO notification_preferences VALUES(?,?,1,?)', (self.owner, json.dumps({'types': {'job_completed': 'yes'}, 'discreet': True}), time.time()))
        with self.assertRaises(ValueError):
            validate(db, {self.owner})
        db.close()

    def test_malicious_reference_to_another_owner_is_rejected_during_backup_validation(self):
        project = self.workspace.action(self.other, {'action': 'project_create', 'title': 'Autre espace'})['id']
        document = self.workspace.action(self.other, {'action': 'document_create', 'project': project, 'title': 'note', 'text': 'contenu'})['id']
        with self.assertRaises(ValueError):
            self.inbox.publish(self.owner, 'document_indexed', 'foreign-reference', {'kind': 'document', 'id': document, 'project': project})
        identity = self.publish('malicious-backup')
        with self.workspace.db() as db:
            db.execute('UPDATE notifications SET target=? WHERE id=?', (json.dumps({'kind': 'document', 'id': document, 'project': project}), identity))
            with self.assertRaises(ValueError):
                validate(db, {self.owner, self.other})

    def test_concurrent_same_event_has_one_stable_identity(self):
        barrier = threading.Barrier(6); identities = []; errors = []
        def send():
            try:
                barrier.wait()
                identities.append(self.publish('concurrent'))
            except Exception as error:
                errors.append(error)
        threads = [threading.Thread(target=send) for _ in range(6)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(5)
        self.assertEqual([], errors)
        self.assertEqual(6, len(identities))
        self.assertEqual(1, len(set(identities)))

    def test_retention_bounds_inbox_and_cascades_delivery_receipts(self):
        old = self.publish('old')
        self.inbox.action(self.owner, {'action': 'delivered', 'ids': [old]})
        with self.workspace.db() as db:
            db.execute('UPDATE notifications SET created=? WHERE id=?', (time.time()-(RETENTION_DAYS+1)*86400, old))
            for index in range(MAX_OWNER + 5):
                publish(db, self.owner, 'job_completed', 'bounded:' + str(index))
            self.assertEqual(MAX_OWNER, db.execute('SELECT COUNT(*) FROM notifications WHERE owner=?', (self.owner,)).fetchone()[0])
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM notification_deliveries').fetchone()[0])
        self.assertEqual(MAX_OWNER, self.inbox.snapshot(self.owner)['unread_count'])

    def test_maintenance_blocks_mutations_and_publication(self):
        identity = self.publish()
        self.workspace.maintenance = True
        with self.assertRaises(Denied):
            self.inbox.action(self.owner, {'action': 'read', 'ids': [identity]})
        self.assertEqual({'created': False, 'maintenance': True}, self.inbox.publish(self.owner, 'job_completed', 'during-maintenance'))

    def test_retention_runs_when_consulting_a_quiet_inbox(self):
        identity = self.publish()
        with self.workspace.db() as db:
            db.execute('UPDATE notifications SET created=? WHERE id=?', (time.time()-(RETENTION_DAYS+1)*86400, identity))
        result = self.inbox.snapshot(self.owner)
        self.assertEqual([], result['items'])
        self.assertNotIn(identity, result['retained_ids'])

    def test_generation_marker_is_returned_for_dedup_reset_after_restore(self):
        from server_state import new_generation
        before = self.inbox.snapshot(self.owner)
        new_generation(self.workspace.home)
        after = self.inbox.snapshot(self.owner)
        self.assertNotEqual(before['generation'], after['generation'])
        self.assertTrue(after['restored'])

    def test_invalid_inputs_do_not_change_preferences_or_notifications(self):
        for body in ({'action': 'list', 'after': True}, {'action': 'list', 'limit': 101},
                     {'action': 'read', 'ids': ['bad']}, {'action': 'subscribe', 'enabled': 1},
                     {'action': 'preferences', 'revision': 0, 'types': {'job_failed': 1}}):
            with self.assertRaises(ValueError):
                self.inbox.action(self.owner, body)
        self.assertEqual(0, self.inbox.snapshot(self.owner)['preferences']['revision'])


if __name__ == '__main__':
    unittest.main()
