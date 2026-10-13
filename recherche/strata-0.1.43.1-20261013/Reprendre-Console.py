"""Reconnect the console watcher to the restored server without stopping its model."""
import json, subprocess, time, urllib.request
from pathlib import Path
import psutil

ROOT=Path(__file__).resolve().parent
PROD=ROOT.parent.parent
identity=json.loads((PROD/'lanceur/interface.pid.json').read_text(encoding='utf-8-sig'))
proc=psutil.Process(identity['pid'])
assert abs(proc.create_time()-identity['created'])<.1, 'PID de console reutilise'
cmd=proc.cmdline()
assert str(PROD/'lanceur/app.py').lower() in [s.lower() for s in cmd], cmd
assert '--port' in cmd and cmd[cmd.index('--port')+1]=='8765', cmd
engines=[]
for p in psutil.process_iter(['name']):
    try:
        if p.info['name']=='strata.exe' and Path(p.exe()).resolve()==PROD/'strata-build-p100/strata.exe':
            engines.append((p.pid,p.create_time()))
    except psutil.Error: pass
assert len(engines)==1, engines
proc.terminate()
psutil.wait_procs([proc],timeout=10)
time.sleep(2)
with (ROOT/'logs/reprise-console.log').open('w',encoding='utf-8') as stream:
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',
        '-File',str(PROD/'Start-Interface-Qwen.ps1'),'-SansNavigateur','-PreserverEtatModele'],
        stdout=stream,stderr=stream,timeout=45)
assert result.returncode==0, 'Consulter reprise-console.log'
new_identity=json.loads((PROD/'lanceur/interface.pid.json').read_text(encoding='utf-8-sig'))
assert new_identity['pid']!=identity['pid']
for pid,created in engines:
    assert abs(psutil.Process(pid).create_time()-created)<.1, 'Le moteur a ete remplace'
report={'console_reconnected':True,'previous_pid':identity['pid'],'new_pid':new_identity['pid'],
        'engine_pid_unchanged':engines[0][0],'preserve_model_state':True,
        'autoload_and_restart_settings':json.loads((PROD/'lanceur/exploitation.json').read_text(encoding='utf-8-sig'))}
(ROOT/'validation/console-reprise.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report),flush=True)
