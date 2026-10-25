"""Compare real-time endpoint delays on synthetic speech; never open a microphone."""
import json
from pathlib import Path
import sys
import time
import wave
import numpy as np

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'client-voice'))
import recognition


def main():
    with wave.open(str(ROOT/'preuves/voix-small-20261011/francais.wav')) as wav:
        rate=wav.getframerate();assert wav.getnchannels()==1 and wav.getsampwidth()==2
        audio=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(np.float32)/32768
    if rate!=16000:
        import math
        from scipy.signal import resample_poly
        d=math.gcd(rate,16000);audio=resample_poly(audio,16000//d,rate//d).astype(np.float32)
    frame=1600;last_sound=max(i+len(audio[i:i+frame]) for i in range(0,len(audio),frame) if np.sqrt(np.mean(audio[i:i+frame]**2))>.003)/16000
    results=[]
    for label,minimum,maximum in [('previous',.85,2.5),('updated',.65,1.6)]:
        recognition.CONVERSATION_SILENCE=minimum;recognition.CONVERSATION_MAX_SILENCE=maximum
        recognizer=recognition.Recognizer(ROOT/'toolchain/asr-models')
        start=time.perf_counter();first=None;endpoint=None;turns_seen=0
        try:
            padded=np.concatenate((audio,np.zeros(48000,dtype=np.float32)))
            for at in range(0,len(padded),frame):
                target=start+(at+frame)/16000;time.sleep(max(0,target-time.perf_counter()))
                speaking=recognizer.speech;recognizer.accept(padded[at:at+frame]);state=recognizer.status()
                elapsed=time.perf_counter()-start-last_sound
                if speaking and not recognizer.speech and elapsed>=0:endpoint=elapsed
                if len(state['turns'])>turns_seen:
                    turns_seen=len(state['turns'])
                    if elapsed>=0:first=elapsed
            recognizer.drain();state=recognizer.status();text=' '.join(t['text'] for t in state['turns'])
            assert text=='Bonjour Fred. Je souhaite préparer une réunion demain matin. Ajoute les documents du projet et résume les décisions importantes.',text
            assert first is not None,'No automatic endpoint'
            results.append({'configuration':label,'minimum_silence_seconds':minimum,'maximum_silence_seconds':maximum,'text':text,
                            'last_sound_seconds':last_sound,'endpoint_after_last_sound_seconds':endpoint,'text_available_after_last_sound_seconds':first,'decode_compute_seconds':state['compute_seconds']})
        finally:recognizer.close()
    report={'passed':True,'model':'Parakeet v3 int8','results':results,'limits':'One synthetic spoken fixture fed in real time on this PC. Does not establish microphone, noise or human pause performance.'}
    (OUT/'asr-latency.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
