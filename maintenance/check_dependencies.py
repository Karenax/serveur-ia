"""Query OSV for installed public Python versions; report every environment."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import urllib.request
from verrous_runtime import environments, inventory, OUT as LOCKS


def query(pair):
    name,version=pair
    try:
        request=urllib.request.Request('https://api.osv.dev/v1/query',json.dumps({
            'package':{'ecosystem':'PyPI','name':name},'version':version}).encode(),
            {'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=30) as response:data=json.load(response)
        return {'package':name,'version':version,'advisories':[{'id':row['id'],'aliases':row.get('aliases',[]),
                 'summary':row.get('summary',''),'references':row.get('references',[])} for row in data.get('vulns',[])]}
    except Exception as error:
        return {'package':name,'version':version,'error':type(error).__name__}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    excluded=set(json.loads((LOCKS/'manifest.json').read_text(encoding='utf-8'))['local_exclusions'])
    installed={name:inventory(python) for name,python in environments().items()}
    pairs=sorted({(name,version) for packages in installed.values() for name,version in packages.items() if name not in excluded})
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(query,pairs))
    affected=[value for value in results if value.get('advisories')];errors=[value for value in results if value.get('error')]
    report={'passed':not affected and not errors,'checked_versions':len(results),'runtimes':list(installed),
            'affected':affected,'errors':errors,'results':results}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('passed','checked_versions','runtimes','affected','errors')},ensure_ascii=False))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
