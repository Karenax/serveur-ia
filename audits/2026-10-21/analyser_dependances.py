"""Inventory installed versions and query public OSV using package/version only."""
import concurrent.futures, json, subprocess, sys, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
envs={'strata':'Strata-src/.venv/Scripts/python.exe','eg2':'toolchain/eg2-python/Scripts/python.exe','voix_serveur':'toolchain/voice-server-python/Scripts/python.exe','conversation_windows':'toolchain/conversation-client-python/Scripts/python.exe'}
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from hermes_service import installation
envs['hermes']=str(installation()['python'])
records={}
for name,path in envs.items():
 p=ROOT/path
 if not p.exists():continue
 packages=json.loads(subprocess.check_output([str(p),'-c',"import importlib.metadata as m,json;print(json.dumps(sorted([{'name':d.metadata['Name'],'version':d.version} for d in m.distributions()],key=lambda x:x['name'].lower())))"],text=True))
 check=subprocess.run([str(p),'-m','pip','check'],capture_output=True,text=True)
 records[name]={'packages':packages,'pip_check_exit':check.returncode,'pip_check':check.stdout.strip()}
(OUT/'dependances-installees.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
unique=sorted({(p['name'],p['version']) for e in records.values() for p in e['packages']})
def query(pair):
 name,version=pair
 payload={'package':{'ecosystem':'PyPI','name':name},'version':version}
 try:
  request=urllib.request.Request('https://api.osv.dev/v1/query',json.dumps(payload).encode(),{'Content-Type':'application/json'})
  with urllib.request.urlopen(request,timeout=35) as response:value=json.load(response)
  return {'package':name,'version':version,'vulnerabilities':[{'id':v['id'],'published':v.get('published'),'modified':v.get('modified'),'aliases':v.get('aliases',[]),'summary':v.get('summary'),'details':v.get('details'),'affected':v.get('affected'),'references':v.get('references',[])} for v in value.get('vulns',[])]}
 except Exception as e:return {'package':name,'version':version,'error':type(e).__name__}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(query,unique))
(OUT/'osv.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'queried':len(results),'errors':sum('error' in r for r in results),'affected':[{k:v for k,v in r.items() if k!='vulnerabilities'}|{'advisories':[v['id'] for v in r.get('vulnerabilities',[])]} for r in results if r.get('vulnerabilities')]},indent=2))
