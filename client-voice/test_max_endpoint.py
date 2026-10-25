"""A captured continuation must never be submitted as a second, unrelated turn."""
from collections import deque
import importlib.util
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class EndpointTests(unittest.TestCase):
    def test_finished_continuation_waiting_for_decode_preserves_the_first_half(self):
        with patch.dict(sys.modules,{'recognition':SimpleNamespace(Recognizer=object,RATE=16000)}):
            spec=importlib.util.spec_from_file_location('endpoint_fixture',Path(__file__).with_name('max_recognition.py'))
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        recognizer=module.MaxRecognizer.__new__(module.MaxRecognizer)
        recognizer.guard=threading.Condition();recognizer.prefix='';recognizer.turn_id=0;recognizer.turns=deque()
        # The second VAD segment has already ended, but its final ASR result is
        # queued behind the first. The expired first result still belongs to it.
        recognizer.speech=False;recognizer.speech_id=2
        recognizer.pending_final={'text':'Retrouve mes conversations','speech_id':1,'release_at':0,'latency':{}}
        recognizer._release()
        self.assertEqual([],list(recognizer.turns))
        self.assertEqual('Retrouve mes conversations',recognizer.prefix)
        recognizer.pending_final={'text':'de la semaine dernière','speech_id':2,'release_at':0,'latency':{}}
        recognizer._release()
        self.assertEqual(['Retrouve mes conversations de la semaine dernière'],[turn['text'] for turn in recognizer.turns])
        self.assertEqual('',recognizer.prefix)


if __name__=='__main__':unittest.main()
