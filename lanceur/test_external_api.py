"""Exercise standard third-party calls through the real authenticated local API."""
import json
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest
import urllib.request
from unittest.mock import patch

import test_remote
from test_remote import FakeModel, client
from hermes_service import installation
from external_api import complete, response_body


class ExternalAPITests(unittest.TestCase):
    setUp=test_remote.RemoteTests.setUp
    tearDown=test_remote.RemoteTests.tearDown
    request=test_remote.RemoteTests.request

    def local_hermes(self):
        self.agent_calls=[]
        self.store.hermes=SimpleNamespace(
            select_model=lambda owner,model:{'id':'fred-qwen','local':True,'available':True,'capabilities':{}},
            stream=lambda *args:self.agent_calls.append(args))

    def test_standard_chat_with_client_tools_and_tool_results_uses_local_model(self):
        self.local_hermes()
        tools=[{'type':'function','function':{'name':'read_client_file','parameters':{'type':'object','properties':{}}}}]
        base=f'http://127.0.0.1:{self.gateway.server_port}'
        remote=client.Remote(self.profile,opener=urllib.request.build_opener(urllib.request.ProxyHandler({})))
        remote.url=base;remote.session=self.session
        with patch.object(client,'settings_path',return_value=Path(self.temporary.name)/'local.dpapi'):
            local=client.serve_local(remote,'fixture-local-key',0)
        threading.Thread(target=local.serve_forever,daemon=True).start()
        try:
            for streaming in (False,True):
                body={'model':'fred-qwen','messages':[{'role':'user','content':'Read'},
                    {'role':'assistant','content':None,'tool_calls':[{'id':'call_test','type':'function','function':{'name':'read_client_file','arguments':'{}'}}]},
                    {'role':'tool','tool_call_id':'call_test','content':'client result'}],
                    'tools':tools,'stream':streaming,'max_tokens':64,'store':False}
                req=urllib.request.Request(f'http://127.0.0.1:{local.server_port}/v1/chat/completions',json.dumps(body).encode(),
                    {'Content-Type':'application/json','Authorization':'Bearer fixture-local-key'})
                with urllib.request.urlopen(req,timeout=10) as response:
                    output=response.read();self.assertIn(b'Bonjour',output)
                    if streaming:self.assertIn(b'[DONE]',output)
                sent=FakeModel.captured[-1][1]
                self.assertEqual(sent['model'],'test-model');self.assertEqual(sent['tools'],tools)
                self.assertEqual(sent['messages'],body['messages']);self.assertEqual(sent['max_tokens'],64)
                self.assertFalse(sent['strata_mcp'])
                self.assertNotIn('store',sent)
            self.assertFalse(self.agent_calls)
        finally:local.shutdown();local.server_close()

    def test_fred_chat_keeps_agent_conversation_route(self):
        self.local_hermes()
        blocks=[b'data: {"choices":[{"delta":{"content":"Agent Fred"}}]}\n\n',b'data: [DONE]\n\n']
        def stream(*args):
            self.agent_calls.append(args)
            yield from blocks
        self.store.hermes.stream=stream
        with self.request('/v1/chat/completions',{'conversation_id':'discussion','turn_id':'a'*32,
            'messages':[{'role':'user','content':'Question'}]}) as response:
            self.assertEqual(json.load(response)['choices'][0]['message']['content'],'Agent Fred')
        self.assertEqual(len(self.agent_calls),1)

    def test_cloud_worker_uses_only_selected_provider_and_returns_standard_json(self):
        selection={'id':'fred-model-test','native_model':'test-model','api_mode':'chat_completions',
                   'base_url':f'http://127.0.0.1:{self.fake.server_port}/v1'}
        models=SimpleNamespace(source=SimpleNamespace(runtime=installation()),
            credential=lambda owner,row:{'access_token':'provider-only-key'})
        result=complete(models,self.access['id'],selection,{'messages':[{'role':'user','content':'Bonjour'}],
            'stream':True,'max_tokens':32,'strata_mcp':False},lambda:True)
        self.assertEqual(result['model'],selection['id'])
        self.assertEqual(result['choices'][0]['message']['content'],'Bonjour')
        headers,body=FakeModel.captured[-1]
        self.assertEqual(headers['Authorization'],'Bearer provider-only-key')
        self.assertNotIn('strata_mcp',body);self.assertEqual(body['max_tokens'],32)

    def test_cloud_sse_tool_calls_have_indices_and_finish_reason(self):
        result={'id':'test','model':'cloud','object':'chat.completion','choices':[{'index':0,
            'message':{'role':'assistant','content':None,'tool_calls':[{'id':'c1','type':'function',
                'function':{'name':'client_tool','arguments':'{}'}}]},'finish_reason':'tool_calls'}]}
        output=response_body(result,True)
        events=[json.loads(line[6:]) for line in output.splitlines() if line.startswith(b'data: ') and line!=b'data: [DONE]']
        self.assertEqual(events[0]['choices'][0]['delta']['tool_calls'][0]['index'],0)
        self.assertEqual(events[1]['choices'][0]['finish_reason'],'tool_calls')
        self.assertTrue(output.endswith(b'data: [DONE]\n\n'))

    def test_cloud_gateway_preserves_public_model_and_sse_tool_call(self):
        selection={'id':'fred-model-test','local':False,'capabilities':{}}
        result={'id':'test','model':selection['id'],'choices':[{'index':0,'message':{'role':'assistant',
            'content':None,'tool_calls':[{'id':'call_test','type':'function','function':{'name':'client_tool','arguments':'{}'}}]},'finish_reason':'tool_calls'}]}
        self.store.hermes=SimpleNamespace(select_model=lambda *args:selection,
            models=SimpleNamespace(valid=lambda *args:True))
        with patch('external_api.complete',return_value=result) as invoked:
            for stream in (False,True):
                with self.request('/v1/chat/completions',{'model':selection['id'],
                    'messages':[{'role':'user','content':'Use client tool'}],'stream':stream}) as response:
                    body=response.read();self.assertIn(b'client_tool',body)
                    if stream:self.assertIn(b'[DONE]',body)
                self.assertEqual(invoked.call_args.args[2],selection)
        self.assertEqual(self.store.scheduler.snapshot()['succeeded'],2)

    def test_revoked_call_does_not_resolve_credentials_or_start_worker(self):
        models=SimpleNamespace(credential=lambda *args:self.fail('credential resolved after revocation'))
        with self.assertRaises(ValueError):complete(models,'owner',{}, {},lambda:False)

    def test_cancellation_terminates_native_worker(self):
        import sys,time
        runtime={'python':sys.executable,'source':Path(self.temporary.name),'tools':Path(self.temporary.name)}
        models=SimpleNamespace(source=SimpleNamespace(runtime=runtime),credential=lambda *args:{'access_token':'fake'})
        selection={'id':'public','native_model':'native','api_mode':'chat_completions','base_url':'https://invalid.test/v1'}
        started=time.monotonic()
        with patch('external_api.WORKER','import sys,json,time; json.load(sys.stdin); time.sleep(60)'):
            with self.assertRaises(ValueError):complete(models,'owner',selection,{},lambda:time.monotonic()-started<.6)
        self.assertLess(time.monotonic()-started,4)


if __name__=='__main__':unittest.main()
