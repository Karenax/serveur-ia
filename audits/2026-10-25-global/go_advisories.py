from pathlib import Path
import concurrent.futures, json, re, urllib.request
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
modules=re.findall(r'^\s*([^\s()]+)\s+(v\S+)',(ROOT/'client-qwen/wireguard-bridge/go.mod').read_text(),re.M)
modules=[('golang.zx2c4.com/wireguard','v0.0.0-20260522210424-ecfc5a8d5446'),*modules,('stdlib','1.27.1')]
def query(pair):
 name,version=pair
 try:
  request=urllib.request.Request('https://api.osv.dev/v1/query',json.dumps({'package':{'ecosystem':'Go','name':name},'version':version}).encode(),{'Content-Type':'application/json'})
  with urllib.request.urlopen(request,timeout=25) as response:data=json.load(response)
  return {'module':name,'version':version,'advisories':[{'id':x['id'],'summary':x.get('summary'),'aliases':x.get('aliases',[]),'affected':x.get('affected',[]),'references':x.get('references',[])} for x in data.get('vulns',[])]}
 except Exception as e:return {'module':name,'version':version,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(query,dict.fromkeys(modules)))
(OUT/'go-osv.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps([{'module':x['module'],'version':x['version'],'advisories':[(a['id'],a['summary']) for a in x.get('advisories',[])],'error':x.get('error')} for x in results],ensure_ascii=False,indent=2))
