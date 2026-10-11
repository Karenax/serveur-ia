"""Restore the saved active session without changing launcher settings."""
import hashlib,json,subprocess,socket,sys
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parent
PROD=ROOT.parent.parent
backup=ROOT/'production-sauvegarde'
info=json.loads((backup/'reprise.json').read_text(encoding='utf-8-sig'))
configpath=Path(info['config_path'])
cfg=json.loads(configpath.read_text(encoding='utf-8-sig'))
saved=json.loads((backup/'configuration-active.json').read_text(encoding='utf-8-sig'))
if cfg!=saved:raise SystemExit('La configuration active a change : reprise refusee.')
for stamp in info['files']:
    if hashlib.sha256(Path(stamp['path']).read_bytes()).hexdigest()!=stamp['sha256']:
        raise SystemExit('Un fichier de production a change : '+stamp['path'])
for p in psutil.process_iter(['name']):
    try:
        if p.exe().lower()==cfg['exe'].replace('/','\\').lower():raise SystemExit('Le moteur de production fonctionne deja.')
    except (psutil.AccessDenied,psutil.NoSuchProcess):pass
with socket.socket() as probe:probe.bind(('127.0.0.1',int(cfg['port'])))
cmd=[str(PROD/'Strata-src/.venv/Scripts/python.exe'),'-u',str(PROD/'lanceur/runtime.py'),
     '--config',str(configpath),'--run-dir',str(configpath.parent),'--floor',str(info['floor'])]
with (ROOT/'logs/reprise-production.log').open('ab') as log:
    p=subprocess.Popen(cmd,cwd=PROD,stdout=log,stderr=log,stdin=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
(ROOT/'validation/reprise-production.json').write_text(json.dumps({'pid':p.pid,'config':str(configpath),'port':cfg['port']},indent=2),encoding='utf-8')
print('Reprise de la production lancee, PID',p.pid,flush=True)
