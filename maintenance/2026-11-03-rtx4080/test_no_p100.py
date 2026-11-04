"""Run the authorized RTX-only trial and restore the managed two-P100 default."""
import json
from pathlib import Path
import subprocess
import sys
import time

import psutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'no-p100'
sys.path.insert(0, str(ROOT / 'lanceur'))
from core import arg, read_json, write_json
from activate_default import get, control


def main():
    OUT.mkdir(exist_ok=False)
    settings = read_json(ROOT / 'lanceur/reglages.json')
    assert len(settings['gpus'].split(',')) == 3 and settings['expert_cache'] == 'auto'
    assert settings['spec'] == 6 and not settings['mtp_enabled']
    status = {'phase': 'waiting_idle', 'saved_settings': settings}
    write_json(OUT / 'status.json', status)
    stopped = False
    try:
        deadline = time.monotonic() + 180
        while True:
            live = get('/metrics', settings['port'])['live']
            if live['state'] == 'idle' and not live.get('queued'):
                break
            if time.monotonic() > deadline:
                raise TimeoutError('Managed generation remains active; benchmark not started')
            print('Waiting for the active generation', flush=True)
            time.sleep(5)
        stopped = True
        status['stop'] = control('stop', {})
        status['phase'] = 'benchmark'
        write_json(OUT / 'status.json', status)
        deadline = time.monotonic() + 90
        while True:
            try:
                get('/health', settings['port'])
            except OSError:
                break
            if time.monotonic() > deadline:
                raise TimeoutError('Managed port not released')
            time.sleep(1)
        command = [sys.executable, '-u', str(HERE.parent / '2026-10-30-rtx3080/benchmark.py'),
                   'rtx4080', '--primary-gpu-uuid', 'GPU-7d35736d-3ef5-1304-0e9e-1d26021be1a0',
                   '--p100-count', '0', '--context', '262144', '--quality-suite', '--long-prefill',
                   '--output-dir', str(OUT / 'trial')]
        with (OUT / 'console.log').open('w', encoding='utf-8') as log:
            proc = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding='utf-8', errors='replace',
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            for line in proc.stdout:
                log.write(line)
                log.flush()
                try:
                    row = json.loads(line)
                except ValueError:
                    print(line.strip()[:240], flush=True)
                    continue
                if 'label' in row:
                    print(json.dumps({'label': row['label'], 'quality': row['quality_pass'],
                                      'decode': row['timings']['predicted_per_second'],
                                      'prefill': row['timings']['prompt_per_second']}), flush=True)
                else:
                    print(line.strip(), flush=True)
            status['benchmark_exit_code'] = proc.wait()
        if status['benchmark_exit_code']:
            raise RuntimeError('RTX-only benchmark failed; raw evidence retained')
    finally:
        if stopped:
            assert not any(c.laddr.port == 18080 and c.status == 'LISTEN' for c in psutil.net_connections(kind='tcp'))
            status['phase'] = 'restoring_default'
            write_json(OUT / 'status.json', status)
            status['restore_start'] = control('start', settings)
            write_json(OUT / 'status.json', status)
            deadline = time.monotonic() + 1200
            last_print = 0
            while time.monotonic() < deadline:
                pointer = read_json(ROOT / 'lanceur/session.json')
                folder = Path(pointer['directory'])
                state = read_json(folder / 'state.json', {})
                if state.get('status') == 'pret':
                    cfg = read_json(folder / 'strata.json')
                    assert len(cfg['env']['CUDA_VISIBLE_DEVICES'].split(',')) == 3
                    assert arg(cfg, '--draft') == 'dflash2' and '--mtp' not in cfg['args']
                    status.update(phase='default_restored', session=str(folder),
                                  managed_health=get('/health', settings['port']),
                                  managed_engine=get('/metrics', settings['port'])['engine'])
                    write_json(OUT / 'status.json', status)
                    print('Two-P100 default restored and ready.', flush=True)
                    break
                if state.get('status') == 'erreur':
                    raise RuntimeError('Restoring default: ' + state.get('error', 'unknown'))
                if time.monotonic() - last_print > 20:
                    print('Restoring default:', state.get('status'), flush=True)
                    last_print = time.monotonic()
                time.sleep(2)
            else:
                raise TimeoutError('Managed default not ready after restoration')


if __name__ == '__main__':
    main()
