import json,sys,urllib.error,time
from pathlib import Path
sys.path[:0]=['lanceur','client-qwen']
from releases import profile
from client import Remote
from connection_settings import HTTPS_ENDPOINT
home=Path('lanceur');records=json.loads((home/'acces-distants.json').read_text())['clients']
p=next(home/'clients'/(r['id']+'.exe') for r in records if not r['revoked'] and (home/'clients'/(r['id']+'.exe')).is_file())
r=Remote(profile(p),endpoint=HTTPS_ENDPOINT)
try:
 with r.open('/v1/models') as response:catalogue=json.load(response)
 for row in catalogue['data']:
  if not row['id'].startswith('fred-model-'):continue
  print(json.dumps({'model':row.get('label') or row.get('name'),'caps':row.get('capabilities')}),flush=True)
  body={'model':row['id'],'messages':[{'role':'user','content':'Réponds uniquement OK.'}],'stream':False,'max_tokens':64}
  began=time.monotonic()
  try:
   with r.open('/v1/chat/completions',json.dumps(body).encode()) as response:value=json.load(response)
   print(json.dumps({'status':'ok','model':row.get('name'),'seconds':round(time.monotonic()-began,2),'text':str(value.get('choices',[{}])[0].get('message',{}).get('content'))[:100]}),flush=True)
  except urllib.error.HTTPError as e:print(json.dumps({'status':e.code,'error':e.read(2048).decode()}),flush=True)
finally:r.close()
