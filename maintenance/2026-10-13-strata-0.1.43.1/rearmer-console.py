import sys,subprocess,time,json
from pathlib import Path
import psutil
ROOT=Path(r'D:\Serveur IA'); sys.path.insert(0,str(ROOT/'lanceur'))
from core import read_json,write_json,same_process,health
assert health().get('loaded')
identity=read_json(ROOT/'lanceur/interface.pid.json')
console=same_process(identity); assert console
assert str(ROOT/'lanceur/app.py') in console.cmdline()
cfg=read_json(Path(read_json(ROOT/'lanceur/session.json')['directory'])/'strata.json')
engines=[(p.pid,p.create_time()) for p in psutil.process_iter(['name']) if p.info['name']=='strata.exe' and p.exe().lower()==cfg['exe'].lower()]
assert len(engines)==1
console.terminate(); console.wait(timeout=15)
write_json(ROOT/'lanceur/relances.json',[])
subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Start-Interface-Qwen.ps1'),'-SansNavigateur','-PreserverEtatModele'],check=True,timeout=45)
for pid,created in engines:assert abs(psutil.Process(pid).create_time()-created)<.01
assert health().get('loaded')
write_json(Path(__file__).parent/'reprise-automatique.json',{'console_restarted':True,'engine_pid_preserved':engines[0][0],'restart_attempts_reset':True,'operations':read_json(ROOT/'lanceur/exploitation.json')})
print('Reprise automatique réarmée, modèle conservé.')
