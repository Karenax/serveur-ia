import json,os,sys,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
import client

class LocalHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.environment=patch.dict(os.environ,{'LOCALAPPDATA':self.temp.name});self.environment.start()
        remote=SimpleNamespace(profile={'url':'https://fixture.invalid','token':'fixture-only'},model='fake')
        self.server=client.serve_local(remote,'voice-fixture-key',0);threading.Thread(target=self.server.serve_forever,daemon=True).start();self.base=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):self.server.shutdown();self.server.server_close();self.environment.stop();self.temp.cleanup()
    def request(self,body=None,headers=None):
        return urllib.request.urlopen(urllib.request.Request(self.base+'/client/voice',None if body is None else json.dumps(body).encode(),{'Content-Type':'application/json',**(headers or {})}),timeout=3)
    def test_no_auth_cannot_open_microphone(self):
        for body in (None,{'action':'start'}):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request(body)
            self.assertEqual(error.exception.code,401);error.exception.close()
        self.assertEqual(self.server.voice.status()['phase'],'idle')
    def test_foreign_origin_is_rejected_even_with_local_key(self):
        with self.assertRaises(urllib.error.HTTPError) as error:self.request({'action':'install'},{'Authorization':'Bearer voice-fixture-key','Origin':'https://attacker.invalid'})
        self.assertEqual(error.exception.code,403);error.exception.close();self.assertIsNone(self.server.voice.thread)
    def test_model_install_required_and_remote_never_contacted(self):
        headers={'Authorization':'Bearer voice-fixture-key'}
        with self.request(headers=headers) as response:status=json.load(response)
        self.assertTrue(status['local']);self.assertFalse(status['installed'])
        with self.assertRaises(urllib.error.HTTPError) as error:self.request({'action':'start'},headers)
        self.assertEqual(error.exception.code,400);error.exception.close();self.assertIsNone(self.server.voice.engine)

if __name__=='__main__':unittest.main(verbosity=2)
