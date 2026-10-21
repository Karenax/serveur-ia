"""Check all locked public package versions against OSV after security updates."""
import concurrent.futures
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
locked=json.loads((ROOT/'dependances/verrous/manifest.json').read_text(encoding='utf-8'))
pairs=sorted({(name,version) for runtime in locked['environments'].values() for name,version in runtime['packages'].items()})
def query(pair):
    name,version=pair
    req=urllib.request.Request('https://api.osv.dev/v1/query',json.dumps({'package':{'ecosystem':'PyPI','name':name},'version':version}).encode(),{'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as response:data=json.load(response)
    return {'package':name,'version':version,'advisories':[{'id':v['id'],'aliases':v.get('aliases',[]),'summary':v.get('summary'),'references':v.get('references',[])} for v in data.get('vulns',[])]}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(query,pairs))
(OUT/'osv-apres.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
affected=[r for r in results if r['advisories']]
print(json.dumps({'queries':len(results),'affected':affected},ensure_ascii=False,indent=2))
