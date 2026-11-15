"""Internal Agent credentials only reach the shared inference endpoints."""

import http.client
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

from remote import AccessStore, serve_gateway


class AgentInferenceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = AccessStore(self.folder.name)
        self.store.agent_inference_token = 'agent-' + 'a' * 40
        self.requests = []
        requests = self.requests

        class Engine(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                data = b'{"loaded":true,"service":"strata"}'
                self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append(payload)
                body = json.dumps({'choices': [{'message': {'role': 'assistant', 'content': 'ok'},
                                                  'finish_reason': 'stop'}]}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.engine = ThreadingHTTPServer(('127.0.0.1', 0), Engine)
        self.gateway = serve_gateway(self.store, lambda: (self.engine.server_port, 'qwen-test', ''), port=0)
        for server in (self.engine, self.gateway):
            threading.Thread(target=server.serve_forever, daemon=True).start()

    def tearDown(self):
        for server in (self.gateway, self.engine):
            server.shutdown()
            server.server_close()
        self.folder.cleanup()

    def call(self, method, path, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.gateway.server_port, timeout=10)
        headers = {'Authorization': 'Bearer ' + self.store.agent_inference_token}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        connection.request(method, path, json.dumps(body).encode() if body is not None else None, headers)
        response = connection.getresponse()
        status = response.status
        payload = json.loads(response.read())
        connection.close()
        return status, payload

    def test_internal_token_is_confined_and_preserves_generation_budget(self):
        self.assertEqual(self.call('GET', '/v1/workspace')[0], 403)
        self.assertEqual(self.call('GET', '/v1/business/api/v1/portfolio')[0], 403)
        status, _ = self.call('POST', '/v1/chat/completions', {
            'model': 'fred-qwen', 'messages': [{'role': 'user', 'content': 'bonjour'}], 'max_tokens': 32})
        self.assertEqual(status, 200)
        self.assertEqual(self.requests[0]['max_tokens'], 32)
        self.assertEqual(self.requests[0]['messages'], [{'role': 'user', 'content': 'bonjour'}])
        self.store.agent_inference_token = None
        self.assertIsNone(self.store.authenticate('agent-' + 'a' * 40))

    def test_embeddings_use_shared_engine(self):
        calls = []

        class Engine:
            def encode(self, texts, mode, timeout, include_usage):
                calls.append((texts, mode))
                return {'vectors': [[1.0] + [0.0] * 767 for _ in texts], 'prompt_tokens': 3}

        self.store.workspace.knowledge = SimpleNamespace(engine=Engine(), close=lambda: None)
        status, result = self.call('POST', '/v1/embeddings', {
            'model': 'google/embeddinggemma-2', 'input': ['title: none | text: exemple']})
        self.assertEqual(status, 200)
        self.assertEqual(len(result['data'][0]['embedding']), 768)
        self.assertEqual(calls, [(['title: none | text: exemple'], 'document')])


if __name__ == '__main__':
    unittest.main()
