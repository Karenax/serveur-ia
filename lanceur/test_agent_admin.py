"""The Agent access policy is only managed by the local authenticated console."""

import json
import re
import threading
import unittest
import urllib.error
import urllib.request
from types import SimpleNamespace

from app import serve


class AgentAdminTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        calls = self.calls

        class Access:
            def operator_for(self, owner):
                return {'id': owner, 'role': 'reader', 'project_ids': [], 'person_id': None}

            def set_operator(self, owner, **values):
                calls.append((owner, values))

            def revoke(self, owner):
                calls.append(('revoke', owner))

        class Service:
            access = Access()
            worker_groups = ('documents', 'planning')
            start_workers = True
            document_project_root = r'D:\Kiara\dossiers-clients'

            def running(self):
                return True

            def enable_meetings(self):
                calls.append('enable-meetings')

            def set_thunderbird_device(self, owner):
                calls.append(('thunderbird-device', owner))

            def management_data(self):
                return {'projects': [{'id': 'project', 'code': 'TEST', 'title': 'Projet fictif'}], 'sessions': []}

        self.controller = SimpleNamespace(lock=threading.RLock(), remote=SimpleNamespace(maintenance=False),
                                          agent_service=Service())
        self.server = serve(0, self.controller)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_address[1]}'
        with urllib.request.urlopen(self.url, timeout=5) as response:
            self.page = response.read().decode()
            self.token = re.search(r'name="launcher-token" content="([^"]+)"', self.page)[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)

    def request(self, data=None, *, token=True, origin=None, path='/api/project-service'):
        headers = {'X-Launcher-Token': self.token} if token else {}
        if origin:
            headers['Origin'] = origin
        if data is not None:
            headers['Content-Type'] = 'application/json'
        request = urllib.request.Request(self.url + path,
                                         json.dumps(data).encode() if data is not None else None, headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as response:
            try:
                return response.code, json.load(response)
            finally:
                response.close()

    def test_access_requires_token_origin_and_explicit_scope(self):
        command = {'action': 'access', 'owner': 'device', 'role': 'reader', 'project_ids': ['project']}
        self.assertEqual(self.request(token=False)[0], 403)
        self.assertEqual(self.request(command, token=False)[0], 403)
        self.assertEqual(self.request(command, origin='https://example.com')[0], 403)
        self.assertEqual(self.request({'action': 'access', 'owner': 'device', 'role': 'reader'})[0], 400)
        self.assertEqual(self.request(command, origin=self.url)[0], 200)
        self.assertEqual(self.calls, [('device', {'role': 'reader', 'project_ids': ['project'], 'person_id': None,
                                                 'agent_operator_id': None})])

    def test_thunderbird_device_is_managed_only_by_authenticated_console(self):
        command = {'action': 'thunderbird-device', 'owner': '0123456789abcdef'}
        self.assertEqual(self.request(command, token=False)[0], 403)
        self.assertEqual(self.request(command, origin='https://example.com')[0], 403)
        self.assertEqual(self.request({'action': 'thunderbird-device'})[0], 400)
        self.assertEqual(self.request(command, origin=self.url)[0], 200)
        self.assertEqual(self.request({**command, 'owner': None}, origin=self.url)[0], 200)
        self.assertEqual(self.calls, [('thunderbird-device', command['owner']), ('thunderbird-device', None)])

    def test_identity_mapping_is_only_accepted_through_authenticated_admin(self):
        command = {'action': 'access', 'owner': 'device', 'role': 'owner', 'project_ids': None,
                   'agent_operator_id': 'ancien-operateur'}
        self.assertEqual(self.request(command, token=False)[0], 403)
        self.assertEqual(self.request(command, origin=self.url)[0], 200)
        self.assertEqual(self.calls[-1][1]['agent_operator_id'], 'ancien-operateur')

    def test_meeting_activation_requires_local_console_token(self):
        command = {'action': 'enable-meetings'}
        self.assertEqual(self.request(command, token=False)[0], 403)
        self.assertEqual(self.request(command, origin='https://example.com')[0], 403)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.request(command, origin=self.url)[0], 200)
        self.assertEqual(self.calls, ['enable-meetings'])

    def test_catalogue_is_only_available_to_authenticated_admin(self):
        for path in ('/api/project-service/catalogue', '/api/agent-service/catalogue'):
            with self.subTest(path=path):
                self.assertEqual(self.request(token=False, path=path)[0], 403)
                status, body = self.request(path=path)
                self.assertEqual(status, 200)
                self.assertEqual(body['projects'][0]['title'], 'Projet fictif')

    def test_configuration_error_requires_admin(self):
        self.controller.agent_service = None
        self.controller.agent_configuration_error = 'Vérifiez agent-service.json.'
        self.assertEqual(self.request(token=False)[0], 403)
        status, body = self.request()
        self.assertEqual(status, 200)
        self.assertFalse(body['configured'])
        self.assertEqual(body['configuration_error'], 'Vérifiez agent-service.json.')

    def test_status_reports_loaded_worker_groups_and_project_storage(self):
        status, body = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(body['worker_groups'], ['documents', 'planning'])
        self.assertEqual(body['document_project_root'], r'D:\Kiara\dossiers-clients')
        self.controller.agent_service.start_workers = False
        self.assertEqual(self.request()[1]['worker_groups'], [])

    def test_console_advertises_project_service(self):
        self.assertIn('data-service-endpoint="/api/project-service"', self.page)
        self.assertNotIn('Configurer Agent', self.page)


if __name__ == '__main__':
    unittest.main()
