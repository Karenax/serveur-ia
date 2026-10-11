"""Worker lifecycle proofs using disposable workspaces and server installations."""
import json
from pathlib import Path
import secrets
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import read_json
from workspace import Workspace


class WorkerLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='fred-worker-lifecycle-')
        self.w=Workspace(Path(self.tmp.name))
        self.entered=threading.Event();self.release=threading.Event()
        self.calls=[]
        self.owner='a';self.project=self.w.action(self.owner,{'action':'project_create','title':'Isolated worker proof'})['id']

    def tearDown(self):
        self.release.set()
        self.w.shutdown()
        self.tmp.cleanup()

    def until(self,predicate,timeout=12):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if predicate():return
            time.sleep(.02)
        self.fail('Worker condition did not complete within isolated test deadline')

    def job(self,prompt,web=False):
        with patch.object(self.w,'allow_web'):
            return self.w.action(self.owner,{'action':'job_create','project':self.project,'prompt':prompt,
                'kind':'web' if web else 'analysis','url':'https://example.test' if web else '',
                'request_key':secrets.token_hex(16)})['id']

    def slow_web(self,*args):
        self.entered.set()
        if not self.release.wait(60):raise TimeoutError('Isolated web fixture release was not received')
        return []

    def generate(self,owner,messages,cancel):
        self.calls.append((threading.current_thread(),messages[0]['content']))
        return 'isolated completed result'

    def state(self,identity):
        with self.w.db() as db:return dict(db.execute('SELECT * FROM jobs WHERE id=?',(identity,)).fetchone())

    def lease(self):
        with self.w.db() as db:
            row=db.execute("SELECT value FROM settings WHERE key='worker'").fetchone()
            return json.loads(row[0]) if row else None

    def slow_running(self):
        self.w.web_sources=self.slow_web
        first=self.job('slow source lookup',web=True)
        second=self.job('queued follow-up')
        self.w.start(self.generate,lambda owner:True)
        self.assertTrue(self.entered.wait(12))
        return first,second,self.w.thread

    def test_slow_worker_restart_waits_for_exit_and_does_not_duplicate(self):
        first,second,old=self.slow_running()
        with self.assertRaisesRegex(RuntimeError,'pas encore arrêtés'):self.w.shutdown()
        self.assertIs(self.w.thread,old);self.assertTrue(old.is_alive())
        self.assertEqual(self.lease()['instance'],self.w.instance)
        callers=[threading.Thread(target=self.w.start,args=(self.generate,lambda owner:True)) for _ in range(8)]
        for caller in callers:caller.start()
        for caller in callers:caller.join(3)
        self.assertIs(self.w.thread,old);self.assertFalse(self.calls)
        # Another object in the same process must respect the still-live lease.
        other=Workspace(self.w.home)
        other.start(self.generate,lambda owner:True)
        self.assertIsNone(other.thread);other.shutdown()
        self.release.set()
        self.until(lambda:self.state(second)['state']=='completed')
        self.assertFalse(old.is_alive());self.assertIsNot(self.w.thread,old)
        self.assertEqual(self.state(first)['state'],'failed');self.assertEqual(self.state(first)['result'],'')
        self.assertEqual(len(self.calls),1)
        self.assertIs(self.calls[0][0],self.w.thread)
        self.assertEqual(self.lease()['instance'],self.w.instance)

    def test_explicit_shutdown_cancels_a_pending_restart(self):
        first,second,old=self.slow_running()
        with self.assertRaises(RuntimeError):self.w.shutdown()
        self.w.start(self.generate,lambda owner:True)
        with self.assertRaises(RuntimeError):self.w.shutdown()
        self.release.set()
        self.until(lambda:self.w.thread is None)
        self.assertFalse(old.is_alive());self.assertIsNone(self.lease())
        self.assertEqual(self.state(second)['state'],'queued');self.assertFalse(self.calls)

    def test_stale_or_malformed_worker_lease_can_be_replaced(self):
        for stale in ('not-json','[]','{"pid":-1}'):
            with self.subTest(lease=stale):
                with self.w.db() as db:db.execute("INSERT OR REPLACE INTO settings VALUES('worker',?)",(stale,))
                self.w.start(self.generate,lambda owner:True)
                self.assertTrue(self.w.thread.is_alive())
                self.assertEqual(self.lease()['instance'],self.w.instance)
                self.w.shutdown()
                self.assertIsNone(self.w.thread);self.assertIsNone(self.lease())

    def test_pending_restart_cannot_claim_or_publish_during_maintenance(self):
        first,second,old=self.slow_running()
        with self.assertRaises(RuntimeError):self.w.shutdown()
        self.w.maintenance=True
        self.w.start(self.generate,lambda owner:True)
        self.release.set()
        self.until(lambda:self.w.thread is None)
        self.assertFalse(old.is_alive());self.assertFalse(self.calls)
        self.assertEqual(self.state(first)['result'],'');self.assertEqual(self.state(second)['state'],'queued')
        self.w.start(self.generate,lambda owner:True)
        self.assertIsNone(self.w.thread)
        self.w.maintenance=False
        self.w.start(self.generate,lambda owner:True)
        self.until(lambda:self.state(second)['state']=='completed')
        self.assertEqual(len(self.calls),1)

    def test_restore_refused_before_applying_resumes_after_slow_worker_exits(self):
        from app import Controller
        from server_state import generation
        with tempfile.TemporaryDirectory(prefix='fred-worker-restore-') as folder:
            c=Controller(folder,include_legacy=False)
            c.wireguard.configure({'public_host':'127.0.0.1','listen_port':51820})
            owner=c.wireguard.create_android('Isolated restore worker','fixture-model')['id']
            c.remote.configure({'enabled':False,'url':'wireguard://10.77.0.1:8766'})
            w=c.remote.workspace
            original=self.w;self.w=w
            self.owner=owner;self.project=w.action(owner,{'action':'project_create','title':'Isolated restore worker'})['id']
            try:
                archive=c.operations.backups.create('isolated worker restoration phrase')
                before=generation(c.home)
                first,second,old=self.slow_running()
                with patch.object(c,'processes',return_value=[]),patch.object(c,'supervisor',return_value=None):
                    with self.assertRaisesRegex(RuntimeError,'pas encore arrêtés'):
                        c.operations.restore({'file':archive['file'],'password':'isolated worker restoration phrase'})
                status=c.operations.restorations.status()
                self.assertEqual(status['state'],'failed');self.assertFalse(status['active'])
                self.assertFalse(c.remote.maintenance);self.assertFalse(w.maintenance)
                self.assertFalse((c.home/'securite'/'retour-restauration.dpapi').exists())
                self.assertEqual(read_json(c.home/'securite'/'restauration.json')['state'],'failed')
                self.assertEqual(generation(c.home),before)
                self.assertTrue(old.is_alive());self.assertFalse(self.calls)
                self.release.set()
                self.until(lambda:self.state(second)['state']=='completed')
                self.assertFalse(old.is_alive());self.assertEqual(self.state(first)['result'],'')
                self.assertEqual(len(self.calls),1)
            finally:
                self.release.set();w.shutdown();c.operations.backups.close();self.w=original


if __name__=='__main__':unittest.main()
