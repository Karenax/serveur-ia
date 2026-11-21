"""Linux adaptation: encrypted storage, bounded import and the real loopback UI."""
import base64
import json
import io
import os
from pathlib import Path
import struct
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cryptography.fernet import Fernet
import client
import linux_support
import portal_origin_state
import portal_recovery_stdio
import relay_control_stream


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

    def test_receiver_timeout_reports_specific_error_and_releases_profile(self):
        from portal_migration_job import MigrationReceiverUnavailable
        (Path(self.directory.name)/'profile.enc').write_bytes(b'profil fictif');guard=Mock()
        with patch.object(client.sys,'platform','linux'), \
             patch.object(client.sys,'stdin',SimpleNamespace(buffer=io.BytesIO())), \
             patch.dict(os.environ,{'KIARA_TEST_RECOVERY_FULL':'1'}), \
             patch.object(linux_support,'data_home',return_value=Path(self.directory.name)), \
             patch.object(client,'read_profile',return_value=profile()), \
             patch.object(client,'settings_path',return_value=Path(self.directory.name)/('a'*20+'.enc')), \
             patch.object(linux_support,'lock_desktop_profile',return_value=guard), \
             patch.object(relay_control_stream,'RelayControlStream'), \
             patch.object(portal_recovery_stdio,'resolve_port_full',side_effect=MigrationReceiverUnavailable('fictif')), \
             patch.object(client,'open_local_relay') as relay,patch('builtins.print') as printed:
            client.relay_stdio(version='4.0.9')
        relay.assert_not_called();guard.close.assert_called_once()
        self.assertEqual(printed.call_args_list[-1].args,('KIARA_RELAY_RECEIVER_UNAVAILABLE',))

    def test_initial_window_leaves_room_on_720p_desktop(self):
        with patch.object(client.sys, 'platform', 'linux'):
            geometry = client.window_geometry()
        self.assertLessEqual(geometry['width'], 1280)
        self.assertLessEqual(geometry['height'], 672)
        self.assertLessEqual(geometry['min_size'][0], geometry['width'])
        self.assertLessEqual(geometry['min_size'][1], geometry['height'])

    def test_tauri_reuses_the_existing_linux_profile_without_windows_updater(self):
        (Path(self.directory.name) / 'profile.enc').write_bytes(b'profil fictif')
        (Path(self.directory.name) / ('a'*20+'.enc')).write_bytes(b'reglages fictifs existants')
        remote = SimpleNamespace(desktop_update=None, close=Mock())
        server = SimpleNamespace(server_port=48001, chat_launch_url='http://127.0.0.1:48001/chat?launch='+'b'*64,
                                 serve_forever=Mock(), shutdown=Mock(), server_close=Mock())
        stdin = SimpleNamespace(buffer=io.BytesIO(b''))
        guard = Mock()
        with patch.object(client.sys, 'platform', 'linux'), \
             patch.object(client.sys, 'stdin', stdin), \
             patch.dict(os.environ, {'KIARA_DESKTOP_UPDATES': '1'}), \
             patch.object(linux_support, 'data_home', return_value=Path(self.directory.name)), \
             patch.object(linux_support, 'lock_desktop_profile', return_value=guard) as lock_profile, \
             patch.object(client, 'read_profile', return_value=profile()) as read, \
             patch.object(client, 'open_local_relay', return_value=(remote, server)) as open_relay, \
             patch.object(client, 'settings_path', return_value=Path(self.directory.name)/('a'*20+'.enc')), \
             patch.object(portal_origin_state, 'read_origin', return_value=17844), \
             patch('builtins.print') as printed:
            client.relay_stdio(version='4.0.9')
        read.assert_called_once_with()
        lock_profile.assert_called_once_with(profile())
        open_relay.assert_called_once_with(profile(), managed=False, required_port=17844)
        self.assertFalse(remote.managed_relay)
        self.assertIsNone(remote.desktop_update)
        self.assertEqual(printed.call_args_list, [unittest.mock.call('KIARA_RELAY_PROFILE_LOCKED', flush=True),
                         unittest.mock.call(f'KIARA_RELAY_READY {server.chat_launch_url} '+('a'*20), flush=True)])
        remote.close.assert_called_once()
        server.server_close.assert_called_once()
        guard.close.assert_called_once()

    def test_locked_profile_is_rejected_before_loading_history_or_opening_a_server(self):
        (Path(self.directory.name) / 'profile.enc').write_bytes(b'profil fictif')
        with patch.object(client.sys, 'platform', 'linux'), \
             patch.object(linux_support, 'data_home', return_value=Path(self.directory.name)), \
             patch.object(client, 'read_profile', return_value=profile()), \
             patch.object(linux_support, 'lock_desktop_profile', side_effect=linux_support.ProfileAlreadyOpen('busy')), \
             patch.object(client, 'open_local_relay') as open_relay, \
             patch('builtins.print') as printed:
            client.relay_stdio(version='4.0.9')
        open_relay.assert_not_called()
        printed.assert_called_once_with('KIARA_RELAY_PROFILE_IN_USE', flush=True)

    def test_unavailable_lock_is_reported_without_opening_a_server(self):
        (Path(self.directory.name) / 'profile.enc').write_bytes(b'profil fictif')
        with patch.object(client.sys, 'platform', 'linux'), \
             patch.object(linux_support, 'data_home', return_value=Path(self.directory.name)), \
             patch.object(client, 'read_profile', return_value=profile()), \
             patch.object(linux_support, 'lock_desktop_profile', side_effect=linux_support.ProfileLockError('unavailable')), \
             patch.object(client, 'open_local_relay') as open_relay, \
             patch('builtins.print') as printed:
            client.relay_stdio(version='4.0.9')
        open_relay.assert_not_called()
        printed.assert_called_once_with('KIARA_RELAY_PROFILE_LOCK_UNAVAILABLE', flush=True)

    def test_relay_releases_profile_if_server_initialization_fails(self):
        (Path(self.directory.name) / 'profile.enc').write_bytes(b'profil fictif')
        guard = Mock()
        with patch.object(client.sys, 'platform', 'linux'), \
             patch.object(linux_support, 'data_home', return_value=Path(self.directory.name)), \
             patch.object(client, 'read_profile', return_value=profile()), \
             patch.object(portal_origin_state, 'fresh_tauri_storage_absent', return_value=False), \
             patch.object(portal_origin_state, 'read_origin', return_value=17844), \
             patch.object(linux_support, 'lock_desktop_profile', return_value=guard), \
             patch.object(client, 'open_local_relay', side_effect=ValueError('error')), \
             patch('builtins.print'):
            with self.assertRaises(ValueError):client.relay_stdio(version='4.0.9')
        guard.close.assert_called_once()

    def test_recorded_port_is_used_and_invalid_state_never_opens_server(self):
        (Path(self.directory.name) / 'profile.enc').write_bytes(b'profil fictif')
        guard = Mock()
        remote = SimpleNamespace(desktop_update=None, close=Mock())
        server = SimpleNamespace(server_port=17844, chat_launch_url='http://127.0.0.1:17844/chat?launch='+'b'*64,
                                 serve_forever=Mock(), shutdown=Mock(), server_close=Mock())
        stdin = SimpleNamespace(buffer=io.BytesIO(b''))
        with patch.object(client.sys, 'platform', 'linux'), \
             patch.object(client.sys, 'stdin', stdin), \
             patch.object(linux_support, 'data_home', return_value=Path(self.directory.name)), \
             patch.object(client, 'read_profile', return_value=profile()), \
             patch.object(linux_support, 'lock_desktop_profile', return_value=guard), \
             patch.object(client, 'settings_path', return_value=Path(self.directory.name)/('a'*20+'.enc')), \
             patch.object(portal_origin_state, 'read_origin', return_value=17844) as read_origin, \
             patch.object(client, 'open_local_relay', return_value=(remote,server)) as open_relay, \
             patch('builtins.print'):
            client.relay_stdio(version='4.0.9')
        read_origin.assert_called_once_with(Path(self.directory.name)/(('a'*20)+'.tauri-origin.json'))
        open_relay.assert_called_once_with(profile(), managed=False, required_port=17844)
        guard.close.assert_called_once()

        guard = Mock()
        with patch.object(client.sys, 'platform', 'linux'), \
             patch.object(linux_support, 'data_home', return_value=Path(self.directory.name)), \
             patch.object(client, 'read_profile', return_value=profile()), \
             patch.object(linux_support, 'lock_desktop_profile', return_value=guard), \
             patch.object(client, 'settings_path', return_value=Path(self.directory.name)/('a'*20+'.enc')), \
             patch.object(portal_origin_state, 'read_origin', side_effect=portal_origin_state.OriginStateError('invalid')), \
             patch.object(client, 'open_local_relay') as open_relay, \
             patch('builtins.print') as printed:
            client.relay_stdio(version='4.0.9')
        open_relay.assert_not_called()
        self.assertEqual(printed.call_args_list[-1].args, ('KIARA_RELAY_ORIGIN_INVALID',))
        guard.close.assert_called_once()

    def test_occupied_recorded_port_is_reported_without_fallback(self):
        (Path(self.directory.name) / 'profile.enc').write_bytes(b'profil fictif')
        guard = Mock()
        with patch.object(client.sys, 'platform', 'linux'), \
             patch.object(linux_support, 'data_home', return_value=Path(self.directory.name)), \
             patch.object(client, 'read_profile', return_value=profile()), \
             patch.object(linux_support, 'lock_desktop_profile', return_value=guard), \
             patch.object(client, 'settings_path', return_value=Path(self.directory.name)/('a'*20+'.enc')), \
             patch.object(portal_origin_state, 'read_origin', return_value=17844), \
             patch.object(client, 'open_local_relay', side_effect=client.LocalOriginPortUnavailable('busy')) as open_relay, \
             patch('builtins.print') as printed:
            client.relay_stdio(version='4.0.9')
        open_relay.assert_called_once_with(profile(), managed=False, required_port=17844)
        self.assertEqual(printed.call_args_list[-1].args, ('KIARA_RELAY_ORIGIN_BUSY',))
        guard.close.assert_called_once()

    def test_unreadable_settings_are_reported_and_profile_is_released(self):
        (Path(self.directory.name) / 'profile.enc').write_bytes(b'profil fictif')
        (Path(self.directory.name) / ('a'*20+'.enc')).write_bytes(b'reglages fictifs illisibles')
        guard = Mock()
        with patch.object(client.sys, 'platform', 'linux'), \
             patch.object(linux_support, 'data_home', return_value=Path(self.directory.name)), \
             patch.object(client, 'read_profile', return_value=profile()), \
             patch.object(linux_support, 'lock_desktop_profile', return_value=guard), \
             patch.object(client, 'settings_path', return_value=Path(self.directory.name)/('a'*20+'.enc')), \
             patch.object(portal_origin_state, 'read_origin', return_value=17844), \
             patch.object(client, 'open_local_relay', side_effect=client.LocalSettingsUnreadable('illisible')), \
             patch('builtins.print') as printed:
            client.relay_stdio(version='4.0.9')
        self.assertEqual(printed.call_args_list, [unittest.mock.call('KIARA_RELAY_PROFILE_LOCKED', flush=True),
                         unittest.mock.call('KIARA_RELAY_SETTINGS_UNREADABLE', flush=True)])
        guard.close.assert_called_once()

    def test_opt_in_recovery_keeps_control_stream_until_relay_stops(self):
        (Path(self.directory.name) / 'profile.enc').write_bytes(b'profil fictif')
        guard=Mock();control=Mock()
        remote=SimpleNamespace(desktop_update=None,close=Mock())
        server=SimpleNamespace(server_port=17844,chat_launch_url='http://127.0.0.1:17844/chat?launch='+'b'*64,
                               serve_forever=Mock(),shutdown=Mock(),server_close=Mock())
        with patch.object(client.sys,'platform','linux'), \
             patch.object(client.sys,'stdin',SimpleNamespace(buffer=io.BytesIO())), \
             patch.dict(os.environ,{'KIARA_TEST_RECOVERY':'1'}), \
             patch.object(linux_support,'data_home',return_value=Path(self.directory.name)), \
             patch.object(client,'read_profile',return_value=profile()), \
             patch.object(client,'settings_path',return_value=Path(self.directory.name)/('a'*20+'.enc')), \
             patch.object(linux_support,'lock_desktop_profile',return_value=guard), \
             patch.object(relay_control_stream,'RelayControlStream',return_value=control), \
             patch.object(portal_recovery_stdio,'recovery_assets',return_value={}), \
             patch.object(portal_recovery_stdio,'resolve_port',return_value=17844) as resolve, \
             patch.object(client,'open_local_relay',return_value=(remote,server)) as open_relay, \
             patch('builtins.print'):
            client.relay_stdio(version='4.0.9')
        resolve.assert_called_once_with(profile(),control,client.sys.stdout,{})
        open_relay.assert_called_once_with(profile(),managed=False,required_port=17844)
        control.read.assert_called_once_with(1);guard.close.assert_called_once()

    def test_opt_in_recovery_refuses_unknown_qt_storage_before_server(self):
        (Path(self.directory.name) / 'profile.enc').write_bytes(b'profil fictif')
        guard=Mock()
        with patch.object(client.sys,'platform','linux'), \
             patch.object(client.sys,'stdin',SimpleNamespace(buffer=io.BytesIO())), \
             patch.dict(os.environ,{'KIARA_TEST_RECOVERY':'1'}), \
             patch.object(linux_support,'data_home',return_value=Path(self.directory.name)), \
             patch.object(client,'read_profile',return_value=profile()), \
             patch.object(client,'settings_path',return_value=Path(self.directory.name)/('a'*20+'.enc')), \
             patch.object(linux_support,'lock_desktop_profile',return_value=guard), \
             patch.object(relay_control_stream,'RelayControlStream'), \
             patch.object(portal_recovery_stdio,'recovery_assets',return_value={}), \
             patch.object(portal_recovery_stdio,'resolve_port',side_effect=portal_recovery_stdio.QtLegacyStoragePresent()), \
             patch.object(client,'open_local_relay') as open_relay,patch('builtins.print') as printed:
            client.relay_stdio(version='4.0.9')
        open_relay.assert_not_called()
        self.assertEqual(printed.call_args_list[-1].args,('KIARA_RELAY_QT_STORAGE',))
        guard.close.assert_called_once()

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
                browser=urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
                with browser.open(server.chat_launch_url) as response:
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
