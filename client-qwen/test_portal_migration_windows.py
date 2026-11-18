"""Exercise only private messages for Tauri recovery windows."""
import io
from pathlib import Path
import unittest
from unittest.mock import Mock

from portal_migration_windows import RecoveryWindows
from portal_migration_job import MigrationJobError


class FakeBroker:
    token='b'*64
    ports=tuple(range(17841,17851))
    result_mode='transfer'
    def __init__(self):
        self.assets={'/recovery.js':b'window','/portal_origin_window.js':b'window',
                     '/portal_origin_sender_result.js':b'sender'}
    def wait_staged(self,_):return True
    def wait_result(self,_):return None


class RecoveryWindowsTests(unittest.TestCase):
    def setUp(self):
        self.output=io.StringIO();self.control=Mock();self.control.wait_recovery_ack.return_value=True
        self.storage=Path(__file__).resolve().parent
        self.adapter=RecoveryWindows('a'*20,self.output,self.control,self.storage,self.storage/'init.js')
        self.job={'engine':'tauri','port':17842,'localEntries':1,'audioChunks':0}

    def test_tauri_windows_are_closed_and_acknowledged(self):
        with self.adapter.open(FakeBroker(),self.job,17841,lambda:False) as windows:
            self.assertTrue(windows.is_running())
            self.assertEqual(windows.startup_timeout,45)
            self.assertTrue(self.output.getvalue().endswith('17842 17841 tauri transfer\n'))
        self.assertTrue(self.output.getvalue().endswith('KIARA_RELAY_ORIGIN_TRANSFER_DONE\n'))
        self.control.wait_recovery_ack.assert_called_once_with(15)

    def test_closure_is_requested_even_if_transfer_fails(self):
        with self.assertRaisesRegex(RuntimeError,'fictif'):
            with self.adapter.open(FakeBroker(),self.job,17841,lambda:False):raise RuntimeError('fictif')
        self.control.wait_recovery_ack.assert_called_once_with(15)

    def test_review_display_requires_acknowledgement_and_is_idempotent(self):
        with self.adapter.open(FakeBroker(),self.job,17841,lambda:False) as windows:
            self.assertTrue(windows.show_review())
            self.assertTrue(windows.show_review())
            self.assertEqual(self.output.getvalue().count('KIARA_RELAY_ORIGIN_REVIEW\n'),1)
            self.control.wait_recovery_ack.assert_called_once_with(15)
        self.assertEqual(self.control.wait_recovery_ack.call_count,2)

    def test_review_refuses_unconfirmed_window(self):
        self.control.wait_recovery_ack.side_effect=[False,True]
        with self.adapter.open(FakeBroker(),self.job,17841,lambda:False) as windows:
            self.assertFalse(windows.show_review())

    def test_unconfirmed_closure_fails_closed(self):
        self.control.wait_recovery_ack.return_value=False
        with self.assertRaises(MigrationJobError):
            with self.adapter.open(FakeBroker(),self.job,17841,lambda:False):pass

    def test_unsupported_legacy_engine_is_never_started(self):
        job={**self.job,'engine':'qt','port':17841}
        with self.assertRaises(MigrationJobError):
            with self.adapter.open(FakeBroker(),job,17841,lambda:False):pass
        self.assertEqual(self.output.getvalue(),'');self.control.wait_recovery_ack.assert_not_called()

    def test_cancel_before_open_does_not_announce_or_close_windows(self):
        with self.assertRaises(MigrationJobError):
            with self.adapter.open(FakeBroker(),self.job,17841,lambda:True):pass
        self.assertEqual(self.output.getvalue(),'');self.control.wait_recovery_ack.assert_not_called()

    def test_unsupported_legacy_snapshot_is_never_started(self):
        broker=FakeBroker();broker.result_mode='snapshot';broker.assets['/portal_origin_snapshot.js']=b'snapshot'
        with self.assertRaises(MigrationJobError):
            with self.adapter.open(broker,{**self.job,'engine':'qt','port':17841},17841,lambda:False):pass
        self.assertEqual(self.output.getvalue(),'');self.control.wait_recovery_ack.assert_not_called()


if __name__=='__main__':unittest.main()
