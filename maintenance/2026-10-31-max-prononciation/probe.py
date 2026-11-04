"""Offline synthetic CPU probe; never contacts or changes a running client/service."""
import hashlib
import json
from pathlib import Path
import sys
import threading
import time
import wave

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'client-voice'))
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np
import ptts
from max_phonon import PhononVoice
from max_asr import WhisperRecognition

configuration=json.loads((ROOT/'toolchain/voice-max-server/runtime.json').read_text(encoding='utf-8'))
folder=Path(configuration['root'])
spec=json.loads((folder/'tts/phonon-model.json').read_text(encoding='utf-8'))
for name,expected in configuration['manifest'].items():
    if name.startswith('tts/'):
        data=(folder/name).read_bytes()
        assert len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256'], name
voice=PhononVoice(folder)
recognizer=WhisperRecognition(folder,device='CPU')
report={'runtime':ptts.__version__,'voice':spec['voice'],'language':spec['language'],
        'pack':configuration['catalogue']['revision'],'device':'CPU',
        'method':'Synthetic audio and automatic retranscription; not a human pronunciation rating.', 'rows':[]}
try:
    for case in json.loads((OUT/'segments.json').read_text(encoding='utf-8')):
        variants={'whole':[case['whole']]}
        if case['parts']!=[case['whole']]:variants['conversation']=case['parts']
        if case['id']=='markdown':variants['sans_espaces_artificiels']=['L’assistant vous permet d’enregistrer vos fichiers.']
        for variant,parts in variants.items():
            audio=bytearray();started=time.perf_counter()
            for part in parts:
                for frame in voice.stream(part,threading.Event()):audio.extend(frame.get('raw_pcm',b''))
            generation=time.perf_counter()-started
            filename=case['id']+'-'+variant+'.wav'
            with wave.open(str(OUT/filename),'wb') as target:
                target.setnchannels(1);target.setsampwidth(2);target.setframerate(24000);target.writeframes(audio)
            samples=np.frombuffer(audio,dtype='<i2')
            positions=np.arange(len(samples)*2//3)*1.5
            resampled=np.interp(positions,np.arange(len(samples)),samples).astype('<i2').tobytes()
            recognized=recognizer.transcribe({'raw_pcm':resampled})
            row={'id':case['id'],'variant':variant,'input':parts,
                 'normalized':[ptts.normalize(part,lang='fr') for part in parts],
                 'recognized':recognized,'audio_seconds':len(audio)/48000,'generation_seconds':generation,'file':filename}
            report['rows'].append(row)
            (OUT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(row,ensure_ascii=False),flush=True)
finally:
    voice.close();recognizer.close()
