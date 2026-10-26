"""Read-only inventory of first-party current sources; AST clones are candidates."""
from __future__ import annotations
import ast
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
roots = ('lanceur/', 'client-qwen/', 'client-voice/', 'client-android/')
extensions = {'.py','.js','.cjs','.mjs','.html','.css','.java','.cpp','.h','.go','.ps1'}
excluded = ('/assets/','/vendor/','/licenses/','/android-outils/','/tests/','/src/androidTest/','/src/debug/')
files=[]; functions=[]; duplicates=defaultdict(list); imports={}; signals=Counter()
for name in names:
    p=ROOT/name
    if not name.startswith(roots) or p.suffix not in extensions or any(x in name for x in excluded): continue
    if p.name.startswith(('test_', 'preview_', 'validate_', 'verify_')) or not p.is_file(): continue
    source=p.read_text(encoding='utf-8-sig'); lines=source.splitlines()
    files.append({'path':name,'lines':len(lines),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    if p.suffix!='.py': continue
    tree=ast.parse(source); imports[name]=sorted({n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) and n.module} | {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names})
    parents={child:parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    for n in ast.walk(tree):
        if isinstance(n,ast.ExceptHandler) and (n.type is None or isinstance(n.type,ast.Name) and n.type.id in ('Exception','BaseException')):
            signals['broad_exception_handlers']+=1
            if all(isinstance(x,ast.Pass) for x in n.body): signals['silent_broad_except_pass']+=1
        if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)): continue
        length=n.end_lineno-n.lineno+1
        parent=parents.get(n); qualifier=(parent.name+'.') if isinstance(parent,ast.ClassDef) else ''
        record={'path':name,'name':qualifier+n.name,'line':n.lineno,'end':n.end_lineno,'lines':length,'branches':sum(isinstance(x,(ast.If,ast.For,ast.While,ast.ExceptHandler,ast.IfExp,ast.Match)) for x in ast.walk(n))}
        functions.append(record)
        body=n.body[1:] if n.body and isinstance(n.body[0],ast.Expr) and isinstance(n.body[0].value,ast.Constant) and isinstance(n.body[0].value.value,str) else n.body
        if length>=6:
            signature=ast.dump(ast.Module(body=body,type_ignores=[]),include_attributes=False)
            duplicates[hashlib.sha256(signature.encode()).hexdigest()].append(record)
report={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(), 'tracked_files':sum(bool(n) for n in names),'components':dict(Counter(n.split('/')[0] if '/' in n else '(root)' for n in names if n)), 'source_files':sorted(files,key=lambda x:-x['lines']),'source_lines':sum(f['lines'] for f in files),'python_functions':len(functions),'largest_functions':sorted(functions,key=lambda x:-x['lines'])[:60],'exact_body_clones':[v for v in duplicates.values() if len(v)>1], 'imports':imports,'signals':dict(signals)}
(OUT/'inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('source_files','imports','largest_functions','exact_body_clones')},ensure_ascii=False))
print(json.dumps({'largest_files':report['source_files'][:20],'largest_functions':report['largest_functions'][:15],'clones':report['exact_body_clones']},ensure_ascii=False,indent=2))
