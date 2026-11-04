"""Linux adaptation: encrypted storage, bounded import and the real loopback UI."""
import base64
import json
import os
from pathlib import Path
import struct
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from cryptography.fernet import Fernet
import client
import linux_support


def profile():
    key=base64.b64encode(bytes(range(32))).decode()
    return {'url':'wireguard://10.77.0.1:8766','transport':'wireguard',
            'token':'qwen_'+'0'*16+'_'+'x'*43,'protocol':4,
            'wireguard':{'private_key':key,'server_public_key':key,'preshared_key':key,
                         'address':'10.77.0.2/32','endpoint':'example.test:51820'}}


class LinuxSupportTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        environment=patch.dict(os.environ,{'XDG_DATA_HOME':self.directory.name})
        environment.start();self.addCleanup(environment.stop)

    def test_import_reads_footer_without_executing_and_rejects_truncation(self):
        path=Path(self.directory.name)/'personal.exe'
        raw=json.dumps(profile()).encode()
        path.write_bytes(b'MZ-not-executable'+raw+struct.pack('<I',len(raw))+b'QWENPROFILE1')
        self.assertEqual(linux_support.import_profile(path),profile())
        for content in (b'',b'0'*16,b'0'+struct.pack('<I',65537)+b'QWENPROFILE1',
                        b'0'+struct.pack('<I',50)+b'QWENPROFILE1'):
            path.write_bytes(content)
            with self.assertRaises(ValueError):linux_support.import_profile(path)

    def test_cipher_roundtrip_and_corruption_preserves_original(self):
        cipher=Fernet(Fernet.generate_key())
        with patch.object(linux_support,'cipher',return_value=cipher):
            encrypted=linux_support.protect('Brouillon privé')
            self.assertNotIn(b'Brouillon',encrypted)
            self.assertEqual(linux_support.protect(encrypted,decrypt=True),'Brouillon privé'.encode())
            with self.assertRaisesRegex(ValueError,'original est conservé'):
                linux_support.protect(encrypted[:-3]+b'bad',decrypt=True)

    def test_distinct_accesses_have_distinct_xdg_settings(self):
        first=linux_support.settings_path(profile())
        other={**profile(),'token':'qwen_'+'1'*16+'_'+'x'*43}
        self.assertNotEqual(first,linux_support.settings_path(other))
        self.assertEqual(first.parent,Path(self.directory.name)/'kiara')
        with patch.dict(os.environ,{'XDG_DATA_HOME':'relative'}):
            with self.assertRaises(ValueError):linux_support.data_home()

    def test_missing_key_never_replaces_existing_encrypted_data(self):
        from unittest.mock import Mock
        backend=Mock();backend.get_password.return_value=None
        path=linux_support.data_home()/'profile.enc';path.write_bytes(b'original')
        with self.assertRaisesRegex(RuntimeError,'Restaurez votre trousseau'):
            linux_support._cipher_with_backend(backend)
        backend.set_password.assert_not_called()
        self.assertEqual(path.read_bytes(),b'original')

    def test_first_key_is_saved_in_keyring_and_reused(self):
        from unittest.mock import Mock
        backend=Mock();backend.get_password.return_value=None
        first=linux_support._cipher_with_backend(backend)
        key=backend.set_password.call_args.args[2]
        backend.get_password.return_value=key
        second=linux_support._cipher_with_backend(backend)
        self.assertEqual(second.decrypt(first.encrypt(b'private draft')),b'private draft')
        self.assertEqual(backend.set_password.call_count,1)

    def test_linux_updates_never_request_windows_release(self):
        remote=client.Remote(profile(),opener=object())
        with patch.object(client.sys,'platform','linux'),patch.object(remote,'open',side_effect=AssertionError('Windows update requested')):
            self.assertFalse(remote.update(True)['available'])
            self.assertIn('paquet Linux',remote.update(False)['message'])

    def test_local_max_cannot_install_windows_components_but_capture_is_enabled(self):
        from conversation_service import ConversationService,DictationService
        services=linux_support.services()
        self.assertIsInstance(services[1],DictationService)
        self.assertIsInstance(services[2],ConversationService)
        self.assertEqual(services[2].cache,Path(self.directory.name)/'kiara/voice/asr')
        for service in (services[0],services[4]):
            self.assertFalse(service.status()['available'])
            self.assertTrue(service.status()['microphone_closed'])
            with self.assertRaisesRegex(ValueError,'serveur Kiara ou Low'):service.install({})

    def test_real_linux_loopback_serves_ui_and_rejects_unauthorized_calls(self):
        remote=client.Remote(profile(),opener=object())
        with patch.object(client.sys,'platform','linux'):
            server=client.serve_local(remote,'test-local-key',0)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            url=f'http://127.0.0.1:{server.server_port}'
            try:
                with urllib.request.urlopen(url+'/chat') as response:
                    html=response.read().decode()
                    self.assertIn("button.id='voice-start'",html)
                    self.assertIn("button.id='conversation-start'",html)
                    self.assertIn('"platform": "linux"',html)
                    self.assertIn("script-src 'nonce-",response.headers['Content-Security-Policy'])
                with self.assertRaises(urllib.error.HTTPError) as failure:
                    urllib.request.urlopen(url+'/client/voice')
                self.assertEqual(failure.exception.code,401)
                call=urllib.request.Request(url+'/client/voice',headers={'Authorization':'Bearer test-local-key'})
                with urllib.request.urlopen(call) as response:
                    status=json.load(response)
                    self.assertEqual(status['model'],'Parakeet v3')
                    self.assertGreater(status['model_bytes'],600000000)
                    self.assertFalse(status['aec_supported'])
                call=urllib.request.Request(url+'/client/voice',data=b'{"action":"start"}',
                    headers={'Authorization':'Bearer test-local-key','Content-Type':'application/json'})
                with self.assertRaises(urllib.error.HTTPError) as failure:
                    urllib.request.urlopen(call)
                self.assertEqual(failure.exception.code,400)
            finally:
                server.shutdown();server.server_close();thread.join(5)


if __name__=='__main__':unittest.main(verbosity=2)
