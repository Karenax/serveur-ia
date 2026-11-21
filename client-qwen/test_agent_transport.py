"""The local Agent interface uses the authenticated client transport."""

import base64
import hashlib
import hmac
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
            self.server = client.serve_local(self.remote, 'local-key', 0, managed=sys.platform == 'win32')
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

    def chat_session(self):
        launch = client.urlsplit(self.server.chat_launch_url)
        status, headers, _ = self.call('GET', launch.path + '?' + launch.query)
        self.assertEqual(status, 303)
        self.assertEqual(headers['Location'], '/chat')
        self.assertEqual(headers['Referrer-Policy'], 'no-referrer')
        self.assertIn('HttpOnly; SameSite=Strict', headers['Set-Cookie'])
        return {'Cookie': headers['Set-Cookie'].split(';', 1)[0]}

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
        status, _, chat = self.call('GET', '/chat', headers=self.chat_session())
        self.assertEqual(status, 200)
        self.assertEqual(b'<body data-kiara-unified-navigation="true"' in chat, sys.platform == 'win32' or sys.platform.startswith('linux'))
        self.assertIn(b'class="conversation-toolbar"', chat)
        sidebar = chat.split(b'<aside class="sidebar"', 1)[1].split(b'</aside>', 1)[0]
        self.assertNotIn(b'id="conversation-list"', sidebar)
        self.assertNotIn(b'data-view-button="connection"', sidebar)
        status, _, html = self.call('GET', '/app', headers={'Cookie': cookie})
        self.assertEqual(status, 200)
        self.assertIn(b'data-kiara-desktop="true"', html)
        self.assertEqual(b'data-kiara-windows="true"' in html, sys.platform == 'win32')
        self.assertEqual(b'data-kiara-linux-system-audio="true"' in html, sys.platform.startswith('linux'))
        self.assertEqual(b'data-kiara-inline-settings="true"' in html, sys.platform == 'win32')
        self.assertEqual(self.call('GET', '/device-settings')[0], 403)
        self.assertEqual(self.call('GET', '/device-settings', headers={
            'Cookie': cookie, 'Origin': 'https://example.com'})[0], 403)
        status, headers, panel = self.call('GET', '/device-settings', headers={'Cookie': cookie})
        self.assertEqual(status, 200 if sys.platform == 'win32' else 403)
        if status == 200:
            self.assertIn("frame-ancestors 'self'", headers['Content-Security-Policy'])
            self.assertIn(b'data-kiara-settings-panel="true">', panel)
            notifications = '/device-settings?section=notifications'
            self.assertEqual(self.call('GET', notifications)[0], 403)
            status, headers, lightweight = self.call('GET', notifications, headers={'Cookie': cookie})
            self.assertEqual(status, 200)
            self.assertIn("frame-ancestors 'self'", headers['Content-Security-Policy'])
            self.assertIn(b'/chat#notifications', lightweight)
            self.assertNotIn(b'id="composer"', lightweight)
            self.assertLess(len(lightweight), len(panel) // 10)
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

    @unittest.skipUnless(sys.platform == 'win32', 'Réglages locaux réservés à Kiara pour Windows')
    def test_native_settings_are_scoped_and_recovery_works_without_projects(self):
        auth = {'Content-Type': 'application/json', 'Authorization': 'Bearer local-key'}
        result = self.call('POST', '/client/project-session', '{}', auth)
        self.assertEqual(result[0], 200)
        agent = result[1]['Set-Cookie'].split(';', 1)[0]
        for section in client.DEVICE_SETTINGS:
            route = '/device-settings?section=' + section
            status, headers, markup = self.call('GET', route, headers={'Cookie': agent})
            self.assertEqual(status, 200)
            self.assertIn("frame-ancestors 'self'", headers['Content-Security-Policy'])
            self.assertNotIn(b'id="composer"', markup)
            self.assertNotIn(b'<nav', markup)
            self.assertNotIn(b'<dialog', markup)
        self.assertEqual(self.call('GET', '/device-settings?section=inconnue', headers={'Cookie': agent})[0], 404)
        self.assertEqual(self.call('GET', '/device-recovery', headers={'Cookie': agent})[0], 403)
        with patch.object(self.remote, 'open', side_effect=OSError('Appareil hors connexion')) as unavailable:
            self.assertEqual(self.call('POST', '/client/project-session', '{}', auth)[0], 503)
            count = unavailable.call_count
            self.assertEqual(self.call('POST', '/client/device-session', '{}')[0], 401)
            self.assertEqual(self.call('POST', '/client/device-session', '{}',
                                       {**auth, 'Origin': 'https://example.test'})[0], 403)
            status, headers, _ = self.call('POST', '/client/device-session', '{}', auth)
            self.assertEqual(status, 200)
            device = headers['Set-Cookie'].split(';', 1)[0]
            self.assertIn('Path=/device-recovery', headers['Set-Cookie'])
            self.assertEqual(self.call('GET', '/app', headers={'Cookie': device})[0], 403)
            self.assertEqual(self.call('GET', '/device-recovery',
                                       headers={'Cookie': device, 'Origin': 'https://example.test'})[0], 403)
            status, headers, markup = self.call('GET', '/device-recovery?section=mises-a-jour', headers={'Cookie': device})
            self.assertEqual(status, 200)
            self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
            self.assertIn(b'id="update-check"', markup)
            self.assertEqual(unavailable.call_count, count)

        # Both writes go through the actual encrypted local settings store on the fixture profile.
        with patch.object(client, 'settings_path', return_value=Path(self.folder.name) / 'device-fixture.dpapi'):
            self.assertEqual(self.call('POST', '/client/preferences', '{"theme":"dark","corrector_text":"Recette"}', auth)[0], 200)
            self.assertEqual(self.call('POST', '/client/preferences', '{"voice_volume":42,"voice_quality":"max"}', auth)[0], 200)
            state = json.loads(self.call('GET', '/client/device-state?section=vocal', headers=auth)[2])
            self.assertEqual(state['voice_preferences'], {'voice_volume': 42, 'voice_quality': 'max'})
            self.assertNotIn('Recette', json.dumps(state))
            self.assertEqual(self.call('POST', '/client/endpoint', '{"endpoint":"example.test:51821"}', auth)[0], 200)
            saved = client.read_settings_for_update(self.remote.profile)
            self.assertEqual(saved['endpoint'], 'example.test:51821')
            self.assertEqual(saved['preferences']['corrector_text'], 'Recette')

    def test_desktop_version_is_visible_through_authenticated_state(self):
        self.remote.version = '3.5.63'
        self.assertEqual(self.call('GET', '/client/state')[0], 401)
        status, _, body = self.call('GET', '/client/state', headers={'Authorization': 'Bearer local-key'})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['version'], '3.5.63')
        self.assertEqual(self.call('GET', '/api/v1/projects')[0], 403)

    def test_state_refuses_unreadable_or_invalid_local_drafts_and_recovers(self):
        settings = Path(self.folder.name)/'settings-local.json'
        headers = {'Authorization': 'Bearer local-key'}
        original = {'preferences': {'conversation_drafts': {'conversation-fictive': 'Brouillon conservé'},
                                    'corrector_text': 'Correction conservée'}}
        encoded = json.dumps(original, ensure_ascii=False).encode('utf-8')
        with patch.object(client, 'settings_path', return_value=settings), \
             patch.object(client, 'protect', side_effect=lambda value, decrypt=False: value if isinstance(value, bytes) else value.encode('utf-8')):
            settings.write_bytes(encoded)
            status, _, body = self.call('GET', '/client/state', headers=headers)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)['preferences'], original['preferences'])
            invalid = [b'{fichier-corrompu',
                       json.dumps({'preferences': []}).encode(),
                       json.dumps({'preferences': {'conversation_drafts': 'invalide'}}).encode(),
                       json.dumps({'preferences': {'corrector_text': None}}).encode()]
            for damaged in invalid:
                settings.write_bytes(damaged)
                status, _, body = self.call('GET', '/client/state', headers=headers)
                self.assertEqual(status, 503, body)
                self.assertNotIn(damaged, body)
                self.assertEqual(settings.read_bytes(), damaged)
                post_headers = {**headers, 'Content-Type': 'application/json'}
                status, _, body = self.call('POST', '/client/preferences',
                                            json.dumps({'theme': 'dark', 'corrector_text': 'nouveau texte'}),
                                            post_headers)
                self.assertEqual(status, 400, body)
                self.assertEqual(settings.read_bytes(), damaged)
            settings.write_bytes(encoded)
            status, _, body = self.call('GET', '/client/state', headers=headers)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)['preferences'], original['preferences'])
            self.assertEqual(settings.read_bytes(), encoded)
            status, _, body = self.call('POST', '/client/preferences', json.dumps({'theme': 'dark'}),
                                        {**headers, 'Content-Type': 'application/json'})
            self.assertEqual(status, 200, body)
            saved = json.loads(settings.read_bytes())['preferences']
            self.assertEqual(saved['corrector_text'], original['preferences']['corrector_text'])
            self.assertEqual(saved['conversation_drafts'], original['preferences']['conversation_drafts'])

    def test_chat_contains_read_only_local_recovery_library_under_its_csp(self):
        self.assertEqual(self.call('GET', '/')[0], 403)
        self.assertEqual(self.call('GET', '/chat')[0], 403)
        session = self.chat_session()
        launch = client.urlsplit(self.server.chat_launch_url)
        self.assertEqual(self.call('GET', launch.path + '?' + launch.query)[0], 403)
        status, headers, body = self.call('GET', '/chat', headers=session)
        self.assertEqual(status, 200)
        page = body.decode('utf-8')
        self.assertNotIn('local-key', page)
        self.assertEqual(self.call('GET', '/client/history', headers=session)[0], 200)
        integration = hmac.new(b'local-key', b'kiara-integration:opencode', hashlib.sha256).hexdigest()
        self.assertEqual(self.call('GET', '/client/history', headers={'Authorization': 'Bearer ' + integration})[0], 401)
        if sys.platform == 'win32':
            address = f'http://127.0.0.1:{self.port}'
            post_headers = {**session, 'Content-Type': 'application/json'}
            self.assertEqual(self.call('POST', '/client/device-session', '{}', post_headers)[0], 401)
            self.assertEqual(self.call('POST', '/client/device-session', '{}', {**post_headers, 'Origin': address})[0], 200)
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
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
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
