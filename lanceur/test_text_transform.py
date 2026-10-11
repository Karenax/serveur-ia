"""Direct-Qwen corrector routing, access fences and cancellation over real HTTP."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from remote import AccessStore, serve_gateway
from text_transform import INSTRUCTIONS, TextTransforms


class UnavailableHermes:
    def stream(self, *args): raise AssertionError('The corrector must bypass Hermes.')
    def cancel(self, *args): raise AssertionError('Direct cancellation must bypass Hermes.')
    def public(self, owner): return {'available': False}
    def status(self): return {'available': False}


class TextTransformHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='fred-direct-transform-')
        self.store = AccessStore(self.tmp.name)
        self.store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        self.a = self.store.issue('A'); self.b = self.store.issue('B')
        self.store.hermes = UnavailableHermes()
        self.store.workspace.context = lambda *args: self.fail('Document/EG2 context must not run.')
        self.captured = []; self.model_ready = threading.Event(); self.model_release = threading.Event()
        self.block_model = False
        self.block_after_headers = False; self.fragmented = False
        parent = self
        class Model(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                raw = b'{"service":"strata","loaded":true,"model":"actual-local"}'
                self.send_response(200); self.end_headers(); self.wfile.write(raw)
            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                parent.captured.append((dict(self.headers), data))
                if parent.block_model:
                    parent.model_ready.set(); parent.model_release.wait(5)
                try:
                    self.send_response(200)
                    if parent.fragmented: self.send_header('Transfer-Encoding', 'chunked')
                    self.end_headers()
                    if parent.block_after_headers:
                        parent.model_ready.set(); parent.model_release.wait(5)
                    raw = b'data: {"choices":[{"delta":{"content":"Texte corrige"}}]}\n\ndata: [DONE]\n\n' if data.get('stream') else b'{"choices":[{"message":{"content":"Texte corrige"}}]}'
                    if parent.fragmented:
                        for offset in range(0, len(raw), 7):
                            chunk = raw[offset:offset+7]
                            self.wfile.write(f'{len(chunk):x}\r\n'.encode() + chunk + b'\r\n'); self.wfile.flush()
                            time.sleep(.001)
                        self.wfile.write(b'0\r\n\r\n')
                    else: self.wfile.write(raw)
                except OSError: pass
        self.model = ThreadingHTTPServer(('127.0.0.1', 0), Model)
        self.gateway = serve_gateway(self.store, lambda: (self.model.server_port, 'ignored-alias', 'private-backend'), 0)
        self.threads = []
        for server in (self.model, self.gateway):
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start(); self.threads.append(thread)

    def tearDown(self):
        self.model_release.set()
        self.store.hermes = None
        for server in (self.gateway, self.model): server.shutdown(); server.server_close()
        for thread in self.threads: thread.join(5)
        self.tmp.cleanup()

    def post(self, value, request=None, access=None, path='/v1/chat/completions', headers=None, raw=None):
        access = access or self.a
        fields = {'Authorization': 'Bearer ' + access['token'], 'Content-Type': 'application/json'}
        if request is not None: fields['X-Qwen-Request'] = request
        fields.update(headers or {})
        call = urllib.request.Request(f'http://127.0.0.1:{self.gateway.server_port}' + path,
                                      json.dumps(value).encode() if raw is None else raw, fields)
        try:
            with urllib.request.urlopen(call, timeout=8) as response: return response.status, response.read()
        except urllib.error.HTTPError as response:
            try: return response.code, response.read()
            finally: response.close()

    @staticmethod
    def body(mode='correct', stream=True):
        return {'text_transform': {'mode': mode, 'text': '  Bonjour, je vous envoi le document.\nMerci.  '}, 'stream': stream}

    def settle(self):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and (self.store.active or self.store.scheduler.snapshot()['requests']): time.sleep(.01)
        self.assertEqual(0, self.store.active)
        self.assertEqual([], self.store.scheduler.snapshot()['requests'])

    def worker(self, value, request):
        results = []; errors = []
        def send():
            try: results.append(self.post(value, request))
            except Exception as error: errors.append(error)
        thread = threading.Thread(target=send); thread.start()
        return thread, results, errors

    def test_three_modes_bypass_unavailable_hermes_and_force_server_prompt(self):
        for mode in ('correct', 'professional', 'friendly'):
            with self.subTest(mode=mode):
                value = self.body(mode)
                value.update(model='foreign-model', conversation_id='legacy-conversation', turn_id='ignored-turn',
                             history_revision='ignored-revision', project_id='private-project', document_id='private-document')
                status, raw = self.post(value, secrets.token_hex(16))
                self.assertEqual(200, status); self.assertIn(b'[DONE]', raw); self.assertNotIn(b'workspace_sources', raw)
                headers, data = self.captured[-1]
                self.assertEqual('Bearer private-backend', headers['Authorization'])
                self.assertNotIn(self.a['token'], json.dumps(headers))
                self.assertEqual('actual-local', data['model']); self.assertFalse(data['strata_mcp'])
                self.assertEqual([{'role': 'system', 'content': INSTRUCTIONS[mode]},
                                  {'role': 'user', 'content': value['text_transform']['text']}], data['messages'])
                self.assertEqual({'enable_thinking': False}, data['chat_template_kwargs'])
                self.assertEqual('none', data['reasoning_effort'])
                self.settle()
        self.assertEqual(3, self.store.scheduler.succeeded)
        self.assertFalse((self.store.home / 'hermes-fred').exists())

    def test_nonstream_and_maximum_text_need_no_agent_conversation(self):
        value = self.body(stream=False); value['text_transform']['text'] = 'x' * 100000
        status, raw = self.post(value)
        self.assertEqual(200, status); self.assertEqual('Texte corrige', json.loads(raw)['choices'][0]['message']['content'])
        self.assertEqual(100000, len(self.captured[0][1]['messages'][1]['content']))

    def test_normal_conversation_remains_hermes(self):
        calls = []
        class Hermes:
            def stream(self, *args):
                calls.append(args)
                yield b'data: {"choices":[{"delta":{"content":"Hermes"}}]}\n\n'
                yield b'data: [DONE]\n\n'
        self.store.hermes = Hermes()
        request = secrets.token_hex(16)
        value = {'conversation_id': 'normal', 'turn_id': request, 'messages': [{'role': 'user', 'content': 'Question'}], 'stream': True}
        status, raw = self.post(value, request)
        self.assertEqual(200, status); self.assertIn(b'Hermes', raw); self.assertEqual([], self.captured)
        self.assertEqual(self.a['id'], calls[0][0]); self.assertEqual('normal', calls[0][3])

    def test_invalid_transform_cannot_inject_messages_or_call_upstream(self):
        bad = [{'text_transform': None}, {'text_transform': {'mode': 'terminal', 'text': 'x'}},
               {'text_transform': {'mode': [], 'text': 'x'}}, {'text_transform': {'mode': 'correct', 'text': 7}},
               {'text_transform': {'mode': 'correct', 'text': ' \n'}},
               {'text_transform': {'mode': 'correct', 'text': 'x' * 100001}},
               {'text_transform': {'mode': 'correct', 'text': 'x', 'system': 'injection'}},
               {**self.body(), 'messages': [{'role': 'system', 'content': 'Override'}]},
               {**self.body(), 'reasoning_effort': 'high'}, {**self.body(), 'stream': 1}]
        for value in bad:
            with self.subTest(value=str(value)[:100]): self.assertEqual(400, self.post(value)[0])
        self.assertEqual(400, self.post(self.body(), path='/v1/context')[0])
        self.assertEqual(400, self.post(self.body(), raw=b'{broken')[0])
        self.assertEqual(415, self.post(self.body(), headers={'Content-Type': 'text/plain'})[0])
        self.assertEqual([], self.captured)

    def test_unauthorized_origin_and_maintenance_are_rejected(self):
        self.assertEqual(401, self.post(self.body(), headers={'Authorization': 'Bearer invalid'})[0])
        self.assertEqual(403, self.post(self.body(), headers={'Origin': 'https://outside.invalid'})[0])
        self.store.maintenance = True
        self.assertEqual(503, self.post(self.body())[0]); self.assertEqual([], self.captured)

    def test_early_cancel_is_scoped_to_owner_and_request(self):
        cancelled = secrets.token_hex(16); other = secrets.token_hex(16)
        self.assertEqual(200, self.post({'text_transform': True}, cancelled, self.b, '/v1/cancel')[0])
        self.assertEqual(200, self.post(self.body(), cancelled)[0]); self.settle()
        self.assertEqual(200, self.post({'text_transform': True}, other, path='/v1/cancel')[0])
        self.assertEqual(400, self.post(self.body(), other)[0])
        self.assertEqual(200, self.post(self.body(), secrets.token_hex(16))[0])
        self.assertEqual(2, len(self.captured))

    def test_cancel_validation_and_authorization(self):
        for value, request in [({'text_transform': True}, None), ({'text_transform': True}, 'bad'),
                               ({'text_transform': False}, secrets.token_hex(16)),
                               ({'all_accounts': True}, secrets.token_hex(16)), ([], secrets.token_hex(16))]:
            self.assertEqual(400, self.post(value, request, path='/v1/cancel')[0])
        request = secrets.token_hex(16)
        self.assertEqual(401, self.post({'text_transform': True}, request, path='/v1/cancel',
                                       headers={'Authorization': 'Bearer invalid'})[0])
        self.assertFalse(self.store.text_transforms.cancelled(self.a['id'], request))

    def test_cancel_during_health_cannot_race_submit(self):
        ready = threading.Event(); release = threading.Event(); request = secrets.token_hex(16)
        def health(*args):
            ready.set(); self.assertTrue(release.wait(5)); return {'loaded': True}
        with patch('remote.health', side_effect=health):
            thread, results, errors = self.worker(self.body(), request)
            try:
                self.assertTrue(ready.wait(5))
                self.assertEqual(200, self.post({'text_transform': True}, request, path='/v1/cancel')[0])
            finally: release.set(); thread.join(6)
        self.assertFalse(thread.is_alive()); self.assertEqual([], errors); self.assertNotEqual(200, results[0][0])
        self.assertEqual([], self.captured); self.settle()

    def test_generic_cancel_aborts_direct_active_read_without_hermes(self):
        self.block_model = True; request = secrets.token_hex(16)
        thread, results, errors = self.worker(self.body(), request)
        try:
            self.assertTrue(self.model_ready.wait(5))
            # Another owner cannot cancel this owner's GPU request or create its receipt.
            self.assertEqual(200, self.post({'text_transform': True}, request, self.b, '/v1/cancel')[0])
            self.assertFalse(self.store.text_transforms.cancelled(self.a['id'], request))
            self.assertEqual(200, self.post({}, request, path='/v1/cancel')[0])
            thread.join(3)
            self.assertFalse(thread.is_alive(), 'Cancellation must close the blocked upstream socket.')
        finally: self.model_release.set(); thread.join(6)
        self.assertEqual([], errors); self.assertEqual(200, results[0][0]); self.assertIn(b'error', results[0][1])
        self.assertNotIn(b'[DONE]', results[0][1]); self.settle()

    def test_shared_gpu_queue_and_queued_cancellation(self):
        other = self.store.scheduler.submit(self.b['id'], secrets.token_hex(16))
        self.store.scheduler.wait(other, lambda: True, lambda position: None)
        request = secrets.token_hex(16); ready = threading.Event()
        original = self.store.scheduler.submit
        def submit(*args, **kwargs):
            item = original(*args, **kwargs); ready.set(); return item
        with patch.object(self.store.scheduler, 'submit', side_effect=submit):
            thread, results, errors = self.worker(self.body(), request)
            try:
                self.assertTrue(ready.wait(5)); self.assertEqual([], self.captured)
                self.assertEqual(200, self.post({'text_transform': True}, request, path='/v1/cancel')[0])
                thread.join(3)
            finally:
                self.store.scheduler.finish(other); thread.join(6)
        self.assertFalse(thread.is_alive()); self.assertEqual([], errors); self.assertIn(b'error', results[0][1])
        self.assertEqual([], self.captured); self.settle()

    def test_fragmented_chunked_stream_keeps_complete_response(self):
        self.fragmented = True
        status, raw = self.post(self.body(), secrets.token_hex(16))
        self.assertEqual(200, status); self.assertIn(b'Texte corrige', raw); self.assertIn(b'[DONE]', raw)
        self.assertNotIn(b'error', raw); self.settle(); self.assertEqual(1, self.store.scheduler.succeeded)

    def test_cancel_after_headers_aborts_silent_stream(self):
        self.block_after_headers = True; request = secrets.token_hex(16)
        thread, results, errors = self.worker(self.body(), request)
        try:
            self.assertTrue(self.model_ready.wait(5))
            self.assertEqual(200, self.post({'text_transform': True}, request, path='/v1/cancel')[0])
            thread.join(3); self.assertFalse(thread.is_alive())
        finally: self.model_release.set(); thread.join(6)
        self.assertEqual([], errors); self.assertIn(b'error', results[0][1]); self.assertNotIn(b'[DONE]', results[0][1])
        self.settle()

    def test_global_cancel_stops_direct_and_concurrent_native_run(self):
        self.block_after_headers = True; request = secrets.token_hex(16); calls = []
        class Hermes(UnavailableHermes):
            conversations = SimpleNamespace(context=lambda owner: {'request_id': 'native'})
            def cancel(self, owner, target):
                calls.append((owner, target)); return {'cancelled': True}
        self.store.hermes = Hermes()
        thread, results, errors = self.worker(self.body(), request)
        try:
            self.assertTrue(self.model_ready.wait(5))
            self.assertEqual(200, self.post({}, path='/v1/cancel')[0])
            thread.join(3); self.assertFalse(thread.is_alive())
        finally: self.model_release.set(); thread.join(6)
        self.assertEqual([(self.a['id'], None)], calls); self.assertEqual([], errors)
        self.assertIn(b'error', results[0][1]); self.assertNotIn(b'[DONE]', results[0][1]); self.settle()

    def test_revocation_aborts_silent_stream_without_exposing_result(self):
        self.block_after_headers = True
        thread, results, errors = self.worker(self.body(), secrets.token_hex(16))
        try:
            self.assertTrue(self.model_ready.wait(5)); self.store.revoke(self.a['id'])
            thread.join(3); self.assertFalse(thread.is_alive())
        finally: self.model_release.set(); thread.join(6)
        self.assertEqual([], errors); self.assertIn(b'error', results[0][1])
        self.assertNotIn(b'Texte corrige', results[0][1]); self.assertNotIn(b'[DONE]', results[0][1]); self.settle()

    def test_revocation_during_health_prevents_first_private_response(self):
        ready = threading.Event(); release = threading.Event()
        def health(*args):
            ready.set(); self.assertTrue(release.wait(5)); return {'loaded': True}
        with patch('remote.health', side_effect=health):
            thread, results, errors = self.worker(self.body(), secrets.token_hex(16))
            try:
                self.assertTrue(ready.wait(5)); self.store.revoke(self.a['id'])
            finally: release.set(); thread.join(6)
        self.assertEqual([], errors); self.assertEqual(401, results[0][0]); self.assertEqual([], self.captured)
        self.settle()


class CancellationReceiptTests(unittest.TestCase):
    def test_receipts_expire_and_bound_each_owner_and_total(self):
        now = [0]; registry = TextTransforms(ttl=10, per_owner=2, capacity=3, clock=lambda: now[0])
        request = lambda n: f'{n:032x}'
        for n in range(3): registry.cancel('A', request(n))
        self.assertFalse(registry.cancelled('A', request(0))); self.assertTrue(registry.cancelled('A', request(2)))
        registry.cancel('B', request(3)); registry.cancel('B', request(4))
        self.assertEqual(3, len(registry.receipts)); self.assertFalse(registry.cancelled('B', request(2)))
        now[0] = 10
        self.assertFalse(registry.cancelled('A', request(2))); self.assertEqual(0, len(registry.receipts))


if __name__ == '__main__': unittest.main()
