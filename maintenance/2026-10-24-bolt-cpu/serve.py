"""Keep the measured CPU-only model loaded locally, without changing Kiara."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

from benchmark import BASE, OUT, PORT, footprint, request, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('baseline', 'dflash'), default='dflash')
    args = parser.parse_args()
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', PORT)) == 0:
            raise RuntimeError(f'Port {PORT} already occupied; no existing process stopped')
    report = json.loads((OUT / f'{args.mode}-t16.json').read_text(encoding='utf-8'))
    if not report.get('passed'):
        raise RuntimeError('Requested configuration did not pass its benchmark')
    command = report['command']
    flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    started = time.perf_counter()
    with (OUT / 'loaded-server.log').open('ab') as log:
        process = subprocess.Popen(command, cwd=str(Path(command[0]).parent), stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=flags, env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1'}, close_fds=True)
    try:
        while time.perf_counter() - started < 180:
            if process.poll() is not None:
                raise RuntimeError(f'Server exited {process.returncode}; see loaded-server.log')
            try:
                if request('/health', timeout=3).get('status') == 'ok':
                    break
            except (OSError, RuntimeError):
                pass
            time.sleep(0.5)
        else:
            raise TimeoutError('CPU server did not become ready')
        result = {'pid': process.pid, 'mode': args.mode, 'base_url': BASE + '/v1', 'cpu_only': True,
                  'model_alias': 'bolt-cpu', 'command': command, 'load_ready_seconds': time.perf_counter() - started,
                  'memory': footprint(process.pid), 'health': request('/health'), 'automatic_startup': False,
                  'kiara_configuration_changed': False}
        write_json(OUT / 'loaded-server.json', result)
        write_json(OUT / 'active-test.json', result)
        print(json.dumps(result, ensure_ascii=True, indent=2))
    except Exception:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=15)
        raise


if __name__ == '__main__':
    main()
