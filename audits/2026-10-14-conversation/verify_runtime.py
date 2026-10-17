"""Real local ASR, microphone frames, Qwen and offline TTS; disposable accounts."""
import argparse
import base64
import json
from pathlib import Path
import queue
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from remote import AccessStore,serve_gateway


def native(packaged=False):
    resources=ROOT/'client-qwen/voice'
    command=[str(resources/'conversation-worker/conversation-worker.exe')] if packaged else [str(ROOT/'toolchain/conversation-client-python/Scripts/python.exe'),'-X','utf8',str(ROOT/'client-voice/conversation_worker.py')]
    common=['--models',str(ROOT/'toolchain/conversation-models'),'--resources',str(resources)]
    fixture=ROOT/'preuves/voix-small-20261011/francais.wav'
    result=subprocess.run(command+common+['--fixture',str(fixture)],capture_output=True,encoding='utf-8',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,result.stderr[-1000:]
    transcript=json.loads(result.stdout.splitlines()[-1]);assert transcript['passed'] and len(transcript['turns'])==2
    process=subprocess.Popen(command+common,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
    events=queue.Queue()
    def read():
        for line in process.stdout:events.put(json.loads(line))
        events.put(None)
    threading.Thread(target=read,daemon=True).start()
    started=time.monotonic();ready=None;captured=0;stopped=False
    try:
        while time.monotonic()-started<20:
            event=events.get(timeout=10)
            if event is None:break
            assert event.get('phase')!='error',event.get('message')
            captured=max(captured,event.get('captured_samples',0))
            if event.get('phase')=='listening' and ready is None:
                ready=time.monotonic()-started;assert event.get('aec') and captured>0
            if ready is not None and captured>=16000:
                process.stdin.write('{"action":"stop"}\n');process.stdin.flush();break
        while time.monotonic()-started<25:
            event=events.get(timeout=5)
            if event is None:break
            if event.get('phase')=='stopped':stopped=True;break
        process.wait(timeout=5);assert ready is not None and stopped and process.returncode==0
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=5)
    report={'passed':True,'packaged':packaged,'actual_microphone_frames':captured,'microphone_ready_seconds':ready,
            'microphone_audio_saved':False,'microphone_transcripts_saved':False,'asr_fixture':{k:transcript[k] for k in ('audio_seconds','compute_seconds','first_partial_audio_seconds','turns')},
            'recognition_limit':'synthetic French speech; two grammar errors persist; no human accuracy claim'}
    (OUT/('native-packaged.json' if packaged else 'native-source.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


def live():
    class NoHermes:
        def stream(self,*args):raise AssertionError('Hermes called')
        def select_model(self,*args):raise AssertionError('Hermes selection called')
        def cancel(self,*args):raise AssertionError('Hermes cancellation called')
    with tempfile.TemporaryDirectory(prefix='fred-voice-live-') as folder:
        store=AccessStore(folder);store.configure({'enabled':True,'url':'wireguard://10.77.0.1:8766'})
        access=store.issue('Vocal proof only');store.hermes=NoHermes()
        gateway=serve_gateway(store,lambda:(8080,'qwen3.8-flash-next-iq4-xs',''),0)
        threading.Thread(target=gateway.serve_forever,daemon=True).start()
        store.voice.configure(True)
        try:
            assert store.voice.ready.wait(45),store.voice.status()
            base='http://127.0.0.1:'+str(gateway.server_port)
            report={'passed':False,'hermes_called':False,'cloud_called':False,'turns':[]}
            for question in ('Bonjour Fred, tu m’entends bien ?','Combien font dix-sept fois dix-neuf ?'):
                request=secrets.token_hex(16);text='';first=None;done=False;start=time.monotonic()
                body={'voice_conversation':True,'conversation_id':'runtime-proof','turn_id':request,'messages':[{'role':'user','content':question}],'stream':True}
                headers={'Content-Type':'application/json','Authorization':'Bearer '+access['token'],'X-Qwen-Request':request}
                with urllib.request.urlopen(urllib.request.Request(base+'/v1/chat/completions',json.dumps(body).encode(),headers),timeout=120) as response:
                    for line in response:
                        if line.strip()==b'data: [DONE]':done=True;break
                        if line.startswith(b'data: '):
                            event=json.loads(line[6:]);assert not event.get('error'),event
                            for choice in event.get('choices',[]):
                                part=choice.get('delta',{}).get('content','')
                                if part and first is None:first=time.monotonic()-start
                                text+=part
                assert done and text
                if 'dix-sept' in question:assert '323' in text or 'trois cent vingt-trois' in text.lower(),text
                begin=time.monotonic();audio_first=None;pcm_bytes=0;audio_done=False
                payload={'request_id':secrets.token_hex(16),'text':text[:600],'stream':True}
                with urllib.request.urlopen(urllib.request.Request(base+'/v1/voice/speech',json.dumps(payload).encode(),headers),timeout=60) as response:
                    for line in response:
                        if not line.startswith(b'data: '):continue
                        event=json.loads(line[6:]);assert not event.get('error'),event
                        if event.get('pcm'):
                            if audio_first is None:audio_first=time.monotonic()-begin
                            pcm_bytes+=len(base64.b64decode(event['pcm']))
                        if event.get('done'):audio_done=True;assert not event.get('cancelled');break
                assert audio_done and pcm_bytes
                report['turns'].append({'question':question,'answer':text,'first_text_seconds':first,'first_tts_fragment_seconds':audio_first,'audio_seconds':pcm_bytes/48000})
            report['passed']=True;report['tts']='real Pocket TTS CPU offline';report['model']='loaded production Qwen, no restart';report['network']='temporary authenticated gateway on loopback'
            (OUT/'live-model-tts.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
        finally:
            store.hermes=None;gateway.shutdown();gateway.server_close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['native','packaged','live']);mode=parser.parse_args().mode
    if mode=='live':live()
    else:native(mode=='packaged')
