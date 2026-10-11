"""Real gateway HTTP/authentication on disposable storage; no production ports."""
import json
import secrets
import tempfile
import threading
import types
import unittest
import urllib.error
import urllib.request

from operations import Operations
from remote import AccessStore, serve_gateway


class NotificationTransportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='fred-notification-transport-')
        self.store = AccessStore(self.directory.name)
        self.first = self.store.issue('Téléphone isolé')
        self.second = self.store.issue('Tablette isolée')
        self.store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        self.gateway = serve_gateway(self.store, lambda: (49998, 'fixture-only', ''), 0)
        self.thread = threading.Thread(target=self.gateway.serve_forever, daemon=True); self.thread.start()
        self.url = 'http://127.0.0.1:' + str(self.gateway.server_port)

    def tearDown(self):
        self.gateway.shutdown(); self.gateway.server_close(); self.thread.join(5)
        self.directory.cleanup()

    def request(self, path='/v1/notifications', value=None, identity=None, raw=None, headers=None):
        access = identity or self.first
        supplied = {'Authorization': 'Bearer ' + access['token'], 'Content-Type': 'application/json'}
        supplied.update(headers or {})
        data = raw if raw is not None else json.dumps(value).encode() if value is not None else None
        with urllib.request.urlopen(urllib.request.Request(self.url + path, data, supplied), timeout=5) as response:
            return json.load(response)

    def action(self, value, **kwargs):
        return self.request('/v1/notifications/action', value, **kwargs)

    def denied(self, status, *args, **kwargs):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request(*args, **kwargs)
        self.assertEqual(status, error.exception.code)
        error.exception.close()

    def test_real_get_list_get_by_id_read_and_preferences(self):
        identity = self.store.notifications.publish(self.first['id'], 'job_completed', 'http:one')['id']
        state = self.request(); self.assertEqual(identity, state['items'][0]['id'])
        self.assertEqual(identity, self.action({'action': 'get', 'id': identity})['notification']['id'])
        self.assertEqual(identity, self.action({'action': 'list', 'after': 0})['items'][0]['id'])
        read = self.action({'action': 'read', 'ids': [identity]})
        self.assertEqual(0, read['unread_count']); self.assertIn(identity, read['read_ids'])
        synchronized = self.action({'action': 'list', 'after': state['cursor']})
        self.assertEqual([], synchronized['items']); self.assertIn(identity, synchronized['read_ids'])
        prefs = self.action({'action': 'preferences', 'revision': 0, 'types': {'job_completed': False}})
        self.assertFalse(prefs['items'][0]['enabled'])
        self.denied(409, '/v1/notifications/action', {'action': 'preferences', 'revision': 0, 'types': {}})

    def test_two_authenticated_owners_and_admin_remain_isolated(self):
        first = self.store.notifications.publish(self.first['id'], 'job_completed', 'first')['id']
        second = self.store.notifications.publish(self.second['id'], 'job_failed', 'second')['id']
        self.store.notifications.publish('admin', 'backup_failed', 'admin')
        self.assertEqual([second], [row['id'] for row in self.request(identity=self.second)['items']])
        self.denied(403, '/v1/notifications/action', {'action': 'get', 'id': first}, identity=self.second)
        self.denied(403, '/v1/notifications/action', {'action': 'read', 'ids': [second, first]}, identity=self.second)
        self.denied(403, '/v1/notifications/action', {'action': 'delivered', 'ids': [first]}, identity=self.second)
        self.denied(404, '/api/notifications')
        self.denied(400, '/v1/notifications/action', {'action': 'read', 'ids': [first], 'owner': self.second['id']})
        self.denied(400, '/v1/notifications/action', {'action': 'publish', 'type': 'backup_failed'})
        self.assertEqual(1, self.request(identity=self.second)['unread_count'])

    def test_origin_json_limits_and_invalid_bearer(self):
        self.denied(403, headers={'Origin': 'https://external.invalid'})
        self.denied(403, '/v1/notifications/action', {'action': 'list'}, headers={'Origin': 'null'})
        self.denied(400, '/v1/notifications/action', raw=b' ' * 65537)
        self.denied(400, '/v1/notifications/action', raw=b'[]')
        self.denied(400, '/v1/notifications/action', raw=b'bad json')
        self.denied(400, '/v1/notifications/action', raw=b'{}', headers={'Content-Type': 'text/plain'})
        self.denied(401, headers={'Authorization': 'Bearer qwen_invalid'})

    def test_revocation_removes_subscription_and_receipts_then_denies_auth(self):
        notification = self.store.notifications.publish(self.first['id'], 'job_completed', 'before-revoke')['id']
        self.action({'action': 'subscribe', 'enabled': True})
        self.action({'action': 'delivered', 'ids': [notification]})
        self.action({'action': 'subscribe', 'enabled': False}, identity=self.second)
        self.store.revoke(self.first['id'])
        self.denied(401)
        self.denied(401, '/v1/notifications/action', {'action': 'subscribe', 'enabled': True})
        self.assertFalse(self.request(identity=self.second)['subscription']['enabled'])
        with self.store.workspace.db() as db:
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM notification_subscriptions WHERE owner=?', (self.first['id'],)).fetchone()[0])
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM notification_deliveries WHERE owner=?', (self.first['id'],)).fetchone()[0])
            self.assertEqual(1, db.execute('SELECT COUNT(*) FROM notifications WHERE owner=?', (self.first['id'],)).fetchone()[0])

    def test_maintenance_denies_notifications_before_any_mutation(self):
        self.store.maintenance = True
        self.denied(503)
        self.denied(503, '/v1/notifications/action', {'action': 'subscribe', 'enabled': True})
        with self.store.workspace.db() as db:
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM notification_subscriptions').fetchone()[0])

    def test_source_reference_cannot_be_consulted_from_another_authenticated_owner(self):
        workspace = self.store.workspace; owner = self.first['id']
        project = workspace.action(owner, {'action': 'project_create', 'title': 'Espace privé'})['id']
        workspace.action(owner, {'action': 'document_create', 'project': project,
                                 'title': 'Mémo privé', 'text': 'La constellation Andromède contient plusieurs étoiles.'})
        sources = workspace.action(owner, {'action': 'search', 'project': project, 'query': 'Andromède'})['sources']
        source_id = sources[0]['source_id']
        own = self.request('/v1/workspace/action', {'action': 'source_get', 'source_id': source_id})
        self.assertIn('Andromède', own['text'])
        self.denied(403, '/v1/workspace/action', {'action': 'source_get', 'source_id': source_id}, identity=self.second)

    def test_operational_events_are_generic_deduplicated_and_skip_maintenance(self):
        operations = Operations.__new__(Operations)
        operations.controller = types.SimpleNamespace(remote=self.store)
        backups = {'job': {'state': 'failed', 'id': 'backup-fixture'},
                   'last_error': 'Disque plein : D:/secret/personnel document confidentiel',
                   'catalog': [{'id': 'secondary-fixture', 'secondary': {'status': 'error'}}]}
        restorations = {'state': 'failed', 'job': {'id': 'restore-fixture'}}
        operations.backups = types.SimpleNamespace(status=lambda: backups)
        operations.restorations = types.SimpleNamespace(status=lambda: restorations)
        operations.notification_tick(); operations.notification_tick()
        admin = self.store.notifications.admin()
        self.assertEqual(4, len(admin['items']))
        self.assertEqual({'backup_failed', 'backup_copy_failed', 'storage_low', 'restore_failed'}, {row['type'] for row in admin['items']})
        self.assertNotIn('secret', json.dumps(admin)); self.assertNotIn('confidentiel', json.dumps(admin))
        self.assertEqual([], self.request()['items'])
        backups['job']['id'] = 'next-fixture'; self.store.maintenance = True
        operations.notification_tick()
        self.assertEqual(4, len(self.store.notifications.admin()['items']))


if __name__ == '__main__':
    unittest.main()
