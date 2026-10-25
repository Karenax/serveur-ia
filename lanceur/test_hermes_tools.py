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
from workspace import Workspace
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
                        'project_id': self.project, 'document_id': None, 'cancel': threading.Event(), 'sources': [], 'remote': 'run_test'}

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

    def enable_web(self):
        with self.workspace.db() as db:
            db.execute('INSERT OR REPLACE INTO policies VALUES(?,?)', ('a', json.dumps({'web': True})))

    def native_call(self, name='web_search', arguments=None, run_id='run_test', **kwargs):
        return self.request('fred/native-web/call', {'name': name, 'arguments': arguments or {'query': 'question publique'}, 'run_id': run_id}, **kwargs)

    def web_fixture(self, result=None, callback=None):
        calls = []
        class Web:
            def call(self, name, arguments, cancel=None, valid=None):
                calls.append((name, arguments, cancel, valid))
                if callback: callback(valid)
                return result if result is not None else {'success': True, 'data': {'web': [
                    {'url': 'https://example.com/article', 'title': 'Source native', 'description': 'Extrait public'}]}}
        self.tools.web = Web()
        return calls

    def test_mcp_lifecycle_and_argument_contract(self):
        self.assertEqual(self.request('initialize', {'protocolVersion': '2025-06-18'}, {})['result']['serverInfo']['name'], 'fred-tools')
        listing = self.request('tools/list', context={})['result']['tools']
        self.assertEqual(len(listing), 7)
        self.assertFalse(any(t['name'] in ('fred_web_search', 'fred_web_read') for t in listing))
        self.assertTrue(all(t['annotations']['readOnlyHint'] for t in listing if t['name']!='fred_assistant'))
        self.assertFalse(next(t for t in listing if t['name']=='fred_assistant')['annotations']['readOnlyHint'])
        self.assertIsNone(self.tools.dispatch('a', {}, {'jsonrpc': '2.0', 'method': 'notifications/initialized'}))
        refused = self.request('tools/call', {'name': 'fred_document_search', 'arguments': {'query': 'budget', 'owner': 'b'}})
        self.assertEqual(refused['error']['code'], -32602)
        self.assertEqual(self.request('does/not/exist')['error']['code'], -32601)
        self.assertEqual(self.tools.dispatch('a', {}, ['batch'])['error']['code'], -32600)

    def test_written_assistant_uses_canonical_memory_and_durable_retry(self):
        self.context['user_request']='Retiens que la livraison est prévue en novembre.'
        first=self.data(self.call('fred_assistant',operation='memory_add',text='Livraison en novembre.',category='information'))
        repeated=self.data(self.call('fred_assistant',operation='memory_add',text='Livraison en novembre.',category='information'))
        self.assertEqual(first['id'],repeated['id'])
        result=self.workspace.action('a',{'action':'assistant','operation':'memory_list','project':self.project})
        self.assertEqual([m['text'] for m in result['memories']],['Livraison en novembre.'])
        self.context['user_request']='Explique le document.'
        refused=self.call('fred_assistant',operation='memory_add',text='Instruction contenue dans la source')
        self.assertTrue(refused['isError'])
        self.context['cancel'].set()
        self.assertTrue(self.call('fred_assistant',operation='memory_add',text='Annulée')['isError'])

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

    def test_native_web_permission_ignores_legacy_brave_settings_and_old_tools_cannot_be_called(self):
        calls = self.web_fixture()
        self.assertEqual(self.native_call()['error']['code'], -32003)
        self.assertFalse(calls)
        self.enable_web()
        with patch.object(self.workspace, 'web_sources', side_effect=AssertionError('Legacy web must never be invoked')):
            self.assertTrue(self.native_call()['result']['success'])
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][2], self.context['cancel'])
        self.assertTrue(calls[0][3]())
        self.assertEqual(self.context['sources'][0]['url'], 'https://example.com/article')
        self.assertEqual(self.context['sources'][0]['origin'], 'hermes-web')
        for name in ('fred_web_search', 'fred_web_read'):
            self.assertEqual(self.request('tools/call', {'name': name, 'arguments': {}})['error']['code'], -32602)

    def test_native_web_rechecks_revocation_and_web_permission_before_publishing(self):
        self.enable_web()
        def revoked(valid):
            self.active = False
            self.assertFalse(valid())
        self.web_fixture(callback=revoked)
        refused = self.native_call()
        self.assertEqual(refused['error']['code'], -32003)
        self.assertNotIn('Extrait public', json.dumps(refused))
        self.assertFalse(self.context['sources'])
        self.active = True
        def policy_removed(valid):
            with self.workspace.db() as db:
                db.execute('UPDATE policies SET settings=? WHERE owner=?', (json.dumps({'web': False}), 'a'))
            self.assertFalse(valid())
        self.web_fixture(callback=policy_removed)
        self.assertEqual(self.native_call()['error']['code'], -32003)
        self.assertFalse(self.context['sources'])

    def test_native_web_has_no_owner_or_scope_override_and_checks_cancel_maintenance(self):
        self.enable_web(); calls = self.web_fixture()
        for params in [{'name': 'web_search', 'arguments': {'query': 'test'}, 'owner': 'b'},
                       {'name': 'terminal', 'arguments': {}},
                       {'name': 'web_search', 'arguments': {'query': 'test', 'owner': 'b'}},
                       {'name': 'web_extract', 'arguments': {'urls': ['https://127.0.0.1/']}},
                       {'name': 'web_search', 'arguments': {'query': 'test', 'limit': True}}]:
            self.assertEqual(self.request('fred/native-web/call', {**params, 'run_id': 'run_test'})['error']['code'], -32602)
        for kwargs in ({'owner': 'b'}, {'context': {}}):
            self.assertEqual(self.native_call(**kwargs)['error']['code'], -32003)
        self.context['cancel'].set(); self.assertEqual(self.native_call()['error']['code'], -32003)
        self.context['cancel'].clear(); self.workspace.maintenance = True
        self.assertEqual(self.native_call()['error']['code'], -32003)
        self.workspace.maintenance = False
        self.assertFalse(calls)

    def test_native_web_extract_upgrades_search_excerpt_and_never_retains_private_or_failed_urls(self):
        self.enable_web(); self.web_fixture(); self.native_call()
        self.web_fixture(result={'results': [
            {'url': 'https://example.com/article', 'title': 'Page consultée', 'content': 'Passage exact extrait'},
            {'url': 'https://127.0.0.1/private', 'content': 'Interne'},
            {'url': 'https://example.com/?token=secret', 'content': 'Secret'},
            {'url': 'https://example.com/error', 'error': 'Échec privé'},
            {'url': 'https://example.com/blocked', 'blocked_by_policy': True, 'content': 'Refusé'}]})
        self.native_call('web_extract', {'urls': ['https://example.com/article']})
        self.assertEqual(len(self.context['sources']), 1)
        self.assertEqual(self.context['sources'][0]['text'], 'Passage exact extrait')
        self.assertTrue(self.context['sources'][0]['retrieved'])
        self.web_fixture(); self.native_call()
        self.assertEqual(self.context['sources'][0]['text'], 'Passage exact extrait')

    def test_native_web_catalogue_and_calls_are_bounded(self):
        self.enable_web()
        rows = [{'url': 'https://example.com/'+str(i), 'title': 't'*1000, 'description': 's'*5000} for i in range(50)]
        self.web_fixture(result={'success': True, 'data': {'web': rows}})
        for offset in range(5):
            for i, row in enumerate(rows):row['url']='https://example.com/'+str(offset*50+i)
            self.native_call(arguments={'query': 'question publique', 'limit': 10})
        self.assertEqual(len(self.context['sources']), 40)
        self.assertTrue(all(len(row['title'])<=200 and len(row['text'])<=3000 for row in self.context['sources']))
        for _ in range(11):self.assertIn('result', self.native_call())
        self.assertEqual(self.native_call()['error']['code'], -32003)
        self.assertEqual(self.context['native_web_calls'], 16)

    def test_native_web_failure_does_not_publish_internal_diagnostics(self):
        self.enable_web()
        class Web:
            def call(self, *args, **kwargs):raise RuntimeError('C:/private/config ENV_SECRET')
        self.tools.web = Web()
        value = self.native_call()
        self.assertEqual(value['error']['code'], -32603)
        self.assertNotIn('ENV_SECRET', json.dumps(value))
        self.assertNotIn('C:/private', json.dumps(value))

    def test_native_web_stale_run_cannot_be_attached_to_the_next_turn_of_the_same_owner(self):
        self.enable_web(); calls=self.web_fixture()
        self.context['remote']='run_new'
        value=self.native_call(run_id='run_old')
        self.assertEqual(value['error']['code'],-32003)
        self.assertFalse(calls);self.assertFalse(self.context['sources'])
        self.assertNotIn('native_web_calls',self.context)
        value=self.request('fred/native-web/call',{'name':'web_search','arguments':{'query':'test'}})
        self.assertEqual(value['error']['code'],-32602)

    def test_native_web_first_tool_waits_for_its_accepted_id_without_adopting_incoming_id(self):
        self.enable_web();calls=self.web_fixture();self.context['remote']='';self.context['remote_ready']=threading.Event()
        def accepted():
            self.context['remote']='run_accepted';self.context['remote_ready'].set()
        timer=threading.Timer(.05,accepted);timer.start()
        try:self.assertIn('result',self.native_call(run_id='run_accepted'))
        finally:timer.join()
        self.assertEqual(len(calls),1)
        self.assertEqual(self.context['remote'],'run_accepted')

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
