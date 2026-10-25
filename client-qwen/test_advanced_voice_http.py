"""The actual authenticated loopback routes, with owned synthetic inference."""
import base64
import json
import urllib.error
import urllib.request
from unittest.mock import patch
import unittest
from test_voice_transport import VoiceTransportTests, Response


class AdvancedVoiceHTTPTests(unittest.TestCase):
    setUp=VoiceTransportTests.setUp
    close=VoiceTransportTests.close

    def request(self,path,value=None,key='fixture-voice-key'):
        call=urllib.request.Request('http://127.0.0.1:'+str(self.server.server_port)+path,
            json.dumps(value).encode() if value is not None else None,
            {'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(call,timeout=5) as response:return response.status,response.read()
        except urllib.error.HTTPError as response:return response.code,response.read()

    def active(self,execution='pc'):
        self.server.conversation.value.update(phase='listening',session='owned',quality='max',execution=execution)

    def test_unauthorized_and_stale_capture_never_reach_inference(self):
        self.active()
        with patch.object(self.server.advanced_voice,'transcribe') as infer:
            body={'pcm':'AAA=','rate':16000,'session':'owned'}
            self.assertEqual(self.request('/client/voice/max/transcribe',body,key='wrong')[0],401)
            self.assertEqual(self.request('/client/voice/max/transcribe',{**body,'session':'stale'})[0],400)
            infer.assert_not_called()

    def test_local_audio_is_kept_local_and_bound_to_session(self):
        self.active()
        def infer(owner,value,valid):
            self.assertEqual(owner,'owned');self.assertTrue(valid())
            self.assertNotIn('session',value)
            self.server.conversation.value['phase']='stopped';self.assertFalse(valid())
            return {'text':'Bonjour'}
        with patch.object(self.server.advanced_voice,'transcribe',infer),patch.object(self.remote,'open',side_effect=AssertionError('Local audio left PC')):
            status,raw=self.request('/client/voice/max/transcribe',{'pcm':'AAA=','rate':16000,'session':'owned'})
        self.assertEqual(status,200);self.assertEqual(json.loads(raw)['text'],'Bonjour')

    def test_server_audio_only_uses_authenticated_kiara_transport(self):
        self.active('server');calls=[]
        def forward(path,data=None,*args):
            calls.append((path,json.loads(data)));return Response(b'{"text":"Bonjour depuis le serveur"}')
        with patch.object(self.remote,'open',forward),patch.object(self.server.advanced_voice,'transcribe',side_effect=AssertionError('Wrong execution target')):
            status,raw=self.request('/client/voice/max/transcribe',{'pcm':'AAA=','rate':16000,'session':'owned','request_id':'b'*32})
        self.assertEqual(status,200)
        self.assertEqual(calls,[('/v1/voice/max/transcribe',{'pcm':'AAA=','rate':16000,'request_id':'b'*32})])

    def test_local_and_forwarded_max_speech_preserve_sse_completion(self):
        for execution in ('pc','server'):
            self.active(execution)
            frames=[{'id':'a'*32,'rate':24000,'pcm':'AAA='},{'id':'a'*32,'done':True}]
            payload=''.join('data: '+json.dumps(frame)+'\n\n' for frame in frames).encode()
            with patch.object(self.remote,'open',return_value=Response(payload)),patch.object(self.server.advanced_voice,'frames',side_effect=lambda *args: (frame for frame in frames)):
                status,raw=self.request('/client/voice/max/speech',{'session':'owned','text':'Bonjour','request_id':'a'*32,'stream':True})
            self.assertEqual(status,200);self.assertEqual(raw,payload);self.assertTrue(self.remote.connected)

    def test_test_cannot_run_during_a_call_or_on_arbitrary_host(self):
        self.active()
        with patch.object(self.server.advanced_voice,'test') as test:
            self.assertEqual(self.request('/client/voice/max/test',{'execution':'pc'})[0],400)
            self.assertEqual(self.request('/client/voice/max/test',{'execution':'https://example.invalid'})[0],400)
            test.assert_not_called()

    def test_unavailable_max_does_not_fall_back_silently_or_open_microphone(self):
        with (patch.object(self.remote,'open',return_value=Response(b'{"available":false}')),
              patch.object(self.server.conversation,'action') as action):
            status,raw=self.request('/client/conversation',{'action':'start','quality':'max','execution':'auto'})
            self.assertEqual(status,400);action.assert_not_called()

    def test_auto_start_passes_the_selected_server_to_the_native_session(self):
        with (patch.object(self.remote,'open',return_value=Response(b'{"available":true,"latency_ms":600}')),
              patch.object(self.server.conversation,'action',return_value={'phase':'loading'}) as action):
            self.assertEqual(self.request('/client/conversation',{'action':'start','quality':'max','execution':'auto'})[0],200)
            action.assert_called_once_with({'action':'start','quality':'max','execution':'server'})

    def test_installation_needs_an_announced_plan_and_cannot_run_during_capture(self):
        installer=self.server.max_installation
        with patch.object(installer,'plan',return_value={'plan':'signed-plan','download_bytes':1900000000}) as plan:
            status,raw=self.request('/client/voice/max/plan',{})
            self.assertEqual(status,200);self.assertEqual(json.loads(raw)['download_bytes'],1900000000)
            self.assertEqual(self.request('/client/voice/max/plan',{'url':'https://example.test'})[0],400)
            self.assertEqual(self.request('/client/voice/max/plan',{},key='wrong')[0],401)
            self.active()
            self.assertEqual(self.request('/client/voice/max/plan',{})[0],400)
            self.assertEqual(plan.call_count,1)
        self.server.conversation.value['phase']='idle'
        with patch.object(installer,'install',return_value={'phase':'downloading'}) as install:
            self.assertEqual(self.request('/client/voice/max/install',{'plan':'signed-plan'})[0],200)
            install.assert_called_once_with('signed-plan')
            self.assertEqual(self.request('/client/voice/max/install',{'url':'https://example.test'})[0],400)

    def test_progressive_segments_remain_bound_to_the_same_authenticated_call(self):
        self.active()
        body={'session':'owned','rate':16000,'pcm':'AAA=','utterance':'b'*32,'offset':16000,'final':False}
        with patch.object(self.server.advanced_voice,'transcribe',return_value={'text':'Une phrase'}) as infer:
            self.assertEqual(self.request('/client/voice/max/transcribe',body)[0],200)
            self.assertEqual(infer.call_args.args[0],'owned')
            self.assertEqual(infer.call_args.args[1]['offset'],16000)
            self.assertEqual(infer.call_args.args[1]['utterance'],'b'*32)

    def test_remove_needs_authentication_confirmation_and_an_idle_client(self):
        with patch.object(self.server.max_installation,'remove',return_value={'phase':'idle'}) as remove:
            for value in ({},{'confirm':False},{'confirm':1},{'confirm':True,'path':'C:/arbitrary'}):
                self.assertEqual(self.request('/client/voice/max/remove',value)[0],400)
            self.assertEqual(self.request('/client/voice/max/remove',{'confirm':True},key='wrong')[0],401)
            remove.assert_not_called()
            self.active()
            self.assertEqual(self.request('/client/voice/max/remove',{'confirm':True})[0],400)
            remove.assert_not_called()
            self.server.conversation.value['phase']='idle'
            self.assertEqual(self.request('/client/voice/max/remove',{'confirm':True})[0],200)
            remove.assert_called_once_with()

    def test_folder_route_cannot_open_a_supplied_path(self):
        with patch.object(self.server.max_installation,'open_folder',return_value={'opened':True}) as folder:
            self.assertEqual(self.request('/client/voice/max/open-folder',{},key='wrong')[0],401)
            self.assertEqual(self.request('/client/voice/max/open-folder',{'path':'C:/arbitrary'})[0],400)
            folder.assert_not_called()
            self.active()
            self.assertEqual(self.request('/client/voice/max/open-folder',{})[0],200)
            folder.assert_called_once_with()

    def test_gpu_routes_are_local_authenticated_and_protect_an_active_call(self):
        with patch.object(self.server.advanced_voice,'detect_devices',return_value={'gpu':{'cards':[]}}) as detect,patch.object(self.server.advanced_voice,'set_gpu',return_value={'gpu':{'selection':'b'*24}}) as select:
            self.assertEqual(self.request('/client/voice/max/devices',{},key='wrong')[0],401)
            self.assertEqual(self.request('/client/voice/max/devices',{'path':'C:/other'})[0],400)
            self.assertEqual(self.request('/client/voice/max/gpu',{'device':'b'*24,'execution':'server'})[0],400)
            detect.assert_not_called();select.assert_not_called()
            self.assertEqual(self.request('/client/voice/max/devices',{})[0],200)
            self.assertEqual(self.request('/client/voice/max/gpu',{'device':'b'*24})[0],200)
            select.assert_called_once_with('b'*24)
            self.active()
            self.assertEqual(self.request('/client/voice/max/gpu',{'device':'a'*24})[0],400)
            self.assertEqual(self.request('/client/voice/max/devices',{})[0],400)
            self.assertEqual(select.call_count,1);self.assertEqual(detect.call_count,1)


if __name__=='__main__':unittest.main(verbosity=2)
