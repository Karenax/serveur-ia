"""Read-only Tauri-origin planning using fictional counts and profiles."""
from contextlib import ExitStack
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch

import client
import portal_origin_session
import portal_recovery_stdio
import relay_control_stream
from portal_origin_session import (OriginInventorySession,OriginNeedsRecovery,
                                   OriginInventoryUnavailable,resolve_origin)
from portal_origin_state import read_origin


class FakeBroker:
    def __init__(self,ports,destination,assets,*,inventory_plan):
        self.token='b'*64;self.plan=inventory_plan;self.complete=None;self.closed=False
    def start(self):pass
    def wait_complete(self,_timeout):return self.complete
    def close(self):self.closed=True


class SafeInventoryTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.marker=self.root/'origin.json';self.sessions=[]

    def factory(self,*args,**kwargs):
        value=OriginInventorySession(*args,**kwargs,broker_factory=FakeBroker)
        self.sessions.append(value);return value

    def scan(self, occupied, *, unavailable=False, selected=None):
        session=self.sessions[-1]
        for port in session.ports:
            if unavailable and port==17842:
                session.plan.submit(port,{'unavailable':True});break
            session.plan.submit(port,{'localEntries':int(port in occupied),'audioChunks':0})
        session.broker.complete=selected

    def test_single_origin_is_recorded_only_after_acknowledgement(self):
        def announce(_descriptor):self.scan({17844},selected=17844)
        self.assertEqual(resolve_origin(self.marker,{},announce,lambda:False,timeout=1,session_factory=self.factory),17844)
        self.assertEqual(read_origin(self.marker),17844);self.assertTrue(self.sessions[-1].finished)

    def test_multiple_origins_stop_without_waiting_for_timeout_or_marker(self):
        def announce(_descriptor):self.scan({17842,17845})
        with self.assertRaises(OriginNeedsRecovery):
            resolve_origin(self.marker,{},announce,lambda:False,timeout=1,session_factory=self.factory)
        self.assertFalse(self.marker.exists());self.assertTrue(self.sessions[-1].finished)

    def test_unreadable_origin_stops_without_marker(self):
        def announce(_descriptor):self.scan(set(),unavailable=True)
        with self.assertRaises(OriginInventoryUnavailable):
            resolve_origin(self.marker,{},announce,lambda:False,timeout=1,session_factory=self.factory)
        self.assertFalse(self.marker.exists());self.assertTrue(self.sessions[-1].finished)

    def test_fixed_port_with_data_elsewhere_never_records_a_guess(self):
        def announce(_descriptor):self.scan({17844})
        with self.assertRaises(OriginNeedsRecovery):
            resolve_origin(self.marker,{},announce,lambda:False,fixed_port=17841,timeout=1,session_factory=self.factory)
        self.assertFalse(self.marker.exists());self.assertTrue(self.sessions[-1].finished)

    def relay_context(self, stack):
        settings=self.root/('a'*20+('.enc' if sys.platform.startswith('linux') else '.dpapi'))
        settings.write_bytes(b'reglages fictifs')
        profile={'url':'https://fiction.example','token':'fictif'};guard=Mock()
        stack.enter_context(patch.object(client,'settings_path',return_value=settings))
        stack.enter_context(patch.object(client.sys,'stdin',SimpleNamespace(buffer=io.BytesIO())))
        stack.enter_context(patch.dict(os.environ,{'KIARA_DESKTOP_UPDATES':'0','LOCALAPPDATA':str(self.root)}))
        for name in ('KIARA_TEST_RECOVERY','KIARA_TEST_RECOVERY_FULL'):os.environ.pop(name,None)
        if sys.platform.startswith('linux'):
            import linux_support
            (self.root/'profile.enc').write_bytes(b'profil fictif')
            stack.enter_context(patch.object(linux_support,'data_home',return_value=self.root))
            stack.enter_context(patch.object(linux_support,'lock_desktop_profile',return_value=guard))
            stack.enter_context(patch.object(client,'read_profile',return_value=profile))
        else:
            import windows_profile_guard
            stack.enter_context(patch.object(windows_profile_guard,'lock_desktop_profile',return_value=guard))
            stack.enter_context(patch.object(client,'read_relay_profile',return_value=profile))
        return settings,profile,guard

    def test_relay_uses_inventory_result_as_the_only_port(self):
        remote=SimpleNamespace(desktop_update=None,close=Mock())
        server=SimpleNamespace(server_port=17844,serve_forever=Mock(),shutdown=Mock(),server_close=Mock())
        with ExitStack() as stack:
            settings,profile,guard=self.relay_context(stack)
            stack.enter_context(patch.object(client,'portal_recovery_fixed_port',return_value=None))
            stack.enter_context(patch.object(portal_recovery_stdio,'recovery_assets',return_value={}))
            stack.enter_context(patch.object(relay_control_stream,'RelayControlStream'))
            resolve=stack.enter_context(patch.object(portal_origin_session,'resolve_origin',return_value=17844))
            opened=stack.enter_context(patch.object(client,'open_local_relay',return_value=(remote,server)))
            stack.enter_context(patch('builtins.print'))
            client.relay_stdio(version='4.0.9')
        self.assertEqual(resolve.call_args.args[0],settings.with_suffix('.tauri-origin.json'))
        opened.assert_called_once_with(profile,managed=not sys.platform.startswith('linux'),required_port=17844)
        self.assertEqual(settings.read_bytes(),b'reglages fictifs');guard.close.assert_called_once()

    def test_relay_reports_multiple_origins_without_opening_main_server(self):
        with ExitStack() as stack:
            settings,_profile,guard=self.relay_context(stack)
            stack.enter_context(patch.object(client,'portal_recovery_fixed_port',return_value=None))
            stack.enter_context(patch.object(portal_recovery_stdio,'recovery_assets',return_value={}))
            stack.enter_context(patch.object(relay_control_stream,'RelayControlStream'))
            stack.enter_context(patch.object(portal_origin_session,'resolve_origin',side_effect=OriginNeedsRecovery('fictif')))
            opened=stack.enter_context(patch.object(client,'open_local_relay'))
            printed=stack.enter_context(patch('builtins.print'))
            client.relay_stdio(version='4.0.9')
        opened.assert_not_called();guard.close.assert_called_once()
        self.assertEqual(printed.call_args_list[-1].args,('KIARA_RELAY_ORIGIN_MULTIPLE',))
        self.assertEqual(settings.read_bytes(),b'reglages fictifs')
        self.assertFalse(settings.with_suffix('.tauri-origin.json').exists())

    def test_unfinished_migration_is_never_replaced_by_inventory(self):
        with ExitStack() as stack:
            settings,_profile,guard=self.relay_context(stack)
            journal=settings.with_suffix('.tauri-migration');journal.write_bytes(b'journal fictif')
            scan=stack.enter_context(patch.object(portal_origin_session,'resolve_origin'))
            opened=stack.enter_context(patch.object(client,'open_local_relay'))
            printed=stack.enter_context(patch('builtins.print'))
            client.relay_stdio(version='4.0.9')
        scan.assert_not_called();opened.assert_not_called();guard.close.assert_called_once()
        self.assertEqual(journal.read_bytes(),b'journal fictif')
        self.assertEqual(printed.call_args_list[-1].args,('KIARA_RELAY_RECOVERY_UNAVAILABLE',))


if __name__=='__main__':unittest.main()
