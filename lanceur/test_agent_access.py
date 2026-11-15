"""Agent permissions are explicit, durable and tied to an active device."""

import contextlib
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from agent_access import AgentAccess


class AgentAccessTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        path = Path(self.folder.name) / 'workspace.db'
        with contextlib.closing(sqlite3.connect(path)) as db:
            db.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
            db.commit()

        class Workspace:
            @contextlib.contextmanager
            def db(self, owner=None):
                connection = sqlite3.connect(path)
                try:
                    with connection:
                        yield connection
                finally:
                    connection.close()

        class Store:
            lock = threading.RLock()
            workspace = Workspace()
            enabled = True

            def valid_owner(self, identity):
                return self.enabled and identity == 'device-a'

        self.store = Store()
        self.access = AgentAccess(self.store)

    def tearDown(self):
        self.folder.cleanup()

    def test_default_deny_scope_and_revocation(self):
        self.assertIsNone(self.access.operator_for('device-a'))
        self.access.set_operator('device-a', role='reader', project_ids=['project-a'])
        self.assertEqual(self.access.operator_for('device-a'), {
            'id': 'device-a', 'role': 'reader', 'project_ids': ['project-a'], 'person_id': None})
        self.store.enabled = False
        self.assertIsNone(self.access.operator_for('device-a'))
        self.store.enabled = True
        self.access.revoke('device-a')
        self.assertIsNone(self.access.operator_for('device-a'))

    def test_invalid_access_does_not_grant_permissions(self):
        with self.assertRaises(ValueError):
            self.access.set_operator('unknown', role='owner', project_ids=None)
        with self.assertRaises(ValueError):
            self.access.set_operator('device-a', role='admin', project_ids=None)
        with self.assertRaises(ValueError):
            self.access.set_operator('device-a', role='reader', project_ids='project-a')
        with self.assertRaises(ValueError):
            self.access.set_operator('device-a', role='owner', project_ids=None, agent_operator_id='kiara-service')
        self.assertIsNone(self.access.operator_for('device-a'))

    def test_explicit_agent_identity_preserves_scope_and_revocation(self):
        self.access.set_operator('device-a', role='reader', project_ids=['project-a'],
                                 agent_operator_id='ancien-operateur')
        self.assertEqual(self.access.operator_for('device-a'), {
            'id': 'ancien-operateur', 'role': 'reader', 'project_ids': ['project-a'], 'person_id': None})
        self.store.enabled = False
        self.assertIsNone(self.access.operator_for('device-a'))
        self.store.enabled = True
        self.access.revoke('device-a')
        self.assertIsNone(self.access.operator_for('device-a'))

    def test_old_access_settings_are_still_understood(self):
        with self.store.workspace.db() as db:
            db.execute('INSERT INTO settings VALUES(?,?)',
                       ('agent-access:device-a', '{"role":"reader","project_ids":[],"person_id":null}'))
        self.assertEqual(self.access.operator_for('device-a')['id'], 'device-a')

    def test_stale_admin_edit_cannot_overwrite_or_revoke_newer_rights(self):
        self.access.set_operator('device-a', role='reader', project_ids=['project-a'], expected=None)
        old = self.access.operator_for('device-a')
        self.access.set_operator('device-a', role='editor', project_ids=['project-a'])
        with self.assertRaisesRegex(ValueError, 'droits ont changé'):
            self.access.set_operator('device-a', role='owner', project_ids=None, expected=old)
        with self.assertRaisesRegex(ValueError, 'droits ont changé'):
            self.access.revoke('device-a', expected=old)
        self.assertEqual(self.access.operator_for('device-a')['role'], 'editor')


if __name__ == '__main__':
    unittest.main()
