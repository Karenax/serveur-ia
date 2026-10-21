"""Pin installed runtime packages and public distribution hashes; verify without network."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dependances/verrous'
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from hermes_service import installation

def environments():
    return {'strata':ROOT/'Strata-src/.venv/Scripts/python.exe',
        'eg2':ROOT/'toolchain/eg2-python/Scripts/python.exe',
        'voix-serveur':ROOT/'toolchain/voice-server-python/Scripts/python.exe',
        'conversation-windows':ROOT/'toolchain/conversation-client-python/Scripts/python.exe',
        'hermes-fred':installation()['python']}

def inventory(python):
    # Some development venvs inherit a tooling site-packages directory. Resolve
    # each name through Python's import priority instead of retaining the last
    # duplicate distribution enumerated from the fallback directory.
    code="import importlib.metadata as m,json;names=dict.fromkeys(d.metadata['Name'] for d in m.distributions());print(json.dumps({n.lower().replace('_','-'):m.version(n) for n in names}))"
    return json.loads(subprocess.check_output([str(python),'-c',code],text=True))

def public_hashes(item):
    name,version=item
    if name in {'hermes-agent','artifact-tool-v2'}:
        return item,{'local_or_tooling':True}
    with urllib.request.urlopen('https://pypi.org/pypi/'+name+'/'+version+'/json',timeout=30) as response:
        metadata=json.load(response)
    hashes=sorted({f['digests']['sha256'] for f in metadata['urls'] if not f.get('yanked')})
    if not hashes:raise ValueError('Aucune distribution publique non retirée : '+name)
    return item,{'hashes':hashes}

def create():
    OUT.mkdir(parents=True,exist_ok=True)
    installed={name:inventory(python) for name,python in environments().items()}
    pairs=sorted({pair for packages in installed.values() for pair in packages.items()})
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        artifacts=dict(pool.map(public_hashes,pairs))
    manifest={'format':1,'environments':{},'local_exclusions':['hermes-agent','artifact-tool-v2']}
    for name,packages in installed.items():
        lines=['# Versions installées et vérifiées le 21 octobre 2026.',
               '# Installation dans un environnement neuf : pip install --require-hashes -r ce-fichier.']
        public={}
        for package,version in sorted(packages.items()):
            record=artifacts[(package,version)]
            if record.get('local_or_tooling'):
                lines.append('# '+package+'=='+version+' : source locale / outil hors application.')
                continue
            public[package]=version
            lines.append(package+'=='+version+' \\\n'+' \\\n'.join('    --hash=sha256:'+value for value in record['hashes']))
        path=OUT/(name+'.requirements.txt')
        path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        manifest['environments'][name]={'packages':public,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Verrous et empreintes publiques générés pour cinq runtimes.')

def check():
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    for name,python in environments().items():
        locked=manifest['environments'][name]
        path=OUT/(name+'.requirements.txt')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=locked['sha256']:
            raise ValueError('Verrou modifié sans nouveau manifeste : '+name)
        actual=inventory(python)
        wrong={p:{'expected':v,'installed':actual.get(p)} for p,v in locked['packages'].items() if actual.get(p)!=v}
        extra=set(actual)-set(locked['packages'])-set(manifest['local_exclusions'])
        if wrong or extra:raise ValueError(json.dumps({'runtime':name,'mismatch':wrong,'extra':sorted(extra)}))
    print('Les cinq runtimes correspondent à leurs verrous.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['create','check']);args=parser.parse_args()
    globals()[args.phase]()
