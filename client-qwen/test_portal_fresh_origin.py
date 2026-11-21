"""First-origin safety on fictional profiles; never open a real browser profile."""
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import ExitStack
import errno
from types import SimpleNamespace
from unittest.mock import Mock, patch

import client
import history_store
import portal_origin_state
from portal_origin_state import fresh_tauri_storage_absent, read_origin


class FreshOriginTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.settings=self.root/'QwenClient'/('a'*20+'.dpapi')
        self.settings.parent.mkdir()
        self.profile={'url':'https://fiction.example','token':'fiction'}
        self.guard=Mock()
        self.remote=SimpleNamespace(desktop_update=None,close=Mock())
        self.server=SimpleNamespace(server_port=17842,chat_launch_url='http://127.0.0.1:17842/chat?launch='+'b'*64,
                                    serve_forever=Mock(),shutdown=Mock(),server_close=Mock())

    def test_unknown_or_existing_state_is_not_fresh(self):
        for linux in (False,True):
            view=self.settings.parent/(('tauri-webview-' if linux else 'webview-')+self.settings.stem)
            self.assertTrue(fresh_tauri_storage_absent(self.settings,linux=linux))
            for path in (self.settings,view,self.settings.with_suffix('.tauri-migration')):
                path.write_bytes(b'fiction')
                self.assertFalse(fresh_tauri_storage_absent(self.settings,linux=linux))
                self.assertEqual(path.read_bytes(),b'fiction');path.unlink()
            self.settings.write_bytes(b'initialise')
            self.assertTrue(fresh_tauri_storage_absent(self.settings,linux=linux,include_settings=False))
            self.settings.unlink()
        with patch.object(Path,'lstat',side_effect=PermissionError('indisponible')):
            self.assertFalse(fresh_tauri_storage_absent(self.settings,linux=True))
        self.assertFalse(fresh_tauri_storage_absent(self.settings.with_name('unknown.dpapi'),linux=False))

    def contexts(self, stack):
        stack.enter_context(patch.object(client,'settings_path',return_value=self.settings))
        stack.enter_context(patch.object(client.sys,'stdin',SimpleNamespace(buffer=io.BytesIO())))
        stack.enter_context(patch.dict(os.environ,{'KIARA_DESKTOP_UPDATES':'0','LOCALAPPDATA':str(self.root)}))
        for name in ('KIARA_TEST_RECOVERY','KIARA_TEST_RECOVERY_FULL'):
            os.environ.pop(name,None)
        stack.enter_context(patch('builtins.print'))

    def reserve(self, settings, *, linux):
        return portal_origin_state.record_origin(settings.with_suffix('.tauri-origin.json'),17842)

    @unittest.skipUnless(sys.platform.startswith('linux'),'Recette Linux')
    def test_linux_new_profile_records_port_before_ready_and_refuses_fallback(self):
        import linux_support
        profile_file=self.root/'profile.enc'
        def create_profile():
            profile_file.write_bytes(b'profil fictif');return self.profile
        def open_first(*_args,**kwargs):
            self.assertEqual(kwargs.get('required_port'),17842)
            self.assertEqual(read_origin(self.settings.with_suffix('.tauri-origin.json')),17842)
            self.settings.write_bytes(b'reglages fictifs');return self.remote,self.server
        with ExitStack() as stack:
            self.contexts(stack)
            stack.enter_context(patch.object(linux_support,'data_home',return_value=self.root))
            stack.enter_context(patch.object(linux_support,'lock_desktop_profile',return_value=self.guard))
            stack.enter_context(patch.object(client,'read_profile',side_effect=create_profile))
            stack.enter_context(patch.object(portal_origin_state,'reserve_fresh_origin',side_effect=self.reserve))
            stack.enter_context(patch.object(client,'open_local_relay',side_effect=open_first))
            client.relay_stdio(version='4.0.9')
        marker=self.settings.with_suffix('.tauri-origin.json')
        self.assertEqual(read_origin(marker),17842)
        self.assertEqual(self.settings.read_bytes(),b'reglages fictifs')
        self.server.server_close.assert_called_once();self.guard.close.assert_called_once()
        with ExitStack() as stack:
            self.contexts(stack)
            stack.enter_context(patch.object(linux_support,'data_home',return_value=self.root))
            stack.enter_context(patch.object(linux_support,'lock_desktop_profile',return_value=self.guard))
            stack.enter_context(patch.object(client,'read_profile',return_value=self.profile))
            opened=stack.enter_context(patch.object(client,'open_local_relay',side_effect=client.LocalOriginPortUnavailable('occupé')))
            printed=stack.enter_context(patch('builtins.print'))
            client.relay_stdio(version='4.0.9')
        opened.assert_called_once_with(self.profile,managed=False,required_port=17842)
        self.assertEqual(printed.call_args_list[-1].args,('KIARA_RELAY_ORIGIN_BUSY',))
        self.assertEqual(read_origin(marker),17842)

    @unittest.skipUnless(os.name=='nt','Recette Windows')
    def test_windows_new_profile_records_port_before_ready_and_refuses_fallback(self):
        import windows_profile_guard
        def open_first(*_args,**kwargs):
            self.assertEqual(kwargs.get('required_port'),17842)
            self.assertEqual(read_origin(self.settings.with_suffix('.tauri-origin.json')),17842)
            self.settings.write_bytes(b'reglages fictifs');return self.remote,self.server
        with ExitStack() as stack:
            self.contexts(stack)
            stack.enter_context(patch.object(windows_profile_guard,'lock_desktop_profile',return_value=self.guard))
            stack.enter_context(patch.object(client,'read_profile',return_value=self.profile))
            stack.enter_context(patch.object(client,'relay_profile_path',return_value=self.root/'tauri-profile.dpapi'))
            stack.enter_context(patch.object(client,'protect',return_value=b'profil chiffre fictif'))
            stack.enter_context(patch.object(history_store,'atomic'))
            stack.enter_context(patch.object(portal_origin_state,'reserve_fresh_origin',side_effect=self.reserve))
            stack.enter_context(patch.object(client,'open_local_relay',side_effect=open_first))
            client.relay_stdio(executable='fiction.exe',version='4.0.9')
        marker=self.settings.with_suffix('.tauri-origin.json')
        self.assertEqual(read_origin(marker),17842)
        self.server.server_close.assert_called_once();self.guard.close.assert_called_once()
        with ExitStack() as stack:
            self.contexts(stack)
            stack.enter_context(patch.object(windows_profile_guard,'lock_desktop_profile',return_value=self.guard))
            stack.enter_context(patch.object(client,'read_relay_profile',return_value=self.profile))
            opened=stack.enter_context(patch.object(client,'open_local_relay',side_effect=client.LocalOriginPortUnavailable('occupé')))
            printed=stack.enter_context(patch('builtins.print'))
            client.relay_stdio(version='4.0.9')
        opened.assert_called_once_with(self.profile,managed=True,required_port=17842)
        self.assertEqual(printed.call_args_list[-1].args,('KIARA_RELAY_ORIGIN_BUSY',))
        self.assertEqual(read_origin(marker),17842)

    @unittest.skipUnless(sys.platform.startswith('linux'),'Recette Linux')
    def test_marker_failure_closes_server_before_any_ready_message(self):
        import linux_support
        def create_profile():
            (self.root/'profile.enc').write_bytes(b'profil fictif');return self.profile
        def open_first(*_args,**_kwargs):
            self.settings.write_bytes(b'reglages fictifs');return self.remote,self.server
        with ExitStack() as stack:
            self.contexts(stack)
            stack.enter_context(patch.object(linux_support,'data_home',return_value=self.root))
            stack.enter_context(patch.object(linux_support,'lock_desktop_profile',return_value=self.guard))
            stack.enter_context(patch.object(client,'read_profile',side_effect=create_profile))
            opened=stack.enter_context(patch.object(client,'open_local_relay',side_effect=open_first))
            stack.enter_context(patch.object(portal_origin_state,'reserve_fresh_origin',side_effect=portal_origin_state.OriginStateError('fictif')))
            printed=stack.enter_context(patch('builtins.print'))
            client.relay_stdio(version='4.0.9')
        self.assertEqual(printed.call_args_list[-1].args,('KIARA_RELAY_ORIGIN_INVALID',))
        self.assertFalse(any('KIARA_RELAY_READY' in call.args[0] for call in printed.call_args_list))
        opened.assert_not_called();self.server.serve_forever.assert_not_called();self.guard.close.assert_called_once()
        self.assertFalse(self.settings.with_suffix('.tauri-origin.json').exists())

    @unittest.skipUnless(sys.platform.startswith('linux'),'Recette Linux')
    def test_storage_appearing_during_port_reservation_blocks_marker_and_startup(self):
        import linux_support
        view=self.settings.parent/('tauri-webview-'+self.settings.stem)
        def create_profile():
            (self.root/'profile.enc').write_bytes(b'profil fictif');return self.profile
        reservation=Mock()
        def bind(_address):view.mkdir();(view/'sentinel').write_bytes(b'conserver')
        reservation.bind.side_effect=bind
        reservation.__enter__=Mock(return_value=reservation);reservation.__exit__=Mock(return_value=False)
        with ExitStack() as stack:
            self.contexts(stack)
            stack.enter_context(patch.object(linux_support,'data_home',return_value=self.root))
            stack.enter_context(patch.object(linux_support,'lock_desktop_profile',return_value=self.guard))
            stack.enter_context(patch.object(client,'read_profile',side_effect=create_profile))
            opened=stack.enter_context(patch.object(client,'open_local_relay'))
            stack.enter_context(patch.object(portal_origin_state.socket,'socket',return_value=reservation))
            printed=stack.enter_context(patch('builtins.print'))
            client.relay_stdio(version='4.0.9')
        self.assertEqual(printed.call_args_list[-1].args,('KIARA_RELAY_ORIGIN_INVALID',))
        self.assertFalse(self.settings.with_suffix('.tauri-origin.json').exists())
        self.assertEqual((view/'sentinel').read_bytes(),b'conserver')
        opened.assert_not_called();self.server.serve_forever.assert_not_called()

    def test_reservation_selects_next_port_and_keeps_it_when_binding_later_fails(self):
        first=Mock();second=Mock()
        for item in (first,second):
            item.__enter__=Mock(return_value=item);item.__exit__=Mock(return_value=False)
        first.bind.side_effect=OSError(errno.EADDRINUSE,'fictif')
        with patch.object(portal_origin_state.socket,'socket',side_effect=[first,second]):
            port=portal_origin_state.reserve_fresh_origin(self.settings,linux=True,ports=(17841,17842))
        self.assertEqual(port,17842);self.assertEqual(read_origin(self.settings.with_suffix('.tauri-origin.json')),17842)
        first.bind.assert_called_once_with(('127.0.0.1',17841));second.bind.assert_called_once_with(('127.0.0.1',17842))

    def test_reservation_error_never_writes_a_port(self):
        with patch.object(portal_origin_state.socket,'socket',side_effect=OSError('indisponible')):
            with self.assertRaises(portal_origin_state.OriginStateError):
                portal_origin_state.reserve_fresh_origin(self.settings,linux=True,ports=(17841,))
        self.assertFalse(self.settings.with_suffix('.tauri-origin.json').exists())

    def test_windows_exclusive_port_access_error_tries_the_next_port(self):
        first=Mock();second=Mock()
        for item in (first,second):
            item.__enter__=Mock(return_value=item);item.__exit__=Mock(return_value=False)
        error=OSError('port utilisé exclusivement');error.winerror=10013
        first.bind.side_effect=error
        with patch.object(portal_origin_state.socket,'socket',side_effect=[first,second]):
            port=portal_origin_state.reserve_fresh_origin(self.settings,linux=False,ports=(17841,17842))
        self.assertEqual(port,17842);self.assertEqual(read_origin(self.settings.with_suffix('.tauri-origin.json')),17842)

    @unittest.skipUnless(sys.platform.startswith('linux'),'Recette Linux')
    def test_failure_after_recording_keeps_port_for_next_launch(self):
        import linux_support
        def create_profile():
            (self.root/'profile.enc').write_bytes(b'profil fictif');return self.profile
        with ExitStack() as stack:
            self.contexts(stack)
            stack.enter_context(patch.object(linux_support,'data_home',return_value=self.root))
            stack.enter_context(patch.object(linux_support,'lock_desktop_profile',return_value=self.guard))
            stack.enter_context(patch.object(client,'read_profile',side_effect=create_profile))
            stack.enter_context(patch.object(portal_origin_state,'reserve_fresh_origin',side_effect=self.reserve))
            stack.enter_context(patch.object(client,'open_local_relay',side_effect=client.LocalOriginPortUnavailable('occupé')))
            client.relay_stdio(version='4.0.9')
        marker=self.settings.with_suffix('.tauri-origin.json')
        self.assertEqual(read_origin(marker),17842)
        with ExitStack() as stack:
            self.contexts(stack)
            stack.enter_context(patch.object(linux_support,'data_home',return_value=self.root))
            stack.enter_context(patch.object(linux_support,'lock_desktop_profile',return_value=self.guard))
            stack.enter_context(patch.object(client,'read_profile',return_value=self.profile))
            no_reservation=stack.enter_context(patch.object(portal_origin_state,'reserve_fresh_origin'))
            opened=stack.enter_context(patch.object(client,'open_local_relay',side_effect=client.LocalOriginPortUnavailable('occupé')))
            client.relay_stdio(version='4.0.9')
        no_reservation.assert_not_called();opened.assert_called_once_with(self.profile,managed=False,required_port=17842)
        self.assertEqual(read_origin(marker),17842)

    @unittest.skipUnless(sys.platform.startswith('linux'),'Recette Linux')
    def test_import_does_not_pin_a_profile_with_existing_tauri_storage(self):
        import linux_support
        import portal_origin_session
        import portal_recovery_stdio
        import relay_control_stream
        view=self.settings.parent/('tauri-webview-'+self.settings.stem);view.mkdir()
        (view/'sentinel').write_bytes(b'conserver')
        def create_profile():
            (self.root/'profile.enc').write_bytes(b'profil fictif');return self.profile
        with ExitStack() as stack:
            self.contexts(stack)
            stack.enter_context(patch.object(linux_support,'data_home',return_value=self.root))
            stack.enter_context(patch.object(linux_support,'lock_desktop_profile',return_value=self.guard))
            stack.enter_context(patch.object(client,'read_profile',side_effect=create_profile))
            stack.enter_context(patch.object(client,'portal_recovery_fixed_port',return_value=None))
            stack.enter_context(patch.object(portal_recovery_stdio,'recovery_assets',return_value={}))
            stack.enter_context(patch.object(relay_control_stream,'RelayControlStream'))
            stack.enter_context(patch.object(portal_origin_session,'resolve_origin',side_effect=portal_origin_session.OriginNeedsRecovery('fictif')))
            opened=stack.enter_context(patch.object(client,'open_local_relay'))
            client.relay_stdio(version='4.0.9')
        opened.assert_not_called()
        self.assertFalse(self.settings.with_suffix('.tauri-origin.json').exists())
        self.assertEqual((view/'sentinel').read_bytes(),b'conserver')

    @unittest.skipUnless(sys.platform.startswith('linux'),'Recette Linux')
    def test_inaccessible_profile_is_not_assumed_to_be_new(self):
        import linux_support
        original=Path.lstat
        def lstat(path):
            if path==self.root/'profile.enc':raise PermissionError('profil inaccessible')
            return original(path)
        with ExitStack() as stack:
            self.contexts(stack)
            stack.enter_context(patch.object(Path,'lstat',lstat))
            stack.enter_context(patch.object(linux_support,'data_home',return_value=self.root))
            stack.enter_context(patch.object(linux_support,'lock_desktop_profile',return_value=self.guard))
            stack.enter_context(patch.object(client,'read_profile',return_value=self.profile))
            reserve=stack.enter_context(patch.object(portal_origin_state,'reserve_fresh_origin'))
            opened=stack.enter_context(patch.object(client,'open_local_relay'))
            client.relay_stdio(version='4.0.9')
        reserve.assert_not_called();opened.assert_not_called()
        self.assertFalse(self.settings.with_suffix('.tauri-origin.json').exists())


if __name__=='__main__':unittest.main()
