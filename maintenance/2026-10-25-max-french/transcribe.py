import sys,wave,json,array
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'client-voice'))
from max_native import ProgressiveParakeet
folder=ROOT/'toolchain/voice-max-optional-qa/packs/vulkan-q4-dcfa1858931e003e/asr'
model=ProgressiveParakeet(str(folder))
results=[]
for path in sorted(Path(__file__).parent.glob('french-*.wav')):
    with wave.open(str(path),'rb') as f:
        pcm=array.array('h');pcm.frombytes(f.readframes(f.getnframes()))
    # 24 kHz to 16 kHz, linear interpolation; PCM fixtures only.
    raw=array.array('h',(round(pcm[(i*3)//2]*(1-((i*3)%2)/2)+pcm[min(len(pcm)-1,(i*3)//2+1)]*(((i*3)%2)/2)) for i in range(len(pcm)*2//3))).tobytes()
    text=model.transcribe({'raw_pcm':raw})
    results.append({'file':path.name,'recognized':text})
Path(__file__).with_name('transcriptions.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False))
