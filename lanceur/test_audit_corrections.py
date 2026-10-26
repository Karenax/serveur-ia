"""Cross-contract regressions found by the October audit, using isolated data."""
import base64
from contextlib import contextmanager, closing
import copy
import json
import secrets
import socket
import sqlite3
import threading
import time
import unittest
import urllib.request
from unittest.mock import patch

import test_hermes_conversations as turns
import test_hermes_inference as provider
from client_storage import ClientStorage
from hermes_backup import HermesBackup
from history_store import validate
from workspace import DEFAULT_LIMITS


@contextmanager
def fixture(kind=turns.ConversationsTests):
    case = kind(); case.setUp()
    try: yield case
    finally: case.tearDown()


def save_history(case, history):
    current = case.store.workspace.history_read(case.a)
    case.store.workspace.history_write(case.a, {**{k: current[k] for k in ('revision','reset_id','generation')}, 'history': history})


class AuditCorrections(unittest.TestCase):
    def test_project_conversations_export_with_archive_state_and_valid_backup(self):
        with fixture() as c:
            storage = ClientStorage(c.store)
            project = c.store.workspace.action(c.a, {'action':'project_create','title':'Export'})['id']
            identity = secrets.token_hex(16)
            c.store.workspace.action(c.a, {'action':'conversation_save','project':project,'id':identity,
                'title':'Conversation','messages':[{'role':'user','content':'Question'}],
                'revision':0,'reset_id':c.store.workspace.history_read(c.a)['reset_id']})
            for archived, revision in ((False,1),(True,2)):
                if archived: c.store.workspace.action(c.a, {'action':'conversation_archive','id':identity,'revision':1,'archived':True})
                storage.synchronize()
                path = storage.directory(c.a)/'donnees.sqlite3'
                with closing(sqlite3.connect(path)) as db:
                    self.assertEqual(db.execute('SELECT archived,revision FROM conversations').fetchone(), (int(archived),revision))
                    self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                c.store.workspace.validate_backup(base64.b64encode(path.read_bytes()).decode(), {c.a})
            storage.close()

    def test_message_limit_refused_before_native_side_effects(self):
        with fixture() as c:
            c.data['messages'] = [{'role':'user','content':'Question'}] * 1000
            with self.assertRaisesRegex(ValueError,'limite de messages'): c.run_turn()
            self.assertFalse(c.service.calls); self.assertFalse(c.manager.active)
            self.assertFalse(c.manager.storage.reservations)

    def test_oversize_answer_keeps_valid_history_and_recoverable_full_result(self):
        with fixture() as c:
            history = copy.deepcopy(c.history)
            history['conversations'][0]['messages'].insert(0, {'role':'assistant','content':'A'*(8*1024*1024)})
            save_history(c,history)
            c.data['messages'] = copy.deepcopy(history['conversations'][0]['messages'])
            c.service.output = 'R'*(1536*1024)
            events = c.run_turn()
            saved = c.store.workspace.history_read(c.a)['history']
            validate(saved); self.assertEqual(saved,history)
            result = c.completed(); self.assertEqual(result['status'],'completed')
            self.assertEqual(result['text'],c.service.output); self.assertTrue(result['history_error'])
            self.assertTrue(next(e['hermes_run'] for e in events if 'hermes_run' in e)['history_error'])
            c.manager.prune(now=time.time()+2*86400)
            self.assertEqual(c.completed()['text'],c.service.output)

    def test_projection_io_failure_preserves_completed_answer_for_export(self):
        with fixture() as c:
            with patch.object(c.manager,'_project',side_effect=sqlite3.OperationalError('Synthetic storage failure')):c.run_turn()
            result=c.completed();self.assertEqual(result['status'],'completed')
            self.assertEqual(result['text'],c.service.output);self.assertTrue(result['history_error'])

    def test_journal_deduplicates_large_requests_and_is_accounted_and_backed_up(self):
        with fixture() as c:
            data={'messages':[{'role':'user','content':'S'*(2*1024*1024)}],'reasoning_effort':'none'}
            for i in range(6): list(c.manager.stream(c.b,data,secrets.token_hex(16),'api-'+str(i)))
            with c.manager.db() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM agent_runs WHERE owner=?',(c.b,)).fetchone()[0],6)
                self.assertEqual(db.execute('SELECT SUM(length(messages)+length(input)) FROM agent_runs').fetchone()[0],0)
            with c.store.workspace.db() as db: self.assertGreater(c.store.workspace.usage(db,c.b),0)
            self.assertLess(c.manager.path.stat().st_size,1024*1024)
            package=HermesBackup(c.manager.root).export({c.a,c.b})
            HermesBackup(c.manager.root).validate(package,{c.a,c.b})
            c.manager.prune(now=time.time()+2*86400)
            with c.manager.db() as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM agent_runs').fetchone()[0],0)

    def test_native_profile_storage_prevents_quota_bypass(self):
        with fixture() as c:
            c.store.workspace.admin_action({'action':'policy','owner':c.b,'limits':{**DEFAULT_LIMITS,'storage_mb':1}},{c.a,c.b})
            directory=c.manager.root/'profiles'/('fred-'+c.b)/'sessions'; directory.mkdir(parents=True)
            (directory/'bounded-fixture.json').write_bytes(b'x'*(2*1024*1024))
            with self.assertRaisesRegex(ValueError,'stockage'): list(c.manager.stream(c.b,c.data,secrets.token_hex(16),'too-large'))
            self.assertFalse(c.manager.active); self.assertFalse(c.manager.storage.reservations)

    def test_images_survive_reconstruction_and_image_edits_change_session(self):
        with fixture() as c:
            image='data:image/png;base64,'+base64.b64encode(b'\x89PNG\r\n\x1a\nfixture').decode()
            user={'role':'user','content':[{'type':'text','text':'Image'},{'type':'image_url','image_url':{'url':image}}]}
            c.data['messages']=[user,{'role':'assistant','content':'Décrite'},{'role':'user','content':'Relis'}]
            c.run_turn(); first=next(call[3] for call in c.service.calls if call[2]=='/v1/runs')
            self.assertEqual(first['conversation_history'][0]['content'][1]['image_url']['url'],image)
            c.data['messages'] += [{'role':'assistant','content':c.service.output},{'role':'user','content':'Suite'}]
            c.data['messages'][0]['content'][1]['image_url']['url']=image+'AAAA'
            c.request=secrets.token_hex(16);c.run_turn()
            latest=[call[3] for call in c.service.calls if call[2]=='/v1/runs'][-1]
            self.assertNotEqual(first['session_id'],latest['session_id']);self.assertIn('conversation_history',latest)

    def test_memory_edit_uses_delta_at_quota_boundary(self):
        with fixture() as c:
            w=c.store.workspace; project=w.action(c.b,{'action':'project_create','title':'Quota'})['id']
            memory=w.action(c.b,{'action':'memory_create','project':project,'text':'M'*1500})['id']
            w.admin_action({'action':'policy','owner':c.b,'limits':{**DEFAULT_LIMITS,'storage_mb':1}},{c.a,c.b})
            with patch.object(w,'usage',return_value=1024*1024-1000):
                revision=w.snapshot(c.b)['projects'][0]['memories'][0]['revision']
                saved=w.action(c.b,{'action':'memory_save','id':memory,'text':'M'*1500,'revision':revision})
                saved=w.action(c.b,{'action':'memory_save','id':memory,'text':'M'*1400,'revision':saved['revision']})
                with self.assertRaisesRegex(ValueError,'stockage'): w.action(c.b,{'action':'memory_save','id':memory,'text':'é'*1500,'revision':saved['revision']})

    def test_delayed_mcp_and_inference_cannot_use_next_turn(self):
        with fixture(provider.PrivateInferenceTests) as c:
            old=c.activate(); old['remote']='run-old';old['remote_ready'].set()
            old['cancelled'].set();c.manager.active.clear();c.store.active=0;c.manager.storage.release(c.a)
            current=c.activate();current['remote']='run-new';current['remote_ready'].set()
            call={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'fred_workspace_info','arguments':{},'_meta':{'fred_run_id':'run-old'}}}
            request=urllib.request.Request(c.private.url+'/mcp',json.dumps(call).encode(),headers={'Authorization':'Bearer tool-A','Content-Type':'application/json'})
            with urllib.request.urlopen(request) as response: result=json.load(response)
            self.assertTrue(result['result']['isError'])
            self.assertFalse(c.manager.valid(c.a,old))
            call['params']['_meta']['fred_run_id']='run-new'
            request=urllib.request.Request(c.private.url+'/mcp',json.dumps(call).encode(),headers={'Authorization':'Bearer tool-A','Content-Type':'application/json'})
            with urllib.request.urlopen(request) as response: result=json.load(response)
            self.assertFalse(result['result']['isError'])

    def test_private_http_bounds_stalled_connections_and_recovers_slot(self):
        with fixture(provider.PrivateInferenceTests) as c:
            server=c.private.server;server.workers=threading.BoundedSemaphore(1);server.request_timeout=.3
            with socket.create_connection(server.server_address) as pending:
                pending.sendall(b'POST /mcp HTTP/1.1\r\n')
                deadline=time.monotonic()+1
                while server.workers._value and time.monotonic()<deadline:time.sleep(.01)
                with socket.create_connection(server.server_address) as second:
                    second.settimeout(1);second.sendall(b'GET / HTTP/1.0\r\n\r\n')
                    self.assertIn(b'503',second.recv(512))
                time.sleep(.4)
                self.assertEqual(server.workers._value,1)

    def test_client_exports_skip_unchanged_owners_and_isolate_failed_client(self):
        with fixture() as c:
            storage=ClientStorage(c.store)
            storage.synchronize(incremental=True)
            with patch.object(storage,'publish',wraps=storage.publish) as publish:
                storage.synchronize(incremental=True)
                self.assertEqual(publish.call_count,0)
                with c.store.workspace.db() as db:db.execute("INSERT OR REPLACE INTO settings VALUES('worker','synthetic-heartbeat')")
                storage.synchronize(incremental=True)
                self.assertEqual(publish.call_count,0,'Worker lease heartbeats do not change exported client data')
                c.store.workspace.action(c.b,{'action':'project_create','title':'Une modification'})
                storage.synchronize(incremental=True)
                self.assertEqual(publish.call_count,1)
                self.assertEqual(publish.call_args.args[0]['client']['id'],c.b)
            original=storage.publish
            def broken(snapshot):
                if snapshot['client']['id']==c.a:raise sqlite3.OperationalError('Synthetic schema failure')
                return original(snapshot)
            storage.changed()
            with patch.object(storage,'publish',side_effect=broken):storage.synchronize(incremental=True)
            self.assertEqual(storage.client_status(c.a)['status'],'error')
            self.assertEqual(storage.client_status(c.b)['status'],'ready')
            storage.close()

    def test_knowledge_skips_unchanged_sources_but_refreshes_after_edit(self):
        from knowledge import Knowledge
        from test_knowledge import FixtureEngine
        with fixture() as c:
            index=Knowledge(c.store.workspace,FixtureEngine());c.store.workspace.knowledge=index
            try:
                with patch.object(index,'source_records',wraps=index.source_records) as read:
                    index.synchronize(encode=False);index.synchronize(encode=False)
                    self.assertEqual(read.call_count,1)
                    c.store.workspace.action(c.a,{'action':'project_create','title':'Index'})
                    index.synchronize(encode=False)
                    self.assertEqual(read.call_count,2)
            finally:index.close()


if __name__=='__main__':unittest.main()
