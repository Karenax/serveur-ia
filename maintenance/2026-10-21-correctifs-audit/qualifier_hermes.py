"""Match source-based Hermes advisories against the actual installed base commit."""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from hermes_service import installation
runtime=installation()
data=json.loads((ROOT/'audits/2026-10-21/osv.json').read_text(encoding='utf-8'))
rows=[]
for package in data:
    if package['package']!='hermes-agent':continue
    for item in package['vulnerabilities']:
        if not item['id'].startswith('GHSA'):continue
        commits=[r['url'].rsplit('/',1)[1] for r in item.get('references',[]) if '/hermes-agent/commit/' in r['url']]
        included={sha:subprocess.run(['git','merge-base','--is-ancestor',sha,runtime['commit']],cwd=runtime['source'],capture_output=True).returncode==0 for sha in commits}
        rows.append({'id':item['id'],'summary':item.get('summary'),'fix_commits_in_base':included,
            'fixed_in_base':bool(included) and all(included.values()),'details':item.get('details'),
            'not_exposed_in_fred':item['id']=='GHSA-pmqc-57g8-c22c',
            'exposure_note':'Feishu webhook platform is not configured; Fred enables only api_server.'
                if item['id']=='GHSA-pmqc-57g8-c22c' else 'Fix commit already present.'})
(OUT/'hermes-avis-source.json').write_text(json.dumps({'base_commit':runtime['commit'],'advisories':rows},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{'id':r['id'],'fixed_in_base':r['fixed_in_base'],'known_fix_commits':len(r['fix_commits_in_base'])} for r in rows],indent=2))
