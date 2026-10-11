"""Local Windows streaming ASR + Silero VAD + Smart Turn; no network or audio files."""
import argparse
import json
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
import threading
import time
from collections import deque
import numpy as np
import onnxruntime as ort
import sherpa_onnx
from turn_features import features
from aec_capture import EchoMicrophone

class Recognizer:
    def __init__(self,models):
        models=Path(models)
        self.asr=sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(models/'tokens.txt'),encoder=str(models/'encoder.onnx'),
            decoder=str(models/'decoder.onnx'),joiner=str(models/'joiner.onnx'),
            num_threads=3,provider='cpu',enable_endpoint_detection=False)
        config=sherpa_onnx.VadModelConfig()
        config.sample_rate=16000;config.num_threads=1
        config.silero_vad.model=str(models/'silero-vad.onnx')
        config.silero_vad.threshold=.6;config.silero_vad.min_silence_duration=.2
        config.silero_vad.min_speech_duration=.12;config.silero_vad.max_speech_duration=30
        self.vad=sherpa_onnx.VoiceActivityDetector(config,buffer_size_in_seconds=35)
        options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
        self.turn=ort.InferenceSession(str(models/'smart-turn.onnx'),options,providers=['CPUExecutionProvider'])
        self.input_name=self.turn.get_inputs()[0].name
        self.stream=self._new_stream();self.window=deque();self.window_samples=0
        self.samples=0;self.last_voice=0;self.started=0;self.next_check=0
        self.speech=False;self.was_speech=False;self.speech_id=0;self.turn_id=0
        self.partial='';self.turns=deque();self.last_probability=None;self.compute=0
    def _new_stream(self):
        stream=self.asr.create_stream()
        stream.accept_waveform(16000,np.zeros(4800,dtype=np.float32))
        return stream
    def accept(self,audio):
        start=time.perf_counter();audio=np.asarray(audio,dtype=np.float32)
        self.samples+=len(audio);self.window.append(audio.copy());self.window_samples+=len(audio)
        while self.window and self.window_samples-len(self.window[0])>=128000:self.window_samples-=len(self.window.popleft())
        self.stream.accept_waveform(16000,audio)
        while self.asr.is_ready(self.stream):self.asr.decode_stream(self.stream)
        self.vad.accept_waveform(audio)
        speech=self.vad.is_speech_detected()
        while not self.vad.empty():self.vad.pop()
        if speech:
            self.last_voice=self.samples
            if not self.speech:self.started=self.samples;self.speech=True
            if not self.was_speech:self.speech_id+=1
        self.was_speech=speech
        self.partial=self.asr.get_result(self.stream).strip() if self.speech else ''
        silence=(self.samples-self.last_voice)/16000
        if self.speech and not speech and silence>=.55 and self.samples>=self.next_check:
            self.next_check=self.samples+8000
            self.last_probability=float(np.asarray(self.turn.run(None,{self.input_name:features(np.concatenate(self.window))})[0]).reshape(-1)[0])
            if self.last_probability>.5 or silence>=4:self.finish()
        elif self.speech and (self.samples-self.started)>=30*16000:self.finish()
        self.compute+=time.perf_counter()-start
    def finish(self):
        if not self.speech:return
        # The French model's first chunk spans roughly 2.6 seconds. A short
        # greeting still needs enough right padding to flush that first chunk.
        self.stream.accept_waveform(16000,np.zeros(48000,dtype=np.float32))
        self.stream.input_finished()
        while self.asr.is_ready(self.stream):self.asr.decode_stream(self.stream)
        text=self.asr.get_result(self.stream).strip()
        if text:
            if len(self.turns)>=8:raise ValueError('Trop de demandes vocales en attente. Raccrochez puis recommencez.')
            self.turn_id+=1;self.turns.append({'id':self.turn_id,'text':text[:6000]})
        self.stream=self._new_stream();self.partial='';self.speech=False
        self.window.clear();self.window_samples=0;self.next_check=0
    def status(self):
        return {'partial':self.partial,'turns':list(self.turns),'speech_id':self.speech_id,
                'speaking':self.was_speech,'turn_probability':self.last_probability}

def emit(value):print(json.dumps(value,ensure_ascii=False),flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--models',required=True)
    parser.add_argument('--resources',required=True);parser.add_argument('--fixture')
    args=parser.parse_args();stop=threading.Event();acks=deque()
    def commands():
        try:
            for line in sys.stdin:
                if len(line)>1024:raise ValueError('Command too large')
                value=json.loads(line)
                if value.get('action')=='stop':stop.set();break
                if value.get('action')=='ack' and isinstance(value.get('turn'),int):acks.append(value['turn'])
        finally:stop.set()
    if not args.fixture:threading.Thread(target=commands,daemon=True).start()
    started=time.monotonic();recognizer=Recognizer(args.models);emit({'phase':'listening','loading_seconds':time.monotonic()-started,'aec':True})
    microphone=None
    try:
        if args.fixture:
            import wave
            with wave.open(args.fixture) as audio:
                assert audio.getframerate()==16000 and audio.getnchannels()==1 and audio.getsampwidth()==2
                pcm=np.frombuffer(audio.readframes(audio.getnframes()),dtype='<i2').astype(np.float32)/32768
            first=None
            for offset in range(0,len(pcm)+5*16000,1600):
                frame=pcm[offset:offset+1600] if offset<len(pcm) else np.zeros(1600,dtype=np.float32)
                recognizer.accept(frame)
                if first is None and recognizer.partial:first=(offset+1600)/16000
            recognizer.finish()
            emit({'phase':'test_done','passed':bool(recognizer.turns),'first_partial_audio_seconds':first,
                  'compute_seconds':recognizer.compute,'audio_seconds':len(pcm)/16000,**recognizer.status()});return
        if stop.is_set():return
        microphone=EchoMicrophone(args.resources);last_emit=0;last_speech=last_turn=0
        while not stop.is_set() and time.monotonic()-started<15*60:
            while acks:
                acknowledged=acks.popleft()
                while recognizer.turns and recognizer.turns[0]['id']<=acknowledged:recognizer.turns.popleft()
            pcm=microphone.read()
            if not pcm:continue
            recognizer.accept(np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768)
            if time.monotonic()-last_emit>.1 or recognizer.speech_id!=last_speech or recognizer.turn_id!=last_turn:
                emit({'phase':'listening','aec':True,**recognizer.status()})
                last_emit=time.monotonic();last_speech=recognizer.speech_id;last_turn=recognizer.turn_id
    finally:
        if microphone:microphone.close()
    emit({'phase':'stopped','partial':'','turns':[],'microphone_closed':True})

if __name__=='__main__':
    try:main()
    except Exception as error:
        emit({'phase':'error','message':str(error) if isinstance(error,(ValueError,OSError)) else 'Le moteur de conversation a échoué.','microphone_closed':True})
        raise
