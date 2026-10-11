"""Native web routing, secret isolation and cancellation without cloud inference."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

from core import write_json
from test_hermes_models import Source
from hermes_fred import HermesFred
from hermes_service import child_environment, installation
from hermes_web import NativeHermesWeb, arguments_for, clean_result, public_url
from remote import AccessStore
from workspace import Workspace
from hermes_tools import FredTools
from hermes_inference import HermesPrivateServer


class WebBounds(unittest.TestCase):
    def test_only_two_native_tools_and_bounded_inputs_are_allowed(self):
        self.assertEqual(arguments_for('web_search', {'query': ' Public question '}), {'query': 'Public question', 'limit': 5})
        self.assertEqual(arguments_for('web_extract', {'urls': [{'href': 'https://example.org/'}]}),
                         {'urls': ['https://example.org/'], 'char_limit': 15000})
        for name, value in [('terminal', {}), ('browser_navigate', {}), ('web_search', {'query': 'q', 'owner': 'another'}),
                ('web_search', {'query': ''}), ('web_search', {'query': 'q', 'limit': True}),
                ('web_search', {'query': 'q', 'limit': 11}), ('web_search', {'query': 'x' * 2001}),
                ('web_extract', {'urls': []}), ('web_extract', {'urls': ['https://example.org/'] * 6}),
                ('web_extract', {'urls': ['https://example.org/'], 'char_limit': 50001})]:
            with self.subTest(name=name, value=value), self.assertRaises(ValueError): arguments_for(name, value)

    def test_urls_private_credentials_and_reserved_hosts_are_refused(self):
        for url in ('http://127.0.0.1/', 'http://10.0.0.1/', 'https://[::1]/', 'https://localhost/',
                'https://printer.local/', 'https://metadata.google.internal/', 'file:///etc/passwd',
                'https://u:p@example.org/', 'https://example.org:8643/', 'https://example.org/?access_token=abc',
                'https://example.org/?%61pi_key=abc', 'https://example.org/\nsecret'):
            self.assertFalse(public_url(url), url)
            with self.assertRaises(ValueError): arguments_for('web_extract', {'urls': [url]})
        self.assertTrue(public_url('https://example.org/?key=facet'))

    def test_provider_errors_paths_and_extra_fields_never_reach_model(self):
        private = {'success': False, 'error': 'Bearer fixture-secret http://192.168.1.1/auth'}
        safe = clean_result('web_search', private, {'limit': 5})
        self.assertNotIn('fixture-secret', json.dumps(safe)); self.assertNotIn('192.168', json.dumps(safe))
        result = clean_result('web_search', {'data': {'web': [
            {'url': 'https://example.org/', 'title': 'Public', 'description': 'Data', 'api_key': 'fixture-secret'},
            {'url': 'http://127.0.0.1/', 'title': 'Private'}]}}, {'limit': 5})
        self.assertEqual(len(result['data']['web']), 1); self.assertNotIn('fixture-secret', json.dumps(result))
        result = clean_result('web_extract', {'results': [{'url': 'https://example.org/',
            'content': 'Secret error output', 'error': private['error'], 'path': 'C:/personal/secret'}]}, {'char_limit': 2000})
        self.assertEqual(result['results'][0]['content'], ''); self.assertNotIn('personal', json.dumps(result))

    def test_cancellation_and_revocation_interrupt_running_subprocess(self):
        runtime = {'python': Path(sys.executable), 'source': Path(__file__).parent, 'tools': Path(tempfile.gettempdir())}
        for kind in ('cancel', 'revocation'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(prefix='fred-web-cancel-') as temporary:
                home = Path(temporary); marker = home / 'started'; finished = home / 'finished'
                script = 'import json,sys,time; from pathlib import Path; json.load(sys.stdin); Path(' + repr(str(marker)) + ").touch(); time.sleep(10); Path(" + repr(str(finished)) + ").touch(); print('{}')"
                web = NativeHermesWeb(runtime, home, timeout=12); cancel = threading.Event(); valid = [True]; errors = []
                def worker():
                    try: web.call('web_search', {'query': 'public'}, cancel, lambda: valid[0])
                    except ValueError as error: errors.append(str(error))
                with patch('hermes_web._NATIVE', script):
                    thread = threading.Thread(target=worker); thread.start()
                    deadline = time.monotonic() + 5
                    while not marker.exists() and time.monotonic() < deadline: time.sleep(.02)
                    self.assertTrue(marker.exists())
                    if kind == 'cancel': cancel.set()
                    else: valid[0] = False
                    thread.join(2)
                self.assertFalse(thread.is_alive()); self.assertTrue(errors); self.assertFalse(finished.exists())

    def test_timeout_and_oversized_subprocess_output_are_bounded(self):
        runtime = {'python': Path(sys.executable), 'source': Path(__file__).parent, 'tools': Path(tempfile.gettempdir())}
        with tempfile.TemporaryDirectory() as temporary:
            web = NativeHermesWeb(runtime, Path(temporary), timeout=.25)
            with patch('hermes_web._NATIVE', "import json,sys,time; json.load(sys.stdin); time.sleep(10)"), self.assertRaises(ValueError):
                web.call('web_search', {'query': 'public'})
            web.timeout = 2
            with patch('hermes_web._NATIVE', "import json,sys; json.load(sys.stdin); print('x'*400001)"), self.assertRaises(ValueError):
                web.call('web_search', {'query': 'public'})


class WebHTTPFixture:
    def __init__(self):
        self.calls = []; self.redirect = None
        fixture = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def reply(self, value):
                raw = json.dumps(value).encode(); self.send_response(200)
                self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(raw)))
                self.end_headers(); self.wfile.write(raw)
            def do_GET(self): self.reply({'object': 'list', 'data': [{'id': 'model-a'}]})
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                fixture.calls.append((self.path, self.headers.get('Authorization'), body))
                if self.path == '/v2/search':
                    return self.reply({'success': True, 'data': {'web': [{'url': 'https://example.org/',
                        'title': 'Public fixture', 'description': 'Synthetic public source.'}]}})
                if self.path == '/v2/scrape':
                    return self.reply({'success': True, 'data': {'markdown': 'Synthetic extracted content.',
                        'metadata': {'title': 'Public fixture', 'sourceURL': fixture.redirect or body['url']}}})
                if self.path != '/v1/chat/completions': return self.send_error(404)
                tool_messages = [m for m in body['messages'] if m.get('role') == 'tool']
                schema_names = {tool['function']['name'] for tool in body.get('tools', [])}
                if not tool_messages:
                    name, args = 'web_search', {'query': 'Public synthetic web fixture', 'limit': 2}
                elif len(tool_messages) == 1:
                    name, args = 'web_extract', {'urls': ['https://example.org/'], 'char_limit': 2000}
                else: name, args = None, None
                if name and name not in schema_names: return self.send_error(422)
                message = {'role': 'assistant', 'content': None} if name else {'role': 'assistant', 'content': 'Synthetic answer from [Public fixture](https://example.org/).'}
                if name: message['tool_calls'] = [{'id': 'call_' + name, 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args)}}]
                finish = 'tool_calls' if name else 'stop'
                if not body.get('stream'):
                    return self.reply({'id': 'chat_fixture', 'object': 'chat.completion', 'created': int(time.time()),
                        'model': body['model'], 'choices': [{'index': 0, 'message': message, 'finish_reason': finish}],
                        'usage': {'prompt_tokens': 20, 'completion_tokens': 10, 'total_tokens': 30}})
                self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.end_headers()
                delta = dict(message)
                if name: delta['tool_calls'][0]['index'] = 0
                event = {'id': 'chat_fixture', 'object': 'chat.completion.chunk', 'created': int(time.time()),
                    'model': body['model'], 'choices': [{'index': 0, 'delta': delta, 'finish_reason': None}]}
                self.wfile.write(('data: ' + json.dumps(event) + '\n\n').encode())
                event['choices'] = [{'index': 0, 'delta': {}, 'finish_reason': finish}]
                self.wfile.write(('data: ' + json.dumps(event) + '\n\ndata: [DONE]\n\n').encode())
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)
    def close(self): self.server.shutdown(); self.server.server_close()


_SOURCE = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'hermes/hermes-agent'
@unittest.skipUnless(os.name == 'nt' and (_SOURCE / 'hermes_cli/main.py').is_file(), 'Installed native Hermes required.')
class NativeWebTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='fred-native-web-'); self.root = Path(self.tmp.name)
        self.http = WebHTTPFixture(); self.personal = self.root / 'synthetic-personal'; self.personal.mkdir()
        write_json(self.personal / 'config.yaml', {'web': {'backend': 'firecrawl'},
            'security': {'allow_private_urls': True, 'fake_ip_ranges': ['198.18.0.0/15']}})
        (self.personal / '.env').write_text('FIRECRAWL_API_URL=' + self.http.url + '\nFIRECRAWL_API_KEY=fixture-web-key\n', encoding='utf-8')
        self.runtime = installation(); self.web = NativeHermesWeb(self.runtime, self.personal, timeout=30)
    def tearDown(self): self.http.close(); self.tmp.cleanup()
    def test_actual_native_firecrawl_search_extract_keep_keys_central_and_block_redirects(self):
        initial = (self.personal / 'config.yaml').read_bytes()
        result = self.web.call('web_search', {'query': 'public fixture', 'limit': 2})
        self.assertTrue(result['success']); self.assertEqual(result['data']['web'][0]['url'], 'https://example.org/')
        result = self.web.call('web_extract', {'urls': ['https://example.org/'], 'char_limit': 2000})
        self.assertEqual(result['results'][0]['content'], 'Synthetic extracted content.')
        self.assertNotIn('fixture-web-key', json.dumps(result))
        self.assertTrue(all(auth == 'Bearer fixture-web-key' for _, auth, _ in self.http.calls))
        self.assertEqual(initial, (self.personal / 'config.yaml').read_bytes())
        self.assertFalse((self.personal / 'config_backups').exists())
        # Even the permissive PC config cannot allow a public extraction to
        # return a redirect into the private network. The configured API endpoint
        # above remains a trusted server connection rather than a user URL.
        self.http.redirect = 'http://127.0.0.1/private'
        result = self.web.call('web_extract', {'urls': ['https://example.org/redirect']})
        self.assertEqual(result['results'], [])
    def test_actual_native_ssrf_rebinding_redirect_and_fake_ip_policy_stay_fail_closed(self):
        import hermes_web
        # Inject only DNS answers in the real native interpreter. These checks
        # execute after Fred's forced policy and before the selected provider.
        replacement = '''
  import socket
  url_safety._getaddrinfo=lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('198.18.0.1',443))]
  from tools.url_safety import SSRFConnectionBlocked
  checks={'preflight':url_safety.is_safe_url('https://example.org/'), 'connect_blocked':False}
  try:url_safety._resolved_http_connect_ips('example.org',443,'https')
  except SSRFConnectionBlocked:checks['connect_blocked']=True
  result=checks
'''
        original = hermes_web._NATIVE
        start = original.index("  if data['operation']=='status':")
        stop = original.index('\nexcept Exception:')
        with patch('hermes_web._NATIVE', original[:start] + replacement + original[stop:]):
            result = self.web._run({'operation': 'status'})
        self.assertFalse(result['preflight']); self.assertTrue(result['connect_blocked'])
        self.assertFalse(self.http.calls)
    def test_actual_gateway_calls_native_web_through_authenticated_broker_and_returns_sources(self):
        store = AccessStore(self.root / 'fred'); store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        owner = store.issue('Isolated native web')['id']
        with store.workspace.db() as db:
            db.execute('INSERT INTO policies VALUES(?,?)', (owner, json.dumps({'web': True})))
        facade = HermesFred(store, lambda: (_ for _ in ()).throw(AssertionError('No Qwen inference')), port=0, private_port=0)
        facade.models.source = Source(self.http.url + '/v1'); facade.models.source.rows[0]['models'] = facade.models.source.rows[0]['models'][:1]
        facade.models.configure({'share_all': True}); facade.tools.web = self.web; store.hermes = facade
        try:
            facade.start(); model = facade.model_catalog(owner)['data'][1]['id']; request = secrets.token_hex(16)
            events = list(facade.stream(owner, {'model': model, 'messages': [{'role': 'user', 'content': 'Synthetic public search and read.'}]}, request, 'native-web-fixture'))
            self.assertIn(b'Synthetic answer', b''.join(events))
            self.assertEqual(facade.conversations.reconcile(owner, request, 'native-web-fixture')['status'], 'completed')
            self.assertEqual([path for path, _, _ in self.http.calls if path.startswith('/v2/')], ['/v2/search', '/v2/scrape'])
            model_requests = [body for path, _, body in self.http.calls if path == '/v1/chat/completions']
            self.assertEqual(len(model_requests), 3)
            tool_names = {tool['function']['name'] for tool in model_requests[0]['tools']}
            self.assertIn('web_search', tool_names); self.assertIn('web_extract', tool_names)
            self.assertNotIn('mcp__fred__fred_web_search', tool_names)
            self.assertFalse({'terminal', 'browser_navigate'} & tool_names)
            self.assertIn('Synthetic extracted content.', json.dumps(model_requests[-1]['messages']))
            self.assertIn(b'example.org', b''.join(events))
            sources = facade.conversations.reconcile(owner, request, 'native-web-fixture')['sources']
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0]['text'], 'Synthetic extracted content.')
            self.assertEqual(sources[0]['origin'], 'hermes-web'); self.assertTrue(sources[0]['retrieved'])
            self.assertIn(b'workspace_sources', b''.join(events))
            profile = facade.accounts.root / 'profiles' / ('fred-' + owner)
            for filename in ('.env', 'config.yaml'):
                raw = (profile / filename).read_text()
                self.assertNotIn('fixture-web-key', raw); self.assertNotIn('FIRECRAWL_API_KEY', raw)
        finally:
            facade.close(); store.hermes = None; store.workspace.shutdown(); store.voice.close()

    def test_native_bridge_multiplex_secret_scopes_do_not_leak_between_concurrent_profiles(self):
        import hermes_web
        calls = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                value = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append((self.headers.get('Authorization'), value['params']['name'], value['params'].get('run_id')))
                raw = json.dumps({'jsonrpc': '2.0', 'id': value['id'], 'result': {'results': []}}).encode()
                self.send_response(200); self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw))); self.end_headers(); self.wfile.write(raw)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        target = 'http://127.0.0.1:' + str(server.server_port) + '/mcp'
        script = hermes_web.PATCH_SOURCE + r'''
import asyncio,contextlib,io,json,logging,os,sys
logging.disable(logging.CRITICAL)
data=json.load(sys.stdin)
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
 _fred_install_web_bridge()
 from agent.secret_scope import set_multiplex_active,set_secret_scope,reset_secret_scope
 from tools.approval_context import set_current_session_key,reset_current_session_key
 from tools.registry import registry
 set_multiplex_active(True)
 os.environ['FRED_TOOL_KEY']='wrong-global-token'
 os.environ['FIRECRAWL_API_KEY']='wrong-global-web-token'
 async def run(key):
  token=set_secret_scope({'FRED_WEB_URL':data['url'],'FRED_TOOL_KEY':key},profile_home=data['home']+'/'+key)
  binding=set_current_session_key('run-'+key)
  try:
   result=await registry.get_entry('web_extract').handler({'urls':['https://example.org/']})
   return json.loads(result)
  finally:reset_current_session_key(binding);reset_secret_scope(token)
 async def all():return await asyncio.gather(run('scope-a'),run('scope-b'))
 results=asyncio.run(all())
 # Unscoped reads fail closed even with a tempting process-global key present.
 blocked=not registry.get_entry('web_search').check_fn()
print(json.dumps({'results':results,'unscoped_blocked':blocked}))
'''
        try:
            result = subprocess.run([str(self.runtime['python']), '-c', script], input=json.dumps({'url': target, 'home': str(self.root)}).encode(),
                env=child_environment(self.root, self.runtime), cwd=self.runtime['source'], stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, timeout=25)
            self.assertEqual(result.returncode, 0, 'Native scope fixture failed; diagnostics kept private.')
            value = json.loads(result.stdout)
            self.assertTrue(value['unscoped_blocked'])
            self.assertEqual(value['results'], [{'results': []}, {'results': []}])
            self.assertEqual(set(calls), {('Bearer scope-a', 'web_extract', 'run-scope-a'), ('Bearer scope-b', 'web_extract', 'run-scope-b')})
        finally: server.shutdown(); server.server_close()

    def test_delayed_cancelled_native_tool_cannot_execute_on_following_turn(self):
        import hermes_web
        workspace = Workspace(self.root / 'stale-workspace')
        with workspace.db() as db:
            db.execute('INSERT INTO policies VALUES(?,?)', ('a', json.dumps({'web': True})))
        old = {'request_id': 'a' * 32, 'remote': 'run_old', 'cancel': threading.Event(), 'sources': []}
        new = {'request_id': 'b' * 32, 'remote': 'run_new', 'cancel': threading.Event(), 'sources': []}
        active, executions = [old], []
        tools = FredTools(workspace, lambda owner, context: owner == 'a' and active[0] is context)
        class Web:
            def call(self, name, arguments, cancel=None, valid=None):
                assert valid(); executions.append(active[0]['request_id'])
                return {'results': [{'url': 'https://example.org/', 'title': 'Synthetic', 'content': 'Late old request'}]}
        tools.web = Web()
        private = HermesPrivateServer(SimpleNamespace(valid_owner=lambda owner: owner == 'a'), lambda: None, port=0)
        private.accounts = SimpleNamespace(authenticate_private=lambda token, kind:
            'a' if token == 'fixture-owner-token' and kind == 'tool' else None)
        private.conversations = SimpleNamespace(context=lambda owner: active[0]); private.tools = tools
        private.start()
        script = hermes_web.PATCH_SOURCE + r'''
import asyncio,contextlib,io,json,logging,sys,time
from pathlib import Path
logging.disable(logging.CRITICAL)
data=json.load(sys.stdin)
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
 _fred_install_web_bridge()
 from agent.secret_scope import set_multiplex_active,set_secret_scope,reset_secret_scope
 from tools.approval_context import set_current_session_key,reset_current_session_key
 from tools.registry import registry
 import http.client
 original=http.client.HTTPConnection.request
 def delayed(self,*args,**kw):
  Path(data['gate']).touch()
  while not Path(data['release']).exists():time.sleep(.01)
  return original(self,*args,**kw)
 http.client.HTTPConnection.request=delayed
 set_multiplex_active(True)
 scope=set_secret_scope({'FRED_WEB_URL':data['url'],'FRED_TOOL_KEY':'fixture-owner-token'},profile_home=data['home'])
 binding=set_current_session_key('run_old')
 try:
  handler=registry.get_entry(data['name']).handler
  result=asyncio.run(handler(data['arguments'])) if data['name']=='web_extract' else handler(data['arguments'])
 finally:reset_current_session_key(binding);reset_secret_scope(scope)
print(result)
'''
        try:
            for name, args in [('web_extract', {'urls': ['https://example.org/']}), ('web_search', {'query': 'public fixture'})]:
                with self.subTest(name=name):
                    old['cancel'].clear(); old['sources'].clear(); new['sources'].clear(); active[0] = old
                    gate, release = self.root / ('gate-' + name), self.root / ('release-' + name)
                    process = subprocess.Popen([str(self.runtime['python']), '-c', script], cwd=self.runtime['source'],
                        env=child_environment(self.root, self.runtime), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    try:
                        process.stdin.write(json.dumps({'url': private.url + '/mcp', 'home': str(self.root),
                            'gate': str(gate), 'release': str(release), 'name': name, 'arguments': args}).encode())
                        process.stdin.close(); process.stdin = None
                        deadline = time.monotonic() + 20
                        while not gate.exists() and process.poll() is None and time.monotonic() < deadline: time.sleep(.02)
                        self.assertTrue(gate.exists(), 'Native bridge did not reach delayed HTTP gate.')
                        old['cancel'].set(); active[0] = new; release.touch()
                        output, _ = process.communicate(timeout=10)
                        self.assertEqual(process.returncode, 0); self.assertFalse(json.loads(output)['success'])
                        self.assertFalse(executions); self.assertFalse(old['sources']); self.assertFalse(new['sources'])
                    finally:
                        if process.poll() is None: process.kill(); process.wait()
        finally: private.close(); workspace.shutdown()

    def test_native_keyless_firecrawl_attests_destination_before_returning_content(self):
        import hermes_web
        # Execute the installed keyless parser and Fred's native-worker hook,
        # with transport payloads in memory. No anonymous provider/network calls.
        replacement = r'''
  import socket
  url_safety._getaddrinfo=lambda host,*a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,'',(('127.0.0.1' if host=='127.0.0.1' else '8.8.8.8'),443))]
  cases=[]
  for final in ('http://127.0.0.1/private','https://public.example/final',None):
   metadata={'title':'Public fixture'}
   if final:metadata['sourceURL']=final
   firecrawl._KeylessFirecrawlClient._post=lambda *a,_metadata=metadata,**k:{'data':{'metadata':_metadata,'markdown':'Synthetic page content'}}
   rows=keyless_mcp.firecrawl_extract_keyless(['https://public.example/requested'])
   cases.append(rows)
  result={'cases':cases}
'''
        original = hermes_web._NATIVE; start = original.index("  if data['operation']=='status':"); stop = original.index('\nexcept Exception:')
        with patch('hermes_web._NATIVE', original[:start] + replacement + original[stop:]):
            result = self.web._run({'operation': 'status'})
        private, public, unknown = [rows[0] for rows in result['cases']]
        for row in (private, unknown):
            self.assertTrue(row['blocked_by_policy']); self.assertEqual(row['content'], ''); self.assertTrue(row['error'])
        self.assertEqual(public['url'], 'https://public.example/final'); self.assertEqual(public['content'], 'Synthetic page content')
        self.assertFalse(self.http.calls)


if __name__ == '__main__': unittest.main()
