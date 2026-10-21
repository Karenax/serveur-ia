"""Evidence collection for audit: read-only production checks and isolated comparisons."""
import difflib, hashlib, importlib.util, json, subprocess, sys, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
def save(name,value):
 (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def get(url):
 with urllib.request.urlopen(url,timeout=15) as response:return json.load(response)
state={'checks':{}}
for label,url in [('console','http://127.0.0.1:8765/health'),('model','http://127.0.0.1:8080/health'),('backups','http://127.0.0.1:8765/api/backups'),('operations','http://127.0.0.1:8765/api/operations')]:
 try:
  value=get(url)
  if label=='backups':
   value={'enabled':value.get('config',{}).get('enabled'),'time':value.get('config',{}).get('time'),'secondary_configured':bool(value.get('config',{}).get('secondary_destination')),'last_success':value.get('last_success'),'last_error':value.get('last_error'),'job':value.get('job'),'catalog_count':len(value.get('catalog',[])),'recent':[{'created_at':r.get('created_at'),'verified':r.get('verified'),'size':r.get('size'),'secondary':r.get('secondary',{}).get('status')} for r in value.get('catalog',[])[:3]]}
  elif label=='operations':value={k:value.get(k) for k in ('version','desired','startup','error')}
  state['checks'][label]=value
 except Exception as e:state['checks'][label]={'unavailable':type(e).__name__}
import psutil
state['listeners']=[{'address':c.laddr.ip,'port':c.laddr.port,'pid':c.pid} for c in psutil.net_connections('tcp') if c.status=='LISTEN' and c.laddr.port in (8080,8765,8766,8768,8643,8767)]
state['resources']={'ram_available_gib':round(psutil.virtual_memory().available/2**30,2),'disks':{p:round(psutil.disk_usage(p).free/2**30,2) for p in ('C:/','D:/')}}
save('production-lecture-seule.json',state)
spec=importlib.util.spec_from_file_location('prepare_assets',ROOT/'client-android/scripts/Prepare-Assets.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
expected=m.prepare(ROOT/'client-qwen');actual=m.read(ROOT/'client-android/app/src/main/assets/android-chat.html')
delta=''.join(difflib.unified_diff(actual.splitlines(True),expected.splitlines(True),fromfile='android-embarque',tofile='android-genere-depuis-sources',n=3))
(OUT/'android-assets.diff').write_text(delta,encoding='utf-8')
manifest=json.loads((ROOT/'client-android/app/src/main/assets/ui-package.json').read_text())
save('android-assets.json',{'equal':actual==expected,'actual_sha256':hashlib.sha256(actual.encode()).hexdigest(),'expected_sha256':hashlib.sha256(expected.encode()).hexdigest(),'shared_mismatches':[n for n,h in manifest['shared_sources'].items() if hashlib.sha256((ROOT/'client-qwen'/n).read_bytes()).hexdigest()!=h]})
import releases,android_releases
release=releases.status(ROOT/'lanceur');save('livraisons.json',{'windows':{'verified':release.get('verified'),'version':release.get('release',{}).get('version')},'android':android_releases.status()[0]})
print(json.dumps(state,ensure_ascii=False,indent=2));print('Asset diff lines:',len(delta.splitlines()))
