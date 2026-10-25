"""Reload gateway code; protect the already loaded model and its supervisors."""
import json,subprocess,sys,time
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
from core import HOME
from validate_live_lots6_8 import get,models
before=json.loads((OUT/'avant-livraison.json').read_text(encoding='utf-8'))
assert models()==before['models'] and not get('/api/state')['queue']['active']
record=json.loads((HOME/'interface.pid.json').read_text(encoding='utf-8'))
parent=psutil.Process(record['pid']);assert abs(parent.create_time()-record['created'])<.01
assert str(HOME/'app.py').casefold() in [str(v).casefold() for v in parent.cmdline()]
protected=set()
for item in before['models']:
    process=psutil.Process(item['pid']);assert abs(process.create_time()-item['created'])<.01
    protected.add(process.pid);protected.update(p.pid for p in process.children(recursive=True))
    for ancestor in process.parents():
        if ancestor.pid==parent.pid:break
        protected.add(ancestor.pid)
children=[(p,p.create_time()) for p in parent.children(recursive=True) if p.pid not in protected]
parent.terminate();parent.wait(timeout=15)
for process,created in reversed(children):
    try:
        if process.is_running() and abs(process.create_time()-created)<.01:
            process.terminate()
            try:process.wait(timeout=10)
            except psutil.TimeoutExpired:
                if process.is_running() and abs(process.create_time()-created)<.01:process.kill()
    except psutil.NoSuchProcess:pass
result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(ROOT/'Start-Interface-Qwen.ps1'),'-SansNavigateur','-PreserverEtatModele'],capture_output=True,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
deadline=time.monotonic()+120
while time.monotonic()<deadline:
    try:
        if get('/api/state')['health']['loaded']:break
    except (OSError,ValueError,KeyError):pass
    time.sleep(1)
else:raise TimeoutError('Gateway restart did not finish')
assert models()==before['models']
print(json.dumps({'passed':True,'model_processes_preserved':True,'launcher_exit_code':result.returncode}))
