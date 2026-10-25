"""Replay a real French recording with an inserted intra-phrase pause."""
import base64,json,sys,time,uuid,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'client-qwen'),str(ROOT/'client-voice')]
import numpy as np
from advanced_voice import AdvancedVoice
from max_recognition import MaxRecognizer
runtime=AdvancedVoice(ROOT/'toolchain/vocal-realtime-stack-qa');recognizer=None
try:
    runtime.warm('pause',uuid.uuid4().hex)
    def transcribe(audio,**segments):
        pcm=(np.clip(audio,-1,1)*32767).astype('<i2').tobytes()
        return runtime.transcribe('pause',{'rate':16000,'pcm':base64.b64encode(pcm).decode(),'request_id':uuid.uuid4().hex,**segments})['text']
    recognizer=MaxRecognizer(runtime.configuration()['asr'],transcribe,'Whisper Turbo · français')
    with wave.open(str(ROOT/'toolchain/french-speech-benchmark/fleurs-fr-1.wav')) as source:
        original=np.frombuffer(source.readframes(source.getnframes()),dtype='<i2').astype(np.float32)/32768
    audio=np.concatenate((original[:64000],np.zeros(12800,np.float32),original[64000:]))
    started=time.monotonic();turns=[]
    for offset in range(0,len(audio)+4*16000,1600):
        frame=audio[offset:offset+1600] if offset<len(audio) else np.zeros(1600,np.float32)
        recognizer.accept(frame)
        delay=started+(offset+len(frame))/16000-time.monotonic()
        if delay>0:time.sleep(delay)
        turns=recognizer.status()['turns']
        assert not turns or offset+len(frame)>=len(audio),('Premature split',turns)
        if turns:break
    assert len(turns)==1,turns
    text=turns[0]['text'].lower()
    assert 'accident' in text and 'malveillant' in text,text
    proof={'passed':True,'source':'FLEURS fr_fr/test first recording','inserted_pause_ms':800,'single_complete_turn':True,'recognized':turns[0]['text']}
    (OUT/'pause-validation.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(proof,ensure_ascii=False))
finally:
    if recognizer:recognizer.close()
    runtime.close()
