"""Attend le chargement et la validation CUDA de la production restauree."""
import json
from pathlib import Path
import time
import urllib.request
import psutil

ROOT=Path(__file__).resolve().parent
metadata=json.loads((ROOT/'retablissement-production.json').read_text(encoding='utf-8'))
started=time.monotonic()
state_path=Path(metadata['run_dir'])/'state.json'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
while time.monotonic()-started<5400:
    state=json.loads(state_path.read_text(encoding='utf-8-sig'))
    try:
        health=json.load(opener.open('http://127.0.0.1:8080/health',timeout=3))
    except OSError:
        health={}
    if state['status']=='erreur':
        raise RuntimeError(state.get('error','Erreur de restauration'))
    if state['status']=='pret' and health.get('loaded'):
        interface=json.load(opener.open('http://127.0.0.1:8765/api/state',timeout=10))
        if health['max_context']!=262144 or interface['active']['history']!=6 or not interface['managed']:
            raise RuntimeError('Le profil restaure ne correspond pas au profil original')
        result=dict(status='pret',health=health,active=interface['active'],managed=interface['managed'],
            engine_exe=metadata['exe'],loading_seconds=state.get('loaded_seconds'),
            ready_seconds=state.get('ready_seconds'),supervisor=state['supervisor'])
        (ROOT/'verification-production-prete.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False),flush=True)
        break
    if not psutil.pid_exists(metadata['pid']):
        raise RuntimeError('Le superviseur de production a quitte')
    print(json.dumps(dict(status=state['status'],elapsed_seconds=round(time.monotonic()-started),
        available_ram_gib=state.get('available_ram_gib'),health_loaded=health.get('loaded',False)),ensure_ascii=False),flush=True)
    time.sleep(20)
else:
    raise TimeoutError('Chargement de production non termine apres 90 minutes')
