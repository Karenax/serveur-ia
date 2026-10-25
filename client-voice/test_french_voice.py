"""The Max voice must be anchored to French, including at the native ABI boundary."""
import array
import ctypes as c
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
import wave
from french_voice import reference
from max_native import NativeVoice,Params,VoiceReference


class FrenchVoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        shutil.copytree(Path(__file__).with_name('max-french'),self.root/'voices/fr-fr')

    def test_reference_is_pinned_mono_french_and_not_a_user_recording(self):
        wav,text,samples=reference(self.root)
        self.assertTrue(wav.is_file());self.assertIn('Bonjour',text)
        self.assertGreater(len(samples),3*24000);self.assertLess(len(samples),12*24000)
        self.assertGreater(max(samples),.05)
        spec=json.loads(wav.with_suffix('.json').read_text(encoding='utf-8'))
        self.assertIn('Synthetic speech',spec['source']);self.assertEqual(spec['locale'],'fr-FR')

    def test_invalid_reference_never_falls_back_to_a_chinese_preset(self):
        folder=self.root/'voices/fr-fr';original=(folder/'reference.json').read_bytes()
        for edit in ({'locale':'zh-CN'},{'text':''},{'audio_sha256':'0'*64}):
            spec=json.loads(original);spec.update(edit)
            (folder/'reference.json').write_text(json.dumps(spec),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'française'):reference(self.root)
        (folder/'reference.json').write_bytes(original)
        (folder/'reference.wav').write_bytes(b'incomplete')
        with self.assertRaisesRegex(ValueError,'française'):reference(self.root)

    def test_stream_passes_french_conditioning_and_reuses_its_latents(self):
        owner=self
        class Native:
            calls=0;freed=0;refs_freed=0
            def qt_tts_default_params(self,params):pass
            def qt_synthesize(self,handle,params,result):
                p=c.cast(params,c.POINTER(Params)).contents
                owner.assertEqual(p.lang,b'french');owner.assertIsNone(p.speaker);owner.assertIsNone(p.instruct)
                owner.assertEqual(p.ref_text,'Bonjour, je suis Kiara.'.encode())
                owner.assertEqual(p.ref_spk_dim,2048);owner.assertEqual(p.ref_T,24)
                owner.assertEqual(c.addressof(p.ref_spk_emb.contents),c.addressof(emb))
                owner.assertEqual(c.addressof(p.ref_codes.contents),c.addressof(codes))
                raw=(c.c_float*240)(*[.1]*240)
                owner.assertTrue(p.on_chunk(raw,240,None));self.calls+=1;return 0
            def qt_audio_free(self,result):self.freed+=1
            def qt_voice_ref_free(self,ref):self.refs_freed+=1
            def qt_free(self,handle):pass
        emb=(c.c_float*2048)();codes=(c.c_int32*(16*24))()
        voice=NativeVoice.__new__(NativeVoice);voice.handle=1;voice.lib=Native()
        voice.reference_text='Bonjour, je suis Kiara.'
        voice.voice_reference=VoiceReference(emb,2048,codes,24,16)
        for text in ('Bonjour !','Je vous écoute.'):
            frames=list(voice.stream(text,threading.Event()))
            self.assertEqual(sum(len(frame.get('raw_pcm',b'')) for frame in frames),480)
        self.assertEqual(voice.lib.calls,2);self.assertEqual(voice.lib.freed,2)
        voice.close();voice.close();self.assertEqual(voice.lib.refs_freed,1)


if __name__=='__main__':unittest.main()
