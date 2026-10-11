"""Provider sharing, native credential helpers and selected-model isolation."""
import copy
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core import HIDDEN, read_json, write_json
from hermes_accounts import CONFIG_VERSION, HermesAccounts, profile_name
from hermes_conversations import HermesConversations
from hermes_fred import HermesFred
from hermes_inference import HermesPrivateServer
from hermes_models import HermesModels, ModelUnavailable, NativeModelSource, normalize_policy
from hermes_service import child_environment, installation
from remote import AccessStore
from test_hermes_accounts import fake_profile
from test_hermes_conversations import Service
from workspace import Conflict, Denied, HISTORY_RESET_ID


class Source:
    def __init__(self, endpoint='https://provider.invalid/v1'):
        self.runtime = None
        self.key = 'fixture-provider-key'
        self.rows = [{'provider':'fixture','label':'Provider fixture','configured':True,
            'base_url':endpoint,'api_mode':'chat_completions','models':[
                {'id':'model-a','name':'Model A','context_length':131072,'capabilities':{'vision':True,'thinking':True}},
                {'id':'model-b','name':'Model B','context_length':65536}]}]
        self.calls = []
    def discover(self):return {'providers':copy.deepcopy(self.rows)}
    def credential(self, provider, model):
        self.calls.append((provider,model))
        row=next(row for row in self.rows if row['provider']==provider)
        item=next(item for item in row['models'] if item['id']==model)
        return {'api_key':self.key,'base_url':row['base_url'],'api_mode':item.get('api_mode',row['api_mode'])}


class ModelsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='fred-model-policy-')
        self.store=AccessStore(Path(self.tmp.name))
        self.store.configure({'enabled':True,'url':'wireguard://10.77.0.1:8766'})
        self.a=self.store.issue('A')['id'];self.b=self.store.issue('B')['id']
        self.accounts=HermesAccounts(self.store.home,authorized=self.store.valid_owner,profile_factory=fake_profile)
        self.accounts.ensure(self.a);self.accounts.ensure(self.b)
        self.source=Source()
        self.models=HermesModels(self.store,lambda:(1,'actual-local','local-private-key'),self.accounts,source=self.source)
        self.accounts.models=self.models
        self.live=patch('hermes_models.health',return_value={'loaded':True,'model':'actual-local','images':True})
        self.live.start()
        self.service=Service()
        self.manager=HermesConversations(self.store,self.accounts,self.service)
        self.manager.models=self.models
        self.private=HermesPrivateServer(self.store,lambda: (_ for _ in ()).throw(AssertionError('Qwen must remain unloaded')))
        self.private.accounts=self.accounts;self.private.conversations=self.manager;self.private.models=self.models
        self.private.start()
    def tearDown(self):
        for context in self.manager.active.values():context['cancelled'].set()
        self.manager.active.clear();self.store.active=0
        self.manager.close();self.private.close();self.accounts.clear_runtime_secrets()
        self.store.workspace.shutdown();self.store.voice.close();self.live.stop();self.tmp.cleanup()
    def shared(self):
        self.models.configure({'share_all':True})
        return self.models.catalog(self.a)['data'][1:]
    def prepare(self, model, request=None, conversation='discussion'):
        return self.manager._prepare(self.a,{'model':model,'messages':[{'role':'user','content':'Question'}]},
            request or secrets.token_hex(16),conversation,None,None,False)[1]
    def clear(self):self.manager.active.clear();self.store.active=0
    def post(self, value, owner=None, token=None, path='/v1/provider/credential'):
        token=token or self.accounts.credentials(owner or self.a)['inference_key']
        request=urllib.request.Request(self.private.url+path,json.dumps(value).encode(),headers={
            'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(request,timeout=5) as response:return response.status,json.loads(response.read())
        except urllib.error.HTTPError as response:return response.code,json.loads(response.read())
    def test_default_is_local_and_public_catalog_contains_no_server_route_or_secrets(self):
        public=self.models.catalog(self.a)
        self.assertEqual(public['default_model'],'fred-qwen');self.assertEqual(public['source'],'hermes')
        self.assertEqual(len(public['data']),1)
        caps=public['data'][0]['capabilities']
        self.assertEqual(caps['files'],['txt','md','pdf','docx']);self.assertTrue(caps['thinking'])
        self.assertGreater(caps['max_file_bytes'],0)
        rows=self.shared();self.assertEqual(len(rows),2)
        raw=json.dumps(self.models.admin())
        for secret in (self.source.key,'provider.invalid','local-private-key','base_url','key_cmd','native_provider'):
            self.assertNotIn(secret,raw)
        self.assertTrue(rows[0]['capabilities']['vision']);self.assertTrue(rows[0]['capabilities']['images'])
        self.assertFalse(rows[1]['capabilities']['thinking'])
    def test_per_account_sharing_and_revocation_are_enforced_on_each_use(self):
        rows=self.models.admin()['models'];selection_id=rows[0]['id']
        self.models.configure({'shared_accounts':[self.a]})
        self.assertEqual(len(self.models.catalog(self.a)['data']),3)
        self.assertEqual(len(self.models.catalog(self.b)['data']),1)
        with self.assertRaises(Denied):self.models.select(self.b,selection_id)
        selection=self.models.select(self.a,selection_id)
        self.assertTrue(self.models.valid(self.a,selection))
        self.models.configure({'shared_accounts':[]})
        self.assertFalse(self.models.valid(self.a,selection))
        with self.assertRaises(Denied):self.models.credential(self.a,selection)
        self.models.configure({'share_all':True});self.store.revoke(self.a)
        self.assertFalse(self.models.valid(self.a,selection))
        with self.assertRaises(Denied):self.models.catalog(self.a)
    def test_policy_schema_is_strict_and_unknown_accounts_cannot_receive_grants(self):
        for value in ({'share_all':'yes'},{'version':True},{'shared_accounts':['../a']},{'api_key':'secret'},[],None):
            with self.subTest(value=value),self.assertRaises(ValueError):normalize_policy(value)
        with self.assertRaises(ValueError):self.models.configure({'shared_accounts':['0'*16]})
        with self.assertRaises(ValueError):self.models.configure({'version':1})
        self.assertEqual(normalize_policy({'shared_accounts':[self.a,self.a]})['shared_accounts'],[self.a])
        write_json(self.models.path,{'share_all':'bad'})
        self.assertFalse(self.models.allowed(self.a))
    def test_local_alias_compatibility_and_cloud_stays_available_with_qwen_unloaded(self):
        rows=self.shared();self.assertEqual(self.models.select(self.a,'actual-local')['id'],'fred-qwen')
        with patch('hermes_models.health',return_value={'loaded':False}):
            with self.assertRaises(ModelUnavailable):self.models.select(self.a)
            selected=self.models.select(self.a,rows[0]['id'])
            self.assertFalse(selected['local']);self.assertTrue(selected['available'])
        for bad in ('model-a','https://evil','custom:fixture',{'provider':'fixture'}):
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.models.select(self.a,bad)
    def test_discovery_uses_valid_configured_providers_and_preserves_empty_metadata(self):
        self.source.rows += [
            {'provider':'empty','label':'Empty connected','configured':True,'base_url':'https://empty.invalid','models':[]},
            {'provider':'bad','label':'Bad endpoint','configured':True,'base_url':'http://remote.invalid','models':[{'id':'x'}]},
            {'provider':'unconfigured','label':'No credentials','configured':False,'base_url':'https://unused.invalid','models':[{'id':'x'}]}]
        admin=self.models.admin()
        self.assertEqual([(r['label'],r['model_count']) for r in admin['providers']],
            [('Provider fixture',2),('Empty connected',0)])
        self.source.discover=lambda: (_ for _ in ()).throw(ValueError(self.source.key))
        self.models.refresh(force=True)
        self.assertNotIn(self.source.key,self.models.admin()['error'])
    def test_newly_discovered_model_is_materialized_before_native_admission(self):
        rows=self.shared();self.prepare(rows[0]['id']);self.clear()
        self.source.rows[0]['models'].append({'id':'late-model','name':'Late model'})
        self.models.refresh(force=True)
        selected=self.models.admin()['models'][-1]['id'];context=self.prepare(selected)
        config=read_json(self.accounts.root/'profiles'/profile_name(self.a)/'config.yaml')
        self.assertIn(selected,config['providers'])
        self.assertEqual(context['body']['provider'],'custom:'+selected)
        self.assertEqual(context['body']['model'],'late-model')
        self.assertNotIn(self.source.key,json.dumps(config))
        self.assertNotIn('context_length',config['providers'][selected])
    def test_request_identity_includes_model_and_model_switch_branches_session(self):
        rows=self.shared();request=secrets.token_hex(16)
        context=self.prepare(rows[0]['id'],request);first=context['body']['session_id'];self.clear()
        with self.assertRaises(Conflict):self.prepare(rows[1]['id'],request)
        second=self.prepare(rows[1]['id'])['body']['session_id'];self.assertNotEqual(first,second)
    def test_history_projection_keeps_selected_model_and_does_not_merge_other_model(self):
        selected=self.shared()[0]['id'];request=secrets.token_hex(16)
        history={'currentId':'discussion','conversations':[{'id':'discussion','title':'Test','model':selected,
            'messages':[{'role':'user','content':'Question','turn_id':request}]}]}
        self.store.workspace.history_write(self.a,{'history':history,'revision':0,'reset_id':HISTORY_RESET_ID})
        list(self.manager.stream(self.a,{'model':selected,'messages':[{'role':'user','content':'Question'}]},request,'discussion'))
        saved=self.store.workspace.history_read(self.a)['history']['conversations'][0]
        self.assertEqual(saved['model'],selected);self.assertEqual(len(saved['messages']),2)
        self.assertEqual(self.manager.reconcile(self.a,request,'discussion')['model'],selected)
        changed=copy.deepcopy(history);changed['conversations'][0]['model']='fred-qwen'
        self.manager.merge_completed(self.a,changed)
        self.assertEqual(len(changed['conversations'][0]['messages']),1)
    def test_private_broker_authenticates_active_owner_model_and_live_policy(self):
        selected=self.shared()[0]['id'];value={'model_id':selected}
        self.assertEqual(self.post(value,token='invalid')[0],401)
        self.assertEqual(self.post(value)[0],401)
        self.prepare(selected)
        self.assertEqual(self.post(value,owner=self.b)[0],401)
        self.assertEqual(self.post({'model_id':'fred-model-'+'f'*24})[0],403)
        self.assertEqual(self.post({**value,'base_url':'https://evil'})[0],403)
        status,answer=self.post(value)
        self.assertEqual(status,200);self.assertEqual(answer['access_token'],self.source.key)
        self.assertEqual(self.source.calls,[('fixture','model-a')])
        self.assertEqual(self.post({'messages':[{'role':'user','content':'Q'}]},path='/v1/chat/completions')[0],403)
        self.models.configure({'share_all':False})
        self.assertEqual(self.post(value)[0],401)
    def test_private_broker_refuses_changed_endpoint_and_does_not_expose_errors(self):
        selected=self.shared()[0]['id'];self.prepare(selected)
        self.source.rows[0]['base_url']='https://changed.invalid'
        status,answer=self.post({'model_id':selected})
        self.assertEqual(status,403)
        self.assertNotIn('changed.invalid',json.dumps(answer));self.assertNotIn(self.source.key,json.dumps(answer))
    def test_fixed_native_key_helper_requires_private_run_and_returns_only_bounded_token(self):
        selected=self.shared()[0]['id'];self.prepare(selected)
        runtime=installation();env=child_environment(self.accounts.root/'profiles'/profile_name(self.a),runtime)
        env['FRED_INFERENCE_KEY']=self.accounts.credentials(self.a)['inference_key']
        env['FRED_PROVIDER_URL']=self.private.url+'/v1/provider/credential'
        helper=Path(__file__).with_name('hermes_model_key.py')
        result=subprocess.run([str(runtime['python']),str(helper),selected],env=env,
            capture_output=True,timeout=15,creationflags=HIDDEN)
        self.assertEqual(result.returncode,0);self.assertEqual(result.stderr,b'')
        self.assertEqual(json.loads(result.stdout),{'access_token':self.source.key,'expires_in':1})
        self.manager.context(self.a)['cancelled'].set()
        result=subprocess.run([str(runtime['python']),str(helper),selected],env=env,
            capture_output=True,timeout=15,creationflags=HIDDEN)
        self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'');self.assertEqual(result.stderr,b'')
    def test_profile_migration_keeps_identity_and_binds_all_auxiliary_tasks_to_main(self):
        owner=self.a;before=self.accounts.credentials(owner);directory=self.accounts.root/'profiles'/profile_name(owner)
        (directory/'identity-fixture.txt').write_text('keep',encoding='utf-8')
        with self.accounts._db() as db:db.execute('UPDATE hermes_bindings SET config_version=? WHERE owner=?',(CONFIG_VERSION-1,owner))
        self.accounts.ensure(owner)
        self.assertEqual(before,self.accounts.credentials(owner));self.assertEqual((directory/'identity-fixture.txt').read_text(),'keep')
        config=read_json(directory/'config.yaml')
        for task,value in config['auxiliary'].items():
            if task=='refine':continue
            self.assertEqual(value['provider'],'main');self.assertEqual(value['fallback_chain'],[])
            self.assertNotIn('api_key',value);self.assertNotIn('base_url',value)
    def test_native_credential_requests_coalesce_same_model_but_other_provider_is_independent(self):
        source=NativeModelSource();entered=threading.Event();release=threading.Event();calls=[];results=[]
        def run(operation,timeout,**values):
            calls.append((values['provider'],values['model']))
            if values['provider']=='slow':entered.set();self.assertTrue(release.wait(3))
            return {'api_key':'fixture','base_url':'https://provider.invalid','api_mode':'chat_completions'}
        source._run=run
        first=threading.Thread(target=lambda:results.append(source.credential('slow','same')))
        second=threading.Thread(target=lambda:results.append(source.credential('slow','same')))
        first.start();self.assertTrue(entered.wait(1));second.start()
        try:
            start=time.monotonic();source.credential('other','same')
            self.assertLess(time.monotonic()-start,.5)
        finally:release.set();first.join(3);second.join(3)
        self.assertEqual(len(results),2);self.assertEqual(calls.count(('slow','same')),1)
        source.credential('slow','different')
        self.assertIn(('slow','different'),calls)
    def test_native_credential_wait_is_bounded_and_near_expiry_tokens_are_not_cached(self):
        source=NativeModelSource();calls=[]
        def run(operation,timeout,**values):
            calls.append(timeout)
            return {'api_key':'fixture','expires_at':time.time()+1}
        source._run=run
        source.credential('provider','model');source.credential('provider','model')
        self.assertEqual(len(calls),2);self.assertTrue(all(0<timeout<=11.5 for timeout in calls))
        guard=source.provider_locks['provider'];guard.acquire()
        try:
            # Fast test for the wait fence: advance the deadline once established.
            actual=time.monotonic()
            with patch('hermes_models.time.monotonic',side_effect=[actual,actual+12]):
                with self.assertRaises(ModelUnavailable):source.credential('provider','model')
        finally:guard.release()
    def test_low_context_cloud_is_visible_but_cannot_be_selected(self):
        self.source.rows[0]['models'][0]['context_length']=32000
        selected=self.shared()[0]
        self.assertFalse(selected['available'])
        with self.assertRaises(ModelUnavailable):self.models.select(self.a,selected['id'])
    def test_incomplete_copilot_is_visible_unavailable_and_cannot_receive_credentials(self):
        self.source.rows[0].update(provider='copilot',label='GitHub Copilot',available=False)
        selected=self.shared()[0]
        self.assertFalse(selected['available'])
        provider=self.models.admin()['providers'][0]
        self.assertFalse(provider['available']);self.assertEqual(provider['model_count'],2)
        self.assertEqual(provider['unavailable_reason'],'Connexion Copilot incomplète ou non autorisée.')
        with self.assertRaises(ModelUnavailable):self.models.select(self.a,selected['id'])
        stale=self.models.select(self.a,selected['id'],require_available=False)
        with self.assertRaises(Denied):self.models.credential(self.a,stale)
        self.assertEqual(self.source.calls,[])
    def test_refresh_revokes_model_that_becomes_unavailable_and_keeps_native_efforts(self):
        self.source.rows[0]['models'][0]['capabilities']['reasoning_efforts']=['low','high','xhigh']
        selected=self.shared()[0];selection=self.models.select(self.a,selected['id'])
        self.assertEqual(selected['capabilities']['reasoning_efforts'],['low','high','xhigh'])
        self.assertTrue(self.models.valid(self.a,selection))
        self.source.rows[0]['models'][0]['available']=False
        self.models.refresh(force=True)
        self.assertFalse(self.models.valid(self.a,selection))
        with self.assertRaises(Denied):self.models.credential(self.a,selection)


class CloudFixture:
    """Actual HTTP chat/Responses endpoints; no external provider traffic."""
    def __init__(self):
        self.calls=[]
        fixture=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def reply(self,value):
                raw=json.dumps(value).encode();self.send_response(200)
                self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)))
                self.end_headers();self.wfile.write(raw)
            def do_GET(self):
                self.reply({'object':'list','data':[{'id':'model-a'},{'id':'model-b'}]})
            def do_POST(self):
                data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                fixture.calls.append((self.path,self.headers.get('Authorization'),data))
                model=data.get('model','model-a')
                if self.path.endswith('/responses'):
                    response={'id':'resp_fixture','object':'response','created_at':int(time.time()),'status':'completed',
                        'model':model,'output':[{'id':'msg_fixture','type':'message','role':'assistant','status':'completed',
                            'content':[{'type':'output_text','text':'Native cloud reply','annotations':[]}]}],
                        'usage':{'input_tokens':2,'output_tokens':3,'total_tokens':5}}
                    if data.get('stream'):
                        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                        events=[{'type':'response.output_item.done','sequence_number':0,'output_index':0,'item':response['output'][0]},
                            {'type':'response.completed','sequence_number':1,'response':response}]
                        for event in events:self.wfile.write(('event: '+event['type']+'\ndata: '+json.dumps(event)+'\n\n').encode())
                    else:self.reply(response)
                elif self.path.endswith('/chat/completions'):
                    if data.get('stream'):
                        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                        event={'id':'chat_fixture','object':'chat.completion.chunk','created':int(time.time()),'model':model,
                            'choices':[{'index':0,'delta':{'role':'assistant','content':'Native cloud reply'},'finish_reason':None}]}
                        self.wfile.write(('data: '+json.dumps(event)+'\n\n').encode())
                        event['choices']=[{'index':0,'delta':{},'finish_reason':'stop'}]
                        self.wfile.write(('data: '+json.dumps(event)+'\n\ndata: [DONE]\n\n').encode())
                    else:self.reply({'id':'chat_fixture','object':'chat.completion','created':int(time.time()),'model':model,
                        'choices':[{'index':0,'message':{'role':'assistant','content':'Native cloud reply'},'finish_reason':'stop'}],
                        'usage':{'prompt_tokens':2,'completion_tokens':3,'total_tokens':5}})
                else:self.send_error(404)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.url='http://127.0.0.1:'+str(self.server.server_port)+'/v1'
    def close(self):self.server.shutdown();self.server.server_close()


_SOURCE=Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData/Local'))/'hermes/hermes-agent'
@unittest.skipUnless(os.name=='nt' and (_SOURCE/'hermes_cli/main.py').is_file(),'Installed native Hermes required.')
class NativeCloudTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='fred-native-cloud-')
        self.store=AccessStore(Path(self.tmp.name))
        self.store.configure({'enabled':True,'url':'wireguard://10.77.0.1:8766'})
        self.owner=self.store.issue('Isolated cloud test')['id']
        self.cloud=CloudFixture();self.source=Source(self.cloud.url)
        self.source.rows[0]['models'][1]['api_mode']='codex_responses'
        self.facade=HermesFred(self.store,lambda: (_ for _ in ()).throw(AssertionError('Qwen disabled')),port=0,private_port=0)
        self.facade.models.source=self.source
        self.facade.models.configure({'share_all':True})
        self.store.hermes=self.facade
    def tearDown(self):
        self.facade.close();self.store.hermes=None
        self.cloud.close();self.store.workspace.shutdown();self.store.voice.close();self.tmp.cleanup()
    def test_actual_native_gateway_selects_shared_cloud_and_preserves_private_session(self):
        self.facade.start()
        for item in self.facade.model_catalog(self.owner)['data'][1:]:
            with self.subTest(model=item['name']):
                request=secrets.token_hex(16)
                events=list(self.facade.stream(self.owner,{'model':item['id'],'messages':[{'role':'user','content':'Reply briefly.'}]},
                    request,'native-'+item['name']))
                self.assertIn(b'Native cloud reply',b''.join(events))
                self.assertEqual(self.facade.conversations.reconcile(self.owner,request,'native-'+item['name'])['status'],'completed')
        self.assertTrue(self.source.calls)
        self.assertTrue(self.cloud.calls)
        self.assertTrue(all(auth=='Bearer '+self.source.key for _,auth,_ in self.cloud.calls))
        self.assertEqual({body['model'] for _,_,body in self.cloud.calls},{'model-a','model-b'})
        profile=self.facade.accounts.root/'profiles'/profile_name(self.owner)
        self.assertNotIn(self.source.key,(profile/'.env').read_text())
        self.assertNotIn(self.source.key,(profile/'config.yaml').read_text())
        self.assertEqual(self.store.scheduler.snapshot()['active'],0)
    def test_native_key_cmd_and_auxiliary_main_cover_chat_and_responses_without_qwen(self):
        # Real installed SDK clients, provider resolver, key_cmd and Fred broker.
        # Only the network/model endpoint is synthetic.
        self.facade.private.start()
        self.facade.accounts.ensure(self.owner)
        runtime=installation()
        script=r'''
import contextlib,io,json,logging,sys
logging.disable(logging.CRITICAL)
data=json.load(sys.stdin)
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
 from hermes_constants import get_hermes_home
 from dotenv import load_dotenv
 load_dotenv(get_hermes_home()/'.env',override=True)
 from hermes_cli.runtime_provider import resolve_runtime_provider
 from agent.auxiliary_client import set_runtime_main,get_text_auxiliary_client
 native=resolve_runtime_provider(requested=data['provider'],target_model=data['model'])
 set_runtime_main(native['provider'],data['model'],base_url=native['base_url'],api_key=native['api_key'],api_mode=native['api_mode'])
 client,model=get_text_auxiliary_client('compression')
 reply=client.chat.completions.create(model=model,messages=[{'role':'user','content':'Small compression fixture'}],max_tokens=24)
 result={'text':reply.choices[0].message.content,'model':model,'mode':native['api_mode'],'callable_key':callable(native['api_key'])}
print(json.dumps(result))
'''
        for item in self.facade.model_catalog(self.owner)['data'][1:]:
            with self.subTest(model=item['name']):
                context=self.facade.conversations._prepare(self.owner,{'model':item['id'],'messages':[{'role':'user','content':'Q'}]},
                    secrets.token_hex(16),'aux-'+item['name'],None,None,False)[1]
                try:
                    selection=context['model_selection'];profile=self.facade.accounts.root/'profiles'/profile_name(self.owner)
                    result=subprocess.run([str(runtime['python']),'-c',script],input=json.dumps({
                        'provider':selection['native_provider'],'model':selection['native_model']}).encode(),
                        env=child_environment(profile,runtime),cwd=runtime['source'],capture_output=True,timeout=40,creationflags=HIDDEN)
                    self.assertEqual(result.returncode,0,'Native auxiliary client failed (output intentionally private).')
                    answer=json.loads(result.stdout);self.assertEqual(answer['text'],'Native cloud reply')
                    self.assertEqual(answer['model'],item['name']);self.assertTrue(answer['callable_key'])
                    self.assertEqual(answer['mode'],selection['api_mode'])
                finally:self.facade.conversations.active.clear();self.store.active=0
        self.assertEqual({path for path,_,_ in self.cloud.calls},{'/v1/chat/completions','/v1/responses'})
        self.assertTrue(all(auth=='Bearer '+self.source.key for _,auth,_ in self.cloud.calls))
    def test_native_inventory_discovers_configured_endpoint_without_cold_cache(self):
        personal=Path(self.tmp.name)/'isolated-personal';personal.mkdir()
        write_json(personal/'config.yaml',{'model':{'provider':'custom:fixture','default':'model-a'},
            'providers':{'fixture':{'name':'Inventory fixture','base_url':self.cloud.url,'key_env':'FIXTURE_PROVIDER_KEY'}}})
        (personal/'.env').write_text('FIXTURE_PROVIDER_KEY=fixture-provider-key\n',encoding='utf-8')
        source=NativeModelSource(installation(),personal_home=personal)
        discovered=source.discover()
        rows=[row for row in discovered['providers'] if row['label']=='Inventory fixture']
        self.assertEqual(len(rows),1)
        self.assertEqual({item['id'] for item in rows[0]['models']},{'model-a','model-b'})
        self.assertNotIn(self.source.key,json.dumps(discovered))
    def test_native_copilot_uses_live_limits_endpoints_and_rejects_degraded_github_key(self):
        # Pinned native imports/helpers run in a real subprocess. Auth/catalogue
        # responses are fixtures so neither a login nor a paid inference occurs.
        import hermes_models
        personal=Path(self.tmp.name)/'isolated-copilot';personal.mkdir()
        write_json(personal/'config.yaml',{'model':''})
        source=NativeModelSource(installation(),personal_home=personal)
        catalog=[{'id':'gpt-5-mini','name':'Live mini','model_picker_enabled':True,
            'supported_endpoints':['/responses'],'capabilities':{'type':'chat',
                'limits':{'max_prompt_tokens':128000,'max_context_window_tokens':264000},
                'supports':{'vision':True,'reasoning_effort':['low','high']}}}]
        original=hermes_models._NATIVE
        for degraded in (True,False):
            with self.subTest(degraded=degraded):
                preamble='''
import contextlib,io
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
 from hermes_cli import inventory,models,runtime_provider,copilot_auth
 inventory.build_models_payload=lambda *a,**k: {'providers':[{'slug':'copilot','name':'GitHub Copilot','authenticated':True,'models':['obsolete-cached-model']}]}
 runtime_provider.resolve_runtime_provider=lambda *a,**k: {'api_key':'fixture-central-key','base_url':'https://api.githubcopilot.com','api_mode':'chat_completions'}
 copilot_auth.validate_copilot_token=lambda *a,**k: (DEGRADED,'fixture')
 models.fetch_github_model_catalog=lambda *a,**k: CATALOG
'''.replace('DEGRADED',repr(degraded)).replace('CATALOG',repr(catalog))
                with patch('hermes_models._NATIVE',preamble+original):
                    provider=source.discover()['providers'][0]
                    self.assertEqual(provider['available'],not degraded)
                    item=provider['models'][0]
                    self.assertEqual(item['id'],'gpt-5-mini')
                    self.assertEqual(item['context_length'],128000)
                    self.assertEqual(item['api_mode'],'codex_responses')
                    self.assertTrue(item['capabilities']['vision'])
                    self.assertEqual(item['capabilities']['reasoning_efforts'],['low','high'])
                    self.assertNotIn('fixture-central-key',json.dumps(provider))
                    if degraded:
                        with self.assertRaises(ModelUnavailable):source.credential('copilot','gpt-5-mini')
                    else:
                        credential=source.credential('copilot','gpt-5-mini')
                        self.assertEqual(credential['api_mode'],'codex_responses')


if __name__=='__main__':unittest.main()
