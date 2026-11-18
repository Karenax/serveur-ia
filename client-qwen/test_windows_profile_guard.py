"""Windows profile mutex tests use only temporary fictional paths."""
import os
import io
import ctypes
from ctypes import wintypes
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import client
import windows_profile_guard
import portal_origin_state
import portal_recovery_stdio
import relay_control_stream
from windows_profile_guard import ProfileAlreadyOpen, lock_desktop_profile


@unittest.skipUnless(os.name == 'nt', 'Verrou Windows : testé sur Windows.')
class WindowsProfileGuardTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.target = self.root/'fiction.dpapi'

    def child(self):
        code = ("import sys;from windows_profile_guard import lock_desktop_profile;"
                "g=lock_desktop_profile(sys.argv[1]);print('held',flush=True);"
                "sys.stdin.readline();g.close()")
        process = subprocess.Popen([sys.executable,'-c',code,str(self.target)],stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                                   creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        def cleanup():
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream:
                    stream.close()
        self.addCleanup(cleanup)
        self.assertEqual(process.stdout.readline().strip(),'held')
        return process

    def test_other_process_is_refused_but_another_profile_can_open(self):
        child=self.child()
        with self.assertRaises(ProfileAlreadyOpen):lock_desktop_profile(self.target)
        with lock_desktop_profile(self.root/'other.dpapi'):pass
        child.stdin.write('close\n');child.stdin.flush()
        self.assertEqual(child.wait(timeout=10),0)
        with lock_desktop_profile(self.target):pass

    def test_abandoned_guard_is_released_after_process_termination(self):
        child=self.child();child.terminate();child.wait(timeout=10)
        guard=lock_desktop_profile(self.target);guard.close();guard.close()

    def test_path_case_does_not_create_a_second_guard(self):
        child=self.child()
        with self.assertRaises(ProfileAlreadyOpen):lock_desktop_profile(str(self.target).upper())
        child.stdin.write('close\n');child.stdin.flush();self.assertEqual(child.wait(timeout=10),0)

    def test_existing_webview_lock_is_detected_without_modifying_it(self):
        directory=self.root/'webview-fiction'/'EBWebView'
        directory.mkdir(parents=True)
        path=directory/'lockfile';path.write_bytes('témoin fictif'.encode('utf-8'))
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
        kernel.CreateFileW.restype=wintypes.HANDLE
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=kernel.CreateFileW(str(path),0x80000000,0,None,3,0x80,None)
        self.assertNotEqual(handle,ctypes.c_void_p(-1).value)
        try:
            with self.assertRaises(ProfileAlreadyOpen):lock_desktop_profile(self.target)
        finally:
            kernel.CloseHandle(handle)
        self.assertEqual(path.read_bytes(),'témoin fictif'.encode('utf-8'))
        with lock_desktop_profile(self.target):pass

    def test_relay_refuses_locked_profile_before_loading_local_services(self):
        profile={'url':'https://example.test','token':'fiction'}
        with patch.object(client,'read_relay_profile',return_value=profile), \
             patch.object(client,'settings_path',return_value=self.target), \
             patch.object(windows_profile_guard,'lock_desktop_profile',side_effect=ProfileAlreadyOpen('busy')), \
             patch.object(client,'open_local_relay') as relay, \
             patch('builtins.print') as printed:
            client.relay_stdio(version='4.0.9')
        relay.assert_not_called()
        printed.assert_called_once_with('KIARA_RELAY_PROFILE_IN_USE',flush=True)

    def test_relay_announces_and_releases_guard_after_server_closes(self):
        profile={'url':'https://example.test','token':'fiction'}
        guard=Mock();remote=SimpleNamespace(desktop_update=None,close=Mock())
        server=SimpleNamespace(server_port=48001,serve_forever=Mock(),shutdown=Mock(),server_close=Mock())
        stdin=SimpleNamespace(buffer=io.BytesIO(b''))
        with patch.object(client,'read_relay_profile',return_value=profile), \
             patch.object(client,'settings_path',return_value=self.target), \
             patch.object(client.sys,'stdin',stdin), \
             patch.dict(os.environ,{'KIARA_DESKTOP_UPDATES':'0'}), \
             patch.object(windows_profile_guard,'lock_desktop_profile',return_value=guard), \
             patch.object(portal_origin_state,'read_origin',return_value=17844), \
             patch.object(client,'open_local_relay',return_value=(remote,server)), \
             patch('builtins.print') as printed:
            client.relay_stdio(version='4.0.9')
        self.assertEqual(printed.call_args_list[0].args,('KIARA_RELAY_PROFILE_LOCKED',))
        self.assertTrue(printed.call_args_list[1].args[0].startswith('KIARA_RELAY_READY '))
        server.server_close.assert_called_once()
        remote.close.assert_called_once()
        guard.close.assert_called_once()

    def test_recorded_origin_is_pinned_and_busy_origin_does_not_fallback(self):
        profile={'url':'https://example.test','token':'fiction'}
        guard=Mock()
        with patch.object(client,'read_relay_profile',return_value=profile), \
             patch.object(client,'settings_path',return_value=self.target), \
             patch.object(windows_profile_guard,'lock_desktop_profile',return_value=guard), \
             patch.object(portal_origin_state,'read_origin',return_value=17844), \
             patch.object(client,'open_local_relay',side_effect=client.LocalOriginPortUnavailable('busy')) as relay, \
             patch('builtins.print') as printed:
            client.relay_stdio(version='4.0.9')
        relay.assert_called_once_with(profile,managed=True,required_port=17844)
        self.assertEqual(printed.call_args_list[-1].args,('KIARA_RELAY_ORIGIN_BUSY',))
        guard.close.assert_called_once()

    def test_unreadable_settings_are_reported_and_profile_is_released(self):
        profile={'url':'https://example.test','token':'fiction'}
        guard=Mock()
        with patch.object(client,'read_relay_profile',return_value=profile), \
             patch.object(client,'settings_path',return_value=self.target), \
             patch.object(windows_profile_guard,'lock_desktop_profile',return_value=guard), \
             patch.object(portal_origin_state,'read_origin',return_value=17844), \
             patch.object(client,'open_local_relay',side_effect=client.LocalSettingsUnreadable('illisible')), \
             patch('builtins.print') as printed:
            client.relay_stdio(version='4.0.9')
        self.assertEqual(printed.call_args_list,[unittest.mock.call('KIARA_RELAY_PROFILE_LOCKED',flush=True),
                         unittest.mock.call('KIARA_RELAY_SETTINGS_UNREADABLE',flush=True)])
        guard.close.assert_called_once()

    def test_opt_in_recovery_passes_verified_origin_to_relay(self):
        profile={'url':'https://example.test','token':'fiction'}
        guard=Mock();control=Mock();remote=SimpleNamespace(desktop_update=None,close=Mock())
        server=SimpleNamespace(server_port=17844,serve_forever=Mock(),shutdown=Mock(),server_close=Mock())
        with patch.object(client,'read_relay_profile',return_value=profile), \
             patch.object(client,'settings_path',return_value=self.target), \
             patch.object(client.sys,'stdin',SimpleNamespace(buffer=io.BytesIO())), \
             patch.dict(os.environ,{'KIARA_TEST_RECOVERY':'1','KIARA_DESKTOP_UPDATES':'0'}), \
             patch.object(windows_profile_guard,'lock_desktop_profile',return_value=guard), \
             patch.object(relay_control_stream,'RelayControlStream',return_value=control), \
             patch.object(portal_recovery_stdio,'recovery_assets',return_value={}), \
             patch.object(portal_recovery_stdio,'resolve_port',return_value=17844), \
             patch.object(client,'open_local_relay',return_value=(remote,server)) as relay, \
             patch('builtins.print'):
            client.relay_stdio(version='4.0.9')
        relay.assert_called_once_with(profile,managed=True,required_port=17844)
        control.read.assert_called_once_with(1);guard.close.assert_called_once()

    def test_receiver_timeout_reports_specific_error_and_releases_profile(self):
        from portal_migration_job import MigrationReceiverUnavailable
        profile={'url':'https://example.test','token':'fiction'};guard=Mock()
        with patch.object(client,'read_relay_profile',return_value=profile), \
             patch.object(client,'settings_path',return_value=self.target), \
             patch.object(client.sys,'stdin',SimpleNamespace(buffer=io.BytesIO())), \
             patch.dict(os.environ,{'KIARA_TEST_RECOVERY_FULL':'1','KIARA_DESKTOP_UPDATES':'0'}), \
             patch.object(windows_profile_guard,'lock_desktop_profile',return_value=guard), \
             patch.object(relay_control_stream,'RelayControlStream'), \
             patch.object(portal_recovery_stdio,'resolve_port_full',side_effect=MigrationReceiverUnavailable('fictif')), \
             patch.object(client,'open_local_relay') as relay,patch('builtins.print') as printed:
            client.relay_stdio(version='4.0.9')
        relay.assert_not_called();guard.close.assert_called_once()
        self.assertEqual(printed.call_args_list[-1].args,('KIARA_RELAY_RECEIVER_UNAVAILABLE',))

    def test_desktop_refuses_locked_profile_before_opening_local_services(self):
        profile={'url':'https://example.test','token':'fiction'}
        root=Mock()
        with patch.object(client.sys,'argv',['client']), \
             patch.dict(sys.modules,{'webview':Mock()}), \
             patch.object(client,'read_profile',return_value=profile), \
             patch.object(client,'settings_path',return_value=self.target), \
             patch.object(windows_profile_guard,'lock_desktop_profile',side_effect=ProfileAlreadyOpen('Profil déjà ouvert.')), \
             patch.object(client,'open_local_relay') as relay, \
             patch.object(client.tk,'Tk',return_value=root), \
             patch.object(client.messagebox,'showerror') as error:
            client.main()
        relay.assert_not_called()
        error.assert_called_once_with(client.APP_NAME,'Profil déjà ouvert.',parent=root)

if __name__ == '__main__':unittest.main()
