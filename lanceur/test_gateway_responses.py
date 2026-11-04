"""Real HTTP transport of Strata's native events, without loading a GPU model."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from core import ROOT
from remote import AccessStore, serve_gateway
from scheduler import Scheduler
from gateway_responses import responses_request
import test_remote
from test_remote import client

sys.path.insert(0, str(ROOT / 'dependances/strata-0.1.43.1/source'))
from serve.responses import Assembler, request_tools, input_messages
from serve.frontend import Event, ToolCall


class ResponsesTransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = AccessStore(self.tmp.name)
        self.store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        self.access = self.store.issue('Isolated Codex test')
        self.calls = []
        self.first = threading.Event(); self.release = threading.Event()
        self.mode = 'text'
        parent = self

        class Engine(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"loaded":true,"service":"strata"}')
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                parent.calls.append((self.path, dict(self.headers), body))
                if parent.mode == 'refused':
                    self.send_response(400); self.end_headers()
                    self.wfile.write(b'{"error":{"code":"context_length_exceeded","param":"input","message":"private engine detail"}}'); return
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream' if body.get('stream') else 'application/json')
                self.end_headers()
                _, names, _ = request_tools(body)
                assembler = Assembler(body, 'native-qwen', 10, names, True)
                events = assembler.start()
                if parent.mode == 'tool':
                    events += assembler.feed(Event('tool_call', call=ToolCall('read_client_file', {}, id='call_client')))
                else:
                    events += assembler.feed(Event('content', 'Bonjour'))
                events += assembler.finish({'finish': 'stop', 'completion_tokens': 2})
                if not body.get('stream'):
                    self.wfile.write(json.dumps(assembler.response).encode()); return
                for i, event in enumerate(events):
                    try:
                        self.wfile.write(('event: '+event['type']+'\ndata: '+json.dumps(event)+'\n\n').encode()); self.wfile.flush()
                    except OSError: return  # Revocation deliberately closes the engine socket.
                    if parent.mode in ('blocked', 'partial') and i == 0:
                        parent.first.set(); parent.release.wait(8)
                        if parent.mode == 'partial': return

        self.engine = ThreadingHTTPServer(('127.0.0.1', 0), Engine)
        self.gateway = serve_gateway(self.store, lambda: (self.engine.server_port, 'native-qwen', 'private-engine-key'), 0)
        for server in (self.engine, self.gateway):
            threading.Thread(target=server.serve_forever, daemon=True).start()
        self.base = 'http://127.0.0.1:' + str(self.gateway.server_port)

    def tearDown(self):
        self.release.set()
        for server in (self.gateway, self.engine): server.shutdown(); server.server_close()
        self.tmp.cleanup()

    def request(self, body=None, token=None, base=None):
        req = urllib.request.Request((base or self.base) + '/v1/responses', json.dumps(body or {'model': 'fred-qwen', 'input': 'Bonjour'}).encode(),
            {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + (token or self.access['token'])})
        return urllib.request.urlopen(req, timeout=10)

    def test_json_alias_budget_and_private_credential(self):
        with self.request({'model': 'fred-qwen', 'input': 'Bonjour', 'store': True, 'max_output_tokens': 123}) as r:
            result = json.load(r)
        self.assertEqual(result['model'], 'fred-qwen'); self.assertEqual(result['status'], 'completed')
        path, headers, body = self.calls[-1]
        self.assertEqual(path, '/v1/responses'); self.assertEqual(body['max_output_tokens'], 123)
        self.assertFalse(body['store']); self.assertEqual(headers['Authorization'], 'Bearer private-engine-key')
        self.assertEqual(self.store.scheduler.snapshot()['succeeded'], 1)

    def test_native_function_call_and_replayed_result_keep_ids(self):
        self.mode = 'tool'
        tools = [{'type': 'function', 'name': 'read_client_file', 'parameters': {'type': 'object', 'properties': {}}}]
        body = {'model': 'fred-qwen', 'input': [{'role': 'user', 'content': 'Lis le fichier'}], 'tools': tools, 'stream': True}
        with self.request(body) as r:
            events = [json.loads(line[6:]) for line in r if line.startswith(b'data: ')]
        result = events[-1]['response']
        self.assertEqual(events[-1]['type'], 'response.completed')
        self.assertTrue(all(event['response']['model']=='fred-qwen' for event in events if 'response' in event))
        self.assertEqual(result['output'][0]['call_id'], 'call_client')
        body['input'] += result['output'] + [{'type': 'function_call_output', 'call_id': 'call_client', 'output': 'fichier fictif'}]
        self.mode = 'text'
        with self.request(body) as r: self.assertIn(b'Bonjour', r.read())
        self.assertEqual(self.calls[-1][2]['input'], body['input'])
        self.assertEqual(input_messages(body)[-1]['content'], 'fichier fictif')

    def test_stream_is_incremental(self):
        self.mode = 'blocked'
        with self.request({'model': 'fred-qwen', 'input': 'Bonjour', 'stream': True}) as r:
            line = next(line for line in r if line.startswith(b'event: '))
            self.assertEqual(line.strip(), b'event: response.created')
            self.assertFalse(self.release.is_set())
            self.release.set(); self.assertIn(b'response.completed', r.read())

    def test_partial_stream_gets_failed_terminal(self):
        self.mode = 'partial'; self.release.set()
        with self.request({'model': 'fred-qwen', 'input': 'Bonjour', 'stream': True}) as r: raw = r.read()
        self.assertIn(b'event: response.failed', raw); self.assertNotIn(b'event: response.completed', raw)
        self.assertEqual(self.store.scheduler.snapshot()['failed'], 1)

    def test_revocation_during_blocked_read_aborts(self):
        self.mode = 'blocked'
        with self.request({'model': 'fred-qwen', 'input': 'Bonjour', 'stream': True}) as r:
            self.assertEqual(next(line for line in r if line.startswith(b'event: ')).strip(), b'event: response.created')
            self.store.revoke(self.access['id'])
            started = time.monotonic(); raw = r.read()
            self.assertLess(time.monotonic() - started, 3)
        self.assertNotIn(b'Bonjour', raw); self.assertIn(b'response.failed', raw)

    def test_http_errors_keep_code_status_and_hide_engine_detail(self):
        self.mode = 'refused'
        with self.assertRaises(urllib.error.HTTPError) as e: self.request()
        self.assertEqual(e.exception.code, 400)
        body = json.load(e.exception)
        self.assertEqual(body['error']['code'], 'context_length_exceeded')
        self.assertEqual(body['error']['param'], 'input')
        self.assertNotIn('private engine detail', str(body))

    def test_unauthorized_and_unknown_model_do_not_reach_engine(self):
        for token, model, status in [('x'*30, 'fred-qwen', 401), (self.access['token'], 'unknown', 404)]:
            with self.assertRaises(urllib.error.HTTPError) as e:
                self.request({'model': model, 'input': 'Bonjour'}, token=token)
            self.assertEqual(e.exception.code, status)
        self.assertFalse(self.calls)

    def test_remote_provider_cannot_be_routed_to_local_qwen(self):
        self.store.hermes = SimpleNamespace(select_model=lambda *args: {'local': False})
        with self.assertRaises(urllib.error.HTTPError) as e: self.request()
        self.assertEqual(e.exception.code, 400); self.assertFalse(self.calls)

    def test_desktop_proxy_recognizes_responses_terminal(self):
        from wg_crypto import keypair
        private, public = keypair()
        profile = {'url': 'wireguard://10.77.0.1:8766', 'token': self.access['token'], 'local_routes': [],
                   'transport': 'wireguard', 'wireguard': {'private_key': private, 'server_public_key': public,
                       'preshared_key': private, 'address': '10.77.0.2/32', 'endpoint': '127.0.0.1:51820'}}
        remote = client.Remote(profile, opener=urllib.request.build_opener(urllib.request.ProxyHandler({})))
        remote.url = self.base
        with patch.object(client, 'settings_path', return_value=Path(self.tmp.name)/'client.dpapi'):
            local = client.serve_local(remote, 'local-responses-test', 0)
        threading.Thread(target=local.serve_forever, daemon=True).start()
        try:
            with self.request({'model': 'fred-qwen', 'input': 'Bonjour', 'stream': True}, token='local-responses-test',
                              base='http://127.0.0.1:'+str(local.server_port)) as r: raw = r.read()
            self.assertIn(b'response.completed', raw)
            self.assertNotIn(b'connection_error', raw)
        finally: local.shutdown(); local.server_close()

    def test_encrypted_wireguard_carries_native_responses(self):
        from wireguard_access import WireGuardAccess, Engine
        from wg_bridge import Bridge
        wireguard = WireGuardAccess(self.store, self.tmp.name)
        wireguard.configure({'public_host':'127.0.0.1','listen_port':51820})
        profile = dict(wireguard.new_peer(self.access), model='fred-qwen', local_routes=[])
        engine = Engine({'role':'server', 'wireguard':{'private_key':wireguard.vault()['private_key']},
                         'listen_port':0, 'upstream_port':self.gateway.server_port, 'peers':wireguard.peers()})
        profile['wireguard']['endpoint'] = '127.0.0.1:'+str(engine.port)
        bridge = Bridge(profile)
        try:
            body={'model':'fred-qwen','input':'Bonjour','stream':True}
            request=urllib.request.Request(bridge.url+'/v1/responses',json.dumps(body).encode(),
                {'X-Qwen-Bridge':bridge.key,'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=20) as response: raw=response.read()
            self.assertIn(b'response.completed',raw); self.assertIn(b'Bonjour',raw)
            self.assertEqual(self.calls[-1][0],'/v1/responses')
            self.assertEqual(self.calls[-1][1]['Authorization'],'Bearer private-engine-key')
        finally: bridge.close(); engine.close(); wireguard.close()


class ResponsesValidationTests(unittest.TestCase):
    def test_remote_images_host_tools_and_private_parameters_are_rejected(self):
        for fields in [{'input': [{'role': 'user', 'content': [{'type': 'input_image', 'image_url': 'http://127.0.0.1/private'}]}]},
                       {'strata_mcp': True}, {'tools': [{'type': 'mcp', 'server_url': 'http://localhost'}]},
                       {'input': [{'type': 'additional_tools', 'tools': [{'type': 'mcp'}]}]},
                       {'previous_response_id': 'resp_other'}, {'stream': 1}, {'max_output_tokens': True}]:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                responses_request(dict({'model': 'fred-qwen', 'input': 'Test'}, **fields))

    def test_namespaces_and_custom_tools_keep_their_schema(self):
        tools = [{'type': 'namespace', 'name': 'functions', 'tools': [{'type': 'custom', 'name': 'apply_patch', 'format': {'type': 'text'}}]}]
        self.assertEqual(responses_request({'model': 'fred-qwen', 'input': 'Test', 'tools': tools})['tools'], tools)

    def test_bounded_subagent_queue_retains_chat_exclusion(self):
        scheduler = Scheduler()
        items = [scheduler.submit('owner', concurrent=True) for _ in range(4)]
        with self.assertRaises(ValueError): scheduler.submit('owner', concurrent=True)
        with self.assertRaises(ValueError): scheduler.submit('owner')
        self.assertEqual([scheduler.position(item) for item in items], list(range(4)))
        scheduler.cancel('other'); self.assertFalse(any(item['cancelled'] for item in items))
        scheduler.cancel('owner', items[1]['id']); self.assertEqual(len(scheduler.requests), 3)
        scheduler.submit('owner', concurrent=True)
        scheduler.cancel('owner'); self.assertFalse(scheduler.requests)
        scheduler.submit('owner')
        with self.assertRaises(ValueError): scheduler.submit('owner', concurrent=True)


if __name__ == '__main__': unittest.main()
