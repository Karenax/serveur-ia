"""Reduce audit evidence to reproducible counters; no application writes."""
import ast, collections, hashlib, json, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from hermes_service import installation
inventory=json.loads((OUT/'inventaire.json').read_text(encoding='utf-8'))
env=json.loads((OUT/'dependances-installees.json').read_text())
osv=json.loads((OUT/'osv.json').read_text(encoding='utf-8'))
dependency_rows=[]
for row in osv:
 if not row.get('vulnerabilities'):continue
 groups=[]
 for v in row['vulnerabilities']:
  ids={v['id'],*v.get('aliases',[])}
  merged=[g for g in groups if g & ids]
  for g in merged:groups.remove(g);ids|=g
  groups.append(ids)
 dependency_rows.append({'name':row['package'],'version':row['version'],'environments':[k for k,e in env.items() if any(x['name'].casefold()==row['package'].casefold() and x['version']==row['version'] for x in e['packages'])],'raw_advisories':len(row['vulnerabilities']),'distinct_advisories':len(groups),'fixed_versions':sorted({event['fixed'] for v in row['vulnerabilities'] for a in v.get('affected',[]) for r in a.get('ranges',[]) if r.get('type')=='ECOSYSTEM' for event in r.get('events',[]) if 'fixed' in event})})
tests={}
for label,name in [('serveur','tests-serveur.txt'),('windows','tests-windows.txt'),('voix','tests-voix.txt'),('android','tests-android.txt')]:
 content=(OUT/name).read_text(encoding='utf-8',errors='replace');m=re.search(r'Ran (\d+) tests? in ([\d.]+)s',content)
 tests[label]={'completed':bool(m),'tests':int(m[1]) if m else None,'seconds':float(m[2]) if m else None,'ok':bool(re.search(r'^OK(?:\s|$)',content,re.M)),'failure_markers':len(re.findall(r'\.\.\. (FAIL|ERROR)',content))}
sources=[r for r in inventory['source_files'] if Path(r['file']).suffix in {'.py','.js','.cjs','.mjs','.java','.cpp','.h','.ps1','.html','.css','.gradle'}]
runtime=installation()
manifest_rows=[]
for platform in ('client-qwen','client-android'):
 m=json.loads((ROOT/platform/'dist/build-manifest.json').read_text(encoding='utf-8'))
 manifest_rows.append({'component':platform,'created_at':m.get('created_at'),'python':m.get('python',{}),'hermes':m.get('hermes')})
engine=ROOT/'dependances/strata-0.1.45.3/engine-cuda12/strata.exe'
with engine.open('rb') as stream:engine_hash=hashlib.file_digest(stream,'sha256').hexdigest()
engine_expected=json.loads((ROOT/'maintenance/2026-10-19-strata-0.1.45.3/production.json').read_text())['engine_sha256']
summary={'tests':tests,'source_files':len(sources),'source_lines':sum(r['lines'] for r in sources),'osv_queries':len(osv),'osv_errors':sum('error' in r for r in osv),'dependencies':dependency_rows,'hermes_commit':runtime['commit'],'python_version':sys.version.split()[0],'engine_hash_matches_deployment':engine_hash==engine_expected,'engine_sha256':engine_hash,'builds':manifest_rows}
(OUT/'synthese.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='builds'},ensure_ascii=False,indent=2))
