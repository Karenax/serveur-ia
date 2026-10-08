"""Isolation, persistence, quotas, parsing, tools, gateway and backup integration."""
import base64
import io
import json
from pathlib import Path
import secrets
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'client-qwen'))
from workspace import Workspace,Denied,Conflict,extract,public_url,DEFAULT_LIMITS,HISTORY_RESET_ID
from scheduler import Scheduler

class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='fred-workspace-');self.home=Path(self.tmp.name);self.w=Workspace(self.home)
        self.p=self.act('project_create',title='Projet A')['id']
    def tearDown(self):self.w.stop.set();self.tmp.cleanup()
    def act(self,action,**values):return self.w.action('a',{'action':action,'reset_id':HISTORY_RESET_ID,**values})
    def document(self,content='Le budget approuvé est de 2500 euros.'):
        return self.act('document_create',project=self.p,title='Budget',text=content)['id']
    def job(self,**kwargs):return self.act('job_create',project=self.p,prompt='Résume le budget',request_key=secrets.token_hex(16),**kwargs)['id']

    def test_owner_isolation_on_all_objects(self):
        d=self.document();m=self.act('memory_create',project=self.p,text='Préférer le français')['id'];j=self.job()
        for action,v in [('document_get',{'id':d}),('document_download',{'id':d}),('document_delete',{'id':d}),('memory_delete',{'id':m}),('job_get',{'id':j}),('job_retry',{'id':j}),('project_save',{'id':self.p}),('search',{'project':self.p,'query':'budget'}),('document_create',{'project':self.p,'title':'attack','text':'x'})]:
            with self.subTest(action=action),self.assertRaises(Denied):self.w.action('b',{'action':action,**v})
        self.assertEqual(self.w.snapshot('b')['projects'],[]);self.assertEqual(self.w.snapshot('b')['jobs'],[])

    def test_revision_conflicts_retain_original(self):
        d=self.document();self.act('document_save',id=d,project=self.p,title='Budget',text='budget 3500',revision=1)
        with self.assertRaises(Conflict):self.act('document_save',id=d,project=self.p,title='Budget',text='budget 1',revision=1)
        self.assertEqual(self.act('document_get',id=d)['text'],'budget 3500')
        self.act('project_save',id=self.p,title='Nouveau',instructions='clair',revision=1)
        with self.assertRaises(Conflict):self.act('project_save',id=self.p,title='Ancien',instructions='',revision=1)

    def test_document_search_citations_and_delete(self):
        d=self.document();result=self.act('search',project=self.p,query='budget euros')
        self.assertEqual(result['sources'][0]['document'],d);self.assertIn('2500',result['sources'][0]['text'])
        self.act('document_delete',id=d,revision=1)
        self.assertEqual(self.act('search',project=self.p,query='budget euros')['sources'],[])

    def test_explicit_memory_and_permissions(self):
        self.document();m=self.act('memory_create',project=self.p,text='Utiliser les euros')['id']
        context,sources=self.w.context('a',[{'role':'user','content':'Quel budget ?'}],self.p)
        self.assertIn('Utiliser les euros',context[0]['content']);self.assertTrue(sources)
        self.assertNotIn('assistants',self.w.snapshot('a'))
        self.assertNotIn('assistants',self.w.snapshot('a')['capabilities'])
        self.act('memory_save',id=m,text='Utiliser les dollars');self.act('memory_delete',id=m)
        self.assertFalse(self.w.snapshot('a')['projects'][0]['memories'])

    def test_document_context_rejects_other_project(self):
        d=self.document();p=self.act('project_create',title='Autre')['id']
        with self.assertRaises(Denied):self.w.context('a',[{'role':'user','content':'budget'}],p,document=d)

    def test_conversation_publish_is_explicit_and_versioned(self):
        id=secrets.token_hex(16);messages=[{'role':'user','content':'privé'},{'role':'assistant','content':'réponse'}]
        self.assertEqual(self.w.snapshot('a')['projects'][0]['conversations'],[])
        self.act('conversation_save',project=self.p,id=id,title='Discussion',messages=messages)
        with self.assertRaises(Conflict):self.act('conversation_save',project=self.p,id=id,title='Discussion',messages=messages,revision=0)
        with self.assertRaises(Denied):self.w.action('b',{'action':'conversation_get','id':id})
        self.assertEqual(self.act('conversation_get',id=id)['messages'],messages)

    def test_move_archive_restore_and_delete_published_conversation(self):
        identity=secrets.token_hex(16);messages=[{'role':'user','content':'À conserver'}]
        target=self.act('project_create',title='Projet B')['id']
        self.act('conversation_save',project=self.p,id=identity,title='Discussion',messages=messages)
        self.assertEqual(self.act('conversation_move',id=identity,project=target,revision=1)['revision'],2)
        projects={p['id']:p for p in self.w.snapshot('a')['projects']}
        self.assertEqual(projects[self.p]['conversations'],[])
        self.assertEqual(projects[target]['conversations'][0]['id'],identity)
        with self.assertRaises(Conflict):self.act('conversation_archive',id=identity,archived=True,revision=1)
        self.act('conversation_archive',id=identity,archived=True,revision=2)
        reloaded=Workspace(self.home);stored=reloaded.action('a',{'action':'conversation_get','id':identity})
        self.assertEqual(stored['messages'],messages);self.assertEqual(stored['archived'],1)
        # Publishing an edited message must preserve the archive state.
        self.act('conversation_save',id=identity,project=target,title='Renommée',messages=messages,revision=3)
        self.assertEqual(self.act('conversation_get',id=identity)['archived'],1)
        self.act('conversation_archive',id=identity,archived=False,revision=4)
        self.act('conversation_delete',id=identity,revision=5)
        with self.assertRaises(Denied):self.act('conversation_get',id=identity)

    def test_conversation_actions_reject_other_owner_and_archived_destination(self):
        identity=secrets.token_hex(16);self.act('conversation_save',id=identity,project=self.p,title='Privée',messages=[])
        other=self.w.action('b',{'action':'project_create','title':'Autre accès'})['id']
        with self.assertRaises(Denied):self.act('conversation_move',id=identity,project=other,revision=1)
        for action,values in [('conversation_move',{'project':other}),('conversation_archive',{'archived':True}),('conversation_delete',{})]:
            with self.subTest(action=action),self.assertRaises(Denied):self.w.action('b',{'action':action,'id':identity,'revision':1,**values})
        target=self.act('project_create',title='Archivé')['id']
        self.act('project_save',id=target,title='Archivé',instructions='',archived=True,revision=1)
        with self.assertRaises(ValueError):self.act('conversation_move',id=identity,project=target,revision=1)
        with self.assertRaises(ValueError):self.act('conversation_archive',id=identity,archived=1,revision=1)
        self.assertEqual(self.act('conversation_get',id=identity)['revision'],1)

    def test_legacy_profiles_and_histories_are_removed_while_documents_survive(self):
        from workspace import LEGACY_SCHEMA
        legacy=sqlite3.connect(':memory:');legacy.executescript(LEGACY_SCHEMA)
        identity=secrets.token_hex(16)
        legacy.execute('INSERT INTO projects VALUES(?,?,?,?,0,1,?)',(self.p,'a','Ancien projet','',time.time()))
        legacy.execute('INSERT INTO conversations VALUES(?,?,?,?,?,?,?)',(identity,'a',self.p,'Ancienne discussion','[]',1,time.time()))
        legacy.execute("INSERT INTO assistants VALUES('code','Code','Anciennes consignes','documents',1)")
        legacy.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,1,?)',(identity,'a',self.p,'Note','Texte conservé',None,'note',time.time()))
        old={'currentId':identity,'conversations':[{'id':identity,'title':'Ancienne discussion','messages':[{'role':'user','content':'Ancien texte'}]}]}
        legacy.execute('INSERT INTO client_histories VALUES(?,?,1,?)',('a',json.dumps(old),time.time()))
        raw=legacy.serialize();legacy.close()
        validated=self.w.validate_backup(base64.b64encode(raw).decode(),{'a'})
        self.w.restore(validated)
        self.assertIsNone(self.w.history_read('a')['history'])
        self.assertEqual(self.w.snapshot('a')['projects'][0]['conversations'],[])
        self.assertEqual(self.act('document_get',id=identity)['text'],'Texte conservé')
        with self.w.db() as db:
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='assistants'").fetchone())
            self.assertNotIn('assistant',{r[1] for r in db.execute('PRAGMA table_info(jobs)')})
        # A new conversation survives later restarts; the reset happens once.
        self.act('conversation_save',id=identity,project=self.p,title='Nouvelle',messages=[])
        self.assertEqual(Workspace(self.home).snapshot('a')['projects'][0]['conversations'][0]['title'],'Nouvelle')

    def test_old_clients_cannot_republish_deleted_discussions(self):
        with self.assertRaises(Conflict):
            self.w.action('a',{'action':'conversation_save','id':secrets.token_hex(16),'project':self.p,'title':'Ancienne','messages':[]})

    def test_storage_and_project_quotas(self):
        self.w.admin_action({'action':'policy','owner':'a','limits':{**DEFAULT_LIMITS,'projects':1,'storage_mb':1}},{'a'})
        with self.assertRaises(ValueError):self.act('project_create',title='Débordement')
        with self.assertRaises(ValueError):self.document('x'*500000)
        self.assertEqual(self.w.snapshot('a')['projects'][0]['documents'],[])

    def test_job_idempotency_priority_and_restart(self):
        request_key=secrets.token_hex(16);args={'action':'job_create','project':self.p,'prompt':'Analyse','request_key':request_key}
        first=self.w.action('a',args);self.assertEqual(first,self.w.action('a',args))
        scheduler=Scheduler();active=scheduler.submit('x');scheduler.wait(active,lambda:True,lambda _:None)
        background=scheduler.submit('a',background=True);interactive=scheduler.submit('b');same_owner=scheduler.submit('a')
        self.assertEqual(scheduler.requests,[active,interactive,same_owner,background])
        with self.w.db() as db:db.execute("UPDATE jobs SET state='running'")
        reloaded=Workspace(self.home);self.assertEqual(reloaded.snapshot('a')['jobs'][0]['state'],'failed')

    def test_background_results_persist_and_recurrence(self):
        j=self.job(repeat_hours=24);self.w.valid=lambda owner:True;self.w.generation=lambda owner,messages,cancel:'Résultat sourcé'
        self.assertTrue(self.w.run_one());result=self.act('job_get',id=j)
        self.assertEqual(result['state'],'completed');self.assertEqual(json.loads(result['result'])['text'],'Résultat sourcé')
        jobs=self.w.snapshot('a')['jobs'];self.assertEqual(len(jobs),2);next_job=next(j for j in jobs if j['state']=='queued');self.assertEqual(next_job['parent'],j)
        self.assertGreater(next_job['due'],time.time()+23*3600)
        reloaded=Workspace(self.home);self.assertEqual(reloaded.action('a',{'action':'job_get','id':j})['state'],'completed')

    def test_cancel_running_job_prevents_publication(self):
        j=self.job();ready=threading.Event();release=threading.Event()
        def generate(owner,messages,cancel):ready.set();release.wait(3);return 'do not publish'
        self.w.generation=generate;thread=threading.Thread(target=self.w.run_one);thread.start();self.assertTrue(ready.wait(3))
        self.act('job_cancel',id=j);release.set();thread.join(4)
        result=self.act('job_get',id=j);self.assertEqual(result['state'],'cancelled');self.assertEqual(result['result'],'')

    def test_failure_pause_retry_and_disabled_access(self):
        j=self.job();self.act('job_pause',id=j);self.assertFalse(self.w.run_one());self.act('job_retry',id=j)
        self.w.valid=lambda owner:False;self.w.generation=lambda *args:self.fail('Inference must not execute')
        self.w.run_one();self.assertEqual(self.act('job_get',id=j)['state'],'failed')
        self.w.cancel_owner('a');self.assertEqual(self.act('job_get',id=j)['state'],'failed')

    def test_schedule_delay(self):
        j=self.job(delay_minutes=60);self.w.generation=lambda *args:self.fail('Scheduled job ran early')
        self.assertFalse(self.w.run_one());self.assertGreater(self.act('job_get',id=j)['due'],time.time()+3500)

    def test_empty_results_fail_and_code_indentation_is_preserved(self):
        d=self.document('    value = 1\n')
        self.assertEqual(self.act('document_get',id=d)['text'],'    value = 1\n')
        j=self.job();self.w.generation=lambda *args:'';self.w.run_one()
        self.assertEqual(self.act('job_get',id=j)['state'],'failed')

    def test_web_is_checked_per_client_and_server_without_profiles(self):
        with self.assertRaises(Denied):self.job(kind='web',url='https://example.com')
        self.w.admin_action({'action':'web_config','enabled':True},{'a'})
        with self.assertRaises(Denied):self.job(kind='web',url='https://example.com')
        self.w.admin_action({'action':'policy','owner':'a','limits':{**DEFAULT_LIMITS,'web':True}},{'a'})
        j=self.job(kind='web',url='https://example.com')
        with patch('workspace.fetch_public',return_value={'url':'https://example.com','text':'public facts'}):
            self.w.generation=lambda owner,messages,cancel:messages[0]['content'];self.w.run_one()
        self.assertIn('public facts',self.act('job_get',id=j)['result'])

    def test_ssrf_public_validation(self):
        for url in ['http://example.com','https://localhost','https://127.0.0.1','https://user:secret@example.com','https://example.com:8765','https://[::1]']:
            with self.subTest(url=url),self.assertRaises((ValueError,OSError)):public_url(url)
        with patch('workspace.socket.getaddrinfo',return_value=[(2,1,6,'',('10.0.0.1',443))]),self.assertRaises(ValueError):public_url('https://public.example')

    def test_bounded_parsers_utf8_pdf_and_docx(self):
        self.assertEqual(extract('note.txt','Résumé français'.encode()),['Résumé français'])
        for name,raw in [('x.txt',b'\xff'),('x.exe',b'MZ'),('x.pdf',b'not pdf'),('empty.txt',b''),('binary.txt',b'abc\x00')]:
            with self.subTest(name=name),self.assertRaises(ValueError):extract(name,raw)
        from docx import Document
        d=Document();d.add_paragraph('Budget approuvé : 2500 euros');data=io.BytesIO();d.save(data)
        self.assertIn('2500',extract('budget.docx',data.getvalue())[0])
        from pypdf import PdfWriter
        writer=PdfWriter();writer.add_blank_page(200,200);data=io.BytesIO();writer.write(data)
        with self.assertRaisesRegex(ValueError,'OCR'):extract('scan.pdf',data.getvalue())

    def test_web_decompression_bombs_and_truncated_gzip(self):
        import gzip
        from workspace import bounded_body
        class Response:
            def __init__(self,data):self.data=data
            def read(self,n):return self.data[:n]
            def getheader(self,*args):return 'gzip'
        self.assertEqual(bounded_body(Response(gzip.compress(b'public text'))),b'public text')
        with self.assertRaises(ValueError):bounded_body(Response(gzip.compress(b'x'*(2*1024*1024))))
        with self.assertRaises(ValueError):bounded_body(Response(gzip.compress(b'public text')[:-5]))

    def test_real_extraction_subprocess_upload(self):
        raw='Le budget est de 2500 euros.'.encode();d=self.act('document_upload',project=self.p,title='budget.txt',data=base64.b64encode(raw).decode())['id']
        self.assertEqual(self.act('document_get',id=d)['text'],raw.decode())
        self.assertEqual(base64.b64decode(self.act('document_download',id=d)['data']),raw)

    def test_backup_roundtrip_and_foreign_owner_rejection(self):
        d=self.document();j=self.job();value=self.w.backup()
        with self.assertRaises(ValueError):self.w.validate_backup(value,{'b'})
        raw=self.w.validate_backup(value,{'a'});self.w.restore(raw)
        self.assertEqual(self.act('document_get',id=d)['text'],'Le budget approuvé est de 2500 euros.')
        self.assertEqual(self.act('job_get',id=j)['state'],'failed')
        self.assertTrue(self.act('search',project=self.p,query='budget')['sources'])

    def test_backup_rejects_modified_schema(self):
        raw=base64.b64decode(self.w.backup());db=sqlite3.connect(':memory:');db.deserialize(raw);db.execute('CREATE TABLE evil(x)');bad=base64.b64encode(db.serialize()).decode();db.close()
        with self.assertRaisesRegex(ValueError,'Schéma'):self.w.validate_backup(bad,{'a'})

    def test_drafts_are_encrypted_and_windows_cannot_clear_each_other(self):
        from draft_store import DraftStore
        from client import protect
        settings=self.home/'local-settings.json';a=DraftStore(settings,protect);b=DraftStore(settings,protect)
        draft={'id':secrets.token_hex(16),'project':self.p,'title':'Privé','text':'brouillon confidentiel','revision':1}
        a.write(draft);b.write({**draft,'text':'autre fenêtre'});b.write(None)
        self.assertEqual(a.read()['draft'],draft);self.assertIsNone(b.read()['draft']);self.assertNotIn(b'confidentiel',a.path.read_bytes())
        recovered=DraftStore(settings,protect)
        with patch.object(DraftStore,'active',return_value=False):self.assertEqual(recovered.read()['draft'],draft)
        self.assertFalse(a.path.exists());self.assertEqual(recovered.read()['draft'],draft)

    def test_bad_drafts_preserve_previous_content(self):
        from draft_store import DraftStore
        from client import protect
        store=DraftStore(self.home/'local-settings.json',protect)
        draft={'id':secrets.token_hex(16),'project':self.p,'title':'Note','text':'Texte','revision':1};store.write(draft);before=store.path.read_bytes()
        for changes in [{'revision':False},{'id':'../../outside'},{'text':None},{'secret':'unexpected'}]:
            with self.assertRaises(ValueError):store.write({**draft,**changes})
        self.assertEqual(store.path.read_bytes(),before)

class GatewayWorkspaceTests(unittest.TestCase):
    def test_authenticated_gateway_with_real_wireguard(self):
        from test_remote import RemoteTests
        from wireguard_access import Engine
        from client import Remote
        fixture=RemoteTests();fixture.setUp()
        engine=Engine({'role':'server','wireguard':{'private_key':fixture.wireguard.vault()['private_key']},'listen_port':0,'upstream_port':fixture.gateway.server_port,'peers':fixture.wireguard.peers()})
        remote=Remote(fixture.profile,endpoint=f'127.0.0.1:{engine.port}')
        try:
                def post(value):
                    with remote.open('/v1/workspace/action',json.dumps(value).encode()) as response:return json.load(response)
                p=post({'action':'project_create','title':'Via tunnel'})['id']
                with remote.open('/v1/workspace') as response:self.assertEqual(json.load(response)['projects'][0]['id'],p)
                d=post({'action':'document_create','project':p,'title':'note','text':'Texte privé'})['id']
                self.assertEqual(post({'action':'document_get','id':d})['text'],'Texte privé')
                j=post({'action':'job_create','project':p,'prompt':'Résume le texte','request_key':secrets.token_hex(16)})['id']
                # The client tunnel is closed while the server completes the work.
                remote.close()
                deadline=time.monotonic()+10
                while time.monotonic()<deadline:
                    row=fixture.store.workspace.action(fixture.access['id'],{'action':'job_get','id':j})
                    if row['state'] in ('completed','failed'):break
                    time.sleep(.1)
                self.assertEqual(row['state'],'completed',row['error'])
                result=post({'action':'job_get','id':j})
                self.assertEqual(json.loads(result['result'])['text'],'Bonjour')
                fixture.store.revoke(fixture.access['id'])
                with self.assertRaises(urllib.error.HTTPError) as error:remote.open('/v1/workspace')
                self.assertEqual(error.exception.code,401)
        finally:
            if remote.bridge:remote.bridge.close()
            engine.close();fixture.tearDown()

    def test_encrypted_operations_backup_contains_spaces_and_restores(self):
        from app import Controller
        from test_remote import RemoteTests
        fixture=RemoteTests();fixture.setUp()
        try:
            c=Controller(fixture.temporary.name,include_legacy=False);c.remote=fixture.store;c.wireguard=fixture.wireguard
            owner=fixture.access['id'];w=c.remote.workspace
            p=w.action(owner,{'action':'project_create','title':'Original'})['id']
            d=w.action(owner,{'action':'document_upload','project':p,'title':'privé.txt','data':base64.b64encode('texte confidentiel de test'.encode()).decode()})['id']
            backup=c.operations.backup('workspace backup password example')
            self.assertNotIn(b'texte confidentiel',Path(backup['file']).read_bytes())
            w.action(owner,{'action':'document_save','id':d,'project':p,'title':'Modifié','text':'nouvelle version','revision':1})
            fixture.store.configure({'enabled':False,'url':'wireguard://10.77.0.1:8766'})
            with patch.object(c,'processes',return_value=[]),patch.object(c,'supervisor',return_value=None):
                c.operations.restore({'file':backup['file'],'password':'workspace backup password example'})
            restored=w.action(owner,{'action':'document_get','id':d});self.assertIn('confidentiel',restored['text'])
            self.assertEqual(base64.b64decode(w.action(owner,{'action':'document_download','id':d})['data']),'texte confidentiel de test'.encode())
        finally:fixture.tearDown()

if __name__=='__main__':unittest.main()
