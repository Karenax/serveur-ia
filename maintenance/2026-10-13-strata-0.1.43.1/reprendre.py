import json,re,urllib.request,sys
from pathlib import Path
root=Path(r'D:\Serveur IA'); here=root/'maintenance/2026-10-13-strata-0.1.43.1'
sys.path.insert(0,str(root/'lanceur'))
from core import write_json
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
token=re.search(r'name="launcher-token" content="([^"]+)"',op.open('http://127.0.0.1:8765/').read().decode()).group(1)
def post(route,data):
 req=urllib.request.Request('http://127.0.0.1:8765'+route,data=json.dumps(data).encode(),headers={'Content-Type':'application/json','X-Launcher-Token':token,'Origin':'http://127.0.0.1:8765'})
 try: return json.load(op.open(req,timeout=90))
 except urllib.error.HTTPError as e: print(e.read().decode()); raise
settings=json.loads((here/'nouveaux-reglages.json').read_text())
print(post('/api/startup',{'enabled':False}),flush=True)
print(post('/api/stop',{}),flush=True)
write_json(root/'lanceur/derniers-reglages-valides.json',settings)
print(post('/api/start',settings),flush=True)
print(post('/api/startup',{'enabled':True}),flush=True)
