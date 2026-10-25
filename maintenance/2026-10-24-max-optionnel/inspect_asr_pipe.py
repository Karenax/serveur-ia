"""Bounded diagnostic of the packaged ASR protocol, using the synthetic QA fixture."""
import array
import base64
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
import wave

ROOT=Path(__file__).resolve().parents[2]
cfg=ROOT/'toolchain/voice-max-optional-qa/runtime.json'
configuration=json.loads(cfg.read_text(encoding='utf-8'))
with wave.open(str(Path(__file__).with_name('native-french-fixture.wav'))) as source:
    original=array.array('h');original.frombytes(source.readframes(source.getnframes()))
samples=array.array('h',(original[int(i*1.5)] for i in range(48000)))
payload={'action':'transcribe','id':'a'*32,'pcm':base64.b64encode(samples.tobytes()).decode(),'rate':16000,
         'utterance':'b'*32,'offset':0,'final':False,'stream_key':'c'*64}
for label,command in (
    ('source',[str(ROOT/'toolchain/conversation-client-python/Scripts/python.exe'),str(ROOT/'client-voice/max_pack_worker.py')]),
    ('packaged',[str(Path(configuration['root'])/'max-worker.exe')])):
    with Path(__file__).with_name('pipe-'+label+'.log').open('w',encoding='utf-8') as diagnostics:
        child=subprocess.Popen([*command,'--config',str(cfg),'--engine','asr'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                               stderr=diagnostics,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        output=queue.Queue()
        def reader():
            for line in child.stdout:output.put(line)
        threading.Thread(target=reader,daemon=True).start()
        try:
            print(label,output.get(timeout=30),flush=True)
            child.stdin.write(json.dumps(payload)+'\n');child.stdin.flush()
            print(label,'sent',flush=True)
            while True:
                line=output.get(timeout=15);print(label,line,flush=True)
                if json.loads(line).get('done'):break
        except queue.Empty:
            print(label,'TIMEOUT',flush=True)
        finally:
            child.stdin.close()
            try:child.wait(timeout=3)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=3)
            child.stdout.close()
