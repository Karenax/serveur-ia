from pathlib import Path
import json
OUT=Path(__file__).resolve().parent
source=(OUT/'govulncheck.jsonl').read_text(encoding='utf-8-sig');decoder=json.JSONDecoder();messages=[]
while source.strip():
 value,end=decoder.raw_decode(source.lstrip());messages.append(value);source=source.lstrip()[end:]
definitions={m['osv']['id']:m['osv'] for m in messages if 'osv' in m}
findings=[m['finding'] for m in messages if 'finding' in m]
called=[f for f in findings if f.get('trace') and f['trace'][0].get('function')]
summary={'config':[m['config'] for m in messages if 'config' in m], 'finding_records':len(findings),'called_advisories':[]}
for identity in sorted({f['osv'] for f in called}):
 fs=[f for f in called if f['osv']==identity];d=definitions[identity]
 summary['called_advisories'].append({'id':identity,'summary':d.get('summary'),'fixed':sorted({f.get('fixed_version','') for f in fs}),'symbols':sorted({f['trace'][0]['package']+'.'+f['trace'][0]['function'] for f in fs}),'application_frames':[frame for f in fs for frame in f['trace'] if frame.get('package')=='qwen.local/wireguard-bridge']})
(OUT/'go-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
