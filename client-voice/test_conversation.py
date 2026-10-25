"""Meaningful failure, ownership and cancellation checks without model downloads."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'client-qwen'));sys.path.insert(0,str(ROOT/'lanceur'))
from conversation_service import ConversationService, DictationService
from voice import VoiceService

class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.model=self.root/'models';self.model.mkdir()
        item={'name':'test.onnx','bytes':4,'sha256':hashlib.sha256(b'good').hexdigest(),'url':'https://example.invalid/public-model'}
        (self.root/'conversation-models.json').write_text(json.dumps({'files':[item]}),encoding='utf-8')
        self.client=ConversationService(self.root,self.model);self.addCleanup(self.client.close)
    def test_no_microphone_until_all_hashes_verified(self):
        (self.model/'test.onnx').write_bytes(b'evil')
        with patch('conversation_service.subprocess.Popen') as spawn:
            self.client.action({'action':'start'});self.client.thread.join(2)
            self.assertEqual(self.client.status()['phase'],'error');spawn.assert_not_called()
    def test_missing_model_never_starts_capture(self):
        with self.assertRaises(ValueError):self.client.action({'action':'start'})
    def test_stale_session_cannot_stop_current_capture(self):
        self.client.value.update(phase='listening',session='current')
        with self.assertRaises(ValueError):self.client.action({'action':'stop','session':'old'})
        self.assertFalse(self.client.cancelled.is_set())
    def test_mute_is_owned_and_waits_for_capture_confirmation(self):
        self.client.value.update(phase='listening',session='current',muted=False,microphone_closed=False)
        with patch.object(self.client,'_send') as send:
            with self.assertRaises(ValueError):self.client.action({'action':'mute','session':'old','muted':True})
            send.assert_not_called()
            state=self.client.action({'action':'mute','session':'current','muted':True})
            send.assert_called_once_with({'action':'mute','muted':True})
        self.assertTrue(self.client.mute_requested);self.assertTrue(state['mute_pending'])
        self.assertFalse(state['muted']);self.assertFalse(state['microphone_closed'])
        self.assertEqual(state['phase'],'listening');self.assertFalse(self.client.cancelled.is_set())
    def test_unmute_and_loading_mute_require_a_boolean(self):
        self.client.value.update(phase='loading',session='current',muted=True,microphone_closed=True)
        for invalid in ('false',None,0):
            with self.assertRaises(ValueError):self.client.action({'action':'mute','session':'current','muted':invalid})
        with patch.object(self.client,'_send') as send:
            state=self.client.action({'action':'mute','session':'current','muted':False})
            send.assert_called_once_with({'action':'mute','muted':False})
        self.assertTrue(state['muted']);self.assertFalse(self.client.mute_requested)
        self.assertTrue(state['mute_pending'])
        dictation=DictationService(self.root,self.model)
        dictation.value.update(phase='listening',session='current')
        with self.assertRaises(ValueError):dictation.action({'action':'mute','session':'current','muted':True})
    def test_unknown_action_fields_rejected(self):
        with self.assertRaises(ValueError):self.client.action({'action':'start','command':'arbitrary'})
    def test_playback_pause_is_owned_and_only_available_for_active_max(self):
        self.client.value.update(phase='listening',session='current',quality='max')
        message={'action':'playback','session':'current','playing':True,'interruptions':False}
        with patch.object(self.client,'_send') as send:
            for invalid in ({**message,'session':'old'},{**message,'playing':'true'}):
                with self.assertRaises(ValueError):self.client.action(invalid)
            send.assert_not_called()
            self.client.action(message)
            send.assert_called_once_with({'action':'playback','playing':True,'interruptions':False})
        self.assertTrue(self.client.playback_requested)
        self.client.value['quality']='low'
        with self.assertRaises(ValueError):self.client.action(message)
        self.assertFalse(self.client.cancelled.is_set())
    def test_stop_after_worker_failure_unlocks_client(self):
        self.client.value.update(phase='error',session='ended')
        result=self.client.action({'action':'stop','session':'ended'})
        self.assertEqual(result['phase'],'stopped')
    def test_public_download_never_replaces_good_model_with_corrupt_data(self):
        from io import BytesIO
        (self.model/'test.onnx').write_bytes(b'good')
        self.client.spec['files'].append({**self.client.spec['files'][0],'name':'missing.onnx'})
        with patch('conversation_service.urllib.request.build_opener') as opener:
            opener.return_value.open.return_value=BytesIO(b'evil')
            self.client.action({'action':'install'});self.client.thread.join(2)
        self.assertEqual((self.model/'test.onnx').read_bytes(),b'good')
        self.assertEqual(self.client.status()['phase'],'error')
    def test_repair_reuses_verified_files_without_network(self):
        (self.model/'test.onnx').write_bytes(b'good')
        with patch('conversation_service.urllib.request.build_opener') as opener:
            self.client.action({'action':'install'});self.client.thread.join(2)
            opener.return_value.open.assert_not_called()
        self.assertEqual(self.client.status()['phase'],'idle')
    def test_dictation_and_conversation_share_one_cache(self):
        with patch.dict('os.environ',{'LOCALAPPDATA':str(self.root)}):
            oral=ConversationService(self.root);dictation=DictationService(self.root)
            self.assertEqual(oral.cache,dictation.cache)
            self.assertEqual(oral.spec,dictation.spec)
    def test_dictation_stop_finalizes_but_cancel_discards(self):
        dictation=DictationService(self.root,self.model)
        dictation.value.update(phase='listening',session='dictation',text='Texte à conserver')
        with patch.object(dictation,'_send') as send:
            value=dictation.action({'action':'stop','session':'dictation'})
            send.assert_called_once_with({'action':'finish'})
        self.assertEqual(value['text'],'Texte à conserver');self.assertFalse(dictation.cancelled.is_set())
        value=dictation.action({'action':'cancel','session':'dictation'})
        self.assertEqual(value['phase'],'cancelled');self.assertEqual(value['text'],'')
    def test_cancel_only_own_speech(self):
        voice=VoiceService(self.root);job={'owner':'alice','id':'a'*32,'cancel':threading.Event(),'finished':threading.Event()}
        voice.current=job
        with patch.object(voice,'_write') as write:
            voice.cancel('bob','a'*32);self.assertFalse(job['cancel'].is_set());write.assert_not_called()
            voice.cancel('alice','a'*32);self.assertTrue(job['cancel'].is_set());write.assert_called_once()
    def test_speech_payload_cannot_read_paths_or_urls(self):
        voice=VoiceService(self.root)
        with self.assertRaises(ValueError):voice.stream('alice',{'request_id':'a'*32,'text':'Bonjour','voice':'file:///private'})
        with self.assertRaises(ValueError):voice.stream('alice',{'request_id':'a'*32,'text':'x'*601})
    def test_disabled_service_does_not_start_process(self):
        voice=VoiceService(self.root)
        with patch('voice.subprocess.Popen') as process:
            with self.assertRaises(ValueError):voice.stream('alice',{'request_id':'a'*32,'text':'Bonjour'})
            process.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
