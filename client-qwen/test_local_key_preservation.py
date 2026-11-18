"""Local API key initialization must preserve existing fictional settings."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import client


class LocalKeyPreservationTests(unittest.TestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        self.path=Path(directory.name)/'settings.dpapi'
        context=patch.object(client,'settings_path',return_value=self.path);context.start();self.addCleanup(context.stop)

    @staticmethod
    def clear(value,decrypt=False):
        if value == b'corrupt':raise ValueError('fake decryption failure')
        return value if isinstance(value,bytes) else value.encode('utf-8')

    def test_unreadable_encrypted_settings_are_never_replaced(self):
        self.path.write_bytes(b'corrupt')
        with patch.object(client,'protect',side_effect=self.clear):
            with self.assertRaises(ValueError):client.local_key({})
        self.assertEqual(self.path.read_bytes(),b'corrupt')

    def test_unavailable_keyring_is_reported_without_replacing_settings(self):
        original=b'reglages chiffres fictifs';self.path.write_bytes(original)
        with patch.object(client,'protect',side_effect=RuntimeError('trousseau indisponible')):
            with self.assertRaises(client.LocalSettingsUnreadable):client.local_key({})
        self.assertEqual(self.path.read_bytes(),original)

    def test_relay_reports_unavailable_keyring_before_opening_services(self):
        original=b'reglages chiffres fictifs';self.path.write_bytes(original)
        with patch.object(client,'protect',side_effect=RuntimeError('trousseau indisponible')), \
             patch.object(client,'Remote') as remote, patch.object(client,'serve_local') as serve:
            with self.assertRaises(client.LocalSettingsUnreadable):client.open_local_relay({})
        remote.assert_not_called();serve.assert_not_called()
        self.assertEqual(self.path.read_bytes(),original)

    def test_future_origin_inventory_preserves_existing_thunderbird_port(self):
        original=json.dumps({'thunderbird_token':'fictif','future':'conserver'}).encode()
        self.path.write_bytes(original)
        with patch.object(client,'protect',side_effect=self.clear):
            self.assertEqual(client.portal_recovery_fixed_port({}),client.LOCAL_API_PORT)
        self.assertEqual(self.path.read_bytes(),original)
        self.path.write_bytes(b'corrupt')
        with patch.object(client,'protect',side_effect=self.clear):
            with self.assertRaises(client.LocalSettingsUnreadable):client.portal_recovery_fixed_port({})
        self.assertEqual(self.path.read_bytes(),b'corrupt')

    def test_other_settings_writers_preserve_unreadable_original(self):
        for operation in (lambda:client.save_endpoint({},None),
                          lambda:client.save_preferences({}, {'theme':'dark'})):
            self.path.write_bytes(b'corrupt')
            with patch.object(client,'protect',side_effect=self.clear):
                with self.assertRaises(ValueError):operation()
            self.assertEqual(self.path.read_bytes(),b'corrupt')

    @unittest.skipUnless(os.name == 'nt', 'Liaison Thunderbird Windows.')
    def test_thunderbird_does_not_package_or_update_unreadable_settings(self):
        import thunderbird_integration
        self.path.write_bytes(b'corrupt')
        source=Path(__file__).resolve().parents[1]/'agent'/'extensions'/'thunderbird-agent'
        with patch.object(client,'protect',side_effect=self.clear), \
             patch.object(thunderbird_integration,'distribution_policy',return_value=None), \
             patch.object(thunderbird_integration,'policy') as policy, \
             patch.object(thunderbird_integration,'package') as package:
            with self.assertRaises(ValueError):thunderbird_integration.manage({},source,enable=True)
        policy.assert_not_called();package.assert_not_called()
        self.assertEqual(self.path.read_bytes(),b'corrupt')

    def test_settings_symlink_is_not_followed_or_replaced(self):
        target=self.path.with_name('sentinel');target.write_bytes(b'preserve')
        try:self.path.symlink_to(target)
        except (OSError,NotImplementedError):self.skipTest('Lien symbolique indisponible.')
        with patch.object(client,'protect',side_effect=self.clear):
            with self.assertRaises(ValueError):client.local_key({})
        self.assertEqual(target.read_bytes(),b'preserve');self.assertTrue(self.path.is_symlink())

    def test_malformed_json_and_invalid_existing_key_are_preserved(self):
        for original in (b'{broken',json.dumps({'local_key':'short','preferences':{'theme':'dark'}}).encode()):
            self.path.write_bytes(original)
            with patch.object(client,'protect',side_effect=self.clear):
                with self.assertRaises(ValueError):client.local_key({})
            self.assertEqual(self.path.read_bytes(),original)

    def test_legacy_settings_gain_key_without_losing_other_fields(self):
        initial={'preferences':{'theme':'dark'},'unrecognized_future_field':{'x':1}}
        self.path.write_bytes(json.dumps(initial).encode())
        with patch.object(client,'protect',side_effect=self.clear):key=client.local_key({})
        value=json.loads(self.path.read_bytes());self.assertEqual(value['preferences'],initial['preferences']);self.assertEqual(value['unrecognized_future_field'],initial['unrecognized_future_field']);self.assertEqual(value['local_key'],key)

    def test_existing_key_is_reused_without_rewriting(self):
        initial=json.dumps({'local_key':'local_'+'a'*40,'preferences':{'theme':'light'}}).encode();self.path.write_bytes(initial)
        with patch.object(client,'protect',side_effect=self.clear):key=client.local_key({})
        self.assertEqual(key,'local_'+'a'*40);self.assertEqual(self.path.read_bytes(),initial)

    def test_new_profile_gets_a_key(self):
        with patch.object(client,'protect',side_effect=self.clear):key=client.local_key({})
        self.assertEqual(json.loads(self.path.read_bytes())['local_key'],key)

if __name__=='__main__':unittest.main()
