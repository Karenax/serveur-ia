"""Inspect actual runtimes; query OSV with public package names/versions only."""
from pathlib import Path
import concurrent.futures, hashlib, importlib.util, json, subprocess, urllib.request
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('runtime_locks',ROOT/'maintenance/verrous_runtime.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
manifest=json.loads((ROOT/'dependances/verrous/manifest.json').read_text(encoding='utf-8'))
result={}
for name,python in m.environments().items():
 try:
  actual=m.inventory(python);locked=manifest['environments'][name]
  check=subprocess.run([str(python),'-m','pip','check'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
  result[name]={'installed':actual,'lock_hash_valid':hashlib.sha256((ROOT/'dependances/verrous'/(name+'.requirements.txt')).read_bytes()).hexdigest()==locked['sha256'], 'mismatch':{p:{'expected':v,'installed':actual.get(p)} for p,v in locked['packages'].items() if actual.get(p)!=v}, 'extra':{p:actual[p] for p in sorted(set(actual)-set(locked['packages'])-set(manifest['local_exclusions']))}, 'pip_check':{'returncode':check.returncode,'output':(check.stdout+check.stderr).replace(str(python),'[runtime]')}}
 except Exception as e:result[name]={'error':type(e).__name__+': '+str(e)}
(OUT/'runtimes.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:{a:b for a,b in v.items() if a!='installed'} for k,v in result.items()},ensure_ascii=False),flush=True)
pairs=sorted({(p,v) for r in result.values() for p,v in r.get('installed',{}).items() if p not in manifest['local_exclusions']})
def query(pair):
 name,version=pair
 try:
  request=urllib.request.Request('https://api.osv.dev/v1/query',json.dumps({'package':{'ecosystem':'PyPI','name':name},'version':version}).encode(),{'Content-Type':'application/json'})
  with urllib.request.urlopen(request,timeout=25) as response: data=json.load(response)
  return {'package':name,'version':version,'advisories':[{'id':v['id'],'summary':v.get('summary'),'aliases':v.get('aliases',[]),'references':v.get('references',[])} for v in data.get('vulns',[])]}
 except Exception as e:return {'package':name,'version':version,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:queries=list(pool.map(query,pairs))
(OUT/'osv.json').write_text(json.dumps(queries,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'queries':len(queries),'affected':[x for x in queries if x.get('advisories')],'errors':[x for x in queries if x.get('error')]},ensure_ascii=False),flush=True)
