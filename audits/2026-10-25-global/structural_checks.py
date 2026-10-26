"""Supplementary read-only structural checks; potential secrets never printed."""
from pathlib import Path
from collections import defaultdict, Counter
import ast, difflib, hashlib, json, re, subprocess, sys, urllib.request
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
report=json.loads((OUT/'inventory.json').read_text(encoding='utf-8'))
clones=defaultdict(list);samefiles=defaultdict(list);names=[];longlines=[]
for item in report['source_files']:
 p=ROOT/item['path'];source=p.read_text(encoding='utf-8-sig');names.append(item['path'])
 samefiles[hashlib.sha256(p.read_bytes()).hexdigest()].append(item['path'])
 longlines.extend({'path':item['path'],'line':i+1,'characters':len(s)} for i,s in enumerate(source.splitlines()) if len(s)>1000)
 if p.suffix!='.py':continue
 for n in ast.walk(ast.parse(source)):
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
   body=ast.Module(body=n.body,type_ignores=[])
   if sum(1 for _ in ast.walk(body))<30:continue
   key=ast.dump(body,include_attributes=False)
   clones[key].append({'path':item['path'],'name':n.name,'line':n.lineno,'lines':n.end_lineno-n.lineno+1})
blocks=[]
for a,b in [('client-voice/max_worker.py','client-voice/max_pack_worker.py'),('lanceur/core.py','lanceur/client_storage.py'),('client-qwen/history_store.py','client-qwen/draft_store.py')]:
 left=(ROOT/a).read_text(encoding='utf-8-sig').splitlines();right=(ROOT/b).read_text(encoding='utf-8-sig').splitlines()
 for match in difflib.SequenceMatcher(a=[x.strip() for x in left],b=[x.strip() for x in right],autojunk=False).get_matching_blocks():
  if match.size>=5 and sum(len(x) for x in left[match.a:match.a+match.size])>=200:
   blocks.append({'a':a,'a_line':match.a+1,'b':b,'b_line':match.b+1,'lines':match.size})
patterns={'private_key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----','github_token':r'\b(?:ghp_|github_pat_)[A-Za-z0-9_]{30,}', 'provider_key':r'\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{24,}', 'fred_token':r'\bqwen_[a-f0-9]{16}_[A-Za-z0-9_-]{35,}'}
secret_candidates=[];scanned=0
tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
for name in filter(None,tracked):
 p=ROOT/name
 if not p.is_file() or p.stat().st_size>3_000_000:continue
 try:s=p.read_text(encoding='utf-8-sig')
 except (UnicodeError,OSError):continue
 scanned+=1
 for kind,pattern in patterns.items():
  for m in re.finditer(pattern,s):secret_candidates.append({'path':name,'line':s[:m.start()].count('\n')+1,'kind':kind})
incoming=Counter(i for deps in report['imports'].values() for i in deps)
counts=Counter(p.split('/')[0] for p in names)
evidence={'source_file_count':len(names),'source_components':dict(counts),'exact_function_body_candidates':[v for v in clones.values() if len(v)>1], 'exact_file_candidates':[v for v in samefiles.values() if len(v)>1],'selected_common_blocks':blocks,'lines_over_1000_chars':len(longlines),'longest_lines':sorted(longlines,key=lambda v:-v['characters'])[:20], 'most_imported_local':[(n,incoming[Path(n).stem]) for n in report['imports'] if incoming[Path(n).stem]>3], 'secret_scan':{'text_files':scanned,'candidates':secret_candidates}}
(OUT/'structure.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(evidence,ensure_ascii=False,indent=2))
