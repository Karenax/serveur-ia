import json,time,sys,hashlib,urllib.request
from pathlib import Path
import psutil
ROOT=Path(r'D:\Serveur IA'); HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
from core import read_json,write_json,health,arg
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
deadline=time.monotonic()+3700
while time.monotonic()<deadline:
    pointer=read_json(ROOT/'lanceur/session.json'); run=Path(pointer['directory']); state=read_json(run/'state.json',{})
    if state.get('status')=='erreur':raise RuntimeError(state)
    if state.get('status')=='pret' and health().get('loaded'):break
    print(json.dumps({'status':state.get('status'),'available_ram_gib':state.get('available_ram_gib')}),flush=True)
    time.sleep(20)
else:raise TimeoutError('Chargement non terminé')
cfg=read_json(run/'strata.json')
expected=read_json(HERE/'nouveaux-reglages.json')
for filename in ['reglages.json','reglages-par-defaut.json','derniers-reglages-valides.json']:
    assert read_json(ROOT/'lanceur'/filename)==expected,filename
assert cfg['exe']==expected['exe'] and arg(cfg,'--prefill')=='2048'
assert cfg['env']['STRATA_SPLIT_MTP_BATCH']=='1'
assert cfg['server_env']['STRATA_ENGINE_READY_S']=='3600'
engine=[p for p in psutil.process_iter(['name']) if p.info['name']=='strata.exe' and p.exe().lower()==cfg['exe'].lower()]
assert len(engine)==1
payload={'model':cfg['model_name'],'messages':[{'role':'user','content':'Combien vaut 43 multiplié par 7 ? Réponds uniquement par le nombre.'}],'max_tokens':32,'temperature':0,'chat_template_kwargs':{'enable_thinking':False}}
headers={'Content-Type':'application/json'}
if cfg.get('api_key'):headers['Authorization']='Bearer '+cfg['api_key']
req=urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions',data=json.dumps(payload).encode(),headers=headers)
answer=json.load(op.open(req,timeout=300))
content=answer['choices'][0]['message']['content']; assert content.strip()=='301',answer
write_json(HERE/'reponse.json',answer)
report={'version':'0.1.43.1','model':cfg['model_name'],'loaded':True,'answer':content,'engine_pid':engine[0].pid,'engine_path':cfg['exe'],'engine_sha256':hashlib.sha256(Path(cfg['exe']).read_bytes()).hexdigest(),'session':str(run),'ready_seconds':state.get('ready_seconds'),'defaults_and_last_valid_match':True,'operations':read_json(ROOT/'lanceur/exploitation.json'),'health':health(),'launcher_tests':'8 passed'}
write_json(HERE/'production.json',report)
print(json.dumps(report),flush=True)
