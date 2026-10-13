"""Private ingress credentials, GPU scheduling and fixed inference destination."""
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from hermes_inference import HermesPrivateServer
from hermes_conversations import HermesConversations
from hermes_tools import FredTools
from remote import AccessStore
from test_hermes_conversations import Accounts, Service


class PrivateInferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='fred-hermes-provider-')
        self.store = AccessStore(Path(self.tmp.name))
        self.store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        self.a = self.store.issue('A')['id']; self.b = self.store.issue('B')['id']
        self.captured = []; self.truncated = False
        parent = self
        class Model(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                raw = b'{"service":"strata","loaded":true,"model":"actual-local"}'
                self.send_response(200); self.end_headers(); self.wfile.write(raw)
            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                parent.captured.append((dict(self.headers), data))
                self.send_response(200); self.end_headers()
                self.wfile.write(b'data: {"choices":[{"delta":{"content":"Final"}}]}\n\n')
                if not parent.truncated: self.wfile.write(b'data: [DONE]\n\n')
        self.model = ThreadingHTTPServer(('127.0.0.1', 0), Model)
        threading.Thread(target=self.model.serve_forever, daemon=True).start()
        self.accounts = Accounts()
        self.accounts.authenticate_private = lambda token, kind: self.a if (kind, token) in [('inference', 'key-A'), ('tool', 'tool-A')] else self.b if (kind, token) == ('inference', 'key-B') else None
        self.manager = HermesConversations(self.store, self.accounts, Service())
        self.private = HermesPrivateServer(self.store, lambda: (self.model.server_port, 'ignored', 'backend-secret'))
        self.private.accounts = self.accounts; self.private.conversations = self.manager
        self.private.tools = FredTools(self.store.workspace, lambda owner, context: bool(context and self.manager.context(owner) is context and self.manager.valid(owner, context)))
        self.private.start()
    def tearDown(self):
        self.manager.active.clear(); self.store.active = 0
        self.manager.close(); self.private.close(); self.model.shutdown(); self.model.server_close()
        self.store.workspace.shutdown(); self.store.voice.close(); self.tmp.cleanup()
    def post(self, path, value, token):
        context = self.manager.context(self.a if token in ('key-A','tool-A') else self.b)
        request = urllib.request.Request(self.private.url + path, json.dumps(value).encode(),
                                        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json',
                                                 **({'X-Fred-Request': context['request_id']} if context else {})})
        try:
            with urllib.request.urlopen(request, timeout=5) as response: return response.status, response.read()
        except urllib.error.HTTPError as response: return response.code, response.read()
    def activate(self):
        return self.manager._prepare(self.a, {'messages': [{'role': 'user', 'content': 'Question'}]}, secrets.token_hex(16), 'test', None, None, False)[1]
    def test_provider_requires_own_active_run_and_forces_local_model_credentials(self):
        body = {'messages': [{'role': 'user', 'content': 'Question'}], 'model': 'attacker', 'base_url': 'http://outside', 'api_key': 'leak', 'stream': True, 'max_tokens': 999999}
        self.assertEqual(self.post('/v1/chat/completions', body, 'key-A')[0], 401)
        self.activate()
        self.assertEqual(self.post('/v1/chat/completions', body, 'key-B')[0], 401)
        status, raw = self.post('/v1/chat/completions', body, 'key-A')
        self.assertEqual(status, 200); self.assertIn(b'[DONE]', raw)
        headers, data = self.captured[-1]
        self.assertEqual(headers['Authorization'], 'Bearer backend-secret')
        self.assertEqual(data['model'], 'actual-local'); self.assertEqual(data['max_tokens'], 16384)
        self.assertFalse(data['strata_mcp']); self.assertNotIn('base_url', data); self.assertNotIn('api_key', data)
        self.assertEqual(self.manager.context(self.a)['model_calls'], 1)
        self.assertEqual(self.store.scheduler.snapshot()['active'], 0)
    def test_mcp_lifecycle_without_run_but_tool_call_needs_active_authorization(self):
        initialize = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18'}}
        status, raw = self.post('/mcp', initialize, 'tool-A')
        self.assertEqual(status, 200); self.assertEqual(json.loads(raw)['result']['serverInfo']['name'], 'fred-tools')
        call = {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'fred_calculate', 'arguments': {'expression': '(2+3)*4'}}}
        self.assertTrue(json.loads(self.post('/mcp', call, 'tool-A')[1])['result']['isError'])
        self.activate()
        result = json.loads(self.post('/mcp', call, 'tool-A')[1])['result']
        self.assertFalse(result['isError']); self.assertIn('20', result['content'][0]['text'])
        self.store.revoke(self.a)
        self.assertTrue(json.loads(self.post('/mcp', call, 'tool-A')[1])['result']['isError'])
    def test_truncated_model_stream_never_counts_as_success(self):
        self.activate(); self.truncated = True
        status, raw = self.post('/v1/chat/completions', {'messages': [{'role': 'user', 'content': 'Q'}], 'stream': True}, 'key-A')
        self.assertEqual(status, 200); self.assertNotIn(b'[DONE]', raw)
        self.assertIn(b'"error"',raw)
        self.assertEqual(self.store.scheduler.succeeded, 0)
        self.assertEqual(self.store.scheduler.failed, 1)
    def test_local_provider_cannot_change_the_admitted_thinking_choice(self):
        for effort in ('none','low','medium','high'):
            with self.subTest(effort=effort):
                self.manager.active.clear();self.store.active=0
                self.manager._prepare(self.a,{'messages':[{'role':'user','content':'Q'}],'reasoning_effort':effort},
                    secrets.token_hex(16),'thinking-'+effort,None,None,False)
                status,_=self.post('/v1/chat/completions',{'messages':[{'role':'user','content':'Q'}],
                    'reasoning_effort':'low','chat_template_kwargs':{'enable_thinking':False},'stream':True},'key-A')
                self.assertEqual(status,200);body=self.captured[-1][1]
                self.assertEqual(body['reasoning_effort'],effort)
                self.assertEqual(body['chat_template_kwargs']['enable_thinking'],effort!='none')


if __name__ == '__main__': unittest.main()
