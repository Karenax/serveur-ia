"""Direct local oral turns use the protected gateway, never Hermes or a cloud model."""
import json
import secrets
import unittest
from unittest.mock import patch
import test_text_transform as fixtures
from test_text_transform import UnavailableHermes
from workspace import Denied


class VoiceConversationHTTPTests(unittest.TestCase):
    setUp=fixtures.TextTransformHTTPTests.setUp
    tearDown=fixtures.TextTransformHTTPTests.tearDown
    post=fixtures.TextTransformHTTPTests.post
    worker=fixtures.TextTransformHTTPTests.worker
    settle=fixtures.TextTransformHTTPTests.settle

    @staticmethod
    def body(request):
        return {'voice_conversation':True,'conversation_id':'oral-conversation','turn_id':request,'model':'ignored-cloud',
                'messages':[{'role':'user','content':'Bonjour, tu m’entends ?'}],'stream':True}

    def test_oral_turn_bypasses_broken_hermes_and_disables_thinking(self):
        class Broken(UnavailableHermes):
            def select_model(self,*args):raise AssertionError('Voice must not query Hermes.')
        self.store.hermes=Broken();request=secrets.token_hex(16);value=self.body(request)
        value.update(reasoning_effort='high',chat_template_kwargs={'enable_thinking':True})
        value['messages'].insert(0,{'role':'assistant','content':'Texte précédent.','reasoning_content':'Ancienne réflexion.'})
        status,raw=self.post(value,request)
        self.assertEqual(200,status);self.assertIn(b'[DONE]',raw);self.assertNotIn(b'hermes',raw)
        headers,data=self.captured[-1]
        self.assertEqual('actual-local',data['model']);self.assertEqual(100000,data['max_tokens'])
        self.assertEqual('none',data['reasoning_effort']);self.assertEqual({'enable_thinking':False},data['chat_template_kwargs'])
        self.assertFalse(data['strata_mcp']);self.assertEqual('system',data['messages'][0]['role'])
        self.assertIn('Tu es Kiara',data['messages'][0]['content'])
        self.assertNotIn('reasoning_content',data['messages'][1]);self.settle()

    def test_silent_model_sends_keepalive_before_headers_and_keeps_one_request(self):
        import json,threading,urllib.request
        self.block_model=True;self.block_seconds=10;request=secrets.token_hex(16)
        keepalive=threading.Event();received=[];errors=[]
        def read():
            try:
                call=urllib.request.Request(f'http://127.0.0.1:{self.gateway.server_port}/v1/chat/completions',json.dumps(self.body(request)).encode(),
                    {'Authorization':'Bearer '+self.a['token'],'Content-Type':'application/json','X-Qwen-Request':request})
                with urllib.request.urlopen(call,timeout=7) as response:
                    for line in response:
                        received.append(line)
                        if line.startswith(b': qwen-keepalive'):keepalive.set()
            except Exception as error:errors.append(error)
        thread=threading.Thread(target=read);thread.start()
        try:
            self.assertTrue(self.model_ready.wait(3));self.assertTrue(keepalive.wait(7))
            self.assertNotIn(b'Texte corrige',b''.join(received))
        finally:self.model_release.set();thread.join(4)
        self.assertFalse(thread.is_alive());self.assertEqual([],errors)
        self.assertIn(b'[DONE]',b''.join(received));self.assertEqual(1,len(self.captured));self.settle()

    def test_invalid_mode_identity_and_tools_cannot_reach_upstream(self):
        request=secrets.token_hex(16)
        for change in ({'voice_conversation':False},{'voice_conversation':1},{'turn_id':'other'},
                       {'conversation_id':None},{'tools':[]},{'text_transform':{'mode':'correct','text':'x'}}):
            with self.subTest(change=change):self.assertEqual(400,self.post({**self.body(request),**change},request)[0])
        self.assertEqual(400,self.post(self.body(request),request,path='/v1/context')[0])
        self.assertEqual([],self.captured)

    def test_project_context_stays_scoped_to_the_authenticated_owner(self):
        request=secrets.token_hex(16);value={**self.body(request),'project_id':'private-project'}
        with patch.object(self.store.workspace,'context',return_value=(value['messages'],[])) as context:
            self.assertEqual(200,self.post(value,request)[0]);self.assertEqual(self.a['id'],context.call_args.args[0])
            self.assertEqual(value['conversation_id'],context.call_args.kwargs['voice_conversation'])
        with patch.object(self.store.workspace,'context',side_effect=Denied('Projet privé.')):
            other=secrets.token_hex(16)
            self.assertEqual(403,self.post({**value,'turn_id':other},other)[0])

    def test_model_capacity_is_applied_by_server_without_modifying_caller_history(self):
        from copy import deepcopy
        request=secrets.token_hex(16);value=self.body(request)
        value['messages']=[{'role':'system','content':'Instructions à préserver.'}]
        for i in range(36):value['messages'] += [{'role':'user','content':str(i)+' question '+('mot '*4000)},{'role':'assistant','content':'réponse '+('mot '*4000)}]
        value['messages'].append({'role':'user','content':'La question finale à préserver.'})
        original=deepcopy(value);status,raw=self.post(value,request)
        self.assertEqual(200,status);self.assertEqual(value,original);self.assertIn(b'voice_context',raw)
        sent=self.captured[-1][1];self.assertEqual('La question finale à préserver.',sent['messages'][-1]['content'])
        self.assertLess(len(sent['messages']),len(value['messages']))
        self.assertLessEqual(sum(len(json.dumps(m)) for m in sent['messages'])//4+20,162144)

    def test_cancel_before_submit_and_during_silent_response(self):
        request=secrets.token_hex(16)
        self.assertEqual(200,self.post({'voice_conversation':True},request,path='/v1/cancel')[0])
        self.assertEqual(400,self.post(self.body(request),request)[0]);self.assertEqual([],self.captured)
        self.block_after_headers=True;request=secrets.token_hex(16)
        thread,results,errors=self.worker(self.body(request),request)
        try:
            self.assertTrue(self.model_ready.wait(5))
            self.assertEqual(200,self.post({'voice_conversation':True},request,path='/v1/cancel')[0])
            thread.join(3);self.assertFalse(thread.is_alive())
        finally:self.model_release.set();thread.join(6)
        self.assertEqual([],errors);self.settle()

    def test_cancellation_and_access_are_owner_scoped(self):
        request=secrets.token_hex(16)
        self.assertEqual(200,self.post({'voice_conversation':True},request,self.b,path='/v1/cancel')[0])
        self.assertEqual(200,self.post(self.body(request),request)[0])
        self.assertEqual(401,self.post(self.body(secrets.token_hex(16)),headers={'Authorization':'Bearer invalid'})[0])
        self.store.maintenance=True
        request=secrets.token_hex(16);self.assertEqual(503,self.post(self.body(request),request)[0])

    def test_revocation_stops_silent_response(self):
        self.block_after_headers=True;request=secrets.token_hex(16)
        thread,results,errors=self.worker(self.body(request),request)
        try:
            self.assertTrue(self.model_ready.wait(5));self.store.revoke(self.a['id'])
            thread.join(3);self.assertFalse(thread.is_alive())
        finally:self.model_release.set();thread.join(6)
        self.assertEqual([],errors);self.assertNotIn(b'Texte corrige',results[0][1]);self.settle()

    def test_explicit_temporary_refusal_retries_before_model_output(self):
        self.model_refusals=['0'];request=secrets.token_hex(16)
        status,raw=self.post(self.body(request),request)
        self.assertEqual(200,status);self.assertEqual(1,raw.count(b'Texte corrige'))
        self.assertEqual(1,raw.count(b'[DONE]'));self.assertEqual(2,len(self.captured));self.settle()
        diagnostics=json.loads((self.store.home/'inference-errors.json').read_text(encoding='utf-8'))
        self.assertEqual(503,diagnostics[-1]['status']);self.assertIn('batch slots',diagnostics[-1]['detail'])

    def test_unknown_503_is_not_replayed_and_keeps_admin_reason(self):
        self.model_refusals=[None];request=secrets.token_hex(16)
        status,raw=self.post(self.body(request),request)
        self.assertEqual(200,status);self.assertEqual(1,len(self.captured));self.settle()
        self.assertIn(b'model_temporarily_unavailable',raw);self.assertNotIn(b'batch slots',raw)
        self.assertIn('batch slots',(self.store.home/'inference-errors.json').read_text(encoding='utf-8'))

    def test_cancel_during_retry_wait_does_not_submit_again(self):
        import time
        self.model_refusals=['1'];request=secrets.token_hex(16)
        thread,results,errors=self.worker(self.body(request),request)
        deadline=time.monotonic()+3
        while not self.captured and time.monotonic()<deadline:time.sleep(.01)
        self.assertEqual(1,len(self.captured))
        self.post({'voice_conversation':True},request,path='/v1/cancel')
        thread.join(3);self.assertFalse(thread.is_alive());self.assertEqual([],errors)
        self.assertEqual(1,len(self.captured));self.settle()


if __name__=='__main__':unittest.main(verbosity=2)
