"""A terminal agent error or intentional cancellation must not disconnect Kiara."""
import base64
import io
import json
import os
import tempfile
import threading
import unittest
import urllib.request
from unittest.mock import patch
import client


class Response(io.BytesIO):
    status=200
    code=200


class VoiceTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.env=patch.dict(os.environ,{'LOCALAPPDATA':self.temp.name});self.env.start();self.addCleanup(self.env.stop)
        encoded=base64.b64encode(bytes(range(32))).decode()
        profile={'url':'wireguard://10.77.0.1:8766','transport':'wireguard','token':'qwen_'+'a'*16+'_'+'b'*43,'protocol':4,
                 'wireguard':{'private_key':encoded,'server_public_key':encoded,'preshared_key':encoded,'address':'10.77.0.2/32','endpoint':'example.test:51820'}}
        parent=self
        class Opener:
            def open(self,request,timeout):return Response(parent.payload)
        self.payload=b''
        self.remote=client.Remote(profile,Opener());self.remote.connected=True
        self.server=client.serve_local(self.remote,'fixture-voice-key',0)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.addCleanup(self.close)

    def close(self):self.server.shutdown();self.server.server_close()

    def call(self,request='a'*32):
        data={'messages':[{'role':'user','content':'Bonjour'}],'stream':True}
        call=urllib.request.Request('http://127.0.0.1:'+str(self.server.server_port)+'/v1/chat/completions',json.dumps(data).encode(),
             {'Authorization':'Bearer fixture-voice-key','Content-Type':'application/json','X-Qwen-Request':request})
        with urllib.request.urlopen(call,timeout=5) as response:return response.read()

    def test_agent_error_is_forwarded_once_without_connection_failure(self):
        self.payload='data: {"error":{"message":"L’assistant a été interrompu."}}\n\n'.encode()
        output=self.call()
        self.assertEqual(self.payload,output)
        self.assertTrue(self.remote.connected)
        self.assertEqual('failed',self.remote.stream['phase'])

    def test_intentional_cancel_does_not_disconnect_but_missing_done_does(self):
        self.payload=b'data: {"choices":[{"delta":{"content":"Bonjour"}}]}\n\n'
        self.remote.cancelled_requests.append('a'*32)
        output=self.call();self.assertTrue(self.remote.connected);self.assertNotIn(b'connection_error',output)
        self.call('b'*32);self.assertFalse(self.remote.connected)
        self.assertEqual('connection_error',self.remote.code)


if __name__=='__main__':unittest.main(verbosity=2)
