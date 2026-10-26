"""Restart the managed idle model and reload the launcher profile."""
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request
import urllib.error

import psutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = 'http://127.0.0.1:8765'


def get(url):
    with HTTP.open(url, timeout=10) as response:
        return json.load(response)


def post(route, data):
    with HTTP.open(BASE, timeout=10) as response:
        html = response.read().decode()
    token = re.search(r'name="launcher-token" content="([^"]+)"', html).group(1)
    request = urllib.request.Request(BASE + route, json.dumps(data).encode(), headers={
        'Content-Type': 'application/json', 'X-Launcher-Token': token, 'Origin': BASE})
    try:
        with HTTP.open(request, timeout=120) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode('utf-8', errors='replace')
        raise RuntimeError(detail) from error


def main():
    try:
        live = get('http://127.0.0.1:8080/metrics')['live']
    except urllib.error.URLError as error:
        if not isinstance(error.reason, ConnectionRefusedError):
            raise
        live = {'state': 'unloaded', 'queued': 0}
    if live['state'] not in ('idle', 'unloaded') or live.get('queued'):
        raise RuntimeError('Un calcul est en cours ; redémarrage différé.')
    state = get(BASE + '/api/state')
    if state.get('queue', {}).get('active'):
        raise RuntimeError('Une conversation est active ; redémarrage différé.')
    deadline = time.monotonic() + 90
    while True:
        try:
            post('/api/stop', {})
            break
        except RuntimeError as error:
            if 'Windows libère encore les processus du modèle' not in str(error) or time.monotonic() >= deadline:
                raise
            time.sleep(2)
    identity = json.loads((ROOT / 'lanceur/interface.pid.json').read_text())
    console = psutil.Process(identity['pid'])
    if abs(console.create_time() - identity['created']) >= .01:
        raise RuntimeError('Identité de la console modifiée.')
    if str(ROOT / 'lanceur/app.py').casefold() not in [arg.casefold() for arg in console.cmdline()]:
        raise RuntimeError('Le processus ne correspond pas à la console.')
    children = [(child, child.create_time()) for child in console.children(recursive=True)]
    console.terminate()
    console.wait(timeout=15)
    for child, created in reversed(children):
        try:
            if child.is_running() and abs(child.create_time() - created) < .01:
                child.terminate()
                child.wait(timeout=10)
        except psutil.NoSuchProcess:
            pass
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                    '-File', str(ROOT / 'Start-Interface-Qwen.ps1'), '-SansNavigateur', '-PreserverEtatModele'],
                   check=False, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
    # The legacy script waits only ten seconds; cold imports can take longer.
    deadline = time.monotonic() + 90
    while True:
        try:
            if get(BASE + '/health').get('service') == 'qwen-launcher':
                break
        except OSError:
            pass
        if time.monotonic() >= deadline:
            raise RuntimeError('La console ne répond pas après le redémarrage.')
        time.sleep(1)
    settings = json.loads((ROOT / 'lanceur/reglages.json').read_text(encoding='utf-8-sig'))
    result = post('/api/start', settings)
    session = json.loads((ROOT / 'lanceur/session.json').read_text())
    (OUT / 'demarrage.json').write_text(json.dumps({'result': result, 'session': session}, indent=2), encoding='utf-8')
    print(json.dumps({'result': result, 'session': session}), flush=True)


if __name__ == '__main__':
    main()
