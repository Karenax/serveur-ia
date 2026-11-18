"""The local Agent interface uses the authenticated client transport."""

import base64
import http.client
import urllib.error
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import client


class AgentTransportTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.calls = []
        calls = self.calls

        class Opener:
            def open(self, request, timeout):
                body = b''.join(request.data) if request.data is not None and not isinstance(request.data, bytes) else request.data
                calls.append((request.get_method(), request.full_url, request.get_header('Content-type'), body))
                payload = b'<html><body><div id="root"></div></body></html>' if request.full_url.endswith('/v1/business/app') else b'{"ok":true}'
                result = io.BytesIO(payload)
                result.status = 200
                result.headers = http.client.HTTPMessage()
                result.headers['Content-Type'] = 'application/json'
                result.headers['Content-Length'] = str(len(result.getvalue()))
                if request.full_url.endswith(('/v1/sources/source-recette/raw', '/api/v1/workspace/sources/source-recette/original')):
                    original = b'\x00\xff\r\nOriginal de recette'
                    result = io.BytesIO(original)
                    result.status = 200
                    result.headers = http.client.HTTPMessage()
                    result.headers['Content-Type'] = 'application/octet-stream'
                    result.headers['Content-Length'] = str(len(original))
                    result.headers['Content-Disposition'] = "attachment; filename*=UTF-8''Pi%C3%A8ce%20originale.pdf"
                if request.full_url.endswith('/documents/prepare-copy'):
                    result.headers['X-Agent-Source-Sha256'] = 'a' * 64
                    result.headers['X-Agent-Values-Sha256'] = 'b' * 64
                    result.headers['X-Agent-Link-Sha256'] = 'c' * 64
                    result.headers['X-Agent-Network-Published'] = 'false'
                return result

        encoded = base64.b64encode(b'x' * 32).decode()
        profile = {'url': 'wireguard://10.77.0.1:8766', 'transport': 'wireguard',
                   'token': 'qwen_' + 'a' * 16 + '_' + 'b' * 43, 'protocol': 4,
                   'wireguard': {'private_key': encoded, 'server_public_key': encoded, 'preshared_key': encoded,
                                 'address': '10.77.0.2/32', 'endpoint': 'example.test:51820'}}
        self.remote = client.Remote(profile, Opener())
        with patch.object(client, 'settings_path', return_value=Path(self.folder.name) / 'settings.json'):
            self.server = client.serve_local(self.remote, 'local-key', 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.folder.cleanup()

    def call(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = (response.status, dict(response.getheaders()), response.read())
        connection.close()
        return result

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Boucle audio réservée au relais Linux')
    def test_linux_system_audio_requires_local_cookie_and_same_origin(self):
        from linux_system_audio import LinuxSystemAudio
        path = '/api/v1/kiara/linux-system-audio'
        lease = '28a62875-2b27-4925-9a15-390032aee5b1'
        payload = json.dumps({'action':'start','lease_id':lease})
        local = f'http://127.0.0.1:{self.port}'
        with patch.object(LinuxSystemAudio, 'start', return_value={'lease_id':lease,'label':'fictif'}) as start:
            self.assertEqual(self.call('POST', path, payload, {'Content-Type':'application/json','Origin':local})[0], 403)
            status, headers, _ = self.call('POST', '/client/project-session', '{}', {
                'Content-Type':'application/json','Authorization':'Bearer local-key'})
            self.assertEqual(status, 200)
            cookie = headers['Set-Cookie'].split(';', 1)[0]
            self.assertEqual(self.call('POST', path, payload, {'Content-Type':'application/json','Cookie':cookie,
                                                               'Origin':'https://example.com'})[0], 403)
            self.assertEqual(self.call('POST', path, payload, {'Content-Type':'application/json','Cookie':cookie})[0], 403)
            self.assertEqual(self.call('GET', path, headers={'Cookie':cookie})[0], 405)
            invalid = json.dumps({'action':'start','lease_id':lease,'extra':True})
            headers = {'Content-Type':'application/json','Cookie':cookie,'Origin':local}
            self.assertEqual(self.call('POST', path, invalid, headers)[0], 400)
            start.assert_not_called()
            status, _, raw = self.call('POST', path, payload, headers)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(raw)['lease_id'], lease)
            start.assert_called_once_with(lease)

    def test_session_and_business_requests_require_local_authorization(self):
        self.assertEqual(self.call('GET', '/app')[0], 403)
        for route in ('/client/project-session', '/client/agent/session'):
            with self.subTest(route=route):
                self.assertEqual(self.call('POST', route, '{}', {'Content-Type': 'application/json'})[0], 401)
        status, headers, _ = self.call('POST', '/client/project-session', '{}', {
            'Content-Type': 'application/json', 'Authorization': 'Bearer local-key'})
        self.assertEqual(status, 200)
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        status, _, html = self.call('GET', '/app', headers={'Cookie': cookie})
        self.assertEqual(status, 200)
        self.assertIn(b'data-kiara-desktop="true"', html)
        self.assertEqual(b'data-kiara-windows="true"' in html, sys.platform == 'win32')
        self.assertEqual(b'data-kiara-linux-system-audio="true"' in html, sys.platform.startswith('linux'))
        path = '/api/v1/projects?limit=5'
        self.assertEqual(self.call('PATCH', path, 'abc', {'Cookie': cookie, 'Origin': 'https://example.com'})[0], 403)
        status, _, _ = self.call('PATCH', path, 'abc', {
            'Cookie': cookie, 'Origin': f'http://127.0.0.1:{self.port}', 'Content-Type': 'text/plain'})
        self.assertEqual(status, 200)
        self.assertEqual(self.calls[-1][0], 'PATCH')
        self.assertTrue(self.calls[-1][1].endswith('/v1/business' + path))
        self.assertEqual(self.calls[-1][2:], ('text/plain', b'abc'))
        resolution = '/v1/resolution/source-recette/confirm'
        self.assertEqual(self.call('POST', resolution, '{}')[0], 403)
        status, _, _ = self.call('POST', resolution, '{}', {
            'Cookie': cookie, 'Origin': f'http://127.0.0.1:{self.port}', 'Content-Type': 'application/json'})
        self.assertEqual(status, 200)
        self.assertTrue(self.calls[-1][1].endswith('/v1/business' + resolution))

    def test_desktop_version_is_visible_through_authenticated_state(self):
        self.remote.version = '3.5.63'
        self.assertEqual(self.call('GET', '/client/state')[0], 401)
        status, _, body = self.call('GET', '/client/state', headers={'Authorization': 'Bearer local-key'})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['version'], '3.5.63')
        self.assertEqual(self.call('GET', '/api/v1/projects')[0], 403)

    def test_chat_contains_read_only_local_recovery_library_under_its_csp(self):
        status, headers, body = self.call('GET', '/chat')
        self.assertEqual(status, 200)
        page = body.decode('utf-8')
        self.assertIn('kiaraPortalConflictArchive', page)
        self.assertIn('kiaraPortalConflictReview', page)
        self.assertIn('kiara-conflict-dialog', page)
        self.assertIn('kiaraPortalAudioConflictArchive', page)
        self.assertIn('Consulter les audios', page)
        self.assertLess(page.index('root.kiaraPortalOriginRecovery = api'), page.index('root.kiaraPortalAudioConflictArchive = api'))
        self.assertLess(page.index('root.kiaraPortalAudioConflictArchive = api'), page.index("'Consulter les audios'"))
        self.assertIn("script-src 'nonce-", headers['Content-Security-Policy'])
        self.assertIn("style-src 'nonce-", headers['Content-Security-Policy'])
        self.assertIn('media-src blob:', headers['Content-Security-Policy'])
        self.assertNotIn("'unsafe-inline'", headers['Content-Security-Policy'])

    def test_unreadable_settings_are_preserved_by_local_api(self):
        path = Path(self.folder.name) / 'fiction-settings.dpapi'
        original = b'reglages chiffres fictifs illisibles'
        path.write_bytes(original)
        headers = {'Authorization': 'Bearer local-key', 'Content-Type': 'application/json'}
        with patch.object(client, 'settings_path', return_value=path), \
             patch.object(client, 'protect', side_effect=ValueError('cle fictive indisponible')):
            for route, body in (('/client/preferences', '{"theme":"dark"}'),
                                ('/client/endpoint', '{}')):
                with self.subTest(route=route):
                    status, _, payload = self.call('POST', route, body, headers)
                    self.assertEqual(status, 400)
                    self.assertIn('original est conservé', json.loads(payload)['error']['message'])
                    self.assertEqual(path.read_bytes(), original)

    def test_denied_remote_access_does_not_open_a_local_session(self):
        error = urllib.error.HTTPError('http://agent.invalid', 403, 'Forbidden', {}, io.BytesIO(b'forbidden'))
        with patch.object(self.remote.opener, 'open', side_effect=error):
            status, headers, _ = self.call('POST', '/client/agent/session', '{}', {
                'Content-Type': 'application/json', 'Authorization': 'Bearer local-key'})
        self.assertNotEqual(status, 200)
        self.assertNotIn('Set-Cookie', headers)
        self.assertEqual(self.call('GET', '/app')[0], 403)

    def test_document_copy_receipt_reaches_the_local_webview(self):
        status, headers, _ = self.call('POST', '/client/agent/session', '{}', {
            'Authorization': 'Bearer local-key', 'Content-Type': 'application/json'})
        self.assertEqual(status, 200)
        status, headers, _ = self.call('POST', '/api/v1/documents/prepare-copy', '{}', {
            'Cookie': headers['Set-Cookie'].split(';', 1)[0],
            'Origin': f'http://127.0.0.1:{self.port}', 'Content-Type': 'application/json'})
        self.assertEqual(status, 200)
        self.assertEqual(headers['X-Agent-Source-Sha256'], 'a' * 64)
        self.assertEqual(headers['X-Agent-Values-Sha256'], 'b' * 64)
        self.assertEqual(headers['X-Agent-Link-Sha256'], 'c' * 64)
        self.assertEqual(headers['X-Agent-Network-Published'], 'false')

    def test_original_documents_are_forwarded_only_with_a_project_session(self):
        status, headers, _ = self.call('POST', '/client/project-session', '{}', {
            'Authorization': 'Bearer local-key', 'Content-Type': 'application/json'})
        self.assertEqual(status, 200)
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        routes = ('/v1/sources/source-recette/raw', '/api/v1/workspace/sources/source-recette/original')
        for route in routes:
            with self.subTest(route=route):
                call_count = len(self.calls)
                self.assertEqual(self.call('GET', route)[0], 403)
                self.assertEqual(len(self.calls), call_count)
                status, response_headers, body = self.call('GET', route, headers={'Cookie': cookie})
                self.assertEqual(status, 200)
                self.assertEqual(response_headers['Content-Type'], 'application/octet-stream')
                self.assertEqual(response_headers['Content-Length'], str(len(body)))
                self.assertEqual(response_headers['Content-Disposition'],
                                 "attachment; filename*=UTF-8''Pi%C3%A8ce%20originale.pdf")
                self.assertEqual(body, b'\x00\xff\r\nOriginal de recette')
                self.assertTrue(self.calls[-1][1].endswith('/v1/business' + route))

    def test_thunderbird_uses_its_own_pairing_and_exact_bridge_routes(self):
        route = '/v1/thunderbird/bridge/heartbeat'
        origin = 'moz-extension://e7429fa4-0521-44a1-872f-4f32f23839cf'
        headers = {'Origin': origin, 'X-Agent-Thunderbird-Token': 'thunderbird-only'}
        with patch.object(client, 'client_settings', return_value={'thunderbird_token': 'thunderbird-only'}):
            self.assertEqual(self.call('POST', route, '{}', {**headers, 'Origin': 'https://example.test'})[0], 403)
            self.assertEqual(self.call('POST', route, '{}', {**headers, 'X-Agent-Thunderbird-Token': 'local-key'})[0], 403)
            self.assertEqual(self.call('POST', route + '?x=1', '{}', headers)[0], 403)
            self.assertFalse(self.calls)
            status, response_headers, _ = self.call('OPTIONS', route, headers={
                'Origin': origin, 'Access-Control-Request-Method': 'POST'})
            self.assertEqual(status, 204)
            self.assertEqual(response_headers['Access-Control-Allow-Origin'], origin)
            status, response_headers, _ = self.call('POST', route, '{}', headers)
            self.assertEqual(status, 200)
            self.assertEqual(response_headers['Access-Control-Allow-Origin'], origin)
            self.assertTrue(self.calls[-1][1].endswith('/v1/business' + route))

    @unittest.skipUnless(sys.platform == 'win32', 'Explorateur Windows')
    def test_agent_opens_allowed_project_paths_only_on_the_client(self):
        root = Path(self.folder.name) / 'documents'
        root.mkdir()
        allowed = root / 'plan.pdf'
        allowed.touch()
        blocked = root / 'programme.exe'
        blocked.touch()
        project = 'e7429fa4-0521-44a1-872f-4f32f23839cf'
        _, session_headers, _ = self.call('POST', '/client/agent/session', '{}', {
            'Content-Type': 'application/json', 'Authorization': 'Bearer local-key'})
        headers = {'Cookie': session_headers['Set-Cookie'].split(';', 1)[0],
                   'Origin': f'http://127.0.0.1:{self.port}', 'Content-Type': 'application/json'}

        def open_path(path, request_headers=headers):
            return self.call('POST', '/api/v1/open-path', json.dumps({'path': str(path), 'project': project}), request_headers)[0]

        with patch.dict(os.environ, {'AGENT_OPEN_ROOTS': str(root)}), patch.object(os, 'startfile') as launch:
            self.assertEqual(open_path(allowed, {**headers, 'Origin': 'https://example.test'}), 403)
            self.assertEqual(open_path(allowed, {**headers, 'Cookie': ''}), 403)
            denied = urllib.error.HTTPError('http://agent.invalid', 403, 'Forbidden', {}, io.BytesIO())
            with patch.object(self.remote.opener, 'open', side_effect=denied):
                self.assertEqual(open_path(allowed), 403)
            self.assertEqual(open_path(blocked), 403)
            self.assertEqual(open_path(root.parent / 'documents-bis'), 403)
            launch.assert_not_called()
            self.assertEqual(open_path(allowed), 200)
            launch.assert_called_once_with(str(allowed.resolve()))
            self.assertTrue(self.calls[-1][1].endswith(f'/projects/{project}/network-links'))


if __name__ == '__main__':
    unittest.main()
