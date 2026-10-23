"""Real packaged ASR and AEC lifecycle; no personal audio stored or sent."""
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import psutil

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'client-qwen'))
from conversation_service import ConversationService, DictationService


def wait(service,phases,timeout=30):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        state=service.status()
        if state['phase'] in phases:return state
        if state['phase']=='error':raise AssertionError(state)
        time.sleep(.05)
    raise TimeoutError(service.status())


def main():
    resources=ROOT/'client-qwen/voice';models=ROOT/'toolchain/asr-models'
    results=[]
    for mode in ('conversation','dictation'):
        args=[str(resources/'conversation-worker/conversation-worker.exe'),'--models',str(models),
              '--resources',str(resources),'--mode',mode,'--fixture',str(ROOT/'preuves/voix-small-20261011/francais.wav')]
        started=time.monotonic()
        process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
        peak=0
        def monitor():
            nonlocal peak
            while process.poll() is None:
                try:peak=max(peak,psutil.Process(process.pid).memory_info().rss)
                except psutil.Error:pass
                time.sleep(.025)
        watch=threading.Thread(target=monitor,daemon=True);watch.start()
        stdout,stderr=process.communicate(timeout=60);watch.join(2)
        assert process.returncode==0,(stdout,stderr)
        final=json.loads(stdout.splitlines()[-1]);assert final['passed'],final
        text=' '.join(t['text'] for t in final['turns']) if mode=='conversation' else final['text']
        assert text=='Bonjour Fred. Je souhaite préparer une réunion demain matin. Ajoute les documents du projet et résume les décisions importantes.',text
        results.append({'mode':mode,'packaged_fixture':final,'wall_seconds':time.monotonic()-started,'peak_rss_bytes':peak})
    # Use the actual Windows DSP only to validate open/read/close. This does not
    # measure acoustic echo quality, double talk or the user's recognition WER.
    for cls in (ConversationService,DictationService):
        service=cls(resources,models)
        try:
            session=service.action({'action':'start'})['session']
            state=wait(service,{'listening'})
            assert state.get('aec') and state.get('captured_samples',0)>0,state
            service.action({'action':'stop','session':session})
            final=wait(service,{'ready'} if cls is DictationService else {'stopped'})
            service.thread.join(5);assert not service.thread.is_alive()
            results.append({'mode':service.mode,'aec_open_read_close':True,'final_phase':final['phase'],'microphone_closed':True})
        finally:service.close()
    report={'passed':True,'model':'Parakeet v3 int8','results':results,
            'limits':'No human speech accuracy, acoustic double-talk, Android device or end-to-end Qwen latency measured.'}
    (OUT/'native-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))


if __name__=='__main__':main()
