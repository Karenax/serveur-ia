"""Profile provisioning, restart recovery and access isolation contracts."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest

from hermes_accounts import CONFIG_VERSION, HermesAccounts, profile_name
from hermes_service import child_environment


def fake_profile(accounts, owner, port):
    directory = accounts.root / 'profiles' / profile_name(owner)
    directory.mkdir(parents=True, exist_ok=True)
    for name in ('memories', 'sessions', 'workspace', 'skills'):
        (directory / name).mkdir(exist_ok=True)


class ProfileContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fred-hermes-accounts-')
        self.home = Path(self.temp.name)
        self.allowed = {'0011223344556677', '8899aabbccddeeff'}
        self.accounts = HermesAccounts(self.home, authorized=lambda owner: owner in self.allowed,
                                       profile_factory=fake_profile)

    def tearDown(self):
        self.accounts.clear_runtime_secrets()
        self.temp.cleanup()

    def test_idempotent_creation_secrets_survive_restart_and_are_protected(self):
        owner = '0011223344556677'
        results = []
        workers = [threading.Thread(target=lambda: results.append(self.accounts.ensure(owner))) for _ in range(4)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        self.assertEqual(len(results), 4)
        self.assertEqual(self.accounts.owners(), [owner])
        self.assertEqual(self.accounts.public(owner)['attempts'], 1)
        credentials = self.accounts.credentials(owner)
        stored = self.accounts.path.read_bytes()
        for kind in ('api_key', 'inference_key', 'tool_key'):
            self.assertNotIn(credentials[kind].encode(), stored)
            self.assertNotIn(credentials[kind], json.dumps(self.accounts.public(owner)))
        self.accounts.clear_runtime_secrets()
        restarted = HermesAccounts(self.home, profile_factory=fake_profile)
        restarted.ensure(owner)
        self.assertEqual(credentials, restarted.credentials(owner))
        self.assertTrue((restarted.root / 'profiles' / profile_name(owner) / '.env').is_file())

    def test_failure_recovery_keeps_same_identity_and_no_exception_secret(self):
        owner = '0011223344556677'
        calls = []
        def partial(accounts, identity, port):
            fake_profile(accounts, identity, port)
            calls.append(identity)
            if len(calls) == 1:
                raise OSError('private-provider-key-leak')
        self.accounts.profile_factory = partial
        with self.assertRaises(ValueError):
            self.accounts.ensure(owner)
        credentials = self.accounts.credentials(owner)
        self.assertEqual(self.accounts.public(owner)['state'], 'error')
        self.assertNotIn('private-provider-key-leak', self.accounts.path.read_bytes().decode('latin1'))
        self.assertIsNone(self.accounts.authenticate_private(credentials['inference_key'], 'inference'))
        self.accounts.ensure(owner)
        self.assertEqual(credentials, self.accounts.credentials(owner))
        self.assertEqual(self.accounts.public(owner)['attempts'], 2)

    def test_profiles_keys_revocation_and_migration_are_per_access(self):
        a, b = sorted(self.allowed)
        self.accounts.ensure(a, 'même propriétaire')
        self.accounts.ensure(b, 'même propriétaire')
        ac, bc = self.accounts.credentials(a), self.accounts.credentials(b)
        self.assertNotEqual(ac['profile'], bc['profile'])
        for kind in ('api_key', 'inference_key', 'tool_key'):
            self.assertNotEqual(ac[kind], bc[kind])
        self.assertEqual(self.accounts.authenticate_private(ac['inference_key'], 'inference'), a)
        self.assertIsNone(self.accounts.authenticate_private(ac['tool_key'], 'inference'))
        self.allowed.remove(a)
        self.assertIsNone(self.accounts.authenticate_private(ac['inference_key'], 'inference'))
        self.assertEqual(self.accounts.authenticate_private(bc['tool_key'], 'tool'), b)
        report = self.accounts.migrate([{'id': a, 'revoked': True}, {'id': b},
                                        {'id': '1122334455667788', 'suspended': True}])
        self.assertEqual(report['ready'], [b])
        self.assertEqual(self.accounts.public(a)['state'], 'revoked')
        self.assertFalse(self.accounts.ensure(a)['ready'])
        self.assertEqual(self.accounts.owners(), [a, b])

    def test_unsafe_id_and_destination_rejected_and_shell_keys_not_inherited(self):
        for owner in ('../other', 'AABB', 'fred/a', '', 'a\nb', 'a' * 57):
            with self.assertRaises(ValueError):
                self.accounts.ensure(owner)
        for url in ('http://192.168.1.1:1/v1', 'https://127.0.0.1:1/v1', 'http://u:p@127.0.0.1:1/v1'):
            with self.assertRaises(ValueError):
                HermesAccounts(self.home, inference_url=url)
        previous = {key: os.environ.get(key) for key in ('FRED_TEST_CREDENTIAL', 'OPENAI_API_KEY')}
        os.environ['FRED_TEST_CREDENTIAL'] = 'must-not-inherit'
        os.environ['OPENAI_API_KEY'] = 'must-not-inherit'
        try:
            env = child_environment(self.accounts.root)
            self.assertNotIn('FRED_TEST_CREDENTIAL', env)
            self.assertNotIn('OPENAI_API_KEY', env)
            self.assertEqual(env['HERMES_HOME'], str(self.accounts.root))
            self.assertEqual(env['HERMES_DISABLE_LAZY_INSTALLS'], '1')
            self.assertFalse(self.accounts.config()['security']['allow_lazy_installs'])
            self.assertFalse(self.accounts.config('0011223344556677')['skills']['inline_shell'])
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_suspend_then_resume_retains_credentials_and_profile_data(self):
        owner = '0011223344556677'
        self.accounts.ensure(owner)
        keys = self.accounts.credentials(owner)
        memory = self.accounts.root / 'profiles' / profile_name(owner) / 'memories/MEMORY.md'
        memory.write_text('Preference privée conservée.', encoding='utf-8')
        self.allowed.remove(owner)
        self.accounts.migrate([{'id': owner, 'suspended': True}])
        self.assertFalse(self.accounts.ensure(owner)['ready'])
        self.assertIsNone(self.accounts.authenticate_private(keys['inference_key'], 'inference'))
        self.allowed.add(owner)
        self.assertEqual(self.accounts.migrate([{'id': owner}])['ready'], [owner])
        self.assertEqual(self.accounts.credentials(owner), keys)
        self.assertEqual(memory.read_text(encoding='utf-8'), 'Preference privée conservée.')
        self.accounts.set_state(owner, 'revoked')
        self.assertFalse(self.accounts.ensure(owner)['ready'])
        self.accounts.set_state(owner, 'archived')
        self.assertFalse(self.accounts.ensure(owner)['ready'])

    def test_profile_directory_link_is_refused_before_any_write(self):
        owner = '0011223344556677'
        outside = self.home / 'outside-profile'
        outside.mkdir()
        marker = outside / 'config.yaml'
        marker.write_text('private external profile', encoding='utf-8')
        profiles = self.accounts.root / 'profiles'
        profiles.mkdir()
        link = profiles / profile_name(owner)
        if os.name == 'nt':
            env = os.environ.copy()
            env.update(FRED_TEST_LINK=str(link), FRED_TEST_TARGET=str(outside))
            subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                'New-Item -ItemType Junction -Path $env:FRED_TEST_LINK -Target $env:FRED_TEST_TARGET -ErrorAction Stop | Out-Null'],
                check=True, env=env, capture_output=True, creationflags=0x08000000)
        else:
            link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.accounts.ensure(owner)
        self.assertEqual(marker.read_text(encoding='utf-8'), 'private external profile')
        self.assertFalse((outside / '.env').exists())

    def test_config_upgrade_preserves_identity_and_disables_unscoped_search(self):
        owner = '0011223344556677'
        self.accounts.ensure(owner)
        keys = self.accounts.credentials(owner)
        directory = self.accounts.root / 'profiles' / keys['profile']
        memory = directory / 'memories/MEMORY.md'
        memory.write_text('Préférence conservée durant la migration.', encoding='utf-8')
        old_config = self.accounts.config(owner)
        old_config['platform_toolsets']['api_server'].append('session_search')
        (directory / 'config.yaml').write_text(json.dumps(old_config), encoding='utf-8')
        with self.accounts._db() as db:
            db.execute('UPDATE hermes_bindings SET config_version=? WHERE owner=?', (CONFIG_VERSION - 1, owner))
        self.assertFalse(self.accounts.enabled(owner))
        self.accounts.ensure(owner)
        self.assertTrue(self.accounts.enabled(owner))
        self.assertEqual(self.accounts.credentials(owner), keys)
        self.assertEqual(memory.read_text(encoding='utf-8'), 'Préférence conservée durant la migration.')
        self.assertNotIn('session_search', json.loads((directory / 'config.yaml').read_text(encoding='utf-8'))['platform_toolsets']['api_server'])
        self.assertEqual(self.accounts.public(owner)['attempts'], 2)
        self.accounts.ensure(owner)
        self.assertEqual(self.accounts.public(owner)['attempts'], 2)


if __name__ == '__main__':
    unittest.main()
