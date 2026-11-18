"""The pre-start protocol preserves the profile and uses a private pipe."""
import io
from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import Mock, patch

import client
from portal_origin_session import OriginInventorySession
from portal_origin_state import read_origin, record_origin
from portal_recovery_stdio import QtLegacyStoragePresent, check_qt_storage, qt_storage_path, recovery_assets, resolve_port, resolve_port_full, transfer_assets
from test_portal_origin_session import FakeBroker


class RecoveryStdioTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/('a'*20+'.dpapi')
        self.output=io.StringIO();self.control=Mock();self.control.cancelled.return_value=False
        context=patch.object(client,'settings_path',return_value=self.path);context.start();self.addCleanup(context.stop)

    def test_bundled_assets_are_fixed_and_nonempty(self):
        assets=recovery_assets(Path(__file__).resolve().parent)
        self.assertEqual(set(assets),{'/recovery','/recovery/scan','/recovery.js','/portal_origin_scan.js','/portal_origin_inventory.js','/portal_origin_recovery.js',
                                     '/portal_origin_transfer.js','/portal_origin_sender.js','/portal_origin_sender_result.js',
                                     '/portal_origin_receiver.js','/portal_origin_window.js','/portal_origin_snapshot.js',
                                     '/portal_conflict_archive.js','/portal_conflict_review.js','/portal_conflict_review.css'})
        self.assertTrue(all(isinstance(value,bytes) and value for value in assets.values()))
        transfer=transfer_assets(Path(__file__).resolve().parent)
        self.assertEqual(transfer['/recovery.js'],transfer['/portal_origin_scan.js'])
        self.assertIn(b'/portal_origin_transfer.js',transfer['/recovery'])
        self.assertEqual(transfer['/recovery/transfer'],transfer['/recovery'])

    def test_audio_resources_are_explicit_and_load_in_dependency_order(self):
        directory=Path(__file__).resolve().parent
        scan=recovery_assets(directory,audio_archives=True);transfer=transfer_assets(directory,audio_archives=True)
        self.assertIn('/portal_audio_conflict_archive.js',scan);self.assertNotIn('/portal_audio_conflict_review.js',scan)
        self.assertIn('/portal_audio_conflict_review.js',transfer)
        for assets,url in ((scan,'/recovery/scan'),(transfer,'/recovery/transfer')):
            html=assets[url]
            self.assertLess(html.index(b'/portal_origin_recovery.js'),html.index(b'/portal_audio_conflict_archive.js'))
            self.assertLess(html.index(b'/portal_audio_conflict_archive.js'),html.index(b'/portal_origin_inventory.js'))
        with self.assertRaises(ValueError):recovery_assets(directory,audio_archives=1)

    def test_preexisting_port_does_not_open_a_window(self):
        marker=self.path.with_suffix('.tauri-origin.json');record_origin(marker,17841)
        with patch.object(client,'portal_recovery_fixed_port',return_value=17841):
            self.assertEqual(resolve_port({},self.control,self.output,{}),17841)
        self.assertEqual(self.output.getvalue(),'');self.control.cancelled.assert_not_called()

    def test_new_profile_has_a_marker_directory_before_the_scan(self):
        path=Path(self.directory.name)/'new-profile'/('a'*20+'.dpapi')
        class StopAfterStart:
            def __init__(inner,marker,assets,*,fixed_port):
                self.assertTrue(path.parent.is_dir())
            def start(inner):return {'token':'b'*64}
            def close(inner):pass
        self.control.cancelled.return_value=True
        with patch.object(client,'settings_path',return_value=path), \
             patch.object(client,'portal_recovery_fixed_port',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'interrompue'):
                resolve_port({},self.control,self.output,{},session_factory=StopAfterStart)
        self.assertTrue(path.parent.is_dir())
        self.assertFalse(path.with_suffix('.taauri-origin.json').exists())

    def test_new_scan_announces_only_profile_id_and_token_on_pipe(self):
        sessions=[]
        class CompletingOutput(io.StringIO):
            def flush(inner):
                session=sessions[0]
                for port in session.ports:
                    session.plan.submit(port,{'localEntries':int(port==17844),'audioChunks':0})
                session.broker.complete=17844
        output=CompletingOutput()
        # Use a protocol-valid token in the fake broker.
        def broker(*args,**kwargs):
            instance=FakeBroker(*args,**kwargs);instance.token='b'*64;return instance
        def factory(*args,**kwargs):
            session=OriginInventorySession(*args,**kwargs,broker_factory=broker)
            sessions.append(session);return session
        with patch.object(client,'portal_recovery_fixed_port',return_value=None):
            self.assertEqual(resolve_port({},self.control,output,{},session_factory=factory),17844)
        self.assertEqual(output.getvalue(),'KIARA_RELAY_ORIGIN_SCAN '+'a'*20+' '+'b'*64+'\n')
        self.assertEqual(read_origin(self.path.with_suffix('.tauri-origin.json')),17844)
        self.assertTrue(sessions[0].finished)

    def test_unreadable_settings_do_not_open_a_window_or_create_a_marker(self):
        with patch.object(client,'portal_recovery_fixed_port',side_effect=client.LocalSettingsUnreadable('illisible')):
            with self.assertRaises(client.LocalSettingsUnreadable):resolve_port({},self.control,self.output,{})
        self.assertEqual(self.output.getvalue(),'')
        self.assertFalse(self.path.with_suffix('.tauri-origin.json').exists())

    def test_full_protocol_announces_private_scan_and_uses_validated_resources(self):
        def coordinator(marker,scan,copy,announce,qt_inventory,windows,cancelled,*,fixed_port,state_path,profile,encrypt,decrypt):
            self.assertEqual(marker,self.path.with_suffix('.tauri-origin.json'))
            self.assertEqual(state_path,self.path.with_suffix('.tauri-migration'));self.assertEqual(profile,'a'*20)
            self.assertTrue(callable(encrypt) and callable(decrypt))
            self.assertEqual(fixed_port,17841);self.assertTrue(callable(windows));self.assertFalse(cancelled())
            self.assertIsNone(qt_inventory(cancelled))
            self.assertIn('/portal_origin_window.js',copy);self.assertIn('/recovery',scan)
            announce({'token':'b'*64});return 17841
        with patch.object(client,'portal_recovery_fixed_port',return_value=17841),patch('portal_recovery_stdio.qt_storage_path',return_value=None):
            self.assertEqual(resolve_port_full({},self.control,self.output,Path(__file__).resolve().parent,coordinator=coordinator),17841)
        self.assertEqual(self.output.getvalue(),'KIARA_RELAY_ORIGIN_SCAN '+'a'*20+' '+'b'*64+'\n')
        self.assertFalse(self.path.with_suffix('.tauri-origin.json').exists())

    def test_linux_qt_storage_is_never_assumed_empty_or_deleted(self):
        legacy=self.path.parent/('webview-'+self.path.stem)
        with patch.object(sys,'platform','linux'):
            check_qt_storage(self.path)
            legacy.mkdir();sentinel=legacy/'brouillon-fictif';sentinel.write_bytes(b'conserver')
            self.assertEqual(qt_storage_path(self.path),legacy)
            with self.assertRaises(QtLegacyStoragePresent):check_qt_storage(self.path)
        self.assertEqual(sentinel.read_bytes(),b'conserver')

    def test_unreadable_qt_storage_fails_closed(self):
        with patch.object(sys,'platform','linux'),patch.object(Path,'lstat',side_effect=PermissionError('refus')):
            with self.assertRaises(QtLegacyStoragePresent):check_qt_storage(self.path)

    def test_qt_storage_symlink_is_not_followed(self):
        legacy=self.path.parent/('webview-'+self.path.stem);target=self.path.parent/'target';target.mkdir()
        try:legacy.symlink_to(target,target_is_directory=True)
        except (OSError,NotImplementedError):self.skipTest('Lien symbolique indisponible.')
        with patch.object(sys,'platform','linux'):
            with self.assertRaises(QtLegacyStoragePresent):qt_storage_path(self.path)
        self.assertTrue(legacy.is_symlink())


if __name__=='__main__':unittest.main()
