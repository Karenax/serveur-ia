"""LAN state, privilege requests and local-console authorization; no OS mutations."""
import json
import re
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from app import serve
from core import read_json, write_json
from local_network import LocalNetwork, system_state


LIVE = {'service': 'strata', 'api_key': False, 'loaded': True, 'model': 'qwen-test'}
ACTIVE = {'mapping': True, 'firewall': True, 'listening': True, 'conflict': False}
OFF = {key: False for key in ACTIVE}


class LocalNetworkTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.network = LocalNetwork(lambda: (8080, 'qwen-test', ''), self.folder.name)
        self.os_state = patch('local_network.system_state', return_value=ACTIVE).start()
        self.health = patch('local_network.health', return_value=LIVE).start()
        self.launch = patch('local_network.subprocess.Popen').start()
        self.launch.return_value.poll.return_value = None
        self.addCleanup(patch.stopall)

    def test_existing_installation_is_detected_without_writing_or_launching(self):
        state = self.network.status()
        self.assertTrue(state['enabled'] and state['available'])
        self.assertEqual(state['model'], 'qwen-test')
        self.assertFalse(self.network.result_path.exists())
        self.launch.assert_not_called()

    def test_model_unavailable_does_not_claim_mode_is_off(self):
        self.health.return_value = {}
        state = self.network.status()
        self.assertTrue(state['enabled'])
        self.assertFalse(state['available'])
        self.assertTrue(state['can_disable'])

    def test_disable_requests_only_our_privileged_helper_and_prevents_double_action(self):
        self.network.configure(False)
        command = self.launch.call_args.args[0]
        self.assertIn('Couper', command)
        self.assertTrue(self.network.status()['pending'])
        with self.assertRaisesRegex(ValueError, 'déjà'):
            self.network.configure(False)
        self.assertEqual(self.launch.call_count, 1)

    def test_enable_validates_model_and_rejects_non_boolean(self):
        self.os_state.return_value = OFF
        for invalid in (None, 1, 'true'):
            with self.assertRaises(ValueError):
                self.network.configure(invalid)
        self.health.return_value = {**LIVE, 'api_key': True}
        with self.assertRaisesRegex(ValueError, 'sans authentification'):
            self.network.configure(True)
        self.launch.assert_not_called()
        self.health.return_value = LIVE
        self.network.configure(True)
        self.assertIn('Activer', self.launch.call_args.args[0])

    def test_disable_still_works_when_model_is_unavailable(self):
        self.health.return_value = {}
        self.network.configure(False)
        self.assertIn('Couper', self.launch.call_args.args[0])

    def test_result_is_verified_against_windows_instead_of_trusting_success_file(self):
        write_json(self.network.result_path, {'state': 'done'})
        self.os_state.return_value = OFF
        state = self.network.status()
        self.assertFalse(state['enabled'])
        self.assertEqual(state['state'], 'disabled')

    def test_cancelled_validation_retains_actual_state_and_visible_error(self):
        write_json(self.network.result_path, {'state': 'failed', 'message': 'Validation Windows annulée.'})
        state = self.network.status()
        self.assertTrue(state['enabled'])
        self.assertIn('annulée', state['error'])

    def test_helper_launch_failure_is_persisted_and_can_be_retried(self):
        self.launch.side_effect = OSError('test')
        with self.assertRaises(ValueError):
            self.network.configure(False)
        self.assertEqual(read_json(self.network.result_path)['state'], 'failed')
        self.assertFalse(self.network.status()['pending'])

    def test_incomplete_or_conflicting_installation(self):
        self.os_state.return_value = {**ACTIVE, 'firewall': False}
        state = self.network.status()
        self.assertEqual(state['state'], 'incomplete')
        self.assertTrue(state['can_disable'])
        self.os_state.return_value = {**OFF, 'conflict': True}
        with self.assertRaises(ValueError):
            self.network.configure(False)
        self.launch.assert_not_called()

    def test_unfinished_helper_cannot_leave_ui_pending_forever(self):
        self.network.configure(False)
        self.launch.return_value.poll.return_value = 1
        state = self.network.status()
        self.assertFalse(state['pending'])
        self.assertIn('error', state)

    def test_firewall_scope_and_listener_are_read_from_actual_os_configuration(self):
        # Use the real function object; registry and process tables are synthetic.
        rule = 'v2.30|Action=Allow|Active=TRUE|Dir=In|Protocol=6|LPort=8080|LA4=192.168.1.41|RA4=192.168.1.0/255.255.255.0|'
        with patch('local_network.registry_value', side_effect=['127.0.0.1/8080', rule]), patch('local_network.psutil.net_connections', return_value=[SimpleNamespace(status='LISTEN', laddr=SimpleNamespace(ip='192.168.1.41', port=8080))]):
            self.assertEqual(system_state(), ACTIVE)
        for changed in (rule.replace('192.168.1.0/255.255.255.0', '*'), rule.replace('Active=TRUE', 'Active=FALSE'), rule + 'Profile=Private|'):
            with patch('local_network.registry_value', side_effect=['127.0.0.1/8080', changed]), patch('local_network.psutil.net_connections', return_value=[]):
                self.assertFalse(system_state()['firewall'])

    def test_http_toggle_requires_console_token_and_rejects_foreign_origin(self):
        controller = SimpleNamespace(local_network=self.network, lock=threading.RLock(), remote=SimpleNamespace(maintenance=False))
        server = serve(0, controller)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with urllib.request.urlopen(base) as response:
                token = re.search(r'name="launcher-token" content="([^"]+)"', response.read().decode())[1]
            for headers in ({}, {'X-Launcher-Token': token, 'Origin': 'https://foreign.example'}):
                request = urllib.request.Request(base + '/api/local-network', b'{"enabled":false}', {'Content-Type': 'application/json', **headers})
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(request)
                self.assertEqual(error.exception.code, 403)
            self.launch.assert_not_called()
            with urllib.request.urlopen(base + '/api/local-network') as response:
                self.assertTrue(json.load(response)['enabled'])
            request = urllib.request.Request(base + '/api/local-network', b'{"enabled":false}', {'Content-Type': 'application/json', 'X-Launcher-Token': token})
            with urllib.request.urlopen(request) as response:
                self.assertIn('Windows', json.load(response)['message'])
            self.assertEqual(self.launch.call_count, 1)
        finally:
            server.shutdown()
            server.server_close()
