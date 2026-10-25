"""Real installed native multiplexer under two isolated Kiara profiles."""
import http.client
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

from hermes_accounts import HermesAccounts
from hermes_service import HermesService, child_environment, installation


_SOURCE = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'hermes/hermes-agent'


@unittest.skipUnless(os.name == 'nt' and (_SOURCE / 'hermes_cli/main.py').is_file(),
                     'Native integration needs the installed Windows Hermes runtime.')
class NativeMultiplexerContracts(unittest.TestCase):
    def test_native_creation_profile_auth_isolation_and_runtime_projection(self):
        with tempfile.TemporaryDirectory(prefix='fred-hermes-native-') as temp:
            accounts = HermesAccounts(temp, mcp_url='')
            a, b = '0011223344556677', '8899aabbccddeeff'
            accounts.ensure(a)
            accounts.ensure(b)
            ac, bc = accounts.credentials(a), accounts.credentials(b)
            service = HermesService(accounts, port=0, supervise=True)
            try:
                status = service.start()
                self.assertTrue(status['ready'])
                self.assertEqual(status['profiles'], 2)
                self.assertEqual(status['source_commit'], installation()['commit'])
                # Native policy must refuse dependency acquisition while both
                # Kiara's environment and durable profile config reuse installed packages.
                runtime = installation()
                policy = subprocess.run([str(runtime['python']), '-c',
                    "import os; from pm.install import lazy_installs_allowed; "
                    "print(int(lazy_installs_allowed())); "
                    "os.environ.pop('HERMES_DISABLE_LAZY_INSTALLS', None); "
                    "print(int(lazy_installs_allowed()))"],
                    cwd=runtime['source'], env=child_environment(accounts.root / 'profiles' / ac['profile'], runtime),
                    capture_output=True, timeout=15, creationflags=0x08000000)
                self.assertEqual(policy.returncode, 0)
                self.assertEqual(policy.stdout.split(), [b'0', b'0'])
                # Native auth must use the routed profile's key, never the root/sibling key.
                for token in (ac['api_key'], accounts.gateway_key()):
                    connection = http.client.HTTPConnection('127.0.0.1', service.port, timeout=10)
                    try:
                        connection.request('GET', '/p/' + bc['profile'] + '/v1/capabilities',
                                           headers={'Authorization': 'Bearer ' + token})
                        response = connection.getresponse()
                        self.assertEqual(response.status, 401)
                        response.read()
                    finally:
                        connection.close()
                for owner in (a, b, a):
                    caps = service.capabilities(owner)
                    self.assertTrue(caps['features']['run_submission'])
                    self.assertTrue(caps['features']['run_events_sse'])
                created = service.request(a, 'POST', '/api/sessions', {'title': 'Session privée A'})
                identifier = created.get('session', {}).get('id')
                self.assertTrue(identifier, created)
                session = service.request(a, 'GET', '/api/sessions/' + identifier)
                self.assertIn(identifier, json.dumps(session))
                with self.assertRaisesRegex(ValueError, 'HTTP 404'):
                    service.request(b, 'GET', '/api/sessions/' + identifier)
                self.assertIn(identifier, json.dumps(service.request(a, 'GET', '/api/sessions/' + identifier)))
                with self.assertRaises(ValueError):
                    service.request(a, 'GET', '/../../p/' + bc['profile'] + '/v1/capabilities')
                toolsets = service.request(a, 'GET', '/v1/toolsets')
                entries = toolsets if isinstance(toolsets, list) else toolsets.get('data', [])
                enabled = {entry['name'] for entry in entries if entry.get('enabled')}
                self.assertNotIn('memory', enabled)
                self.assertNotIn('terminal', enabled)
                self.assertNotIn('file', enabled)
                self.assertNotIn('browser', enabled)
                self.assertNotIn('session_search', enabled)
                # A newly issued client is picked up by the running native multiplexer.
                c = '1122334455667788'
                accounts.ensure(c, port=service.port)
                deadline = time.monotonic() + 40
                while True:
                    try:
                        self.assertTrue(service.capabilities(c)['features']['run_submission'])
                        break
                    except ValueError:
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(.2)
                # Kill only this disposable launcher's PID: the supervisor must also
                # reap its orphan interpreter and recover the same profile/session.
                service.process.kill()
                service.process.wait(timeout=5)
                deadline = time.monotonic() + 40
                while not service.status()['restarts'] and time.monotonic() < deadline:
                    time.sleep(.2)
                self.assertEqual(service.status()['restarts'], 1)
                self.assertTrue(service.status()['available'])
                self.assertIn(identifier, json.dumps(service.request(a, 'GET', '/api/sessions/' + identifier)))
                accounts.set_state(a, 'suspended')
                with self.assertRaisesRegex(ValueError, 'désactivé'):
                    service.capabilities(a)
                self.assertTrue(service.capabilities(b)['features']['session_resources'])
            finally:
                service.close()
            self.assertFalse((accounts.root / '.env').exists())
            self.assertFalse((accounts.root / 'profiles' / ac['profile'] / '.env').exists())
            self.assertEqual(accounts.credentials(a), ac)
            # The installed runtime junction is only dependency reuse; teardown does not delete its target.
            self.assertTrue(installation()['python'].is_file())


if __name__ == '__main__':
    unittest.main()
