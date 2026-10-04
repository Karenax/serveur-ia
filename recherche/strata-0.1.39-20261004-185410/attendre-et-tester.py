"""Attend le vrai READY puis mesure une seule variante a la fois."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import urllib.request
import psutil

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--variant',default='officiel')
parser.add_argument('--context',type=int,default=262144)
parser.add_argument('--repeats',type=int,default=2)
parser.add_argument('--warmups',type=int,default=1)
args=parser.parse_args()
run=ROOT/f'{args.variant}-{args.context}'
config=json.loads((run/'config.json').read_text(encoding='utf-8'))
started=time.monotonic()
while True:
    engines=[]
    for p in psutil.process_iter(['pid','name','exe','memory_info']):
        try:
            if p.info['exe'] and Path(p.info['exe']).resolve()==Path(config['exe']).resolve():
                engines.append(p)
        except psutil.Error:
            pass
    if not engines and time.monotonic()-started<30:
        time.sleep(2)
        continue
    if len(engines)!=1:
        raise RuntimeError(f'Expected one research engine, found {len(engines)}')
    engine=engines[0]
    try:
        with urllib.request.urlopen('http://127.0.0.1:8088/health',timeout=2) as response:
            health=json.load(response)
    except OSError:
        health={}
    if health.get('loaded'):
        if (ROOT/'compilation-adaptee-en-cours.flag').exists():
            print('Version officielle chargee; attente de la fin de la compilation avant les mesures CPU.',flush=True)
            time.sleep(20)
            continue
        break
    print(json.dumps(dict(phase='chargement',wait_seconds=round(time.monotonic()-started),
        engine_pid=engine.pid,ram_gib=round(engine.memory_info().rss/2**30,2)),ensure_ascii=False),flush=True)
    if time.monotonic()-started>5400:
        raise TimeoutError('Loading exceeded 90 minutes')
    time.sleep(20)
out=run/'mesures'
print(json.dumps(dict(phase='benchmarks',engine_pid=engine.pid,health=health),ensure_ascii=False),flush=True)
command=[str(ROOT.parent.parent/'Strata-src/.venv/Scripts/python.exe'),str(ROOT/'bench-recherche.py'),
    '--config',str(run/'config.json'),'--out',str(out),'--label',f"{args.variant}-{config.get('research_engine_version','0.1.39')}-ctx{args.context}",
    '--pid',str(engine.pid),'--repeats',str(args.repeats),'--warmups',str(args.warmups)]
raise SystemExit(subprocess.call(command))
