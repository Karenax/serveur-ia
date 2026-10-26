import json,secrets,unittest
from unittest.mock import patch
import test_text_transform as fixtures
import test_voice_web as web_fixtures
import test_voice_conversation as oral_fixtures


class VoiceRealtimeHTTPTests(unittest.TestCase):
    setUp=fixtures.TextTransformHTTPTests.setUp
    tearDown=fixtures.TextTransformHTTPTests.tearDown
    post=fixtures.TextTransformHTTPTests.post
    worker=fixtures.TextTransformHTTPTests.worker
    settle=fixtures.TextTransformHTTPTests.settle
    permission=web_fixtures.VoiceWebHTTPTests.permission

    def body(self,request):return {**oral_fixtures.VoiceConversationHTTPTests.body(request),'voice_realtime':True}

    def test_ordinary_voice_uses_one_streamed_call_and_no_separate_classifier(self):
        request=secrets.token_hex(16);self.fragmented=True
        with patch('remote.plan_voice_web',side_effect=AssertionError('No extra classification call')):
            status,raw=self.post(self.body(request),request)
        self.assertEqual(status,200);self.assertIn(b'[DONE]',raw)
        self.assertEqual(len(self.captured),1);self.assertNotIn(b'"action"',raw);self.assertNotIn(b'query',raw)
        content=''.join(json.loads(line[6:])['choices'][0]['delta'].get('content','') for line in raw.splitlines() if line.startswith(b'data: {') and 'choices' in json.loads(line[6:]))
        self.assertEqual(content,'Bonjour, je vous écoute.');self.settle()

    def test_plain_numeric_followup_is_streamed_without_an_extra_model_call(self):
        self.oral_reply='42';request=secrets.token_hex(16)
        status,raw=self.post(self.body(request),request)
        self.assertEqual(status,200);self.assertNotIn(b'error',raw)
        self.assertIn(b'42',raw);self.assertEqual(len(self.captured),1);self.settle()

    def test_answer_beyond_old_token_and_character_limits_streams_completely(self):
        answer='Une histoire qui continue. '*2000
        self.oral_reply='R:'+answer;request=secrets.token_hex(16)
        status,raw=self.post(self.body(request),request)
        self.assertEqual(status,200);self.assertNotIn(b'error',raw);self.assertIn(b'[DONE]',raw)
        self.assertEqual(self.captured[0][1]['max_tokens'],100000)
        events=[json.loads(line[6:]) for line in raw.splitlines() if line.startswith(b'data: {')]
        context=next(event['voice_context'] for event in events if 'voice_context' in event)
        self.assertEqual(context['capacity'],262144)
        self.assertEqual(context['output_tokens'],100000)
        text=''.join(event['choices'][0]['delta'].get('content','') for event in events if 'choices' in event)
        self.assertEqual(text,answer);self.settle()

    def test_requested_story_length_reaches_model_without_short_answer_instructions(self):
        request=secrets.token_hex(16);body=self.body(request)
        question='Raconte une histoire de 100 mots en dix phrases sur un petit garçon super-héros.'
        body['messages'][-1]['content']=question
        answer=' '.join('Léo aide ses amis avec ses pouvoirs.' for _ in range(10))
        self.oral_reply='R:'+answer
        status,raw=self.post(body,request)
        self.assertEqual(status,200);self.assertNotIn(b'error',raw)
        sent=self.captured[0][1]
        self.assertEqual(sent['messages'][-1]['content'],question)
        instructions='\n'.join(m['content'] for m in sent['messages'] if m['role']=='system')
        for unwanted in ('réponse orale courte','phrases courtes','deux à quatre phrases','Évite les tableaux','longs préambules'):
            self.assertNotIn(unwanted,instructions)
        self.assertIn('Respecte le contenu, le format et la longueur demandés',instructions)
        text=''.join(json.loads(line[6:])['choices'][0]['delta'].get('content','') for line in raw.splitlines() if line.startswith(b'data: {') and 'choices' in json.loads(line[6:]))
        self.assertEqual(text,answer);self.settle()

    def test_web_runs_only_after_the_complete_decision_and_then_uses_normal_answering(self):
        self.oral_reply={'action':'search','query':'actualité publique du jour','answer':''}
        self.voice_plan={'action':'search','query':'actualité publique du jour'}
        web=web_fixtures.WebFixture();self.store.voice_web.web=web;self.permission(self.a['id'],True)
        request=secrets.token_hex(16);status,raw=self.post(self.body(request),request)
        self.assertEqual(status,200);self.assertEqual(len(self.captured),2)
        self.assertEqual([name for name,_ in web.calls],['web_search','web_extract'])
        self.assertNotIn('response_format',self.captured[1][1]);self.assertIn(b'workspace_sources',raw)
        self.assertNotIn(b'"action"',raw);self.assertIn(b'Texte corrige',raw);self.settle()

    def test_context_rich_query_is_rebuilt_from_public_dialogue_before_leaving_the_server(self):
        self.oral_reply={'action':'search','query':'PRIVATE-DOCUMENT-SECRET','answer':''}
        self.voice_plan={'action':'search','query':'actualité publique du jour'}
        web=web_fixtures.WebFixture();self.store.voice_web.web=web;self.permission(self.a['id'],True)
        request=secrets.token_hex(16);body=self.body(request)
        body['messages'].insert(0,{'role':'system','content':'PRIVATE-DOCUMENT-SECRET'})
        status,raw=self.post(body,request)
        self.assertEqual(status,200);self.assertNotIn(b'error',raw)
        self.assertEqual(web.calls[0][1]['query'],'actualité publique du jour')
        self.assertNotIn('PRIVATE-DOCUMENT-SECRET',json.dumps(self.plan_captured))
        self.settle()

    def test_search_permission_and_incomplete_json_fail_before_any_provider_call(self):
        web=web_fixtures.WebFixture();self.store.voice_web.web=web;self.permission(self.a['id'],False)
        for reply in ({'action':'search','query':'nouvelles','answer':''},'{"action":"search","query":"incomplet'):
            self.oral_reply=reply;request=secrets.token_hex(16)
            status,raw=self.post(self.body(request),request)
            self.assertEqual(status,200);self.assertIn(b'error',raw);self.assertEqual(web.calls,[])
            self.settle()

    def test_cancel_during_the_first_generation_releases_the_shared_slot(self):
        self.block_after_headers=True;request=secrets.token_hex(16)
        thread,results,errors=self.worker(self.body(request),request)
        try:
            self.assertTrue(self.model_ready.wait(4));self.post({'voice_conversation':True},request,path='/v1/cancel')
            thread.join(4);self.assertFalse(thread.is_alive());self.assertEqual(errors,[])
        finally:self.model_release.set();thread.join(4)
        self.settle()


if __name__=='__main__':unittest.main()
