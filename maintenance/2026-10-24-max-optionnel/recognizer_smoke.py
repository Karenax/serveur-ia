"""Actual Max-only VAD/Smart Turn/progressive decoder on synthetic French PCM."""
import base64
import json
from pathlib import Path
import sys
import wave
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'client-voice'))
from max_native import ProgressiveParakeet
from max_recognition import MaxRecognizer

configuration=json.loads((ROOT/'toolchain/voice-max-optional-qa/runtime.json').read_text(encoding='utf-8'))
model=ProgressiveParakeet(configuration['asr'])
sent=[]
def transcribe(audio,**metadata):
    raw=(np.clip(audio,-1,1)*32767).astype('<i2').tobytes()
    sent.append({'samples':len(audio),**metadata})
    return model.transcribe({'raw_pcm':raw,'stream_key':metadata['utterance'],**metadata})

recognizer=MaxRecognizer(configuration['asr'],transcribe)
try:
    with wave.open(str(Path(__file__).with_name('native-french-fixture.wav'))) as source:
        original=np.frombuffer(source.readframes(source.getnframes()),dtype='<i2').astype(np.float32)/32768
    audio=original[(np.arange(len(original)*2//3)*1.5).astype(int)]
    for offset in range(0,len(audio)+32000,1600):
        recognizer.accept(audio[offset:offset+1600] if offset<len(audio) else np.zeros(1600,np.float32))
    recognizer.finish();recognizer.drain()
    result=recognizer.status()
    text=' '.join(turn['text'] for turn in result['turns'])
    assert 'orion' in text.casefold() and any(word in text.casefold() for word in ('15','quinze')),result
    report={'passed':True,'state':result,'segments':sent,'scope':'real CPU models and Max turn logic; synthetic file, no microphone'}
    Path(__file__).with_name('native-recognizer.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
finally:
    recognizer.close()
