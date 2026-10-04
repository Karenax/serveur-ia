"""Relance exactement la session sauvegardee, sans reecrire les parametres du lanceur."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess

ROOT=Path(__file__).resolve().parent
PROD=ROOT.parent.parent
pointer=json.loads((PROD/'lanceur/session.json').read_text(encoding='utf-8-sig'))
initial=json.loads((ROOT/'production-sauvegarde/session.json').read_text(encoding='utf-8-sig'))
if pointer['directory']!=initial['directory']:
    raise RuntimeError('Une autre session de production a ete selectionnee ; ne pas la remplacer')
run=Path(pointer['directory'])
config_path=run/'strata.json'
config=json.loads(config_path.read_text(encoding='utf-8-sig'))
expected=json.loads((ROOT/'production-sauvegarde/configuration-active.json').read_text(encoding='utf-8-sig'))
if config!=expected:
    raise RuntimeError('La configuration de production a change ; ne pas la remplacer')
engine_stamp=next(x for x in json.loads((ROOT/'production-sauvegarde/empreintes.json').read_text(encoding='utf-8-sig')) if Path(x['path'])==Path(config['exe']))
if hashlib.sha256(Path(config['exe']).read_bytes()).hexdigest().upper()!=engine_stamp['sha256']:
    raise RuntimeError('Le binaire de production a change')
with socket.socket() as probe:
    probe.bind((config['host'],config['port']))
env=os.environ.copy()
env.update(PYTHONDONTWRITEBYTECODE='1',TEMP=r'D:\Temp\strata-recherche',TMP=r'D:\Temp\strata-recherche')
command=[str(PROD/'Strata-src/.venv/Scripts/python.exe'),'-u',str(PROD/'lanceur/runtime.py'),
         '--config',str(config_path),'--run-dir',str(run),'--floor','6']
with (ROOT/'retablissement-production.log').open('ab') as log:
    process=subprocess.Popen(command,cwd=PROD,env=env,stdout=log,stderr=log,
        stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
result=dict(pid=process.pid,config_path=str(config_path),run_dir=str(run),exe=config['exe'],port=config['port'],
    context=262144,history_slots=6,settings_rewritten=False)
(ROOT/'retablissement-production.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False),flush=True)
