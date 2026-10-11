"""Exercise packaged capture without retaining any microphone audio or transcript."""
import json
from pathlib import Path
import subprocess
import time
import psutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
resources=ROOT/'client-qwen/voice'
worker=resources/'conversation-worker/conversation-worker.exe'
process=subprocess.Popen([str(worker),'--models',str(ROOT/'toolchain/conversation-models'),'--resources',str(resources)],
    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
started=time.monotonic();ready=None;peak=0;events=0;stop_sent=False;stopped=False
try:
    for line in process.stdout:
        event=json.loads(line);events+=1;peak=max(peak,psutil.Process(process.pid).memory_info().rss)
        if event.get('phase')=='error':raise RuntimeError(event.get('message','Capture error'))
        if event.get('phase')=='listening' and ready is None:
            ready=time.monotonic()-started;assert event.get('aec') is True
        if ready is not None and time.monotonic()-started-ready>2 and not stop_sent:
            process.stdin.write('{"action":"stop"}\n');process.stdin.flush();stop_sent=True
        if event.get('phase')=='stopped':stopped=True
        if time.monotonic()-started>30:raise TimeoutError('Capture start/stop deadline')
    process.wait(timeout=5);assert ready is not None and stopped and process.returncode==0
    value={'passed':True,'packaged_worker':True,'aec':True,'listening_after_seconds':ready,
           'peak_rss_bytes':peak,'events':events,'stopped':stopped,'exit_code':process.returncode,
           'microphone_audio_saved':False,'microphone_transcripts_saved':False}
    (OUT/'native-capture.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value))
finally:
    if process.poll() is None:process.terminate();process.wait(timeout=5)
