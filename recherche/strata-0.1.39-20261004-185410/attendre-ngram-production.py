"""Attend la production retablie et confirme le profil RAM initial apres l'essai SSD."""
import json
from pathlib import Path
import time
import urllib.request
import psutil

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'normal-ngram-ssd-262144'
metadata=json.loads((RUN/'retablissement-production.json').read_text(encoding='utf-8'))
started=time.monotonic()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
while time.monotonic()-started<5400:
    state=json.loads((Path(metadata['run_dir'])/'state.json').read_text(encoding='utf-8-sig'))
    try:
        health=json.load(opener.open('http://127.0.0.1:8080/health',timeout=3))
    except OSError:
        health={}
    if state['status']=='erreur':
        raise RuntimeError(state.get('error','Restauration en erreur'))
    if state['status']=='pret' and health.get('loaded'):
        interface=json.load(opener.open('http://127.0.0.1:8765/api/state',timeout=10))
        active=interface['active']
        if health['max_context']!=262144 or active['history']!=6 or not interface['managed']:
            raise RuntimeError('Profil actif different du profil initial')
        config=json.loads(Path(metadata['config_path']).read_text(encoding='utf-8-sig'))
        if config['args'][config['args'].index('--ple-io')+1]!='ram':
            raise RuntimeError('La PLE de production doit etre en RAM')
        result=dict(status='pret',health=health,active=active,managed=interface['managed'],
            engine_exe=metadata['exe'],loading_seconds=state.get('loaded_seconds'),
            ready_seconds=state.get('ready_seconds'),supervisor=state['supervisor'],ngram_mode='ram')
        (RUN/'verification-production-prete.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False),flush=True)
        break
    if not psutil.pid_exists(metadata['pid']):
        raise RuntimeError('Le superviseur a quitte')
    print(json.dumps(dict(status=state['status'],elapsed_seconds=round(time.monotonic()-started),
        available_ram_gib=state.get('available_ram_gib'),health_loaded=health.get('loaded',False)),ensure_ascii=False),flush=True)
    time.sleep(20)
else:
    raise TimeoutError('La production ne termine pas son chargement apres 90 minutes')
