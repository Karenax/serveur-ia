"""Detached supervisor: startup validation and RAM protection for new launches."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import psutil
from core import ROOT, PYTHON, HIDDEN, read_json, write_json, health, process_identity, stop_processes
from startup_memory import reclaim_loader

def supervise(config_path, run_dir, floor=6, mock=False):
    cfg = read_json(config_path)
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    state_path = run_dir / 'state.json'
    state = {'status': 'chargement', 'started': dt.datetime.now().astimezone().isoformat(),
             'started_epoch': time.time(), 'supervisor': process_identity(psutil.Process()),
             'config_path': str(Path(config_path).resolve()), 'host': cfg['host'], 'port': cfg['port'],
             'model': cfg['model_name'], 'min_free_ram_gib': floor}
    marker = Path(cfg['env'].get('STRATA_P100_DIAGNOSTIC_SYNC_FILE', str(ROOT / 'strata-data/cuda-debug.flag')))
    server = None
    def save():
        write_json(state_path, state)
    save()
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text('Validation initiale CUDA', encoding='utf-8')
        command = [str(PYTHON), '-u', '-m', 'serve.server', '--engine', 'mock' if mock else 'strata',
                   '--config', str(Path(config_path).resolve()), '--host', cfg['host'], '--port', str(cfg['port'])]
        with (run_dir / 'server.stdout.log').open('wb') as stdout, (run_dir / 'server.stderr.log').open('wb') as stderr:
            server_env = os.environ.copy()
            server_env.update(cfg.get('server_env', {}))
            server = subprocess.Popen(command, cwd=cfg['cwd'], env=server_env, stdout=stdout, stderr=stderr, creationflags=HIDDEN)
        state['server'] = process_identity(psutil.Process(server.pid))
        save()
        deadline = time.monotonic() + 90 * 60
        low_since = None
        reclaim_attempted = False
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError('Le serveur a quitté pendant le chargement ; consulter son journal.')
            free = psutil.virtual_memory().available / 2**30
            state['available_ram_gib'] = round(free, 2)
            if not reclaim_attempted and free < floor + 16 and '--resident-cpu-experts' in cfg.get('args', []):
                reclaim_attempted = True
                state['startup_memory_reclaim'] = reclaim_loader(cfg, state['server'])
                free = psutil.virtual_memory().available / 2**30
                state['available_ram_gib'] = round(free, 2)
            if free < floor:
                if low_since is None:
                    low_since = time.monotonic()
                if time.monotonic() - low_since >= 8:
                    raise RuntimeError(f'Protection RAM : moins de {floor:g} Go disponibles pendant le chargement. Le modèle est arrêté.')
            else:
                low_since = None
            ready = health(cfg['host'], cfg['port'])
            if ready.get('service') == 'strata' and ready.get('loaded'):
                state['loaded_seconds'] = round(time.time() - state['started_epoch'], 1)
                break
            save()
            time.sleep(2)
        else:
            raise RuntimeError('Le chargement n’est pas terminé après 90 minutes.')
        state['status'] = 'validation_cuda'
        save()
        payload = {'model': cfg['model_name'], 'messages': [{'role': 'user', 'content': 'Explique en français pourquoi le ciel est bleu, puis pourquoi il devient rouge au coucher du soleil. Donne une explication précise et accessible.'}],
                   'max_tokens': 1, 'temperature': 0, 'seed': 42, 'chat_template_kwargs': {'enable_thinking': False}}
        host = '127.0.0.1' if cfg['host'] == '0.0.0.0' else cfg['host']
        headers = {'Content-Type': 'application/json'}
        if cfg.get('api_key'):
            headers['Authorization'] = 'Bearer ' + cfg['api_key']
        request = urllib.request.Request(f'http://{host}:{cfg["port"]}/v1/chat/completions', data=json.dumps(payload).encode(), headers=headers)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=300) as response:
            answer = json.load(response)
        if answer.get('usage', {}).get('completion_tokens') != 1:
            raise RuntimeError('La validation CUDA n’a pas produit le token attendu.')
        write_json(run_dir / 'warmup.json', answer)
        marker.unlink(missing_ok=True)
        state.update(status='pret', ready_seconds=round(time.time() - state['started_epoch'], 1))
        from core import defaults_from_config
        write_json(run_dir.parent.parent/'derniers-reglages-valides.json',defaults_from_config(cfg))
        save()
        server.wait()
        state.update(status='arrete', stopped_epoch=time.time())
        save()
    except Exception as error:
        state.update(status='erreur', error=str(error))
        save()
        if server and server.poll() is None:
            try:
                stop_processes([psutil.Process(server.pid)])
                server.wait(timeout=12)
            except (psutil.Error, RuntimeError, subprocess.TimeoutExpired):
                pass
        marker.unlink(missing_ok=True)
    return state

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--floor', type=float, default=6)
    parser.add_argument('--mock', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    supervise(args.config, args.run_dir, args.floor, args.mock)
