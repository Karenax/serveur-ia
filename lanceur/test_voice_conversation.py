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
        self.assertEqual('actual-local',data['model']);self.assertEqual(512,data['max_tokens'])
        self.assertEqual('none',data['reasoning_effort']);self.assertEqual({'enable_thinking':False},data['chat_template_kwargs'])
        self.assertFalse(data['strata_mcp']);self.assertEqual('system',data['messages'][0]['role'])
        self.assertNotIn('reasoning_content',data['messages'][1]);self.settle()

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
        with patch.object(self.store.workspace,'context',side_effect=Denied('Projet privé.')):
            other=secrets.token_hex(16)
            self.assertEqual(403,self.post({**value,'turn_id':other},other)[0])

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


if __name__=='__main__':unittest.main(verbosity=2)
