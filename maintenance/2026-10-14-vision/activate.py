"""Activate or restore the isolated vision trial, retaining private backups."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PRIVATE = ROOT / 'toolchain/vision-trial-20261014'
sys.path.insert(0, str(ROOT / 'lanceur'))
from validate_live_lots6_8 import get, models, post


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def restart_console():
    identity = read(ROOT / 'lanceur/interface.pid.json')
    parent = psutil.Process(identity['pid'])
    assert abs(parent.create_time() - identity['created']) < .01
    assert str(ROOT / 'lanceur/app.py').lower() in [arg.lower() for arg in parent.cmdline()]
    assert not models(), 'Stop the model before restarting its console'
    children = [(child, child.create_time()) for child in parent.children(recursive=True)]
    parent.terminate()
    parent.wait(timeout=10)
    for child, created in reversed(children):
        try:
            if child.is_running() and abs(child.create_time() - created) < .01:
                child.terminate()
                child.wait(timeout=10)
        except psutil.NoSuchProcess:
            pass
    result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', str(ROOT / 'Start-Interface-Qwen.ps1'), '-SansNavigateur', '-PreserverEtatModele'],
        capture_output=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0, 'Console restart failed'


def main(restore=False):
    state = get('/api/state')
    assert state.get('queue', {}).get('active', 0) == 0
    assert get('/api/remote').get('active', 0) == 0
    names = ('lanceur/base-strata.json', 'strata-iq4-p100-hybride.json')
    for name in names:
        assert (PRIVATE / 'before' / name).is_file()
    if not restore:
        evidence = read(OUT / 'encoder.json')
        assert evidence['passed'] and evidence['gpu_acceleration']
        cfg = read(PRIVATE / 'vision-config.json')
        stable = ROOT / 'dependances/strata-0.1.43.1/vision-p2200-cuda12.4/strata-vision.exe'
        stable.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cfg['exe'], stable)
        cfg['exe'] = str(stable)
        write(stable.parent / 'BUILD.json', {
            'strata_version': '0.1.43.1', 'cuda': '12.4.131', 'architectures': ['61-real'],
            'llama_cpp_commit': '3cf03257f219afbe7334045ff7c6a06ac68c627d',
            'recipe': 'maintenance/2026-10-14-vision/build_encoder.cmd',
            'sha256': hashlib.sha256(stable.read_bytes()).hexdigest()})
        for name in names:
            base = read(ROOT / name)
            base['vision'] = cfg
            if '--vision' not in base['args']:
                base['args'].append('--vision')
            write(ROOT / name, base)
    else:
        for name in names:
            shutil.copy2(PRIVATE / 'before' / name, ROOT / name)
    print('Stopping Qwen for ' + ('rollback' if restore else 'vision activation'), flush=True)
    post('/api/stop', {})
    for _ in range(30):
        if not models():
            break
        time.sleep(1)
    assert not models()
    restart_console()
    settings = read(PRIVATE / 'before/lanceur/reglages.json')
    result = post('/api/start', settings)
    write(OUT / ('rollback-start.json' if restore else 'activation-start.json'), result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--restore', action='store_true')
    main(parser.parse_args().restore)
