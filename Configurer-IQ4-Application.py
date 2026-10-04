import datetime,json,sys,shutil
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'lanceur'))
from core import read_json,write_json,defaults_from_config,validate,build_config,stop_processes
from app import Controller
import psutil
controller=Controller()
controller.stop()
for process in psutil.process_iter(['name','cmdline']):
 cmd=process.info['cmdline'] or []
 if process.pid != __import__('os').getpid() and any(str(root/'lanceur/app.py').lower()==part.replace('/','\\').lower() for part in cmd):
  stop_processes([process])
backup=root/'lanceur'/'sauvegardes'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-avant-iq4')
backup.mkdir(parents=True)
for name in ('base-strata.json','reglages.json','reglages-par-defaut.json'):
 shutil.copy2(root/'lanceur'/name,backup/name)
shutil.copy2(root/'strata-iq4-p100-hybride.json',backup/'strata-iq4-p100-hybride.json')
cfg=read_json(root/'strata-iq4-p100-hybride.json')
i=cfg['args'].index('--max-context');cfg['args'][i+1]='262144'
old=controller.settings()
s=defaults_from_config(cfg)
for key in ('host','port','api_key','cors_origins','trusted_origins','fit_max_tokens','min_free_ram_gib'):
 s[key]=old[key]
s['context']=262144
s['history_enabled']=False
s=validate(s,check_paths=True)
cfg=build_config(cfg,s)
write_json(root/'strata-iq4-p100-hybride.json',cfg)
write_json(root/'lanceur/base-strata.json',cfg)
write_json(root/'lanceur/reglages.json',s)
write_json(root/'lanceur/reglages-par-defaut.json',s)
print(json.dumps({k:s[k] for k in ('model_name','context','workers','prefill','vram_reserve','layer_split','mtp_enabled','spec','spec_min_p','history_enabled')},ensure_ascii=False))
print('Configuration et réglages par défaut IQ4 enregistrés.')
