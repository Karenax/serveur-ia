"""Read-only audit inventory; never emits credential values or conversation text."""
import ast, collections, datetime, hashlib, json, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).parent
names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
names=[n for n in names if n and (ROOT/n).is_file()]
groups=collections.defaultdict(lambda:{'files':0,'bytes':0})
sources=[]; functions=[]; secrets=[]
patterns={'private_key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----','github_token':r'\b(?:ghp_|github_pat_)[A-Za-z0-9_]{30,}', 'provider_key':r'\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{24,}', 'fred_token':r'\bqwen_[a-f0-9]{16}_[A-Za-z0-9_-]{35,}'}
for n in names:
 p=ROOT/n; g=groups[n.split('/')[0] if '/' in n else '(racine)'];g['files']+=1;g['bytes']+=p.stat().st_size
 if p.suffix.lower() in {'.py','.js','.cjs','.mjs','.java','.cpp','.h','.ps1','.cmd','.html','.css','.json','.md','.txt','.yaml','.yml','.xml','.gradle','.toml'} and p.stat().st_size<3_000_000:
  try:s=p.read_text(encoding='utf-8-sig')
  except UnicodeError:continue
  for k,pat in patterns.items():
   for m in re.finditer(pat,s):secrets.append({'file':n,'line':s[:m.start()].count('\n')+1,'kind':k})
  if n.split('/')[0] in {'lanceur','client-qwen','client-voice','client-android'} and not any(x in n for x in ['/assets/','/vendor/','/validation/']):
   sources.append({'file':n,'lines':len(s.splitlines()),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
   if p.suffix=='.py' and not p.name.startswith(('test_','validate_','verify_','preview_')):
    for node in ast.walk(ast.parse(s)):
     if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
      functions.append({'file':n,'name':node.name,'line':node.lineno,'lines':node.end_lineno-node.lineno+1})
data={'date':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),'tracked_files':len(names),'tracked_bytes':sum(g['bytes'] for g in groups.values()),'groups':dict(sorted(groups.items())),'source_files':sources,'long_functions':sorted(functions,key=lambda x:x['lines'],reverse=True)[:25],'secret_candidates':secrets}
(OUT/'inventaire.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in data.items() if k!='source_files'},ensure_ascii=False,indent=2))
