import json,sys,time,wave,threading,shutil,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'client-voice'))
from max_native import NativeVoice
out=Path(__file__).resolve().parent
home=ROOT/'toolchain/max-french-qa'
shutil.copytree(ROOT/'client-voice/max-french',home/'voices/fr-fr',dirs_exist_ok=True)
started=time.monotonic()
voice=NativeVoice(home,'CPU')
print(json.dumps({'loaded_seconds':time.monotonic()-started}),flush=True)
try:
    for index,text in enumerate(['Bonjour, je suis Kiara. Comment puis-je vous aider ?', 'Vous pouvez créer une nouvelle conversation, puis retrouver vos échanges dans l’historique.']):
        cancelled=threading.Event();timer=threading.Timer(180,cancelled.set);timer.daemon=True;timer.start()
        try:
            raw=bytearray();metrics={}
            for frame in voice.stream(text,cancelled):
                raw.extend(frame.get('raw_pcm',b''));metrics.update(frame.get('metrics',{}))
            assert raw and not cancelled.is_set(),'Audio generation failed or timed out'
            with wave.open(str(out/f'french-{index+1}.wav'),'wb') as target:
                target.setnchannels(1);target.setsampwidth(2);target.setframerate(24000);target.writeframes(raw)
            print(json.dumps({'text':text,'duration':len(raw)/48000,'metrics':metrics}),flush=True)
        finally:timer.cancel()
finally:voice.close()
