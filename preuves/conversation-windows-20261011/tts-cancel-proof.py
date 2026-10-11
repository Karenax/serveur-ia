"""Real CPU worker: cancel before queued synthesis, then verify the next request."""
import json
from pathlib import Path
import subprocess
import time
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
process=subprocess.Popen([str(ROOT/'toolchain/voice-server-python/Scripts/python.exe'),'-X','utf8',str(ROOT/'lanceur/voice_worker.py')],
    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
try:
    ready=json.loads(process.stdout.readline());assert ready.get('ready')
    for command in ({'action':'cancel','id':'a'*32},{'action':'speak','id':'a'*32,'text':'Ce texte ne doit pas être joué.'}):
        process.stdin.write(json.dumps(command)+'\n')
    process.stdin.flush();cancelled=json.loads(process.stdout.readline())
    assert cancelled=={'id':'a'*32,'done':True,'cancelled':True},cancelled
    process.stdin.write(json.dumps({'action':'speak','id':'b'*32,'text':'Bonjour. Le prochain tour fonctionne.'})+'\n');process.stdin.flush()
    started=time.monotonic();first=None;frames=0;pcm_bytes=0
    for line in process.stdout:
        value=json.loads(line);assert value.get('id')=='b'*32 and not value.get('error')
        if 'pcm' in value:
            import base64
            frames+=1;pcm_bytes+=len(base64.b64decode(value['pcm']));assert value['rate']==24000
            if first is None:first=time.monotonic()-started
        if value.get('done'):assert not value.get('cancelled');break
    assert frames and pcm_bytes
    process.stdin.close();process.wait(timeout=5);assert process.returncode==0
    result={'passed':True,'engine':'real Pocket TTS CPU offline','cancel_before_speak':cancelled,'next_request_frames':frames,
            'pcm_bytes':pcm_bytes,'first_chunk_seconds':first,'clean_exit':True,'no_audio_saved':True}
    (OUT/'tts-cancel.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
finally:
    if process.poll() is None:process.terminate();process.wait(timeout=5)
