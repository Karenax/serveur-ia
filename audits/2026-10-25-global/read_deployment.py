"""Read-only operational metadata, excluding accounts, credentials and content."""
from pathlib import Path
import datetime as dt, hashlib, json, subprocess, sys, urllib.request
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
import psutil
from local_network import system_state
state={'observed_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
for name,url in [('console','http://127.0.0.1:8765/health'),('model','http://127.0.0.1:8080/health'),('backups','http://127.0.0.1:8765/api/backups')]:
 try:
  with urllib.request.urlopen(url,timeout=5) as response:value=json.load(response)
  if name=='backups':value={'enabled':value.get('config',{}).get('enabled'),'secondary_configured':bool(value.get('config',{}).get('secondary_destination')),'last_success':value.get('last_success'),'last_error_present':bool(value.get('last_error')),'catalog_count':len(value.get('catalog',[])),'recent':[{'created_at':r.get('created_at'),'verified':r.get('verified'),'size':r.get('size'),'secondary_status':r.get('secondary',{}).get('status')} for r in sorted(value.get('catalog',[]),key=lambda r:r.get('created_at',''),reverse=True)[:3]]}
  else:value={k:value.get(k) for k in ('version','loaded','images','model','ok','status') if k in value}
  state[name]=value
 except Exception as e:state[name]={'unavailable':type(e).__name__}
try:state['lan']=system_state()
except Exception as e:state['lan']={'unavailable':type(e).__name__}
state['listeners']=[{'address':c.laddr.ip,'port':c.laddr.port,'pid':c.pid} for c in psutil.net_connections('tcp') if c.status=='LISTEN' and c.laddr.port in (8080,8765,8766,8768,8643,8767)]
manifest=json.loads((ROOT/'client-qwen/dist/build-manifest.json').read_text(encoding='utf-8'))
state['windows_source_manifest']={'source_commit':manifest.get('source_commit'),'source_count':len(manifest['source_files']),'differences':[name for name,sha in manifest['source_files'].items() if not (ROOT/name).exists() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha]}
go=ROOT/'client-qwen/wireguard-tools/go/bin/go.exe'
result=subprocess.run([str(go),'version','-m',str(ROOT/'client-qwen/wireguard-bridge.exe')],capture_output=True,text=True,timeout=20)
(OUT/'go-binary.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
(OUT/'deployment-readonly.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(state,ensure_ascii=False,indent=2))
