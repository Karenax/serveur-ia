"""Mute closes the capture device on its owning thread and resumes without hanging up."""
import importlib.util
from pathlib import Path
import queue
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class MuteWorkerTests(unittest.TestCase):
    def test_mute_closes_capture_and_preserves_session_until_explicit_stop(self):
        # Import with a recognizer stand-in: no ONNX dependencies or model download.
        with patch.dict(sys.modules,{'recognition':SimpleNamespace(Recognizer=object)}):
            spec=importlib.util.spec_from_file_location('mute_worker_test',Path(__file__).with_name('conversation_worker.py'))
            worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
        lines=queue.Queue();output=queue.Queue();devices=[];errors=[]
        class Input:
            def __iter__(self):return self
            def __next__(self):return lines.get(timeout=5)
        class Microphone:
            def __init__(self,*args):self.owner=threading.get_ident();self.closed=False;self.reads=0;devices.append(self)
            def read(self):
                self.reads+=1;time.sleep(.01);return b'\0'*3200
            def close(self):
                self.assert_owner=threading.get_ident()==self.owner;self.closed=True
        class Recognizer:
            accepted=0;resets=0;closed=False
            def __init__(self,*args,**kwargs):pass
            def accept(self,audio):type(self).accepted+=len(audio)
            def status(self):return {'turns':[],'partial':'','text':'','speech_id':0}
            def reset_capture(self):type(self).resets+=1
            def close(self):type(self).closed=True
        def wait_for(predicate):
            until=time.monotonic()+3
            while time.monotonic()<until:
                frame=output.get(timeout=3)
                if predicate(frame):return frame
            raise AssertionError('Worker state timed out')
        def run():
            try:worker.main()
            except Exception as error:errors.append(error)
        with patch.object(worker,'Recognizer',Recognizer),patch.object(worker,'EchoMicrophone',Microphone),patch.object(worker,'emit',output.put),patch.object(sys,'stdin',Input()),patch.object(sys,'argv',['worker','--models','fixture','--resources','fixture']):
            thread=threading.Thread(target=run);thread.start()
            try:
                wait_for(lambda f:f.get('phase')=='listening')
                lines.put('{"action":"mute","muted":true}\n')
                wait_for(lambda f:f.get('muted') is True and f.get('microphone_closed'))
                before=Recognizer.accepted;reads=devices[0].reads
                time.sleep(.2)
                self.assertEqual(before,Recognizer.accepted);self.assertEqual(reads,devices[0].reads)
                self.assertTrue(devices[0].closed and devices[0].assert_owner)
                self.assertTrue(thread.is_alive());self.assertEqual(1,Recognizer.resets)
                lines.put('{"action":"mute","muted":false}\n')
                wait_for(lambda f:f.get('muted') is False and not f.get('microphone_closed'))
                self.assertEqual(2,len(devices));self.assertGreater(Recognizer.accepted,before)
                self.assertFalse(devices[1].closed)
            finally:lines.put('{"action":"stop"}\n');thread.join(4)
        self.assertFalse(thread.is_alive());self.assertEqual([],errors)
        self.assertTrue(Recognizer.closed);self.assertTrue(devices[-1].closed and devices[-1].assert_owner)


if __name__=='__main__':unittest.main(verbosity=2)
