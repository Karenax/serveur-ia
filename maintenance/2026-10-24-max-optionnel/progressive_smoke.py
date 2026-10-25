"""Exercise incremental PCM through the actual packaged optional ASR worker."""
import array
import base64
import json
from pathlib import Path
import sys
import wave

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'client-qwen'))
from advanced_voice import AdvancedVoice


with wave.open(str(Path(__file__).with_name('native-french-fixture.wav'))) as source:
    original=array.array('h');original.frombytes(source.readframes(source.getnframes()))
samples=array.array('h',(original[min(len(original)-1,int(i*1.5))] for i in range(len(original)*2//3)))
runtime=AdvancedVoice(ROOT/'toolchain/voice-max-optional-qa')
try:
    results=[]
    for offset,end,final in ((0,48000,False),(48000,len(samples),True)):
        value={'pcm':base64.b64encode(samples[offset:end].tobytes()).decode(),'rate':16000,
               'utterance':'a'*32,'offset':offset,'final':final}
        frames=list(runtime.frames('progressive-qa','transcribe',value,testing=True))
        results.append({'offset':offset,'samples':end-offset,'final':final,'frames':frames})
    text=next(frame['text'] for frame in results[-1]['frames'] if 'text' in frame)
    assert 'orion' in text.casefold() and any(word in text.casefold() for word in ('quinze','15')),text
    report={'passed':True,'transport':'two incremental PCM requests, same owned utterance, packaged worker',
            'results':results,'total_audio_samples_sent':sum(x['samples'] for x in results),'fixture_samples':len(samples)}
    Path(__file__).with_name('native-progressive.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
finally:
    runtime.close()
