from contextlib import closing
import json
import sqlite3
import tempfile
import unittest

from maintenance.rehearse_project_migration import rehearse
from kiara_shared.history_store import HISTORY_RESET_ID
from workspace import Workspace


class ProjectMigrationRehearsalTests(unittest.TestCase):
    def test_private_identifiers_data_and_transaction_survive_rehearsal(self):
        with tempfile.TemporaryDirectory(prefix='kiara-projets-fictifs-') as root:
            workspace = Workspace(root)
            owner_a, owner_b = 'a' * 16, 'b' * 16
            title = 'Projet fictif'
            p1 = workspace.action(owner_a, {'action': 'project_create', 'title': title})['id']
            p2 = workspace.action(owner_b, {'action': 'project_create', 'title': title})['id']
            workspace.action(owner_a, {'action': 'document_create', 'project': p1, 'title': 'Compte rendu',
                                       'text': 'Le jalon fictif est prévu mardi.'})
            search = workspace.action(owner_a, {'action': 'search', 'project': p1, 'query': 'jalon'})
            source_id = search['sources'][0]['source_id']
            workspace.action(owner_a, {'action': 'memory_create', 'project': p1, 'text': 'Le suivi est mardi.'})
            workspace.action(owner_a, {'action': 'conversation_save', 'project': p1, 'id': 'c' * 32,
                                       'title': 'Recette', 'messages': [], 'revision': 0, 'reset_id': HISTORY_RESET_ID})
            workspace.action(owner_b, {'action': 'project_save', 'id': p2, 'title': title,
                                       'revision': 1, 'archived': True})
            with (closing(sqlite3.connect(':memory:')) as erp, closing(sqlite3.connect(':memory:')) as brain,
                  closing(sqlite3.connect(':memory:')) as registry, workspace.db() as source):
                erp.executescript('''CREATE TABLE projects(id TEXT PRIMARY KEY);
                    CREATE TABLE brain_links(project_id TEXT, brain_project_id TEXT);
                    INSERT INTO projects VALUES ('ERP-1');
                    INSERT INTO brain_links VALUES ('ERP-1','KNOWLEDGE-1');''')
                brain.executescript("CREATE TABLE projects(id TEXT PRIMARY KEY); INSERT INTO projects VALUES ('KNOWLEDGE-1');")
                report = rehearse(source, erp, brain, registry)
                self.assertEqual(report['private_projects'], 2)
                self.assertEqual(report['archived_private_projects'], 1)
                for entity in ('documents', 'memories', 'conversations', 'document_sources'):
                    self.assertEqual(report['private_objects'][entity], 1)
                first = sorted(registry.execute('SELECT * FROM projects'))
                self.assertIsNotNone(source.execute('SELECT id FROM document_sources WHERE id=?', (source_id,)).fetchone())
                self.assertEqual(rehearse(source, erp, brain, registry), report)
                registry.execute("""CREATE TRIGGER stop_insert BEFORE INSERT ON projects
                    WHEN new.kind='managed' BEGIN SELECT RAISE(ABORT,'interruption'); END""")
                with self.assertRaisesRegex(sqlite3.IntegrityError, 'interruption'):
                    rehearse(source, erp, brain, registry)
                self.assertEqual(sorted(registry.execute('SELECT * FROM projects')), first)
                registry.execute('DROP TRIGGER stop_insert')
                self.assertEqual(rehearse(source, erp, brain, registry), report)
                for key, expected in ((p2, '0 projet(s) introuvable(s), 1'),
                                      ('missing', '1 projet(s) introuvable(s), 0')):
                    history = json.dumps({'conversations': [{'project_id': key}]})
                    source.execute('INSERT INTO client_histories VALUES (?, ?, 1, 0)', (owner_a, history))
                    with self.assertRaises(ValueError) as error:
                        rehearse(source, erp, brain, registry)
                    self.assertIn(expected, str(error.exception))
                    self.assertEqual(sorted(registry.execute('SELECT * FROM projects')), first)
                    source.execute('DELETE FROM client_histories WHERE owner=?', (owner_a,))
                erp.execute('INSERT INTO projects VALUES (?)', (p1,))
                with self.assertRaisesRegex(ValueError, 'collision'):
                    rehearse(source, erp, brain, registry)
