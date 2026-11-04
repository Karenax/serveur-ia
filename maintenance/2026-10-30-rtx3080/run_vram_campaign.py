"""Run four isolated candidates and always restore the managed reference service."""
import datetime
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error
import psutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'optimisation-vram-20261031'
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(url):
    with HTTP.open(url, timeout=10) as response:
        return json.load(response)


def control(action, data):
    with HTTP.open('http://127.0.0.1:8765', timeout=10) as response:
        html = response.read().decode()
    token = re.search('name="launcher-token" content="([^"]+)"', html)[1]
    request = urllib.request.Request('http://127.0.0.1:8765/api/' + action,
        json.dumps(data).encode(), {'Content-Type': 'application/json',
                                  'X-Launcher-Token': token, 'Origin': 'http://127.0.0.1:8765'})
    with HTTP.open(request, timeout=60) as response:
        return json.load(response)


def save(value):
    (OUT / 'status.json').write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--extra-only', action='store_true')
    parser.add_argument('--extra-mtp', type=int, default=3)
    parser.add_argument('--validate-best-only', action='store_true')
    options = parser.parse_args()
    state = {'phase': 'waiting_idle', 'started': datetime.datetime.now().astimezone().isoformat(), 'runs': []}
    settings = json.loads((ROOT / 'lanceur/reglages.json').read_text(encoding='utf-8-sig'))
    plans = [
        ('opt2-ref-fp16', []),
        ('opt2-fp16-p1024-cache1', ['--prefill', '1024', '--expert-cache', '1']),
        ('opt2-int8-p1024-cache1', ['--kv', 'int8', '--prefill', '1024', '--expert-cache', '1']),
        ('opt2-int8-p1024-cache1-mtp4', ['--kv', 'int8', '--prefill', '1024', '--expert-cache', '1', '--spec', '4']),
    ]
    if options.extra_only:
        plans = [
            ('opt3-fp16-headalias-mtpq4-cache1', ['--expert-cache', '1', '--prefill-head-alias', '--mtp-q4', 'all']),
            ('opt3-int8-p2048-cache1', ['--kv', 'int8', '--expert-cache', '1', '--spec', str(options.extra_mtp)]),
        ]
    if options.validate_best_only:
        plans = [('opt4-int8-coexist1g', ['--kv', 'int8', '--expert-cache', '1', '--keep-caches',
                  '--isolate-conversations', '--long-prefill', '--hold-vram-mib', '1024'])]
    stopped = False
    try:
        while True:
            try:
                live = get('http://127.0.0.1:8080/metrics')['live']
            except urllib.error.URLError:
                console = get('http://127.0.0.1:8765/api/state')
                if console['status'] in ('chargement', 'validation_cuda', 'arrete', 'erreur'):
                    break
                raise
            if live['state'] == 'idle' and not live['queued']:
                break
            save(state)
            print('Waiting for active generation', flush=True)
            time.sleep(15)
        stopped = True
        pointer = json.loads((ROOT / 'lanceur/session.json').read_text(encoding='utf-8-sig'))
        managed = json.loads((Path(pointer['directory']) / 'state.json').read_text(encoding='utf-8-sig'))
        identities = {}
        for key in ('worker', 'server', 'supervisor'):
            identity = managed.get(key, pointer.get(key))
            if not identity:
                continue
            try:
                parent = psutil.Process(identity['pid'])
                if abs(parent.create_time() - identity['created']) < .01:
                    for owned in [parent, *parent.children(recursive=True)]:
                        identities[owned.pid] = owned.create_time()
            except psutil.NoSuchProcess:
                pass
        try:
            state['stop'] = control('stop', {})
        except urllib.error.HTTPError as error:
            detail = error.read().decode()
            if 'Windows' not in detail or 'lib' not in detail:
                raise RuntimeError(detail) from error
            state['stop'] = {'cleanup_wait': detail}
        deadline = time.monotonic() + 180
        while identities:
            for pid, created in list(identities.items()):
                try:
                    if abs(psutil.Process(pid).create_time() - created) >= .01:
                        identities.pop(pid)
                except psutil.NoSuchProcess:
                    identities.pop(pid)
            if not identities:
                break
            if time.monotonic() > deadline:
                raise TimeoutError('Owned model processes still cleaning up; no benchmark started')
            time.sleep(2)
        for tag, extra in plans:
            state.update(phase='benchmark', current=tag)
            save(state)
            command = [sys.executable, str(HERE / 'benchmark.py'), 'rtx3080', '--context', '262144',
                       '--tag', tag, '--with-vision', '--quality-suite', *extra]
            with (OUT / (tag + '-console.log')).open('w', encoding='utf-8') as log:
                process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
                state['benchmark_pid'] = process.pid
                save(state)
                for line in process.stdout:
                    log.write(line)
                    log.flush()
                    try:
                        row = json.loads(line)
                    except ValueError:
                        print(line.strip()[:240], flush=True)
                        continue
                    if 'label' in row:
                        timings = row.get('timings') or {}
                        print(json.dumps({'run': tag, 'label': row['label'], 'quality': row['quality_pass'],
                            'prefill': timings.get('prompt_per_second'), 'decode': timings.get('predicted_per_second')}), flush=True)
                    else:
                        print(json.dumps({'run': tag, **row}), flush=True)
                code = process.wait()
            state['runs'].append({'tag': tag, 'exit_code': code})
            save(state)
    finally:
        if stopped:
            state['phase'] = 'restoring_reference'
            save(state)
            state['restore'] = control('start', settings)
            state['phase'] = 'reference_loading_after_trials'
            save(state)
            print('Reference service restoration started', flush=True)


if __name__ == '__main__':
    main()
