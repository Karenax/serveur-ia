"""New gateway routes retain account authentication and cancellation ownership."""
import json
import tempfile
from pathlib import Path
import urllib.request
import urllib.error
import unittest
from unittest.mock import patch
import test_text_transform as fixtures


class MaxVoiceGatewayTests(unittest.TestCase):
    setUp=fixtures.TextTransformHTTPTests.setUp
    tearDown=fixtures.TextTransformHTTPTests.tearDown
    post=fixtures.TextTransformHTTPTests.post

    def test_transcription_uses_authenticated_owner_and_revalidates_account(self):
        def transcribe(owner,value,valid):
            self.assertEqual(owner,self.a['id']);self.assertTrue(valid())
            return {'text':'Bonjour Orion'}
        with patch.object(self.store.voice_max,'transcribe',transcribe):
            status,raw=self.post({'pcm':'AAA=','rate':16000},path='/v1/voice/max/transcribe')
        self.assertEqual(status,200);self.assertEqual(json.loads(raw)['text'],'Bonjour Orion')

    def test_speech_stream_and_cancel_keep_owner_scope(self):
        owners=[]
        def frames(owner,action,value,valid):
            owners.append(owner);self.assertTrue(valid());self.assertEqual(action,'speak')
            yield {'id':value['request_id'],'rate':24000,'pcm':'AAA='}
            yield {'id':value['request_id'],'done':True}
        with patch.object(self.store.voice_max,'frames',frames):
            status,raw=self.post({'request_id':'a'*32,'text':'Bonjour'},path='/v1/voice/max/speech')
        self.assertEqual(status,200);self.assertIn(b'"done": true',raw);self.assertEqual(owners,[self.a['id']])
        with patch.object(self.store.voice_max,'cancel',return_value={'cancelled':True}) as cancel:
            self.assertEqual(self.post({'request_id':'a'*32},access=self.b,path='/v1/voice/max/cancel')[0],200)
            cancel.assert_called_once_with(self.b['id'],'a'*32)

    def test_foreign_target_or_unexpected_test_parameters_never_start_runtime(self):
        with patch.object(self.store.voice_max,'test') as test:
            self.assertEqual(self.post({'url':'https://example.invalid'},path='/v1/voice/max/test')[0],400)
            test.assert_not_called()
        self.assertEqual(self.post({'request_id':[]},path='/v1/voice/max/cancel')[0],400)

    def test_warm_and_release_remain_bound_to_the_authenticated_owner(self):
        with patch.object(self.store.voice_max,'warm',return_value={'loaded':True}) as warm:
            self.assertEqual(self.post({'session':'a'*32},path='/v1/voice/max/warm')[0],200)
            warm.assert_called_once_with(self.a['id'],'a'*32)
        with patch.object(self.store.voice_max,'release',return_value={'released':True}) as release:
            self.assertEqual(self.post({'session':'a'*32},access=self.b,path='/v1/voice/max/end')[0],200)
            release.assert_called_once_with(self.b['id'],'a'*32)

    def test_optional_pack_requires_authentication_and_has_bounded_exact_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'runtime.zip';source.write_bytes(b'fixture signed runtime')
            def get(path,token):
                request=urllib.request.Request('http://127.0.0.1:'+str(self.gateway.server_port)+path,
                    headers={'Authorization':'Bearer '+token})
                try:
                    with urllib.request.urlopen(request,timeout=5) as response:return response.status,response.read()
                except urllib.error.HTTPError as response:
                    with response:return response.code,response.read()
            with patch('voice_max_package.package',return_value=({'format':2,'signature':'fixture'},source)) as package:
                self.assertEqual(get('/v1/voice/max/package','invalid')[0],401)
                package.assert_not_called()
                self.assertEqual(get('/v1/voice/max/package',self.a['token'])[0],200)
                self.assertEqual(get('/v1/voice/max/package/download',self.a['token']),(200,b'fixture signed runtime'))


if __name__=='__main__':unittest.main(verbosity=2)
