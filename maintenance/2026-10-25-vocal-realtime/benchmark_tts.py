import json,sys,time,wave,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'client-voice'),str(ROOT/'lanceur')]
phonon='--phonon' in sys.argv
started=time.perf_counter()
if phonon:
    import numpy as np
    from phonon_model import load,SPEC
    model=load()
else:
    from max_native import NativeVoice
    model=NativeVoice(ROOT/'toolchain/max-french-qa','CPU')
loading=time.perf_counter()-started
phrases=[
    'Bonjour, je vous écoute. Que souhaitez-vous faire aujourd’hui ?',
    'La réunion aura lieu mardi dans la salle principale. Vous pouvez préparer les documents ce matin, puis prévenir les participants. Je garderai ensuite le résumé dans cette conversation.',
    'Pour retrouver vos anciens échanges, ouvrez l’historique. Vous pourrez ensuite reprendre une conversation ou la ranger dans les archives.'
]
results=[]
try:
    for index,text in enumerate(phrases):
        started=time.perf_counter();first=None;raw=bytearray()
        if phonon:
            with model.stream(text,voice=SPEC['voice']) as audio:
                for chunk in audio:
                    if first is None:first=time.perf_counter()-started
                    raw.extend((np.clip(np.asarray(chunk),-1,1)*32767).astype('<i2').tobytes())
        else:
            for frame in model.stream(text,threading.Event()):
                if frame.get('raw_pcm'):
                    if first is None:first=time.perf_counter()-started
                    raw.extend(frame['raw_pcm'])
        total=time.perf_counter()-started;duration=len(raw)/48000
        row={'text':text,'first_audio_seconds':first,'total_seconds':total,'audio_seconds':duration,'rtf':total/duration}
        results.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
        with wave.open(str(OUT/(('phonon' if phonon else 'qwen')+f'-{index+1}.wav')),'wb') as target:
            target.setnchannels(1);target.setsampwidth(2);target.setframerate(24000);target.writeframes(raw)
finally:
    if not phonon:model.close()
(OUT/(('phonon' if phonon else 'qwen')+'-timings.json')).write_text(json.dumps({'engine':'Phonon' if phonon else 'Qwen Base','device':'CPU','loading_seconds':loading,'rows':results},ensure_ascii=False,indent=2),encoding='utf-8')
