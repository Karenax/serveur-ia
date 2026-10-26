"""Reload the idle Python gateway while preserving the loaded model processes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

import psutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'lanceur'))
from core import HOME
from validate_live_lots6_8 import models, preserved_files


def get(route):
    with urllib.request.urlopen('http://127.0.0.1:8765' + route, timeout=8) as response:
        return json.load(response)


def main():
    before = models()
    fingerprints = preserved_files()
    state = get('/api/state')
    if not before or not state['health'].get('loaded'):
        raise RuntimeError('Le modèle chargé doit être identifié avant le rechargement.')
    if state['queue']['active'] or state['queue']['waiting']:
        raise RuntimeError('Une demande est en cours ; rechargement différé.')
    voice_enabled = get('/api/voice')['enabled']
    record = json.loads((HOME / 'interface.pid.json').read_text(encoding='utf-8'))
    parent = psutil.Process(record['pid'])
    if abs(parent.create_time() - record['created']) >= .01:
        raise RuntimeError('Identité de la console modifiée.')
    if str(ROOT / 'lanceur/app.py').casefold() not in [arg.casefold() for arg in parent.cmdline()]:
        raise RuntimeError('Le processus identifié ne correspond pas à la console.')
    protected = set()
    for item in before:
        process = psutil.Process(item['pid'])
        if abs(process.create_time() - item['created']) >= .01:
            raise RuntimeError('Identité du modèle modifiée.')
        protected.add(process.pid)
        protected.update(p.pid for p in process.children(recursive=True))
        for ancestor in process.parents():
            if ancestor.pid == parent.pid:
                break
            protected.add(ancestor.pid)
    children = [(p, p.create_time()) for p in parent.children(recursive=True) if p.pid not in protected]
    parent.terminate()
    parent.wait(timeout=15)
    for process, created in reversed(children):
        try:
            if process.is_running() and abs(process.create_time() - created) < .01:
                process.terminate()
                process.wait(timeout=10)
        except psutil.NoSuchProcess:
            pass
    launch = subprocess.run([
        'powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
        '-File', str(ROOT / 'Start-Interface-Qwen.ps1'), '-SansNavigateur', '-PreserverEtatModele',
    ], capture_output=True, timeout=60, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            state = get('/api/state')
            voice = get('/api/voice')
            if state['health'].get('loaded') and (not voice_enabled or voice['ready']):
                break
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(1)
    else:
        raise TimeoutError('La passerelle ou la voix Low ne sont pas prêtes après rechargement.')
    if models() != before or fingerprints != preserved_files():
        raise RuntimeError('Les contrôles de conservation ont échoué.')
    report = {
        'passed': True, 'model_processes_preserved': True, 'configuration_and_keys_preserved': True,
        'low_ready': voice['ready'], 'launcher_exit_code': launch.returncode,
        'sources': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
            'lanceur/remote.py', 'lanceur/voice_response.py', 'lanceur/voice_web.py',
            'lanceur/voice_context.py', 'lanceur/voice_web_plan.py')},
    }
    (OUT / 'activation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
