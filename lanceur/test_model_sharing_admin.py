"""Server model sharing is managed through the authenticated local console."""
import json
import re
import socket
import threading
from types import SimpleNamespace
import unittest
import urllib.error
import urllib.request

from app import serve


class ModelSharingAdminTests(unittest.TestCase):
    def setUp(self):
        parent = self
        self.configurations = []
        class Models:
            def admin(self):
                return {'providers': [{'id': 'provider-test', 'label': 'Connected provider',
                                       'configured': True, 'model_count': 2}],
                        'share_all': False, 'shared_accounts': []}
            def configure(self, value):
                if set(value) - {'share_all', 'shared_accounts'}: raise ValueError('Réglage inconnu.')
                parent.configurations.append(value)
                return {'message': 'Accès enregistré.'}
        self.controller = SimpleNamespace(lock=threading.RLock(), remote=SimpleNamespace(maintenance=False),
                                          hermes=SimpleNamespace(models=Models()))
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        self.server = serve(port, self.controller)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.url = f'http://127.0.0.1:{port}'
        with urllib.request.urlopen(self.url, timeout=5) as response:
            self.token = re.search(r'name="launcher-token" content="([^"]+)"', response.read().decode())[1]

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(3)

    def call(self, body=None, token=True, origin=None):
        headers = {'X-Launcher-Token': self.token} if token else {}
        if origin: headers['Origin'] = origin
        if body is not None: headers['Content-Type'] = 'application/json'
        route = '/api/hermes/models/configure' if body is not None else '/api/hermes/models'
        request = urllib.request.Request(self.url + route, json.dumps(body).encode() if body is not None else None, headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as response: return response.status, json.load(response)
        except urllib.error.HTTPError as response:
            try: return response.code, json.load(response)
            finally: response.close()

    def test_catalog_requires_console_token_and_contains_only_public_metadata(self):
        self.assertEqual(403, self.call(token=False)[0])
        code, result = self.call()
        self.assertEqual(200, code); self.assertTrue(result['enabled'])
        self.assertEqual(2, result['providers'][0]['model_count'])
        self.assertFalse(result['share_all']); self.assertEqual([], self.configurations)

    def test_sharing_changes_require_console_token_and_same_origin(self):
        self.assertEqual(403, self.call({'share_all': True}, token=False)[0])
        self.assertEqual(403, self.call({'share_all': True}, origin='https://foreign.example')[0])
        self.assertEqual([], self.configurations)
        self.assertEqual(200, self.call({'share_all': True}, origin=self.url)[0])
        self.assertEqual([{'share_all': True}], self.configurations)
        self.assertEqual(400, self.call({'api_key': 'not-permitted'})[0])

    def test_disabled_integration_has_no_sharing_controls(self):
        self.controller.hermes = None
        code, result = self.call()
        self.assertEqual(200, code); self.assertFalse(result['enabled'])
        self.assertEqual(400, self.call({'share_all': True})[0]); self.assertEqual([], self.configurations)


if __name__ == '__main__': unittest.main()
