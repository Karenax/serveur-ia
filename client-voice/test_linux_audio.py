"""Linux audio boundaries and worker lifecycle with synthetic capture devices."""
import importlib.util
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

import linux_audio


class PulseCaptureTests(unittest.TestCase):
    def microphone(self):
        process=Mock();process.stdout.fileno.return_value=7;process.poll.return_value=None
        with patch.object(linux_audio.shutil,'which',return_value='/usr/bin/parec'), \
             patch.object(linux_audio.subprocess,'Popen',return_value=process) as spawn, \
             patch.object(linux_audio.os,'set_blocking'):
            microphone=linux_audio.PulseMicrophone()
        self.addCleanup(microphone.close)
        self.assertIn('--rate=16000',spawn.call_args.args[0])
        self.assertIn('--channels=1',spawn.call_args.args[0])
        self.assertFalse(microphone.aec)
        return microphone,process

    def test_pcm_samples_are_not_lost_at_odd_pipe_boundaries(self):
        microphone,_=self.microphone()
        with patch.object(linux_audio.select,'select',return_value=([7],[],[])), \
             patch.object(linux_audio.os,'read',side_effect=[b'\x01',b'\x02\x03',b'\x04']):
            self.assertEqual(microphone.read(),b'')
            self.assertEqual(microphone.read(),b'\x01\x02')
            self.assertEqual(microphone.read(),b'\x03\x04')

    def test_absent_or_disconnected_microphone_is_an_actionable_error(self):
        with patch.object(linux_audio.shutil,'which',return_value=None):
            with self.assertRaisesRegex(OSError,'pulseaudio-utils'):linux_audio.PulseMicrophone()
        microphone,_=self.microphone()
        with patch.object(linux_audio.select,'select',return_value=([7],[],[])), \
             patch.object(linux_audio.os,'read',return_value=b''):
            with self.assertRaisesRegex(OSError,'déconnecté'):microphone.read()

    def test_bounded_read_and_close_reap_the_owned_capture_process(self):
        microphone,process=self.microphone()
        with patch.object(linux_audio.select,'select',return_value=([],[],[])) as select:
            self.assertEqual(microphone.read(),b'')
            self.assertEqual(select.call_args.args[-1],.1)
        process.wait.side_effect=[subprocess.TimeoutExpired('parec',2),0]
        microphone.close();microphone.close()
        process.terminate.assert_called_once();process.kill.assert_called_once()
        process.stdout.close.assert_called_once()
        with self.assertRaisesRegex(OSError,'fermé'):microphone.read()


class LinuxWorkerTests(unittest.TestCase):
    def test_playback_and_mute_close_capture_then_resume_without_ending_the_call(self):
        with patch.dict(sys.modules,{'recognition':SimpleNamespace(Recognizer=object)}):
            spec=importlib.util.spec_from_file_location('linux_worker_test',Path(__file__).with_name('conversation_worker.py'))
            worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
        lines=queue.Queue();frames=queue.Queue();devices=[];errors=[]
        class Input:
            def __iter__(self):return self
            def __next__(self):return lines.get(timeout=5)
        class Microphone:
            def __init__(self,*args):self.closed=False;self.reads=0;devices.append(self)
            def read(self):self.reads+=1;time.sleep(.01);return b'\0'*3200
            def close(self):self.closed=True
        class Recognizer:
            accepted=0
            def __init__(self,*args,**kwargs):pass
            def accept(self,audio):type(self).accepted+=len(audio)
            def reset_capture(self):pass
            def status(self):return {'turns':[],'partial':'','text':'','speech_id':0}
            def close(self):pass
        def wait_for(predicate):
            deadline=time.monotonic()+4
            while time.monotonic()<deadline:
                frame=frames.get(timeout=4)
                if predicate(frame):return frame
            raise AssertionError('Worker state timed out')
        def run():
            try:worker.main()
            except Exception as error:errors.append(error)
        with patch.object(worker,'Recognizer',Recognizer),patch.object(worker,'EchoMicrophone',Microphone), \
             patch.object(worker,'emit',frames.put),patch.object(sys,'platform','linux'), \
             patch.object(sys,'stdin',Input()),patch.object(sys,'argv',['worker','--models','fixture','--resources','fixture']):
            thread=threading.Thread(target=run);thread.start()
            try:
                wait_for(lambda frame:frame.get('phase')=='listening' and not frame.get('microphone_closed'))
                # An untrusted/stale enabled-interruptions preference must not bypass the pause.
                lines.put('{"action":"playback","playing":true,"interruptions":true}\n')
                frame=wait_for(lambda frame:frame.get('capture_paused') and frame.get('microphone_closed'))
                self.assertFalse(frame['aec']);self.assertTrue(devices[0].closed)
                before=Recognizer.accepted;reads=devices[0].reads;time.sleep(.15)
                self.assertEqual(Recognizer.accepted,before);self.assertEqual(devices[0].reads,reads)
                lines.put('{"action":"mute","muted":true}\n')
                wait_for(lambda frame:frame.get('muted') and frame.get('microphone_closed'))
                lines.put('{"action":"playback","playing":false,"interruptions":false}\n')
                time.sleep(.15);self.assertEqual(len(devices),1)
                lines.put('{"action":"mute","muted":false}\n')
                wait_for(lambda frame:not frame.get('muted') and not frame.get('microphone_closed'))
                self.assertEqual(len(devices),2);self.assertGreater(Recognizer.accepted,before)
            finally:
                lines.put('{"action":"stop"}\n');thread.join(4)
        self.assertFalse(thread.is_alive());self.assertEqual(errors,[])
        self.assertTrue(all(device.closed for device in devices))


if __name__=='__main__':unittest.main(verbosity=2)
