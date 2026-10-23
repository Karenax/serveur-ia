"""Voice gateway authorization and bounded streams, isolated synthetic users."""
import json
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch
import test_remote as fixtures
from core import write_json

class VoiceHTTPTests(unittest.TestCase):
    setUp=fixtures.RemoteTests.setUp
    tearDown=fixtures.RemoteTests.tearDown
    request=fixtures.RemoteTests.request
    def test_voice_status_requires_personal_session(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(self.url+'/v1/voice/status',timeout=3)
        self.assertEqual(error.exception.code,401)
        with self.request('/v1/voice/status') as response:
            value=json.load(response);self.assertFalse(value['enabled']);self.assertFalse(value['ready'])
    def test_disabled_voice_rejects_without_worker(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/v1/voice/speech',{'request_id':'a'*32,'text':'Bonjour'})
        self.assertEqual(error.exception.code,400);self.assertIsNone(self.store.voice.process)
    def test_input_limits_and_custom_voice_rejected(self):
        for value in ({'request_id':'a'*32,'text':'Bonjour','voice':'file:///secret'},
                      {'request_id':'a'*32,'text':'x'*9000}):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/v1/voice/speech',value)
            self.assertEqual(error.exception.code,400)
    def ready(self):
        write_json(self.store.voice.path,{'enabled':True});self.store.voice.ready.set()
    def test_busy_is_bounded_and_does_not_queue_unlimited_requests(self):
        self.ready();self.store.voice.slot.acquire()
        try:
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request('/v1/voice/speech',{'request_id':'a'*32,'text':'Bonjour'})
            self.assertEqual(error.exception.code,429)
        finally:self.store.voice.slot.release()
    def test_stream_returns_pcm_then_done_and_frees_slot(self):
        self.ready()
        def write(command):
            job=self.store.voice.current
            job['queue'].put({'id':command['id'],'pcm':'AAAAAA==','rate':24000})
            job['queue'].put({'id':command['id'],'done':True});job['finished'].set()
        with patch.object(self.store.voice,'_write',side_effect=write):
            with self.request('/v1/voice/speech',{'request_id':'a'*32,'text':'Bonjour'}) as response:
                data=response.read();self.assertIn(b'pcm',data);self.assertIn(b'"done": true',data)
        self.assertIsNone(self.store.voice.current);self.assertTrue(self.store.voice.slot.acquire(False));self.store.voice.slot.release()
    def test_access_revocation_stops_audio_before_first_frame(self):
        self.ready()
        def write(command):
            if command['action']=='speak':
                self.store.revoke(self.access['id'])
                self.store.voice.current['finished'].set()
        with patch.object(self.store.voice,'_write',side_effect=write):
            with self.request('/v1/voice/speech',{'request_id':'a'*32,'text':'Bonjour'}) as response:
                self.assertNotIn(b'pcm',response.read())
        self.assertIsNone(self.store.voice.current)

    def test_silent_synthesis_keeps_stream_alive_without_releasing_its_slot(self):
        import itertools
        self.ready()
        with patch.object(self.store.voice,'_write'),patch('voice.time.monotonic',side_effect=itertools.chain([0,0],itertools.repeat(6))):
            frames=self.store.voice.stream(self.access['id'],{'request_id':'a'*32,'text':'Bonjour'})
            try:
                self.assertEqual({'id':'a'*32,'waiting':True},next(frames))
                self.assertFalse(self.store.voice.slot.acquire(False))
                job=self.store.voice.current;job['queue'].put({'id':'a'*32,'done':True});job['finished'].set()
                self.assertEqual({'id':'a'*32,'done':True},next(frames))
            finally:frames.close()
        self.assertIsNone(self.store.voice.current)

if __name__=='__main__':unittest.main(verbosity=2)
