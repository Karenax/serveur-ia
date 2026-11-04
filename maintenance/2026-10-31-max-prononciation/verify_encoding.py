"""Use the corrected client writer with the unmodified installed frozen worker."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import wave
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'shared'),str(ROOT/'client-voice')]
from kiara_shared.voice_runtime import AdvancedVoice
from max_asr import WhisperRecognition
sys.stdout.reconfigure(encoding='utf-8')
home=Path(os.environ['LOCALAPPDATA'])/'QwenClient/voice-max'
configuration=json.loads((home/'runtime.json').read_text(encoding='utf-8'))
root=Path(configuration['root'])
case=next(row for row in json.loads((OUT/'segments.json').read_text(encoding='utf-8')) if row['id']=='lea')
service=AdvancedVoice(home)
environment={**os.environ,'PYTHONUTF8':'0','PYTHONIOENCODING':'cp1252'}
with (OUT/'encoding-worker.log').open('w',encoding='utf-8') as log:
    worker=subprocess.Popen([str(root/'max-worker.exe'),'--config',str(home/'runtime.json'),'--engine','tts'],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,encoding='utf-8',env=environment,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    service.processes['tts']=worker
    try:
        while True:
            line=worker.stdout.readline()
            if not line:raise RuntimeError('Worker exited')
            frame=json.loads(line)
            if frame.get('error'):raise RuntimeError(frame['error'])
            if frame.get('ready'):break
        raw=bytearray()
        for index,text in enumerate(case['parts']):
            service._write({'action':'speak','id':f'{index:032x}','text':text},'tts')
            while True:
                line=worker.stdout.readline()
                if not line:raise RuntimeError('Worker exited')
                frame=json.loads(line)
                if frame.get('error'):raise RuntimeError(frame['error'])
                if frame.get('pcm'):raw.extend(base64.b64decode(frame['pcm']))
                if frame.get('done'):break
    finally:
        service.processes.clear();worker.stdin.close()
        try:worker.wait(timeout=10)
        except subprocess.TimeoutExpired:worker.kill();worker.wait()
        worker.stdout.close()
filename='lea-client-corrige.wav'
with wave.open(str(OUT/filename),'wb') as target:
    target.setnchannels(1);target.setsampwidth(2);target.setframerate(24000);target.writeframes(raw)
recognizer=WhisperRecognition(root,device='CPU')
try:
    samples=np.frombuffer(raw,dtype='<i2')
    resampled=np.interp(np.arange(len(samples)*2//3)*1.5,np.arange(len(samples)),samples).astype('<i2').tobytes()
    recognized=recognizer.transcribe({'raw_pcm':resampled})
finally:recognizer.close()
result={'text':case['text'],'parts':case['parts'],'pack':configuration['catalogue']['revision'],
        'installed_worker_unchanged':True,'worker_input_encoding':'cp1252 (forced for regression)',
        'writer':'AdvancedVoice._write from corrected source','audio_seconds':len(raw)/48000,
        'recognized':recognized,'file':filename,
        'mojibake_example':'avança'.encode('utf-8').decode('cp1252')}
(OUT/'encoding-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
