"""Wait for the managed engine, then measure three interleaved conversations."""
import datetime
import json
from pathlib import Path
import threading
import time
import urllib.request

import psutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'activation'
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = 'http://127.0.0.1:8080'
REPORT = {'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'calls': []}
LINE_COUNT = 140

def save():
    (OUT / 'mesures.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')

def get(path):
    return json.load(OPENER.open(BASE + path, timeout=15))

def wait_ready():
    deadline = time.monotonic() + 90 * 60
    last_print = 0
    while time.monotonic() < deadline:
        pointer = json.loads((ROOT / 'lanceur/session.json').read_text(encoding='utf-8-sig'))
        run = Path(pointer['directory'])
        state = json.loads((run / 'state.json').read_text(encoding='utf-8-sig'))
        if state.get('status') == 'erreur':
            raise RuntimeError(state.get('error'))
        if state.get('status') == 'pret':
            m = get('/metrics')
            assert m['conversation_cache']['enabled']
            assert m['conversation_cache']['budget_mib'] == 30720
            REPORT['metrics_before'] = m
            REPORT['run_directory'] = str(run)
            REPORT['ready_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            save()
            print('READY; beginning A/reference/B/C/A/B/C alternation.', flush=True)
            return
        if time.monotonic() - last_print >= 30:
            last_print = time.monotonic()
            logs = (run / 'engine.log').read_text(errors='replace') if (run / 'engine.log').exists() else ''
            print(json.dumps({'status': state.get('status'),
                'elapsed_s': round(time.time() - state.get('started_epoch', time.time())),
                'available_ram_gib': round(psutil.virtual_memory().available / 2**30, 2),
                'last_engine_line': logs.splitlines()[-1] if logs.splitlines() else ''}), flush=True)
        time.sleep(2)
    raise RuntimeError('Engine did not become ready within 90 minutes')

def call(label, messages):
    before = get('/metrics')
    samples = []
    stop = threading.Event()
    def sample():
        while not stop.is_set():
            vm = psutil.virtual_memory()
            engine_memory = []
            for p in psutil.process_iter(['name']):
                try:
                    if p.info['name'].lower() == 'strata.exe':
                        mem = p.memory_info()
                        engine_memory.append({'pid': p.pid, 'rss': mem.rss, 'private': getattr(mem, 'private', None)})
                except (psutil.Error, AttributeError):
                    pass
            samples.append({'time': time.time(), 'available_ram_bytes': vm.available,
                            'engine_memory': engine_memory})
            stop.wait(1)
    t = threading.Thread(target=sample, daemon=True)
    t.start()
    data = {'model': 'qwen3.8-flash-next-iq4-xs', 'messages': messages,
            'max_tokens': 32, 'temperature': 0, 'seed': 42, 'stream': False,
            'chat_template_kwargs': {'enable_thinking': False}}
    start = time.monotonic()
    try:
        req = urllib.request.Request(BASE + '/v1/chat/completions', data=json.dumps(data).encode(),
                                     headers={'Content-Type': 'application/json'})
        answer = json.load(OPENER.open(req, timeout=900))
    finally:
        stop.set()
        t.join(timeout=5)
    elapsed = time.monotonic() - start
    after = get('/metrics')
    usage = answer.get('usage', {})
    prompt_tokens = usage.get('prompt_tokens')
    request = next((r for r in after.get('requests', []) if r.get('prompt_tokens') == prompt_tokens), None)
    record = {'label': label, 'wall_seconds': round(elapsed, 3), 'usage': usage,
        'content': answer['choices'][0]['message'].get('content', ''), 'request_metrics': request,
        'cache_before': before['conversation_cache'], 'cache_after': after['conversation_cache'],
        'memory_samples': samples}
    REPORT['calls'].append(record)
    save()
    print(json.dumps({k: record[k] for k in ('label', 'wall_seconds', 'usage', 'request_metrics', 'cache_after')}, ensure_ascii=True), flush=True)
    assert after['conversation_cache']['bytes'] <= 30720 * 1024**2
    return record['content']

def main():
    if (OUT / 'mesures.json').exists():
        raise RuntimeError('Measurement file exists; refusing to overwrite a previous run')
    wait_ready()
    docs = {}
    for label, subject in [('A', 'imprimerie'), ('B', 'navigation'), ('C', 'botanique')]:
        lines = [f'Dossier {label}, rubrique {subject}, fiche {i:04d}. Cette fiche décrit une observation indépendante, '
                 f'sa date de collecte et sa méthode de classement. Les données sont conservées pour comparaison '
                 f'entre les équipes, avec un identifiant stable et une note explicative pour chaque observation.'
                 for i in range(LINE_COUNT)]
        docs[label] = [{'role': 'system', 'content': f'Tu lis le dossier expérimental {label}. Réponds très brièvement en français.'},
                       {'role': 'user', 'content': '\n'.join(lines) + '\nRéponds uniquement : dossier reçu.'}]
    a0 = call('A0_cold', docs['A'])
    a1_messages = docs['A'] + [{'role': 'assistant', 'content': a0},
                             {'role': 'user', 'content': 'Quel est le sujet du dossier ? Réponds en trois mots au maximum.'}]
    reference = call('A1_live_reference', a1_messages)
    b0 = call('B0_cold', docs['B'])
    c0 = call('C0_cold', docs['C'])
    restored = call('A1_restored_after_B_C', a1_messages)
    for label, response in [('B', b0), ('C', c0)]:
        call(label + '1_restored', docs[label] + [{'role': 'assistant', 'content': response},
            {'role': 'user', 'content': 'Quel est le sujet du dossier ? Réponds en trois mots au maximum.'}])
    REPORT['reference_and_restored_content_identical'] = reference == restored
    REPORT['metrics_after'] = get('/metrics')
    restored_calls = [r for r in REPORT['calls'] if 'restored' in r['label']]
    REPORT['passed'] = bool(restored_calls) and all(
        (r['request_metrics'] or {}).get('reused', 0) / max(r['usage'].get('prompt_tokens', 0), 1) > .90
        for r in restored_calls) and REPORT['metrics_after']['conversation_cache']['restores'] >= 3 and reference == restored
    REPORT['finished_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save()
    print('RESULT ' + json.dumps({'passed': REPORT['passed'], 'same_content': reference == restored,
        'cache': REPORT['metrics_after']['conversation_cache']}), flush=True)
    if not REPORT['passed']:
        raise RuntimeError('Cache validation failed; inspect measurements')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--large', action='store_true', help='Use three contexts of approximately 32k tokens')
    args = parser.parse_args()
    if args.large:
        OUT = OUT / 'charge-32k'
        OUT.mkdir(exist_ok=True)
        LINE_COUNT = 560
    if (OUT / 'mesures.json').exists():
        raise SystemExit('Measurement file exists; refusing to overwrite a previous run')
    try:
        main()
    except Exception as error:
        REPORT['error'] = str(error)
        save()
        raise
