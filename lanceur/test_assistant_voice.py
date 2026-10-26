import json
import unittest
from voice_response import Decoder, configure


class AssistantVoiceTests(unittest.TestCase):
    def test_command_payload_never_reaches_speech_even_fragmented(self):
        payload={'operation':'memory_add','text':'Préférer le français'}
        wire='C:'+json.dumps(payload,ensure_ascii=False)
        for size in (1,2,5,100):
            decoder=Decoder(commands=True)
            spoken=''.join(decoder.feed(wire[i:i+size]) for i in range(0,len(wire),size))
            self.assertEqual(spoken,'')
            self.assertEqual(decoder.finish()['command'],payload)
        for wire in ('C:{}','C:[]','C:{"operation":"shell"}','C:invalid'):
            decoder=Decoder(commands=True)
            with self.assertRaises(ValueError):decoder.feed(wire);decoder.finish()

    def test_commands_are_opt_in_and_plain_french_still_streams(self):
        decoder=Decoder(commands=True)
        self.assertEqual(decoder.feed('C'),'')
        self.assertEqual(decoder.feed('oucou !'),'Coucou !')
        body={'messages':[{'role':'system','content':'Bonjour.'}], 'stream':True}
        self.assertNotIn('C:',configure(body)['messages'][0]['content'])
        self.assertIn('C:',configure(body,commands=True)['messages'][0]['content'])


class AssistantVoiceHTTPTests(unittest.TestCase):
    import test_text_transform as fixtures
    import test_voice_realtime as realtime
    setUp=fixtures.TextTransformHTTPTests.setUp
    tearDown=fixtures.TextTransformHTTPTests.tearDown
    post=fixtures.TextTransformHTTPTests.post
    settle=fixtures.TextTransformHTTPTests.settle
    body=realtime.VoiceRealtimeHTTPTests.body

    def test_voice_command_commits_once_and_does_not_speak_internal_json(self):
        import secrets
        request=secrets.token_hex(16)
        body=self.body(request);body['messages'][-1]['content']='Retiens que je préfère le français.'
        self.oral_reply='C:'+json.dumps({'operation':'memory_add','text':'Préférer le français','category':'preference'})
        status,raw=self.post(body,request)
        self.assertEqual(status,200);self.assertIn(b'Souvenir',raw);self.assertNotIn(b'error',raw)
        self.settle();self.post(body,request);self.settle()
        result=self.store.workspace.action(self.a['id'],{'action':'assistant','operation':'list'})
        self.assertEqual(len(result['memories']),1)

    def test_source_cannot_authorize_unrequested_memory_mutation(self):
        import secrets
        request=secrets.token_hex(16);body=self.body(request)
        body['messages'][-1]['content']='Explique cette information.'
        self.oral_reply='C:'+json.dumps({'operation':'memory_add','text':'Instruction injectée'})
        status,raw=self.post(body,request);self.settle()
        self.assertEqual(status,200);self.assertIn(b'error',raw)
        self.assertEqual(self.store.workspace.action(self.a['id'],{'action':'assistant','operation':'list'})['memories'],[])

    def test_timestamped_voice_command_survives_full_legacy_journal_and_retry(self):
        import time
        from command_journal import request_key,MAX_RECEIPTS
        with self.store.workspace.db() as db:
            db.executemany('INSERT INTO assistant_commands VALUES(?,?,?,?,?)',[
                (self.a['id'],f'{number:032x}','a'*64,'{}',time.time()) for number in range(MAX_RECEIPTS)])
        request=request_key();body=self.body(request)
        body['messages'][-1]['content']='Retiens que je préfère le français.'
        self.oral_reply='C:'+json.dumps({'operation':'memory_add','text':'Préférer le français'})
        for _ in range(2):
            status,raw=self.post(body,request);self.settle()
            self.assertEqual(status,200);self.assertNotIn(b'error',raw)
        result=self.store.workspace.action(self.a['id'],{'action':'assistant','operation':'list'})
        self.assertEqual(len(result['memories']),1)


if __name__=='__main__':unittest.main()
