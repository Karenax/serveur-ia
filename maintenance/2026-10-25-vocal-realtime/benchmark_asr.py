import json,sys,time,wave,re,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'client-voice'))
from max_asr import WhisperRecognition,available_devices
from max_native import ProgressiveParakeet
sys.stdout.reconfigure(encoding='utf-8')
OUT=Path(__file__).resolve().parent
corpus=json.loads((OUT/'corpus.json').read_text(encoding='utf-8'))['files']
root=ROOT/'toolchain/max-realtime-qa'
def words(text):return re.findall(r'[a-z0-9]+',unicodedata.normalize('NFKD',text.lower().replace('’',"'")).encode('ascii','ignore').decode())
def distance(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a):
        nxt=[i+1]
        for j,y in enumerate(b):nxt.append(min(nxt[-1]+1,row[j+1]+1,row[j]+(x!=y)))
        row=nxt
    return row[-1]
engines=[('parakeet',lambda:ProgressiveParakeet(ROOT/'toolchain/asr-models')),
         ('whisper-cpu',lambda:WhisperRecognition(root,device='CPU'))]
cards=available_devices(root)
quad=next((card for card in cards if 'P2200' in card['description']),None)
if quad:engines.append(('whisper-vulkan',lambda:WhisperRecognition(root,selection=quad['id'])))
if '--gpu-only' in sys.argv:engines=[item for item in engines if item[0]=='whisper-vulkan']
result={}
for name,load in engines:
    started=time.perf_counter();model=load();loading=time.perf_counter()-started;rows=[]
    try:
        for item in corpus:
            with wave.open(str(ROOT/'toolchain/french-speech-benchmark'/item['file'])) as source:raw=source.readframes(source.getnframes())
            started=time.perf_counter();text=model.transcribe({'raw_pcm':raw});seconds=time.perf_counter()-started
            expected=words(item['text']);actual=words(text)
            rows.append({'file':item['file'],'expected':item['text'],'recognized':text,'seconds':seconds,'rtf':seconds/item['seconds'],'errors':distance(expected,actual),'words':len(expected)})
            print(json.dumps({'engine':name,**rows[-1]},ensure_ascii=False),flush=True)
    finally:
        if hasattr(model,'close'):model.close()
    result[name]={'loading_seconds':loading,'word_error_rate':sum(row['errors'] for row in rows)/sum(row['words'] for row in rows),'mean_seconds':sum(row['seconds'] for row in rows)/len(rows),'rows':rows,'device':quad if name=='whisper-vulkan' else 'CPU'}
    (OUT/('asr-vulkan-comparison.json' if '--gpu-only' in sys.argv else 'asr-comparison.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
