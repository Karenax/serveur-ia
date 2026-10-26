"""Recorded source extraction; compatibility modules retain their import paths."""
from pathlib import Path
import ast
import os
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
PACKAGE=ROOT/'shared/kiara_shared'


def nodes(source, names):
    tree=ast.parse(source)
    return '\n\n'.join(ast.get_source_segment(source,node) for node in tree.body
                       if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in names)


def main():
    mapping={'fred_http':'http','chat_attachments':'attachments','history_store':'history_store',
             'file_lock':'file_lock','advanced_voice':'voice_runtime','max_installation':'voice_packs'}
    originals={name:(ROOT/'client-qwen'/f'{name}.py').read_text(encoding='utf-8-sig') for name in mapping}
    for old,new in mapping.items():
        source=originals[old]
        source=source.replace('from file_lock import','from .file_lock import')
        source=source.replace('from chat_attachments import','from .attachments import')
        source=source.replace('from max_installation import','from .voice_packs import')
        source=source.replace('from local_voice import HTTPSRedirect','from .http_download import HTTPSRedirect')
        if old=='advanced_voice':source=source.replace('Optional, measured Voxtral/Qwen-TTS runtime;', 'Optional voice runtime with versioned pack compatibility;')
        (PACKAGE/f'{new}.py').write_text(source,encoding='utf-8')
    local=(ROOT/'client-qwen/local_voice.py').read_text(encoding='utf-8-sig')
    redirect=nodes(local,{'HTTPSRedirect'})
    (PACKAGE/'http_download.py').write_text('"""HTTPS-only redirects for public runtime downloads."""\nimport urllib.request\n\n'+redirect+'\n',encoding='utf-8')
    bridge=(ROOT/'client-qwen/wg_bridge.py').read_text(encoding='utf-8-sig')
    validators=nodes(bridge,{'validate_endpoint','validate_profile'})
    (PACKAGE/'profiles.py').write_text('"""Shared validation of signed client transport profiles."""\nimport base64\nimport ipaddress\nimport re\n\n'+validators+'\n',encoding='utf-8')
    uv=Path(os.environ['LOCALAPPDATA'])/'hermes/bin/uv.exe'
    subprocess.run([str(uv),'pip','install','--python',sys.executable,'--no-build-isolation','-e',str(ROOT/'shared')],check=True)
    for old,new in mapping.items():
        (ROOT/'client-qwen'/f'{old}.py').write_text(
            f'"""Compatibility import; implementation belongs to kiara_shared.{new}."""\n'
            f'import sys\nfrom kiara_shared import {new} as _implementation\nsys.modules[__name__] = _implementation\n',encoding='utf-8')
    local=local.replace(redirect,'from kiara_shared.http_download import HTTPSRedirect',1)
    (ROOT/'client-qwen/local_voice.py').write_text(local,encoding='utf-8')
    tree=ast.parse(bridge);lines=bridge.splitlines(keepends=True)
    for node in reversed(tree.body):
        if isinstance(node,ast.FunctionDef) and node.name in {'validate_endpoint','validate_profile'}:
            lines[node.lineno-1:node.end_lineno]=[]
    (ROOT/'client-qwen/wg_bridge.py').write_text('from kiara_shared.profiles import validate_endpoint, validate_profile\n'+''.join(lines),encoding='utf-8')
    for path in (ROOT/'lanceur').glob('*.py'):
        if path.name.startswith('test_'):continue
        source=path.read_text(encoding='utf-8-sig')
        for old,new in [('chat_attachments','attachments'),('history_store','history_store'),('file_lock','file_lock')]:
            source=source.replace('from '+old+' import','from kiara_shared.'+new+' import')
        if path.name=='profiles.py':source=source.replace('from wg_bridge import validate_profile','from kiara_shared.profiles import validate_profile')
        # Only the path injections whose client imports have just moved.
        source=re.sub(r"^[ \t]*sys\.path\.insert\(0,\s*str\((?:Path\(__file__\)\.resolve\(\)\.parent\.parent|ROOT)\s*/\s*'client-qwen'\)\)\n",'',source,flags=re.M)
        if source!=path.read_text(encoding='utf-8-sig'):path.write_text(source,encoding='utf-8')
    (ROOT/'lanceur/http_boundary.py').write_text('"""Canonical bounded HTTP ingress shared with the desktop client."""\nfrom kiara_shared.http import BoundedHTTPServer, json_body\n',encoding='utf-8')
    (ROOT/'lanceur/voice_max.py').write_text('"""Optional voice controller from the explicit shared package."""\nfrom kiara_shared.voice_runtime import AdvancedVoice\n',encoding='utf-8')
    print('Shared package installed; server imports no longer load client source files for these primitives.')


if __name__=='__main__':main()
