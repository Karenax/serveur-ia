"""Cross-protocol concurrency and recovery at real storage/journal boundaries."""
import datetime as dt
import json
from pathlib import Path
import secrets
import tempfile
import time
import unittest
from unittest.mock import patch

from assistant_commands import execute, tick
from command_journal import request_key, MAX_RECEIPTS
from workspace import Workspace, Conflict


class CommandBoundariesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Workspace(Path(self.tmp.name))

    def tearDown(self):
        self.workspace.shutdown()
        self.tmp.cleanup()

    def command(self, operation, **values):
        return execute(self.workspace, 'a', {'operation': operation, **values}, request_key=request_key())

    def test_cross_protocol_stale_update_and_delete_preserve_recent_memory(self):
        for project in (None, self.workspace.action('a', {'action': 'project_create', 'title': 'Projet'})['id']):
            with self.subTest(project=project):
                original = execute(self.workspace, 'a', {'operation': 'memory_add', 'text': 'Avant'},
                                   project=project, request_key=request_key())
                recent = execute(self.workspace, 'a', {'operation': 'memory_update', 'id': original['id'],
                                 'revision': original['revision'], 'text': 'Version récente'},
                                 project=project, request_key=request_key())
                prefix = '' if project else 'personal_'
                for action in ('save', 'delete'):
                    for revision in (None, original['revision']):
                        with self.assertRaises(Conflict):
                            self.workspace.action('a', {'action': prefix+'memory_'+action,
                                'id': original['id'], 'revision': revision, 'text': 'Ancien brouillon'})
                latest = execute(self.workspace, 'a', {'operation': 'memory_list'}, project=project)['memories'][0]
                self.assertEqual(latest['text'], 'Version récente')
                self.assertEqual(latest['revision'], recent['revision'])

    def test_forget_and_cancel_remain_durable_at_both_limits(self):
        for boundary in ('journal', 'quota'):
            with self.subTest(boundary=boundary):
                memory = self.command('memory_add', text='Souvenir fictif')
                reminder = self.command('reminder_create', text='Ne doit pas partir',
                    at=dt.datetime.fromtimestamp(time.time()+3600, dt.timezone.utc).isoformat())
                reminder = next(row for row in self.command('list')['reminders'] if row['id']==reminder['id'])
                if boundary == 'journal':
                    with self.workspace.db() as db:
                        db.executemany('INSERT INTO assistant_commands VALUES(?,?,?,?,?)', [
                            ('a', f'{number:032x}', 'a'*64, '{}', time.time()) for number in range(MAX_RECEIPTS)
                        ])
                    quota = patch.object(self.workspace, 'quota', wraps=self.workspace.quota)
                else:
                    quota = patch.object(self.workspace, 'quota', side_effect=ValueError('Quota plein'))
                with quota:
                    for operation, record in (('memory_forget', memory), ('reminder_cancel', reminder)):
                        key = request_key()
                        values = {'operation': operation, 'id': record['id'], 'revision': record['revision']}
                        first = execute(self.workspace, 'a', values, request_key=key)
                        self.assertEqual(first, execute(self.workspace, 'a', values, request_key=key))
                self.assertEqual(tick(self.workspace, reminder['due']+1), 0)
                self.assertFalse(self.command('list')['memories'])

    def test_compacted_nonce_cannot_replay_a_mutation_after_restart(self):
        now = time.time()
        key = request_key(issued_at=now-200)
        values = {'operation': 'memory_add', 'text': 'Une seule fois'}
        execute(self.workspace, 'a', values, request_key=key)
        with self.workspace.db() as db:
            db.executemany('INSERT INTO assistant_commands VALUES(?,?,?,?,?)', [
                ('a', request_key(issued_at=now-100+number/1000), 'a'*64, '{}', now)
                for number in range(MAX_RECEIPTS)
            ])
        self.command('memory_add', text='Après compactage')
        self.workspace.shutdown()
        self.workspace = Workspace(Path(self.tmp.name))
        with self.assertRaisesRegex(Conflict, 'expiré'):
            execute(self.workspace, 'a', values, request_key=key)
        self.assertEqual(len(self.command('list')['memories']), 2)
        with self.workspace.db() as db:
            self.assertLess(db.execute('SELECT COUNT(*) FROM assistant_commands').fetchone()[0], MAX_RECEIPTS)


if __name__ == '__main__':
    unittest.main()
