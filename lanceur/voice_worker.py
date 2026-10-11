"""Isolated CPU Pocket TTS process. stdin commands; bounded PCM frames on stdout."""
import base64
import json
import os
from pathlib import Path
import queue
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
import threading
import time

ROOT=Path(__file__).resolve().parent.parent
os.environ['HF_HUB_CACHE']=str(ROOT/'toolchain/voice-server-models')
if '--prepare' not in sys.argv:
    os.environ['HF_HUB_OFFLINE']='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
import numpy as np
import torch
torch.set_num_threads(4)
torch.set_num_interop_threads(1)
from pocket_tts import TTSModel

def emit(value):
    print(json.dumps(value,ensure_ascii=False),flush=True)

def load():
    model=TTSModel.load_model(language='french')
    assert str(model.device)=='cpu'
    voice=model.get_state_for_audio_prompt('estelle')
    return model,voice

def main():
    started=time.monotonic()
    model,voice=load()
    emit({'ready':True,'rate':model.sample_rate,'loading_seconds':time.monotonic()-started})
    if '--prepare' in sys.argv:
        import wave
        chunks=[];first=None;start=time.monotonic()
        for chunk in model.generate_audio_stream(voice,'Bonjour, je suis Fred. Nous pouvons maintenant discuter ensemble.'):
            if first is None:first=time.monotonic()-start
            chunks.append(chunk.detach().cpu().numpy())
        samples=np.concatenate(chunks)
        proof=ROOT/'preuves/conversation-windows-20261011'
        with wave.open(str(proof/'fred-francais.wav'),'wb') as output:
            output.setnchannels(1);output.setsampwidth(2);output.setframerate(model.sample_rate)
            output.writeframes((np.clip(samples,-1,1)*32767).astype('<i2').tobytes())
        import psutil
        result={'passed':True,'engine':'Pocket TTS 3.3.0','language':'fr','voice':'estelle',
                'device':str(model.device),'first_chunk_seconds':first,'compute_seconds':time.monotonic()-start,
                'audio_seconds':len(samples)/model.sample_rate,'rss_bytes':psutil.Process().memory_info().rss}
        (proof/'tts-real.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        emit(result);return
    commands=queue.Queue(maxsize=1);stop=threading.Event();current={'id':''};guard=threading.Lock();cancelled=set();closed=threading.Event()
    def reader():
        try:
            for line in sys.stdin:
                if len(line)>8192:raise ValueError('Command too large')
                command=json.loads(line)
                if command.get('action')=='cancel':
                    with guard:
                        cancelled.add(command.get('id'))
                        if len(cancelled)>64:cancelled.clear();cancelled.add(command.get('id'))
                        if command.get('id')==current['id']:stop.set()
                elif command.get('action')=='speak':commands.put(command)
        finally:
            closed.set()
            stop.set()
            try:commands.put_nowait(None)
            except queue.Full:pass
    threading.Thread(target=reader,daemon=True).start()
    while True:
        command=commands.get()
        if command is None:break
        identifier=command['id'];text=command['text']
        with guard:
            current['id']=identifier;stop.clear()
            if identifier in cancelled or closed.is_set():stop.set()
            cancelled.discard(identifier)
        try:
            if not isinstance(text,str) or not 1<=len(text)<=600:raise ValueError('Invalid speech text')
            duration=0
            for chunk in model.generate_audio_stream(voice,text,stop=stop):
                if stop.is_set():break
                pcm=(np.clip(chunk.detach().cpu().numpy(),-1,1)*32767).astype('<i2').tobytes()
                duration+=len(pcm)/2/model.sample_rate
                if duration>90:raise ValueError('Speech duration exceeded')
                for offset in range(0,len(pcm),16000):
                    if stop.is_set():break
                    emit({'id':identifier,'pcm':base64.b64encode(pcm[offset:offset+16000]).decode(),'rate':model.sample_rate})
            emit({'id':identifier,'done':True,'cancelled':stop.is_set()})
        except Exception:
            emit({'id':identifier,'error':'La synthèse vocale a échoué.'})
        finally:
            with guard:current['id']=''
        if closed.is_set():break

if __name__=='__main__':
    try:main()
    except Exception as error:
        emit({'error':'Service vocal indisponible : '+type(error).__name__})
        raise
