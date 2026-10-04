"""Mesure isolee du moteur precedent avec le meme contexte, sans changer la production."""
import datetime as dt
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
PROD=ROOT.parent.parent
RUN=ROOT/'reference-production-262144'
RUN.mkdir(exist_ok=True)
config=json.loads((ROOT/'production-sauvegarde/configuration-active.json').read_text(encoding='utf-8'))
def set_arg(flag,value):
    config['args'][config['args'].index(flag)+1]=str(value)
set_arg('--native',json.loads((ROOT/'modele-ssd.json').read_text(encoding='utf-8'))['native'])
set_arg('--prompt-cache',0)
if '--prompt-cache-every' in config['args']:
    i=config['args'].index('--prompt-cache-every')
    del config['args'][i:i+2]
config['env'].pop('STRATA_P100_DIAGNOSTIC_SYNC_FILE',None)
config.update(host='127.0.0.1',port=8088,api_key='',cors_origins=[],trusted_origins=[],
              log=str(RUN/'engine.log'),research_engine_version='0.1.35+hybride')
def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save(RUN/'config.json',config)
save(RUN/'origine.json',dict(revision='5c284bf7bd64230eb93ac9ff5df71aa6cf8c6505',
    production_executable=config['exe'],context=262144,prompt_cache=0,
    note='Existing production binary, SSD model copy, isolated API/logs; no production settings rewritten'))
env=os.environ.copy()
for key in list(env):
    if key.startswith('STRATA_'):
        del env[key]
env.update(config['env'])
env.update(PYTHONDONTWRITEBYTECODE='1',TEMP=r'D:\Temp\strata-recherche',TMP=r'D:\Temp\strata-recherche')
env['PATH']=os.pathsep.join(config['lib_dirs']+[env.get('PATH','')])
command=[str(PROD/'Strata-src/.venv/Scripts/python.exe'),'-u','-m','serve.server',
         '--engine','strata','--config',str(RUN/'config.json'),'--host','127.0.0.1','--port','8088']
with (RUN/'server.stdout.log').open('ab') as out,(RUN/'server.stderr.log').open('ab') as err:
    process=subprocess.Popen(command,cwd=config['cwd'],env=env,stdout=out,stderr=err,
        stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
save(RUN/'processus.json',dict(pid=process.pid,command=command,started=dt.datetime.now(dt.timezone.utc).isoformat()))
print(json.dumps(dict(run=str(RUN),pid=process.pid,port=8088)),flush=True)
