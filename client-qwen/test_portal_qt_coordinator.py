"""Qt inventory must stay read-only, bounded and fail closed."""
import json,os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

from portal_qt_coordinator import QtInventoryError,inspect_qt

PORTS=tuple(range(20000,20010))


class FakeBroker:
    def __init__(self,ports,destination,assets,*,inventory_plan):
        self.ports=ports;self.plan=inventory_plan;self.token='a'*64;self.mode=assets['mode'];self.closed=False
    def __enter__(self):return self
    def __exit__(self,*_):self.closed=True
    def wait_complete(self,_):
        if self.plan.status()['state']=='scanning':
            for index,port in enumerate(self.ports):
                report={'localEntries':int(index in ((2,7) if self.mode=='multiple' else (2,))), 'audioChunks':0}
                if self.mode=='unavailable' and index==4:report={'unavailable':True}
                self.plan.submit(port,report)
                if report.get('unavailable'):break
        state=self.plan.status()
        return state['port'] if state['state']=='ready' else None


class QtCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name);self.storage=self.root/'qt';self.storage.mkdir()
        self.script=self.root/'guard.js';self.script.write_text('fictif')
        self.sentinel=self.storage/'brouillon-fictif';self.sentinel.write_bytes(b'conserver')
        self.process=Mock();self.process.pid=os.getpid();self.process.poll.return_value=None;self.process.wait.return_value=0

    def run_scan(self,mode,cancelled=lambda:False):
        with patch('portal_qt_coordinator.subprocess.Popen',return_value=self.process) as popen:
            result=inspect_qt(self.storage,self.script,{'mode':mode},cancelled,
                              helper=['helper-fictif'],ports=PORTS,broker_factory=FakeBroker)
        return result,popen

    def test_single_origin_reports_counts_without_writing_a_marker(self):
        result,popen=self.run_scan('one')
        self.assertEqual(result['status']['port'],PORTS[2]);self.assertEqual(len(result['reports']),10)
        self.assertEqual(result['reports'][2],{'port':PORTS[2],'localEntries':1,'audioChunks':0})
        self.assertEqual(self.sentinel.read_bytes(),b'conserver')
        self.assertFalse(list(self.root.glob('*.tauri-origin.json')))
        self.assertEqual(popen.call_args.args[0],['helper-fictif'])
        descriptor=json.loads(self.process.stdin.write.call_args.args[0]);self.assertEqual(descriptor['token'],'a'*64)
        self.process.stdin.close.assert_called_once()

    def test_multiple_and_unavailable_are_not_selected(self):
        for mode,state in (('multiple','needsRecovery'),('unavailable','unavailable')):
            with self.subTest(mode=mode):
                self.process.reset_mock();result,_=self.run_scan(mode)
                self.assertEqual(result['status']['state'],state);self.assertNotIn('port',result['status'])
                self.assertEqual(self.sentinel.read_bytes(),b'conserver')

    def test_cancellation_prevents_the_helper_from_starting(self):
        with patch('portal_qt_coordinator.subprocess.Popen') as popen:
            with self.assertRaises(QtInventoryError):
                inspect_qt(self.storage,self.script,{'mode':'one'},lambda:True,
                           helper=['helper-fictif'],ports=PORTS,broker_factory=FakeBroker)
        popen.assert_not_called();self.assertEqual(self.sentinel.read_bytes(),b'conserver')

    def test_early_helper_exit_is_reported_and_storage_is_preserved(self):
        self.process.poll.return_value=1
        class IdleBroker(FakeBroker):
            def wait_complete(self,_):return None
        with patch('portal_qt_coordinator.subprocess.Popen',return_value=self.process):
            with self.assertRaises(QtInventoryError):
                inspect_qt(self.storage,self.script,{'mode':'one'},lambda:False,
                           helper=['helper-fictif'],ports=PORTS,broker_factory=IdleBroker)
        self.assertEqual(self.sentinel.read_bytes(),b'conserver');self.process.stdin.close.assert_called_once()


if __name__=='__main__':unittest.main()
