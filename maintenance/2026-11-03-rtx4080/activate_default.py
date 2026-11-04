"""Reload the owned console and validate the authorized default through its API."""
import base64
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

import psutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'default-mode'
sys.path.insert(0, str(ROOT / 'lanceur'))
from core import PYTHON, arg, read_json, same_process, stop_processes, write_json

HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(path, port=8765):
    with HTTP.open(f'http://127.0.0.1:{port}{path}', timeout=10) as response:
        return json.load(response)


def control(action, data):
    with HTTP.open('http://127.0.0.1:8765', timeout=10) as response:
        html = response.read().decode()
    token = re.search('name="launcher-token" content="([^"]+)"', html)[1]
    req = urllib.request.Request('http://127.0.0.1:8765/api/' + action, json.dumps(data).encode(),
        {'Content-Type': 'application/json', 'X-Launcher-Token': token, 'Origin': 'http://127.0.0.1:8765'})
    with HTTP.open(req, timeout=60) as response:
        return json.load(response)


def main():
    assert not any(c.laddr.port == 18080 and c.status == 'LISTEN' for c in psutil.net_connections(kind='tcp'))
    assert not get('/api/state')['running'], 'Managed model must be idle/stopped before console reload'
    identity = read_json(ROOT / 'lanceur/interface.pid.json')
    process = same_process(identity)
    assert process is not None
    assert any(Path(a).name == 'app.py' for a in process.cmdline())
    assert any(c.pid == process.pid and c.laddr.port == 8765 and c.status == 'LISTEN'
               for c in psutil.net_connections(kind='tcp'))
    stop_processes([process])
    started_epoch = time.time()
    with (OUT / 'console.stdout.log').open('wb') as stdout, (OUT / 'console.stderr.log').open('wb') as stderr:
        launched = subprocess.Popen([str(PYTHON), '-u', str(ROOT / 'lanceur/app.py'), '--port', '8765',
                                     '--preserve-model-state'], cwd=ROOT, stdout=stdout, stderr=stderr,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
    write_json(OUT / 'console-process.json', {'pid': launched.pid, 'started_epoch': started_epoch,
                                            'replaced_identity': identity})
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            fresh = read_json(ROOT / 'lanceur/interface.pid.json', {})
            if fresh.get('created', 0) >= started_epoch and get('/health').get('service') == 'qwen-launcher':
                break
        except (OSError, ValueError):
            pass
        time.sleep(1)
    else:
        raise TimeoutError('Reloaded console is not ready')
    settings = get('/api/settings')
    assert 'strata-0.1.56-cuda12' in settings['exe']
    assert settings['gpus'].startswith('GPU-7d35736d-3ef5-1304-0e9e-1d26021be1a0,')
    response = control('start', settings)
    write_json(OUT / 'managed-start.json', response)
    deadline = time.monotonic() + 1200
    last_print = 0
    while time.monotonic() < deadline:
        pointer = read_json(ROOT / 'lanceur/session.json', {})
        run = read_json(Path(pointer.get('directory', '.')) / 'state.json', {})
        cfg = read_json(Path(pointer.get('directory', '.')) / 'strata.json', {})
        if cfg:
            assert arg(cfg, '--draft') == 'dflash2' and arg(cfg, '--spec') == '6'
            assert arg(cfg, '--expert-cache') == 'auto' and '--mtp' not in cfg['args']
            assert len(cfg['env']['CUDA_VISIBLE_DEVICES'].split(',')) == 3
        if run.get('status') == 'pret':
            break
        if run.get('status') == 'erreur':
            raise RuntimeError(run.get('error'))
        if time.monotonic() - last_print > 20:
            print('Managed model:', run.get('status'), flush=True)
            last_print = time.monotonic()
        time.sleep(2)
    else:
        raise TimeoutError('Managed model did not become ready')

    def chat(label, content, expected):
        payload = {'model': cfg['model_name'], 'messages': [{'role': 'user', 'content': content}],
                   'temperature': 0, 'max_tokens': 128, 'stream': False,
                   'chat_template_kwargs': {'enable_thinking': False}}
        headers = {'Content-Type': 'application/json'}
        if cfg.get('api_key'):
            headers['Authorization'] = 'Bearer ' + cfg['api_key']
        req = urllib.request.Request(f'http://127.0.0.1:{cfg["port"]}/v1/chat/completions',
                                     json.dumps(payload).encode(), headers)
        with HTTP.open(req, timeout=300) as response:
            result = json.load(response)
        write_json(OUT / (label + '.json'), result)
        text = result['choices'][0]['message'].get('content', '').lower()
        assert all(word in text for word in expected), text
        if label == 'managed-image':
            assert 'carré' in text or 'carre' in text, text

    chat('managed-calculation', 'Calcule 143 + 158. Réponds uniquement avec le résultat.', ['301'])
    image = base64.b64encode((ROOT / 'maintenance/2026-10-14-vision/vision-fixture.png').read_bytes()).decode()
    chat('managed-image', [{'type': 'text', 'text': 'Lis le code et indique les formes rouge et bleue en français.'},
                           {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + image}}],
         ['47', 'cercle', 'rouge', 'bleu'])
    status = read_json(OUT / 'status.json')
    status.update(phase='active_verified', activated=dt.datetime.now().astimezone().isoformat(),
                  session=pointer['directory'], managed_state=run['status'],
                  health=get('/health', cfg['port']), engine_metrics=get('/metrics', cfg['port'])['engine'],
                  managed_calculation_passed=True, managed_image_passed=True,
                  gpu_configuration=cfg['env']['CUDA_VISIBLE_DEVICES'],
                  managed_config_sha256=hashlib.sha256(Path(run['config_path']).read_bytes()).hexdigest())
    write_json(OUT / 'status.json', status)
    print('Default active: RTX 4080 + two P100, DFlash2; calculation and image passed.', flush=True)


if __name__ == '__main__':
    main()
