"""A failed assistant creation remains recoverable without creating another account."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from core import read_json
from remote import AccessStore


class ProvisioningFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='fred-hermes-provision-flow-')
        self.store = AccessStore(Path(self.tmp.name))
        self.store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
    def tearDown(self):
        self.store.workspace.shutdown(); self.store.voice.close(); self.tmp.cleanup()
    def test_failed_creation_is_denied_then_resumes_same_owner_with_new_device_token(self):
        store = self.store
        class Facade:
            fail = True
            def ensure(self, owner, name):
                record = next(c for c in read_json(store.path)['clients'] if c['id'] == owner)
                assert record['hermes_pending']
                if self.fail: raise ValueError('private runtime details')
        facade = Facade(); store.hermes = facade
        with patch('remote.secrets.token_urlsafe',return_value='x'*43), self.assertRaisesRegex(ValueError, 'Création Hermes incomplète'):
            store.issue('Téléphone de preuve', platform='android')
        record = read_json(store.path)['clients'][0]
        self.assertTrue(record['hermes_pending']); self.assertEqual(record['creation_platform'], 'android')
        token='qwen_'+record['id']+'_'+'x'*43
        self.assertEqual(store.denial(token)[0], 'agent_provisioning')
        self.assertIsNone(store.authenticate(token))
        before = record['hash']; facade.fail = False
        access = store.issue(record['name'], resume=record['id'], platform='android')
        records = read_json(store.path)['clients']
        self.assertEqual(len(records), 1); self.assertEqual(access['id'], record['id'])
        self.assertNotEqual(records[0]['hash'], before); self.assertNotIn('hermes_pending', records[0])
        self.assertEqual(store.authenticate(access['token']), record['id'])
        self.assertIsNone(store.authenticate(token))
        with self.assertRaisesRegex(ValueError, 'création Hermes incomplète'):
            store.issue(record['name'], resume=record['id'])


if __name__ == '__main__': unittest.main()
