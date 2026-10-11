"""MCP authorization, project isolation, citations and non-executable arithmetic."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hermes_tools import FredTools, calculate
from workspace import Workspace, public_url
from knowledge import Knowledge


class ToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='fred-hermes-tools-')
        self.workspace = Workspace(self.tmp.name)
        self.active = True
        self.tools = FredTools(self.workspace, lambda owner, context: self.active and owner == 'a')
        self.project = self.workspace.action('a', {'action': 'project_create', 'title': 'Budget'})['id']
        self.other = self.workspace.action('a', {'action': 'project_create', 'title': 'Privé'})['id']
        self.document = self.workspace.action('a', {'action': 'document_create', 'project': self.project,
                                                  'title': 'Budget annuel', 'text': 'Le budget validé est de 2500 euros.'})['id']
        self.private = self.workspace.action('a', {'action': 'document_create', 'project': self.other,
                                                 'title': 'Document privé', 'text': 'Secret hors projet 9999 euros.'})['id']
        self.context = {'request_id': 'run-test', 'conversation_id': 'conversation-test',
                        'project_id': self.project, 'document_id': None, 'cancel': threading.Event(), 'sources': []}

    def tearDown(self):
        self.workspace.shutdown(); self.tmp.cleanup()

    def request(self, method, params=None, context=None, owner='a'):
        return self.tools.dispatch(owner, context if context is not None else self.context,
                                   {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}})

    def call(self, name, **arguments):
        return self.request('tools/call', {'name': name, 'arguments': arguments})['result']

    def data(self, result):
        self.assertFalse(result['isError'], result)
        return json.loads(result['content'][0]['text'])['data']

    def test_mcp_lifecycle_and_argument_contract(self):
        self.assertEqual(self.request('initialize', {'protocolVersion': '2025-06-18'}, {})['result']['serverInfo']['name'], 'fred-tools')
        listing = self.request('tools/list', context={})['result']['tools']
        self.assertEqual(len(listing), 8)
        self.assertTrue(all(t['annotations']['readOnlyHint'] for t in listing))
        self.assertIsNone(self.tools.dispatch('a', {}, {'jsonrpc': '2.0', 'method': 'notifications/initialized'}))
        refused = self.request('tools/call', {'name': 'fred_document_search', 'arguments': {'query': 'budget', 'owner': 'b'}})
        self.assertEqual(refused['error']['code'], -32602)
        self.assertEqual(self.request('does/not/exist')['error']['code'], -32601)
        self.assertEqual(self.tools.dispatch('a', {}, ['batch'])['error']['code'], -32600)

    def test_project_sources_and_bounded_document(self):
        search = self.data(self.call('fred_document_search', query='budget'))
        self.assertEqual(search['sources'][0]['document'], self.document)
        identity = search['sources'][0]['source_id']
        source = self.data(self.call('fred_source_get', source_id=identity))['sources'][0]
        self.assertIn('2500', source['text'])
        self.assertEqual(len(self.context['sources']), 1)
        document = self.data(self.call('fred_document_get', document_id=self.document))
        self.assertIn('2500', document['text'])
        self.assertFalse(document['truncated'])
        self.assertTrue(self.call('fred_document_get', document_id=self.private)['isError'])
        scope = self.data(self.call('fred_workspace_info'))
        self.assertEqual([d['id'] for d in scope['documents']], [self.document])

    def test_source_cannot_escape_project_or_owner(self):
        foreign = self.workspace.action('a', {'action': 'search', 'project': self.other, 'query': 'secret'})['sources'][0]
        self.assertTrue(self.call('fred_source_get', source_id=foreign['source_id'])['isError'])
        self.assertTrue(self.request('tools/call', {'name': 'fred_calculate', 'arguments': {'expression': '2+2'}}, owner='b')['result']['isError'])
        self.context['project_id'] = None
        self.assertTrue(self.call('fred_source_get', source_id=foreign['source_id'])['isError'])

    def test_selected_document_limits_all_tools(self):
        other = self.workspace.action('a', {'action': 'document_create', 'project': self.project,
                                           'title': 'Autre budget', 'text': 'Budget secondaire de 700 euros.'})['id']
        self.context['document_id'] = self.document
        self.assertTrue(self.call('fred_document_get', document_id=other)['isError'])
        self.assertEqual([s['document'] for s in self.data(self.call('fred_document_search', query='budget'))['sources']], [self.document])
        self.assertEqual([s['id'] for s in self.data(self.call('fred_workspace_info'))['documents']], [self.document])

    def test_revocation_cancellation_and_maintenance(self):
        self.active = False
        self.assertTrue(self.call('fred_calculate', expression='2+2')['isError'])
        self.active = True; self.context['cancel'].set()
        self.assertTrue(self.call('fred_calculate', expression='2+2')['isError'])
        self.context['cancel'].clear(); self.workspace.maintenance = True
        self.assertTrue(self.call('fred_calculate', expression='2+2')['isError'])
        self.workspace.maintenance = False
        self.assertTrue(self.request('tools/call', {'name': 'fred_calculate', 'arguments': {'expression': '2+2'}}, context={})['result']['isError'])

    def test_web_permission_and_post_read_revocation(self):
        self.assertTrue(self.call('fred_web_read', url='https://example.com/')['isError'])
        with self.workspace.db() as db:
            db.execute('INSERT INTO policies VALUES(?,?)', ('a', json.dumps({'web': True})))
            db.execute("INSERT INTO settings VALUES('web_enabled','true')")
        with patch('workspace.fetch_public', return_value={'url': 'https://example.com/', 'text': 'Texte public'}):
            self.assertEqual(self.data(self.call('fred_web_read', url='https://example.com/'))['sources'][0]['text'], 'Texte public')
        def revoked(url):
            self.active = False
            return {'url': url, 'text': 'Donnée refusée après révocation'}
        with patch('workspace.fetch_public', side_effect=revoked):
            result = self.call('fred_web_read', url='https://example.com/revoked')
        self.assertTrue(result['isError'])
        self.assertNotIn('Donnée refusée', json.dumps(result))
        self.assertEqual(len(self.context['sources']), 1)
        with self.assertRaises(ValueError): public_url('https://127.0.0.1/')

    def test_arithmetic_cannot_execute_code_or_consume_unbounded_resources(self):
        self.assertEqual(calculate('(2500 * 1.2) - 50')['result'], 2950.0)
        self.assertEqual(self.data(self.call('fred_calculate', expression='7**3'))['result'], 343)
        for expression in ['__import__("os").system("whoami")', 'open("secret")', 'True+1', '9**99999',
                           '2**(12**12)', '1/0', '1e309', '[1]*9999999', '+'.join(['1']*80), '(-1)**0.5']:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                calculate(expression)

    def test_project_archive_blocks_even_calculation(self):
        self.workspace.action('a', {'action': 'project_save', 'id': self.project, 'revision': 1,
                                    'title': 'Budget', 'archived': True})
        self.assertTrue(self.call('fred_calculate', expression='1+1')['isError'])

    def test_real_knowledge_sources_keep_personal_project_and_document_scopes(self):
        class Engine:
            state = 'pret'
            def stop(self): pass
            def encode(self, texts, mode='document', timeout=8):
                return [[1.0] + [0.0]*767 for _ in texts]
        knowledge = Knowledge(self.workspace, Engine()); self.workspace.knowledge = knowledge
        self.workspace.action('a', {'action': 'personal_memory_create', 'text': 'Préférence personnelle : euros'})
        self.workspace.action('a', {'action': 'memory_create', 'project': self.project, 'text': 'Budget du projet confidentiel'})
        knowledge.synchronize()
        project_sources = self.data(self.call('fred_knowledge_search', query='budget'))['sources']
        self.assertTrue(project_sources)
        self.assertTrue(all(s['project'] == self.project for s in project_sources))
        project_reference = project_sources[0]['source_id']
        self.context['project_id'] = None
        personal = self.data(self.call('fred_knowledge_search', query='euros'))['sources']
        self.assertEqual({s['kind'] for s in personal}, {'personal_memory'})
        self.assertTrue(all(s['project'] is None for s in personal))
        self.assertTrue(self.call('fred_source_get', source_id=project_reference)['isError'])
        self.assertFalse(self.call('fred_source_get', source_id=personal[0]['source_id'])['isError'])
        self.context.update(project_id=self.project, document_id=self.document)
        document_sources = self.data(self.call('fred_knowledge_search', query='budget'))['sources']
        self.assertEqual({s['document'] for s in document_sources}, {self.document})


if __name__ == '__main__':
    unittest.main()
