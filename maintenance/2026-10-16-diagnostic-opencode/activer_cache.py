"""Apply the user-authorized 30 GiB conversation cache through the normal launcher."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request

import psutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'activation'
OUT.mkdir(exist_ok=True)
CACHE_SLOTS = 4
sys.path.insert(0, str(ROOT / 'lanceur'))
from core import read_json, write_json, build_config, validate

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
URL = 'http://127.0.0.1:8765'

def get(url):
    return json.load(opener.open(url, timeout=30))

def post(route, data):
    html = opener.open(URL + '/', timeout=15).read().decode()
    token = re.search(r'name="launcher-token" content="([^"]+)"', html).group(1)
    req = urllib.request.Request(URL + route, data=json.dumps(data).encode(), headers={
        'Content-Type': 'application/json', 'X-Launcher-Token': token, 'Origin': URL})
    return json.load(opener.open(req, timeout=90))

def set_arg(cfg, flag, value):
    args = cfg['args']
    if flag in args:
        args[args.index(flag) + 1] = str(value)
    else:
        args.extend([flag, str(value)])

def main():
    if (OUT / 'demarrage.json').exists():
        raise RuntimeError('Activation already attempted; inspect the saved result before retrying.')
    settings = validate(read_json(ROOT / 'lanceur/reglages.json'), check_paths=True)
    metrics = get('http://127.0.0.1:8080/metrics')
    write_json(OUT / 'metrics-avant.json', metrics)
    configs = [ROOT / 'lanceur/base-strata.json', ROOT / 'strata-iq4-p100-hybride.json']
    for p in configs:
        target = OUT / ('avant-' + ('base-strata.json' if p.parent.name == 'lanceur' else p.name))
        if target.exists():
            raise RuntimeError('Backup already exists; refusing to overwrite it.')
        shutil.copy2(p, target)
        cfg = read_json(p)
        set_arg(cfg, '--conversation-cache-mib', 30720)
        set_arg(cfg, '--conversation-cache-slots', CACHE_SLOTS)
        set_arg(cfg, '--conversation-cache-min-free-mib', 6144)
        built = build_config(cfg, settings)
        assert built['args'][built['args'].index('--conversation-cache-mib') + 1] == '30720'
    preserved = [ROOT / 'lanceur/exploitation.json', ROOT / 'lanceur/hermes-models.json',
                 ROOT / 'lanceur/acces-distants.json', ROOT / 'lanceur/wireguard.json']
    fingerprints = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in preserved if p.is_file()}
    write_json(OUT / 'preservation-avant.json', fingerprints)
    print('Stopping the model through its owner...', flush=True)
    stopped = post('/api/stop', {})
    write_json(OUT / 'arret.json', stopped)
    for p in configs:
        cfg = read_json(p)
        set_arg(cfg, '--conversation-cache-mib', 30720)
        set_arg(cfg, '--conversation-cache-slots', CACHE_SLOTS)
        set_arg(cfg, '--conversation-cache-min-free-mib', 6144)
        write_json(p, cfg)
    identity = read_json(ROOT / 'lanceur/interface.pid.json')
    parent = psutil.Process(identity['pid'])
    assert abs(parent.create_time() - identity['created']) < .01
    assert str(ROOT / 'lanceur/app.py').lower() in [a.lower() for a in parent.cmdline()]
    children = [(p, p.create_time()) for p in parent.children(recursive=True)]
    parent.terminate()
    parent.wait(timeout=15)
    for p, created in reversed(children):
        try:
            if p.is_running() and abs(p.create_time() - created) < .01:
                p.terminate()
                p.wait(timeout=10)
        except psutil.NoSuchProcess:
            pass
    print('Reloading the console configuration...', flush=True)
    result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', str(ROOT / 'Start-Interface-Qwen.ps1'), '-SansNavigateur', '-PreserverEtatModele'],
        capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    result = post('/api/start', settings)
    write_json(OUT / 'demarrage.json', result)
    after = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in preserved if p.is_file()}
    assert after == fingerprints, 'A protected configuration changed'
    write_json(OUT / 'preservation-apres.json', after)
    print(json.dumps(result), flush=True)

if __name__ == '__main__':
    main()
