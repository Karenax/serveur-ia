import json, shutil, sys, hashlib, re, urllib.request, time, subprocess
from pathlib import Path
import psutil
ROOT=Path(r'D:\Serveur IA')
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
from core import read_json,write_json,defaults_from_config,validate,build_config
TEST=ROOT/'recherche/strata-0.1.43.1-20261013'
DEST=ROOT/'dependances/strata-0.1.43.1'
backup=HERE/'avant'
backup.mkdir(exist_ok=False)
for rel in ['lanceur/base-strata.json','strata-iq4-p100-hybride.json','lanceur/reglages.json','lanceur/reglages-par-defaut.json','lanceur/derniers-reglages-valides.json','lanceur/session.json','lanceur/exploitation.json','lanceur/runtime.py','Start-Strata-IQ4-P100.ps1']:
    target=backup/rel; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/rel,target)
runtime=backup/'lanceur/runtime.py'
text=runtime.read_text(encoding='utf-8').replace('import os\n','').replace("            server_env = os.environ.copy()\n            server_env.update(cfg.get('server_env', {}))\n",'').replace("cwd=cfg['cwd'], env=server_env,","cwd=cfg['cwd'],")
runtime.write_text(text,encoding='utf-8')
shutil.copytree(TEST/'engine-cuda12',DEST/'engine-cuda12')
shutil.copytree(TEST/'source/Strata-0.1.43.1',DEST/'source',ignore=shutil.ignore_patterns('__pycache__'))
old=ROOT/'recherche/strata-0.1.41-test-20261008'
shutil.copytree(old/'tokenizer',DEST/'tokenizer')
shutil.copy2(old/'donnees/expert-profile.bin',DEST/'expert-profile.bin')
for name in ['cublas','cuda_runtime']:
    shutil.copytree(old/f'.venv/Lib/site-packages/nvidia/{name}/bin',DEST/f'cuda12/{name}/bin')
cfg=read_json(TEST/'config-mtp-batch.json')
prod=read_json(ROOT/'lanceur/reglages.json')
cfg.update(exe=str(DEST/'engine-cuda12/strata.exe'),cwd=str(DEST/'source'),tokenizer=str(DEST/'tokenizer'),
    lib_dirs=[str(DEST/f'cuda12/{name}/bin') for name in ['cublas','cuda_runtime']],
    server_env={'STRATA_ENGINE_READY_S':'3600'})
cfg['args'][cfg['args'].index('--expert-profile')+1]=str(DEST/'expert-profile.bin')
for name in ['model_name','host','port','api_key','fit_max_tokens']:cfg[name]=prod[name]
cfg['cors_origins']=[x for x in prod['cors_origins'].splitlines() if x]
cfg['trusted_origins']=[x for x in prod['trusted_origins'].splitlines() if x]
cfg['log']=str(ROOT/'strata-engine-iq4-p100.log')
settings=defaults_from_config(cfg); settings['min_free_ram_gib']=prod['min_free_ram_gib']
validate(settings,check_paths=True)
assert hashlib.sha256((DEST/'engine-cuda12/strata.exe').read_bytes()).digest()==hashlib.sha256((TEST/'engine-cuda12/strata.exe').read_bytes()).digest()
write_json(ROOT/'lanceur/base-strata.json',cfg); write_json(ROOT/'strata-iq4-p100-hybride.json',cfg)
write_json(HERE/'nouveaux-reglages.json',settings)
subprocess.run([str(ROOT/'Strata-src/.venv/Scripts/python.exe'),'-c','import serve.server; print("Serveur officiel importé")'],cwd=DEST/'source',check=True)
# Reload the console's cached base while the previous model remains running.
subprocess.run([sys.executable,str(TEST/'Reprendre-Console.py')],check=True)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
html=opener.open('http://127.0.0.1:8765/').read().decode()
token=re.search(r'name="launcher-token" content="([^"]+)"',html).group(1)
def post(route,data):
    req=urllib.request.Request('http://127.0.0.1:8765'+route,data=json.dumps(data).encode(),headers={'Content-Type':'application/json','X-Launcher-Token':token,'Origin':'http://127.0.0.1:8765'})
    return json.load(opener.open(req,timeout=90))
post('/api/stop',{})
post('/api/set-default',settings)
result=post('/api/start',settings)
write_json(HERE/'demarrage.json',result)
print(json.dumps(result),flush=True)
