"""Exercise the Kiara gateway against a private signed Agent endpoint."""

from contextlib import closing
import hashlib
from pathlib import Path
import http.client
import json
import threading
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import Mock

from agent_gateway import AgentBridge, project_catalogue, project_context, project_request, proxy
from agent_service import AgentService
from kiara_shared.agent_auth import Verifier
from kiara_shared.releases import DESKTOP_DOWNLOAD, DESKTOP_RELEASE
from core import write_json
from releases import DESKTOP_INSTALLER, DESKTOP_INSTALLER_VERSION
from remote import serve_gateway
from signing import sign
from workspace import Workspace
from workspace_types import Denied, HISTORY_RESET_ID


ERP_PROJECT = '11111111-2222-3333-4444-555555555555'


class AgentGatewayTests(unittest.TestCase):
    def test_signed_desktop_download_uses_its_own_authenticated_channel(self):
        folder = self.store.home / 'installateurs'
        folder.mkdir()
        installer = folder / DESKTOP_INSTALLER
        data = b'fixture installer'
        installer.write_bytes(data)
        release = sign({'version': DESKTOP_INSTALLER_VERSION, 'protocol': 4, 'bytes': len(data),
                        'sha256': hashlib.sha256(data).hexdigest()}, self.store.home)
        write_json(folder / f'kiara-{DESKTOP_INSTALLER_VERSION}.json', release)
        for path, payload in ((DESKTOP_RELEASE, release), (DESKTOP_DOWNLOAD, data)):
            with closing(http.client.HTTPConnection('127.0.0.1', self.gateway.server_port, timeout=5)) as connection:
                connection.request('GET', path)
                response = connection.getresponse()
                self.assertEqual(response.status, 401)
                response.read()
                connection.request('GET', path, headers={'Authorization': 'Bearer valid-token'})
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(json.load(response) if path == DESKTOP_RELEASE else response.read(), payload)

    def setUp(self):
        self.key = b'k' * 32
        verifier = Verifier(self.key)
        self.release_stream = threading.Event()
        release_stream = self.release_stream
        self.upload_started = threading.Event()
        self.upload_received = threading.Event()
        self.upload_data = []
        upload_started, upload_received, upload_data = self.upload_started, self.upload_received, self.upload_data

        class AgentHandler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                operator = verifier.verify(self.headers['X-Kiara-Agent-Context'], 'GET', self.path)
                if self.path == '/v1/sources/fixture/raw':
                    if (operator['id'] != 'device-a' or 'project-a' not in operator['project_ids']
                            or self.headers.get('Range') != 'bytes=1-3'):
                        self.send_error(403)
                        return
                    self.send_response(206)
                    self.send_header('Content-Type', 'application/octet-stream')
                    self.send_header('Content-Length', '3')
                    self.send_header('Content-Range', 'bytes 1-3/5')
                    self.send_header('Content-Disposition', 'attachment; filename="original.txt"')
                    self.end_headers()
                    self.wfile.write(b'rig')
                    return
                if self.path == '/api/v1/stream':
                    self.send_response(200)
                    self.send_header('Content-Length', '11')
                    self.end_headers()
                    self.wfile.write(b'first')
                    self.wfile.flush()
                    release_stream.wait(5)
                    try:
                        self.wfile.write(b'secret')
                    except OSError:
                        pass
                    return
                if operator['id'] == 'kiara-service' and self.path == '/api/v1/project-catalogue':
                    value = [{'id': 'project-a', 'code': 'TEST', 'title': 'Projet fictif', 'status': 'active',
                              'brain_project_id': 'brain-a'}]
                elif self.path == '/api/v1/project-catalogue':
                    value = [{'id': ERP_PROJECT, 'code': 'TEST', 'title': 'Projet fictif', 'status': 'active'}
                             for project in operator['project_ids'] if project == ERP_PROJECT]
                elif self.path == '/internal/kiara/conversations':
                    value = [{'project': ERP_PROJECT, 'id': 'a' * 32, 'title': 'Discussion', 'revision': 1,
                              'archived': False, 'updated': 1}] if operator['id'] == 'device-a' else []
                elif self.path in ('/internal/kiara/memories', f'/internal/kiara/memories?project={ERP_PROJECT}'):
                    value = [{'project': ERP_PROJECT, 'id': 'c' * 32, 'text': 'Mémoire de recette', 'revision': '1'}]
                elif operator['id'] == 'kiara-service' and self.path == '/internal/kiara/personal-sessions':
                    value = {'sessions': [], 'sessions_truncated': False}
                elif self.path == f'/internal/kiara/projects/{ERP_PROJECT}/context?q=vanne':
                    if ERP_PROJECT not in operator['project_ids']:
                        self.send_response(404)
                        self.end_headers()
                        return
                    value = {'items': [{'title': 'Notice', 'excerpt': 'La vanne est ouverte.', 'level': 'validated',
                                        'source_id': 'preuve', 'locator': {'physical_page': 3}}]}
                else:
                    value = operator
                body = json.dumps(value).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                operator = verifier.verify(self.headers['X-Kiara-Agent-Context'], 'POST', self.path)
                if self.path == '/api/v1/upload':
                    upload_started.set()
                    upload_data.append(self.rfile.read(int(self.headers['Content-Length'])))
                    upload_received.set()
                    return
                content = self.rfile.read(int(self.headers['Content-Length']))
                body = json.dumps({'operator': operator, 'data': content.decode()}).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                if self.path == '/api/v1/documents/prepare-copy':
                    self.send_header('X-Agent-Source-Sha256', 'a' * 64)
                    self.send_header('X-Agent-Values-Sha256', 'b' * 64)
                    self.send_header('X-Agent-Link-Sha256', 'c' * 64)
                    self.send_header('X-Agent-Network-Published', 'false')
                self.end_headers()
                self.wfile.write(body)

        self.agent = ThreadingHTTPServer(('127.0.0.1', 0), AgentHandler)
        threading.Thread(target=self.agent.serve_forever, daemon=True).start()

        class Workspace:
            def start(self, valid_owner):
                pass

            def shutdown(self):
                pass

        class Store:
            scheduler = None
            maintenance = False
            lock = threading.RLock()
            agent_active = 0
            workspace = Workspace()
            voice = None
            voice_max = None
            enabled = True
            scope = ['project-a']

            def authenticate(self, token):
                return 'device-a' if self.enabled and token == 'valid-token' else None

            def denial(self, token):
                return 'invalid', 'Accès refusé.'

            def valid_owner(self, owner):
                return owner == 'device-a'

        self.store = Store()
        self.store.home = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.store.agent_bridge = AgentBridge(self.agent.server_port, self.key, lambda owner: {
            'id': owner, 'role': 'reader', 'project_ids': list(self.store.scope), 'person_id': None})
        self.gateway = serve_gateway(self.store, lambda: None, port=0)
        threading.Thread(target=self.gateway.serve_forever, daemon=True).start()

    def tearDown(self):
        self.release_stream.set()
        self.gateway.shutdown()
        self.gateway.server_close()
        self.agent.shutdown()
        self.agent.server_close()

    def request(self, path, token='valid-token'):
        connection = http.client.HTTPConnection('127.0.0.1', self.gateway.server_port, timeout=5)
        connection.request('GET', path, headers={'Authorization': 'Bearer ' + token})
        response = connection.getresponse()
        data = response.read()
        connection.close()
        return response.status, json.loads(data)

    def test_signed_context_and_route(self):
        status, data = self.request('/v1/business/api/v1/portfolio?limit=5')
        self.assertEqual(status, 200)
        self.assertEqual(data['id'], 'device-a')
        self.assertEqual(data['project_ids'], ['project-a'])

    def test_management_reads_erp_catalogue_with_the_service_identity(self):
        service = AgentService(self.store, '.', '.')
        service.process = SimpleNamespace(poll=lambda: None)
        self.assertEqual(service.management_data(), {
            'projects': [{'id': 'project-a', 'code': 'TEST', 'title': 'Projet fictif', 'status': 'active',
                          'knowledge_linked': True}],
            'sessions': [], 'sessions_truncated': False,
        })

    def test_erp_project_survives_history_sync_and_constrains_chat_sources(self):
        self.store.scope = [ERP_PROJECT]
        with tempfile.TemporaryDirectory() as folder:
            workspace = Workspace(folder)
            workspace.agent_context = lambda *args: project_context(self.store, *args)
            history = {'currentId': 'discussion', 'conversations': [
                {'id': 'discussion', 'title': 'Vanne', 'project_id': ERP_PROJECT, 'messages': []}]}
            workspace.history_write('device-a', {'history': history, 'revision': 0, 'reset_id': HISTORY_RESET_ID})
            self.assertEqual(workspace.history_read('device-a')['history']['conversations'][0]['project_id'], ERP_PROJECT)
            messages = [{'role': 'user', 'content': 'vanne'}]
            prompt, sources = workspace.context('device-a', messages, ERP_PROJECT)
            self.assertIn('La vanne est ouverte.', prompt[0]['content'])
            self.assertIn('Mémoire de recette', prompt[0]['content'])
            self.assertEqual((sources[0]['level'], sources[0]['page']), ('validé', 3))
            spoken, _ = workspace.context('device-a', messages, ERP_PROJECT, voice_conversation='discussion')
            self.assertNotIn('La vanne est ouverte.', spoken[0]['content'])
            self.assertIn('La vanne est ouverte.', spoken[-2]['content'])
            self.assertEqual(spoken[-1], messages[-1])
            self.store.scope = []
            with self.assertRaises(Denied):
                workspace.context('device-a', messages, ERP_PROJECT)

    def test_managed_workspace_projects_come_from_agent_even_during_an_outage(self):
        self.store.scope = [ERP_PROJECT]
        with tempfile.TemporaryDirectory() as folder:
            workspace = Workspace(folder)
            workspace.action('device-a', {'action': 'project_create', 'title': 'Projet historique'})
            workspace.agent_catalogue = lambda owner: project_catalogue(self.store, owner)
            workspace.agent_project_request = lambda *args: project_request(self.store, *args)
            snapshot = workspace.snapshot('device-a')
            self.assertEqual([p['id'] for p in snapshot['projects']], [ERP_PROJECT])
            self.assertEqual(snapshot['projects'][0]['project_kind'], 'managed')
            self.assertIsNone(snapshot['projects'][0]['has_knowledge'])
            self.assertEqual([c['id'] for c in snapshot['projects'][0]['conversations']], ['a' * 32])
            self.assertEqual(snapshot['projects'][0]['memories'][0]['text'], 'Mémoire de recette')
            from memory_service import memory_epoch
            epoch = memory_epoch(workspace, 'device-a')
            memory = workspace.action('device-a', {'action': 'memory_create', 'project': ERP_PROJECT,
                                                   'text': 'Nouveau souvenir'})
            self.assertEqual(json.loads(memory['data']), {'action': 'memory_create', 'text': 'Nouveau souvenir'})
            self.assertNotEqual(memory_epoch(workspace, 'device-a'), epoch)
            publication = workspace.action('device-a', {'action': 'conversation_save', 'project': ERP_PROJECT,
                                           'reset_id': HISTORY_RESET_ID, 'id': 'b' * 32,
                                           'title': 'Discussion', 'messages': []})
            self.assertEqual(publication['operator']['id'], 'device-a')
            self.assertEqual(json.loads(publication['data']), {'action': 'conversation_save', 'id': 'b' * 32,
                             'revision': 0, 'title': 'Discussion', 'messages': []})
            self.assertFalse(snapshot['project_catalogue']['can_create'])
            self.assertFalse(snapshot['projects'][0]['can_edit'])
            self.store.agent_bridge = None
            snapshot = workspace.snapshot('device-a')
            self.assertEqual(snapshot['projects'], [])
            self.assertEqual(snapshot['project_catalogue']['state'], 'unavailable')
            with self.assertRaisesRegex(ValueError, 'service Projets de Kiara est indisponible'):
                workspace.action('device-a', {'action': 'project_create', 'title': 'Projet en double'})
            with workspace.db() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM projects').fetchone()[0], 1)

    def test_post_body_is_forwarded(self):
        connection = http.client.HTTPConnection('127.0.0.1', self.gateway.server_port, timeout=5)
        connection.request('POST', '/v1/business/api/v1/test', body='hello',
                           headers={'Authorization': 'Bearer valid-token', 'Content-Type': 'text/plain'})
        response = connection.getresponse()
        payload = json.loads(response.read())
        connection.close()
        self.assertEqual(response.status, 200)
        self.assertEqual(payload['operator']['id'], 'device-a')
        self.assertEqual(payload['data'], 'hello')

    def test_document_copy_receipt_is_forwarded(self):
        with closing(http.client.HTTPConnection('127.0.0.1', self.gateway.server_port, timeout=5)) as connection:
            connection.request('POST', '/v1/business/api/v1/documents/prepare-copy', '{}',
                               {'Authorization': 'Bearer valid-token'})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader('X-Agent-Source-Sha256'), 'a' * 64)
            self.assertEqual(response.getheader('X-Agent-Values-Sha256'), 'b' * 64)
            self.assertEqual(response.getheader('X-Agent-Link-Sha256'), 'c' * 64)
            self.assertEqual(response.getheader('X-Agent-Network-Published'), 'false')
            response.read()

    def test_thunderbird_bridge_requires_the_designated_writing_device(self):
        def heartbeat(token='valid-token'):
            with closing(http.client.HTTPConnection('127.0.0.1', self.gateway.server_port, timeout=5)) as connection:
                connection.request('POST', '/v1/business/v1/thunderbird/bridge/heartbeat', '{}',
                                   {'Authorization': 'Bearer ' + token})
                response = connection.getresponse()
                return response.status, json.loads(response.read())

        bridge = self.store.agent_bridge
        owner = {'id': 'agent-owner', 'role': 'owner', 'project_ids': ['project-a'], 'person_id': None}
        self.assertEqual(heartbeat()[0], 403)
        bridge.thunderbird_device = 'device-a'
        self.assertEqual(heartbeat()[0], 403)
        bridge.operator_for = lambda _: owner
        self.assertEqual(heartbeat('invalid-token')[0], 401)
        self.assertEqual(heartbeat(), (200, {'operator': {**owner, 'id': 'kiara-thunderbird', 'project_ids': []}, 'data': '{}'}))
        with closing(http.client.HTTPConnection('127.0.0.1', self.gateway.server_port, timeout=5)) as connection:
            connection.request('POST', '/v1/business/v1/thunderbird/drafts', '{}',
                               {'Authorization': 'Bearer valid-token'})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())['operator'], {**owner, 'id': 'kiara-thunderbird-reply'})

    def test_revocation_while_waiting_does_not_forward_the_next_stream_chunk(self):
        connection = http.client.HTTPConnection('127.0.0.1', self.gateway.server_port, timeout=5)
        connection.request('GET', '/v1/business/api/v1/stream', headers={'Authorization': 'Bearer valid-token'})
        response = connection.getresponse()
        self.assertEqual(response.read(5), b'first')
        self.assertEqual(self.store.agent_active, 1)
        self.store.enabled = False
        self.release_stream.set()
        with self.assertRaises(http.client.IncompleteRead) as failure:
            response.read()
        self.assertEqual(failure.exception.partial, b'')
        connection.close()

    def test_cancelled_browser_request_releases_the_gateway_slot(self):
        handler = SimpleNamespace(
            command='GET', headers=http.client.HTTPMessage(), send_response=Mock(),
            send_header=Mock(), end_headers=Mock(), respond=Mock(),
            wfile=Mock(write=Mock(side_effect=ConnectionAbortedError(10053, 'Browser aborted request'))),
        )
        proxy(handler, self.store, '/api/v1/portfolio', '', 'device-a', lambda: True,
              browser=True, browser_prefix='/agent')
        handler.send_response.assert_called_once_with(200)
        handler.wfile.write.assert_called_once()
        handler.respond.assert_not_called()
        self.assertEqual(self.store.agent_active, 0)

    def test_revocation_while_waiting_does_not_forward_upload_bytes(self):
        connection = http.client.HTTPConnection('127.0.0.1', self.gateway.server_port, timeout=5)
        connection.putrequest('POST', '/v1/business/api/v1/upload')
        connection.putheader('Authorization', 'Bearer valid-token')
        connection.putheader('Content-Length', '12')
        connection.endheaders()
        connection.send(b'first-')
        self.assertTrue(self.upload_started.wait(5))
        self.store.enabled = False
        connection.send(b'secret')
        with self.assertRaises(http.client.RemoteDisconnected):
            connection.getresponse()
        self.assertTrue(self.upload_received.wait(5))
        self.assertEqual(self.upload_data, [b''])
        connection.close()

    def test_scope_change_while_waiting_does_not_forward_the_next_chunk(self):
        connection = http.client.HTTPConnection('127.0.0.1', self.gateway.server_port, timeout=5)
        connection.request('GET', '/v1/business/api/v1/stream', headers={'Authorization': 'Bearer valid-token'})
        response = connection.getresponse()
        self.assertEqual(response.read(5), b'first')
        self.store.scope = []
        self.release_stream.set()
        with self.assertRaises(http.client.IncompleteRead) as failure:
            response.read()
        self.assertEqual(failure.exception.partial, b'')
        connection.close()

    def test_access_and_native_routes_are_restricted(self):
        self.assertEqual(self.request('/v1/business/api/v1/portfolio', 'invalid')[0], 401)
        self.assertEqual(self.request('/v1/business/api/v1/open-path')[0], 403)
        connection = http.client.HTTPConnection('127.0.0.1', self.gateway.server_port, timeout=5)
        connection.request('POST', '/v1/business/api/v1/meeting-sessions/a/native-capture/start',
                           body='{}', headers={'Authorization': 'Bearer valid-token'})
        response = connection.getresponse()
        self.assertEqual(response.status, 403)
        response.read()
        connection.close()
        self.store.agent_bridge = None
        self.assertEqual(self.request('/v1/business/api/v1/portfolio')[0], 503)


if __name__ == '__main__':
    unittest.main()
