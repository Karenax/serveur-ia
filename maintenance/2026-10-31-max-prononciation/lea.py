"""Compare the user's exact text with the installed client pack, without changing it."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import wave

import numpy as np
import ptts

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'client-voice'))
from max_asr import WhisperRecognition

sys.stdout.reconfigure(encoding='utf-8')
home=Path(os.environ['LOCALAPPDATA'])/'QwenClient/voice-max'
configuration=json.loads((home/'runtime.json').read_text(encoding='utf-8'))
folder=Path(configuration['root'])
spec=json.loads((folder/'tts/phonon-model.json').read_text(encoding='utf-8'))
case=next(row for row in json.loads((OUT/'segments.json').read_text(encoding='utf-8')) if row['id']=='lea')
inventory={}
for name,expected in configuration['manifest'].items():
    if name.startswith('tts/') or name in ('max-worker.exe','_internal/ptts/_ptts.pyd'):
        data=(folder/name).read_bytes()
        actual=hashlib.sha256(data).hexdigest()
        assert len(data)==expected['bytes'] and actual==expected['sha256'],name
        inventory[name]=actual
ptts.set_num_threads(4)
report={'installed_home':str(home),'root':str(folder),'pack':configuration['catalogue']['revision'],
        'spec':{k:spec[k] for k in ['repository','revision','language','voice','runtime','quant']},
        'verified_files':inventory,'text':case['text'],'parts':case['parts'],'rows':[]}

def save(name,raw,seconds):
    with wave.open(str(OUT/(name+'.wav')),'wb') as target:
        target.setnchannels(1);target.setsampwidth(2);target.setframerate(24000);target.writeframes(raw)
    row={'name':name,'file':name+'.wav','audio_seconds':len(raw)/48000,'generation_seconds':seconds,
         'normalized':ptts.normalize(case['text'],lang='fr')}
    report['rows'].append(row)
    (OUT/'lea-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(row,ensure_ascii=False),flush=True)

process=subprocess.Popen([str(folder/'max-worker.exe'),'--config',str(home/'runtime.json'),'--engine','tts'],
                         stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(OUT/'lea-worker.log').open('w',encoding='utf-8'),
                         text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
try:
    while True:
        line=process.stdout.readline()
        if not line:raise RuntimeError('Installed worker exited; see lea-worker.log')
        frame=json.loads(line)
        if frame.get('error'):raise RuntimeError(frame['error'])
        if frame.get('ready'):break
    for name,parts in [('lea-client-entier',[case['text']]),('lea-client-conversation',case['parts'])]:
        raw=bytearray();started=time.perf_counter()
        for index,part in enumerate(parts):
            identifier=f'{index:032x}'
            process.stdin.write(json.dumps({'id':identifier,'action':'speak','text':part},ensure_ascii=False)+'\n');process.stdin.flush()
            while True:
                line=process.stdout.readline()
                if not line:raise RuntimeError('Installed worker exited')
                frame=json.loads(line)
                if frame.get('error'):raise RuntimeError(frame['error'])
                if frame.get('pcm'):raw.extend(base64.b64decode(frame['pcm']))
                if frame.get('done'):break
        save(name,raw,time.perf_counter()-started)
finally:
    process.stdin.close()
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:process.kill();process.wait()
    process.stdout.close()

for name,voice,quant,temperature in [('lea-reference-tiphaine','Tiphaine','q8_0',.3),
                                   ('lea-voix-origine','default','q8_0',.3),
                                   ('lea-temperature08','Tiphaine','q8_0',.8),
                                   ('lea-f32','Tiphaine','f32',.3)]:
    model=ptts.TTS(str(folder/'tts'),lang='fr',device='cpu',quant=quant,voice='default',voice_catalog=str(folder/'tts'),temperature=temperature)
    model.add_voice('Tiphaine',str(folder/'tts'/spec['voice_file']))
    started=time.perf_counter();audio=model.synth(case['text'],voice=voice)
    raw=(np.clip(audio,-1,1)*32767).astype('<i2').tobytes()
    save(name,raw,time.perf_counter()-started)
    report['rows'][-1].update(model_languages=model.languages,voice=voice,quant=model.quant,temperature=temperature)
    del model

recognizer=WhisperRecognition(folder,device='CPU')
try:
    for row in report['rows']:
        with wave.open(str(OUT/row['file']),'rb') as source:samples=np.frombuffer(source.readframes(source.getnframes()),dtype='<i2')
        positions=np.arange(len(samples)*2//3)*1.5
        raw=np.interp(positions,np.arange(len(samples)),samples).astype('<i2').tobytes()
        row['recognized']=recognizer.transcribe({'raw_pcm':raw})
        print(json.dumps({'name':row['name'],'recognized':row['recognized']},ensure_ascii=False),flush=True)
        (OUT/'lea-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
finally:recognizer.close()
