import hashlib
import http.client
import json
import threading
import unittest
from urllib.parse import urlencode

from agent_web import OLD_WINDOWS_DOWNLOAD, WINDOWS_DOWNLOAD, WINDOWS_INSTALLER, serve_agent_web
from core import write_json
from releases import DESKTOP_INSTALLER_VERSION
from remote import serve_gateway
from signing import sign
from workspace import Workspace
import test_agent_gateway


class AgentWebTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_agent_gateway.AgentGatewayTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.addCleanup(self.fixture.tearDown)
        self.store = self.fixture.store
        self.store.workspace = Workspace(self.store.home)
        self.store.valid_owner = lambda identity, **_: identity == 'device-a'
        self.server = serve_agent_web(self.store, 'https://agent.example.test', 0)
        worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, method, path, body=None, **headers):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            connection.request(method, path, body, {'Host': 'agent.example.test', **headers})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def login(self, origin='https://agent.example.test'):
        return self.request('POST', '/connexion', urlencode({'access': 'valid-token'}),
                            **{'Content-Type': 'application/x-www-form-urlencoded', 'Origin': origin})

    def test_listener_probe_uses_the_configured_host(self):
        status, headers, body = self.request('HEAD', '/')
        self.assertEqual((status, body), (200, b''))
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(self.request('HEAD', '/', Host='other.example.test')[0], 400)

    def test_cookie_session_origin_logout_and_revocation(self):
        self.assertEqual(self.request('GET', '/app')[0], 303)
        self.assertEqual(self.request('GET', '/api/v1/session')[0], 401)
        self.assertEqual(self.login('https://other.example.test')[0], 403)
        status, headers, _ = self.login()
        self.assertEqual(status, 303)
        self.assertEqual(headers['Location'], '/app')
        self.assertIn('Secure; HttpOnly; SameSite=Strict', headers['Set-Cookie'])
        self.assertNotIn('valid-token', headers['Set-Cookie'])
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        self.assertEqual(self.request('GET', '/api/v1/session', Cookie=cookie)[0], 200)
        self.assertEqual(self.request('POST', '/api/v1/test', '{}', Cookie=cookie)[0], 403)
        self.assertEqual(self.request('POST', '/v1/thunderbird/bridge/jobs/claim', '{}',
                                      Cookie=cookie, Origin='https://agent.example.test')[0], 403)
        self.assertEqual(self.request('GET', '/v1/models', Cookie=cookie, Host='other.example.test')[0], 400)
        self.assertEqual(self.request('POST', '/deconnexion', '', Cookie=cookie,
                                      Origin='https://agent.example.test')[0], 303)
        self.assertEqual(self.request('GET', '/api/v1/session', Cookie=cookie)[0], 401)

        cookie = self.login()[1]['Set-Cookie'].split(';', 1)[0]
        self.store.valid_owner = lambda *_args, **_kwargs: False
        self.assertEqual(self.request('GET', '/api/v1/session', Cookie=cookie)[0], 401)

    def test_authenticated_windows_installer_does_not_use_legacy_update_route(self):
        installer = self.store.home / 'installateurs' / WINDOWS_INSTALLER
        installer.parent.mkdir()
        installer.write_bytes(b'fixture installer')
        release = {'version': DESKTOP_INSTALLER_VERSION, 'protocol': 4, 'bytes': 17,
                   'sha256': hashlib.sha256(b'fixture installer').hexdigest()}
        write_json(installer.parent / f'kiara-{DESKTOP_INSTALLER_VERSION}.json', sign(release, self.store.home))
        self.assertNotIn(WINDOWS_DOWNLOAD.encode(), self.request('GET', '/')[2])
        status, _, body = self.request('GET', WINDOWS_DOWNLOAD)
        self.assertEqual(status, 200)
        self.assertIn(b'action="/connexion?destination=windows"', body)
        self.assertEqual(self.request('HEAD', WINDOWS_DOWNLOAD)[0], 401)
        status, headers, _ = self.request('GET', OLD_WINDOWS_DOWNLOAD)
        self.assertEqual((status, headers['Location']), (303, WINDOWS_DOWNLOAD))
        form = {'Content-Type': 'application/x-www-form-urlencoded', 'Origin': 'https://agent.example.test'}
        status, _, body = self.request('POST', '/connexion?destination=windows', urlencode({'access': 'invalid'}), **form)
        self.assertEqual(status, 403)
        self.assertIn(b'action="/connexion?destination=windows"', body)
        status, headers, _ = self.request('POST', '/connexion?destination=windows', urlencode({'access': 'valid-token'}), **form)
        self.assertEqual((status, headers['Location']), (303, WINDOWS_DOWNLOAD))
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        self.assertIn(WINDOWS_DOWNLOAD.encode(), self.request('GET', '/', Cookie=cookie)[2])
        status, headers, data = self.request('GET', WINDOWS_DOWNLOAD, Cookie=cookie)
        self.assertEqual((status, data), (200, b'fixture installer'))
        self.assertEqual(headers['Content-Disposition'], f'attachment; filename="{WINDOWS_INSTALLER}"')
        self.assertEqual(headers['Cache-Control'], 'private, no-store')
        status, headers, data = self.request('HEAD', WINDOWS_DOWNLOAD, Cookie=cookie)
        self.assertEqual((status, headers['Content-Length'], data), (200, '17', b''))
        installer.write_bytes(b'altered installer data')
        status, headers, _ = self.request('GET', WINDOWS_DOWNLOAD, Cookie=cookie)
        self.assertEqual(status, 503)
        self.assertNotIn('Content-Disposition', headers)
        self.store.valid_owner = lambda *_args, **_kwargs: False
        self.assertEqual(self.request('HEAD', WINDOWS_DOWNLOAD, Cookie=cookie)[0], 401)
        self.assertNotIn('attachment', str(self.request('GET', WINDOWS_DOWNLOAD, Cookie=cookie)[1]))

    def test_shared_gateway_keeps_session_under_both_portal_prefixes(self):
        server = serve_gateway(self.store, lambda: None, port=0, agent_web_origin='https://agent.example.test')
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.server = server
        self.assertEqual(self.request('HEAD', '/agent/')[0], 200)
        self.assertEqual(self.request('GET', '/agent')[1]['Location'], '/agent/')
        self.assertEqual(self.request('GET', '/agent/app')[1]['Location'], '/agent/')
        status, headers, _ = self.request('POST', '/agent/connexion', urlencode({'access': 'valid-token'}),
                                         Origin='https://agent.example.test',
                                         **{'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(status, 303)
        self.assertEqual(headers['Location'], '/agent/app/conversations')
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        self.assertEqual(self.request('GET', '/agent/api/v1/session', Cookie=cookie)[0], 200)
        self.assertEqual(self.request('GET', '/v1/models', Cookie=cookie)[0], 401)
        self.check_conversations('/agent', cookie)
        self.assertEqual(self.request('HEAD', '/kiara/')[0], 200)
        self.assertEqual(self.request('GET', '/kiara')[1]['Location'], '/kiara/')
        self.assertEqual(self.request('GET', '/kiara/app')[1]['Location'], '/kiara/')
        self.assertEqual(self.request('GET', '/kiara/api/v1/session', Cookie=cookie)[0], 200)
        self.check_conversations('/kiara', cookie)
        status, headers, _ = self.request('POST', '/kiara/connexion', urlencode({'access': 'valid-token'}),
                                         Origin='https://agent.example.test',
                                         **{'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(status, 303)
        self.assertEqual(headers['Location'], '/kiara/app/conversations')
        self.assertEqual(self.request('GET', '/kiara/api/v1/session', Cookie=headers['Set-Cookie'].split(';', 1)[0])[0], 200)
        allowed_scope = self.store.scope
        for prefix in ('/agent', '/kiara'):
            with self.subTest(prefix=prefix):
                source = prefix + '/v1/sources/fixture/raw'
                self.store.scope = allowed_scope
                self.assertEqual(self.request('GET', source, Range='bytes=1-3')[0], 401)
                status, headers, body = self.request('GET', source, Cookie=cookie, Range='bytes=1-3')
                self.assertEqual((status, body), (206, b'rig'))
                self.assertEqual(headers['Content-Range'], 'bytes 1-3/5')
                self.assertEqual(headers['Content-Disposition'], 'attachment; filename="original.txt"')
                self.assertEqual(headers['Cache-Control'], 'private, no-store')
                self.store.scope = ['other-project']
                self.assertEqual(self.request('GET', source, Cookie=cookie, Range='bytes=1-3')[0], 403)

    def test_dedicated_gateway_serves_conversations(self):
        server = serve_gateway(self.store, lambda: None, port=0,
                               agent_web_origin='https://agent.example.test', browser_only=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.server = server
        cookie = self.login()[1]['Set-Cookie'].split(';', 1)[0]
        self.check_conversations('', cookie)

    def check_conversations(self, prefix, cookie):
        page = prefix + '/app/conversations'
        self.assertEqual(self.request('GET', page)[0], 303)
        status, headers, data = self.request('GET', page, Cookie=cookie)
        self.assertEqual(status, 200)
        self.assertIn("script-src 'nonce-", headers['Content-Security-Policy'])
        self.assertIn(b'project-conversation-controls', data)
        self.assertIn(b'"web_prefix": ' + json.dumps(prefix).encode(), data)
        self.assertNotIn(b'valid-token', data)
        history = prefix + '/v1/history'
        self.assertEqual(self.request('GET', history)[0], 401)
        status, _, body = self.request('GET', history, Cookie=cookie)
        self.assertEqual(status, 200)
        value = json.loads(body)
        value = {key: value[key] for key in ('revision', 'reset_id', 'generation')}
        value['history'] = {'currentId': 'd' * 32, 'conversations': [
            {'id': 'd' * 32, 'title': 'Recette', 'messages': []}]}
        body = json.dumps(value)
        self.assertEqual(self.request('POST', history, Cookie=cookie)[0], 403)
        headers = {'Cookie': cookie, 'Origin': 'https://agent.example.test',
                   'Content-Type': 'application/json'}
        self.assertEqual(self.request('POST', history, body, **headers)[0], 200)
        self.assertEqual(self.request('POST', history, body, **headers)[0], 409)
        status, _, body = self.request('GET', history, Cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['history']['currentId'], 'd' * 32)
