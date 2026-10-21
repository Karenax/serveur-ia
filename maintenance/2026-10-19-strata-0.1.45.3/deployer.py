import hashlib
import json
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PYTHON = ROOT / 'Strata-src/.venv/Scripts/python.exe'
DEST = ROOT / 'dependances/strata-0.1.45.3/engine-cuda12'
SOURCE = ROOT / 'recherche/strata-0.2.0-beta-20261019/engine-package'
FILES = ['lanceur/base-strata.json', 'strata-iq4-p100-hybride.json',
         'lanceur/reglages.json', 'lanceur/reglages-par-defaut.json',
         'lanceur/derniers-reglages-valides.json']
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def write(p, value):
    Path(p).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def get(url):
    return json.load(HTTP.open(url, timeout=15))

def post(route, data):
    base = 'http://127.0.0.1:8765'
    html = HTTP.open(base, timeout=15).read().decode()
    token = re.search(r'name="launcher-token" content="([^"]+)"', html).group(1)
    req = urllib.request.Request(base + route, data=json.dumps(data).encode(), headers={
        'Content-Type': 'application/json', 'X-Launcher-Token': token, 'Origin': base})
    return json.load(HTTP.open(req, timeout=180))

def sha(p):
    return hashlib.file_digest(Path(p).open('rb'), 'sha256').hexdigest()

def main():
    assert not (OUT / 'avant').exists(), 'Backup already exists; inspect before rerunning'
    live = get('http://127.0.0.1:8080/metrics')['live']
    assert live['state'] == 'idle' and not live.get('queued'), live
    before = {name: read(ROOT / name) for name in FILES}
    for name in FILES + ['lanceur/exploitation.json', 'lanceur/session.json',
                         'lanceur/interface.pid.json', 'lanceur/relances.json']:
        if (ROOT / name).exists():
            p = OUT / 'avant' / name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, p)
    protected = [ROOT / 'dependances/strata-0.1.43.1/source/serve/tool_parser.py']
    protected += [p for p in (ROOT / 'lanceur').glob('*.json')
                  if p.name not in {Path(f).name for f in FILES} | {
                      'session.json', 'interface.pid.json', 'relances.json'}]
    write(OUT / 'empreintes-avant.json', {str(p): sha(p) for p in protected if p.is_file()})
    manifest = read(SOURCE / 'engine-component.json')
    DEST.mkdir(parents=True, exist_ok=True)
    for p in SOURCE.iterdir():
        if p.is_file():
            shutil.copy2(p, DEST / p.name)
    for item in manifest['files']:
        assert sha(DEST / item['path']) == item['sha256'], item['path']
    assert sha(DEST / 'strata.exe') == 'c97c3e84228c928c46bb2727c1753cbfe76c31c3eb0a9edc7bdd3cd78871cac3'
    prepared = {}
    for name, cfg in before.items():
        cfg = dict(cfg, exe=str(DEST / 'strata.exe'))
        if 'lib_dirs' in cfg:
            cfg['lib_dirs'] = [str(DEST)]
        assert {k: v for k, v in cfg.items() if k not in ('exe', 'lib_dirs')} == {
            k: v for k, v in before[name].items() if k not in ('exe', 'lib_dirs')}
        prepared[name] = cfg
    write(OUT / 'configuration-prevue.json', prepared)
    # Recheck before interrupting the managed model.
    live = get('http://127.0.0.1:8080/metrics')['live']
    assert live['state'] == 'idle' and not live.get('queued'), live
    post('/api/stop', {})
    for name, cfg in prepared.items():
        write(ROOT / name, cfg)
    identity = read(ROOT / 'lanceur/interface.pid.json')
    console = psutil.Process(identity['pid'])
    assert abs(console.create_time() - identity['created']) < .01
    assert any(str(ROOT / 'lanceur/app.py').lower() == arg.lower() for arg in console.cmdline())
    console.terminate()
    console.wait(timeout=15)
    subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    str(ROOT / 'Start-Interface-Qwen.ps1'), '-SansNavigateur', '-PreserverEtatModele'],
                   check=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
    settings = prepared['lanceur/reglages.json']
    post('/api/set-default', settings)
    result = post('/api/start', settings)
    write(OUT / 'demarrage.json', {'result': result, 'session': read(ROOT / 'lanceur/session.json'),
                                  'engine_sha256': sha(DEST / 'strata.exe'), 'version': manifest['version']})
    print('Nouveau moteur installé, valeurs par défaut enregistrées, chargement lancé.', flush=True)

if __name__ == '__main__':
    main()
