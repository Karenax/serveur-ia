"""First private SSE frame must be fenced against access changes during context."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from remote import AccessStore, serve_gateway


class SourceAccessFenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='fred-source-access-fence-')
        self.store = AccessStore(self.directory.name)
        self.access = self.store.issue('Accès temporaire des sources')
        self.store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        self.captured = []
        captured = self.captured
        class Model(BaseHTTPRequestHandler):
            def log_message(inner, *args): pass
            def do_GET(inner):
                value = b'{"service":"strata","loaded":true}'
                inner.send_response(200); inner.send_header('Content-Length', str(len(value)))
                inner.end_headers(); inner.wfile.write(value)
            def do_POST(inner):
                captured.append(json.loads(inner.rfile.read(int(inner.headers['Content-Length']))))
                value = b'data: {"choices":[{"delta":{"content":"Resultat isole"}}]}\n\ndata: [DONE]\n\n'
                inner.send_response(200); inner.end_headers(); inner.wfile.write(value)
        self.model = ThreadingHTTPServer(('127.0.0.1', 0), Model)
        self.gateway = serve_gateway(self.store, lambda: (self.model.server_port, 'isolated-model', ''), 0)
        self.threads = []
        for server in (self.model, self.gateway):
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start(); self.threads.append(thread)
        workspace = self.store.workspace
        self.project = workspace.action(self.access['id'], {'action': 'project_create', 'title': 'Projet isolé'})['id']
        workspace.action(self.access['id'], {'action': 'document_create', 'project': self.project,
                                           'title': 'Source confidentielle', 'text': 'Andromède — extrait privé de la fixture.'})

    def tearDown(self):
        for server in (self.gateway, self.model): server.shutdown(); server.server_close()
        for thread in self.threads: thread.join(5)
        self.directory.cleanup()

    def request(self):
        body = json.dumps({'project_id': self.project, 'messages': [{'role': 'user', 'content': 'Andromède'}], 'stream': True}).encode()
        request = urllib.request.Request('http://127.0.0.1:' + str(self.gateway.server_port) + '/v1/chat/completions', body,
                                         {'Authorization': 'Bearer ' + self.access['token'], 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            try: return error.code, error.read()
            finally: error.close()

    def settle(self):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and (self.store.active or self.store.scheduler.snapshot()['requests']):
            time.sleep(.01)
        self.assertEqual(0, self.store.active)
        self.assertEqual([], self.store.scheduler.snapshot()['requests'])

    def assert_context_change_has_no_private_frame(self, change, expected):
        ready = threading.Event(); release = threading.Event(); responses = []; errors = []
        original = self.store.workspace.context
        def delayed_context(*args, **kwargs):
            prepared = original(*args, **kwargs)
            self.assertTrue(prepared[1], 'La fixture doit fournir un extrait privé réel.')
            ready.set()
            if not release.wait(5): raise RuntimeError('Libération du contexte manquante.')
            return prepared
        def send():
            try: responses.append(self.request())
            except Exception as error: errors.append(error)
        with patch.object(self.store.workspace, 'context', side_effect=delayed_context):
            thread = threading.Thread(target=send); thread.start()
            try:
                self.assertTrue(ready.wait(5), 'Lecture documentaire atteinte.')
                change()
            finally:
                release.set(); thread.join(8)
        self.assertFalse(thread.is_alive()); self.assertEqual([], errors)
        self.assertEqual(expected, responses[0][0])
        self.assertNotIn(b'workspace_sources', responses[0][1])
        self.assertNotIn('extrait privé'.encode(), responses[0][1])
        self.assertEqual([], self.captured)
        self.settle()

    def test_revocation_during_context_emits_no_sources_or_inference(self):
        self.assert_context_change_has_no_private_frame(lambda: self.store.revoke(self.access['id']), 401)

    def test_suspension_during_context_emits_no_sources_or_inference(self):
        self.assert_context_change_has_no_private_frame(lambda: self.store.policy({'id': self.access['id'], 'suspended': True}), 401)

    def test_maintenance_during_context_emits_no_sources_or_inference(self):
        def maintenance():
            with self.store.lock:
                self.store.maintenance = True; self.store.workspace.maintenance = True
        self.assert_context_change_has_no_private_frame(maintenance, 503)

    def test_access_change_after_queue_still_prevents_backend_request(self):
        ready = threading.Event(); release = threading.Event(); responses = []; errors = []
        original = self.store.audit
        def delayed_audit(event, identity=''):
            if event == 'inference_started':
                ready.set()
                if not release.wait(5): raise RuntimeError('Libération de la file manquante.')
            return original(event, identity)
        def send():
            try: responses.append(self.request())
            except Exception as error: errors.append(error)
        with patch.object(self.store, 'audit', side_effect=delayed_audit):
            thread = threading.Thread(target=send); thread.start()
            try:
                self.assertTrue(ready.wait(5))
                self.store.policy({'id': self.access['id'], 'suspended': True})
            finally:
                release.set(); thread.join(8)
        self.assertFalse(thread.is_alive()); self.assertEqual([], errors)
        # The initial references were committed while access was still valid.
        self.assertEqual(200, responses[0][0]); self.assertIn(b'workspace_sources', responses[0][1])
        self.assertIn(b'error', responses[0][1]); self.assertEqual([], self.captured)
        self.settle()

    def test_valid_stream_keeps_sources_result_and_balanced_active_counter(self):
        status, body = self.request()
        self.assertEqual(200, status); self.assertIn(b'workspace_sources', body)
        self.assertIn(b'Resultat isole', body); self.assertIn(b'[DONE]', body)
        self.assertEqual(1, len(self.captured)); self.settle()


if __name__ == '__main__':
    unittest.main()
