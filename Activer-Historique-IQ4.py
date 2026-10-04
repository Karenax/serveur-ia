import json,re,urllib.request
base='http://127.0.0.1:8765'
with urllib.request.urlopen(base+'/') as r: html=r.read().decode()
match=re.search(r'(?:name="launcher-token" content="|launcherToken\s*=\s*[\"\x27]|data-token="|name="csrf-token" content=")([^"\x27<>]+)',html)
if not match:
 raise RuntimeError('Launcher token not found')
token=match.group(1)
def post(path,data):
 req=urllib.request.Request(base+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json','X-Launcher-Token':token,'Origin':base})
 with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
with urllib.request.urlopen(base+'/api/settings') as r:s=json.load(r)
s.update(history_enabled=True,history_slots=6,history_every=16384)
post('/api/set-default',s)
print('Réutilisation historique enregistrée : 6 points, intervalle 16384 tokens.')
print(post('/api/stop',{}))
print(post('/api/start',s))

