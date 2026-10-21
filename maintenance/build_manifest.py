"""Record the actual source/tool/runtime versions beside a built public artifact."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
SOURCE_DIRS=('lanceur','client-qwen','client-android','client-voice','maintenance')
SUFFIXES={'.py','.js','.cjs','.html','.css','.ps1','.cmd','.go','.mod','.sum','.java','.gradle','.xml','.toml','.properties','.cpp','.h','.cmake'}

def command(arguments,cwd=ROOT):
    result=subprocess.run(arguments,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
    if result.returncode:raise ValueError('Version outil indisponible : '+str(arguments[0]))
    return (result.stdout+result.stderr).strip()

def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def generate(artifact):
    listed=command(['git','ls-files','--cached','--others','--exclude-standard','-z',*SOURCE_DIRS]).split('\0')
    sources={name:digest(ROOT/name) for name in sorted(set(listed)) if name and (ROOT/name).is_file() and (ROOT/name).suffix.lower() in SUFFIXES}
    engines=json.loads((ROOT/'dependances/moteurs.json').read_text(encoding='utf-8'))
    for row in engines:
        if row.get('patch'):row['patch_sha256']=digest(ROOT/'dependances'/row['patch'])
    result={'version':1,'created_at':datetime.now(timezone.utc).isoformat(),'source_commit':command(['git','rev-parse','HEAD']),
            'source_branch':command(['git','branch','--show-current']),'source_files':sources,
            'artifact':{'name':artifact.name,'bytes':artifact.stat().st_size,'sha256':digest(artifact)},
            'host':{'system':platform.system(),'release':platform.release(),'machine':platform.machine()},
            'python':{'version':platform.python_version(),'packages':{
                name:importlib.metadata.version(name) for name in sorted(
                    {d.metadata['Name'] for d in importlib.metadata.distributions()},key=str.lower)}},
            'engines':engines,'tools':{}}
    for name,path,args in [('go',ROOT/'client-qwen/wireguard-tools/go/bin/go.exe',['version']),
                            ('cmake',ROOT/'toolchain/cmake-3.31.8-windows-x86_64/bin/cmake.exe',['--version'])]:
        if path.is_file():result['tools'][name]=command([str(path),*args])
    import os
    java=Path(os.environ.get('JAVA_HOME',''))/'bin/java.exe'
    if java.is_file():result['tools']['java']=command([str(java),'-version'])
    sdk=ROOT/'toolchain/android-sdk'
    result['android']={name:sorted(p.name for p in (sdk/name).iterdir() if p.is_dir()) if (sdk/name).is_dir() else [] for name in ('build-tools','platforms','ndk')}
    result['android']['gradle']='8.13'
    sys.path.insert(0,str(ROOT/'lanceur'))
    from hermes_service import installation
    try:
        native=installation();result['hermes']={'commit':native['commit'],'python':command([str(native['python']),'--version']),
            'clean_checkout':not command(['git','status','--porcelain'],cwd=native['source'])}
    except (OSError,ValueError):result['hermes']={'available':False}
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--artifact',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();data=generate(args.artifact.resolve());args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Build manifest:',args.output.resolve())
