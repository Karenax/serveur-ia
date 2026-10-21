"""Build a private Fred runtime without changing the user's Hermes installation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'), str(ROOT/'client-qwen')]
from hermes_service import installation

base=installation()
home=Path(os.environ['LOCALAPPDATA'])/'Fred/runtime-security/hermes-20261021'
source=home/'source'
python=home/'venv/Scripts/python.exe'
uv=Path(os.environ['LOCALAPPDATA'])/'hermes/bin/uv.exe'
home.mkdir(parents=True,exist_ok=True)
from wg_crypto import private_directory
private_directory(home)
if not source.exists():
    subprocess.run(['git','clone','--shared','--no-hardlinks',str(base['source']),str(source)],check=True)
project=source/'pyproject.toml'
text=project.read_text(encoding='utf-8')
text=text.replace('  "browser-harness==0.1.13; python_version >= \'3.14\'",\n',
                  '  # Fred never enables host browser tools; omit their Pillow-pinned engine.\n')
for old,new in [('certifi==2026.5.20','certifi==2026.10.19'),('PyJWT[crypto]==2.13.0','PyJWT[crypto]==2.15.0'),
                ('Pillow==12.3.0','Pillow==13.0.0'),('aiohttp==3.14.3','aiohttp==3.14.4'),('mcp==2.0.0','mcp==2.2.0')]:
    text=text.replace(old,new)
project.write_text(text,encoding='utf-8',newline='\n')
patch=subprocess.check_output(['git','diff','--','pyproject.toml'],cwd=source)
(OUT/'hermes-security.patch').write_bytes(patch)
if not python.exists():
    subprocess.run([str(uv),'venv','--python',str(base['python']),str(home/'venv')],check=True)
records=json.loads((OUT/'dependances-avant.json').read_text(encoding='utf-8'))['hermes']
targets={k.casefold():v for k,v in records['targets'].items()}
targets.update({'mcp-types':'2.2.0','yarl':'1.25.1'})
locked={name:targets.get(name.casefold(),value['version']) for name,value in records['packages'].items()
        if name.casefold() not in {'hermes-agent','browser-harness'}}
lock=OUT/'requirements-hermes-fred.lock.txt'
lock.write_text('\n'.join(f'{n}=={v}' for n,v in sorted(locked.items(),key=lambda i:i[0].casefold()))+'\n',encoding='utf-8')
subprocess.run([str(uv),'pip','install','--python',str(python),'-r',str(lock),'-e',str(source)],check=True)
subprocess.run([str(uv),'pip','check','--python',str(python)],check=True)
subprocess.run([str(python),'-c','import certifi,jwt,aiohttp,mcp,multidict,oauthlib,urllib3; from PIL import Image; from gateway.platforms import api_server; print("Private Hermes security imports OK")'],cwd=source,check=True)
manifest={'format':1,'validated':True,'source':str(source),'python':str(python),'source_commit':base['commit'],
          'patch_sha256':hashlib.sha256(patch).hexdigest(),'requirements_sha256':hashlib.sha256(lock.read_bytes()).hexdigest(),
          'original_runtime_unchanged':True}
(ROOT/'toolchain/hermes-security-runtime/runtime.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(OUT/'hermes-runtime.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('Private Fred Hermes runtime ready; original installation preserved.')
