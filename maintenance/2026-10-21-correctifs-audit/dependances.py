"""Stage explicit security updates, retaining wheels for both upgrade and rollback."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'lanceur'), str(ROOT/'client-qwen')]
from hermes_service import installation

UV = Path(os.environ['LOCALAPPDATA'])/'hermes/bin/uv.exe'
TARGETS = {
    'strata': ('Strata-src/.venv/Scripts/python.exe', {'certifi':'2026.10.19', 'pypdf':'6.19.0', 'pillow':'13.0.0'}),
    'eg2': ('toolchain/eg2-python/Scripts/python.exe', {'certifi':'2026.10.19', 'pillow':'13.0.0', 'pip':'26.2.1'}),
    'voix_serveur': ('toolchain/voice-server-python/Scripts/python.exe', {'certifi':'2026.10.19', 'pip':'26.2.1'}),
    'conversation_windows': ('toolchain/conversation-client-python/Scripts/python.exe', {'pip':'26.2.1'}),
    'hermes': (str(installation()['python']), {'certifi':'2026.10.19', 'pillow':'13.0.0', 'PyJWT':'2.15.0',
        'aiohttp':'3.14.4', 'mcp':'2.2.0', 'multidict':'6.9.1', 'oauthlib':'4.0.0', 'urllib3':'2.8.0'}),
}

def inventory(python):
    code = "import importlib.metadata as m,json; print(json.dumps({d.metadata['Name']:{'version':d.version,'requires':d.requires or []} for d in m.distributions()}))"
    return json.loads(subprocess.check_output([str(python), '-c', code], text=True))

def prepare():
    records = {}
    for name, (executable, targets) in TARGETS.items():
        python = ROOT/executable
        installed = inventory(python)
        old = {n: installed[next(k for k in installed if k.casefold()==n.casefold())]['version'] for n in targets}
        records[name] = {'python':str(python), 'before':old, 'targets':targets, 'packages':installed}
        targets_text = '\n'.join(f'{n}=={v}' for n,v in targets.items())+'\n'
        (OUT/f'requirements-security-{name}.txt').write_text(targets_text, encoding='utf-8')
        result = subprocess.run([str(UV), 'pip', 'install', '--dry-run', '--python', str(python), *[f'{n}=={v}' for n,v in targets.items()]], capture_output=True, text=True)
        (OUT/f'dry-run-{name}.txt').write_text(result.stdout+result.stderr, encoding='utf-8')
        records[name]['dry_run_exit'] = result.returncode
    (OUT/'dependances-avant.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({n:{'before':r['before'],'targets':r['targets'],'dry_run_exit':r['dry_run_exit']} for n,r in records.items()},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare']);args=parser.parse_args()
    globals()[args.phase]()
