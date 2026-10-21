"""Compare engine binaries behind the same patched Python server; restore production."""
import argparse
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import statistics
import subprocess
import sys
import threading
import time
import urllib.request

import psutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = HERE / 'mesures' / 'essai-01'
PY = ROOT / 'Strata-src/.venv/Scripts/python.exe'
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
STATE = {}
DONE = threading.Event()
HOT = threading.Event()
TEST = None


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def state(**changes):
    STATE.update(changes)
    STATE['updated_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    write(RUN / 'etat.json', STATE)
    print(json.dumps(changes, ensure_ascii=False), flush=True)


def get(port, path):
    return json.load(OPENER.open(f'http://127.0.0.1:{port}{path}', timeout=20))


def post(port, path, data, timeout=900, headers=None):
    request = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=json.dumps(data).encode(),
                                    headers={'Content-Type': 'application/json', **(headers or {})})
    return json.load(OPENER.open(request, timeout=timeout))


def control(path, data):
    base = 'http://127.0.0.1:8765'
    html = OPENER.open(base + '/', timeout=20).read().decode()
    token = re.search(r'name="launcher-token" content="([^"]+)"', html).group(1)
    return post(8765, path, data, 180, {'X-Launcher-Token': token, 'Origin': base})


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fingerprints():
    names = ['lanceur/base-strata.json', 'strata-iq4-p100-hybride.json', 'lanceur/reglages.json',
             'lanceur/reglages-par-defaut.json', 'lanceur/exploitation.json', 'lanceur/hermes-models.json',
             'lanceur/acces-distants.json', 'lanceur/wireguard.json', 'lanceur/derniers-reglages-valides.json']
    return {n: digest(ROOT / n) for n in names if (ROOT / n).is_file()}


def gpu():
    query = 'uuid,name,temperature.gpu,clocks.sm,power.draw,clocks_throttle_reasons.active,utilization.gpu,memory.used'
    result = subprocess.run(['nvidia-smi', '--query-gpu=' + query, '--format=csv,noheader,nounits'],
                            capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
    result.check_returncode()
    rows = []
    for line in result.stdout.splitlines():
        cols = [v.strip() for v in line.split(',')]
        if 'P100' in cols[1]:
            rows.append(dict(uuid=cols[0], temperature_c=float(cols[2]), sm_mhz=float(cols[3]),
                             power_w=float(cols[4]), throttle_mask=int(cols[5], 16),
                             utilization=float(cols[6]), vram_mib=float(cols[7])))
    assert len(rows) == 2, rows
    return rows


def observer():
    with (RUN / ('telemetrie-' + STATE['arm'] + '.jsonl')).open('a', encoding='utf-8') as stream:
        while not DONE.is_set():
            try:
                rows = gpu()
                stream.write(json.dumps(dict(time=time.time(), phase=STATE.get('phase'), case=STATE.get('case'),
                                             rows=rows, ram_available_gib=psutil.virtual_memory().available / 2**30)) + '\n')
                stream.flush()
                if STATE.get('phase') == 'inference' and any(r['throttle_mask'] & 0x60 for r in rows):
                    HOT.set()
            except Exception as error:
                stream.write(json.dumps({'time': time.time(), 'error': str(error)}) + '\n')
                stream.flush()
            DONE.wait(2)


def cool():
    state(phase='refroidissement')
    end = time.monotonic() + 900
    while True:
        rows = gpu()
        if max(r['temperature_c'] for r in rows) <= 55 and not any(r['throttle_mask'] & 0x60 for r in rows):
            HOT.clear()
            return rows
        if time.monotonic() > end:
            raise RuntimeError('Refroidissement sous 55 C non atteint en 15 minutes')
        time.sleep(3)


def call(port, label, messages, limit=256, expected=None, cache=False, extra=None):
    folder = RUN / STATE['arm']
    folder.mkdir(exist_ok=True)
    before = cool()
    payload = dict(model='qwen3.8-flash-next-iq4-xs', messages=messages, max_tokens=limit, temperature=0,
                   seed=42, stream=False, cache_prompt=cache, reasoning_effort='none',
                   chat_template_kwargs={'enable_thinking': False})
    payload.update(extra or {})
    write(folder / (label + '-request.json'), payload)
    state(phase='inference', case=label)
    started = time.time()
    answer = post(port, '/v1/chat/completions', payload)
    elapsed = time.time() - started
    write(folder / (label + '-response.json'), answer)
    text = answer['choices'][0]['message'].get('content') or ''
    valid = bool(text.strip() or answer['choices'][0]['message'].get('tool_calls'))
    strict = None
    if expected:
        try:
            value = json.loads(text)
            strict = True
        except ValueError:
            strict = False
            match = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```', text.strip(), re.S)
            try:
                value = json.loads(match.group(1)) if match else None
            except ValueError:
                value = None
        valid = isinstance(value, dict) and all(value.get(k) == v for k, v in expected.items())
    timings = answer.get('timings') or {}
    after = gpu()
    thermally_valid = not HOT.is_set() and not any(r['throttle_mask'] & 0x60 for r in after)
    row = dict(name=label, elapsed_s=elapsed, started_epoch=started, timings=timings, usage=answer.get('usage'),
               content=text, quality_pass=valid, strict_json=strict, gpu_before=before, gpu_after=after,
               thermally_valid=thermally_valid, text_sha256=hashlib.sha256(text.encode()).hexdigest())
    records = read(folder / 'results.json') if (folder / 'results.json').exists() else []
    records.append(row)
    write(folder / 'results.json', records)
    state(phase='entre-requetes', last_result={k: row[k] for k in ('name', 'elapsed_s', 'timings', 'quality_pass', 'thermally_valid')})
    # User explicitly removed the 80 C stop; hardware throttling is observed,
    # recorded and reported, rather than terminating the campaign.
    if not valid and not extra:
        raise RuntimeError('Verification de contenu echouee : ' + label)
    if not cache and timings.get('cache_n', 0):
        raise RuntimeError('Reutilisation de prompt inattendue : ' + label)
    return answer


def benchmark(port):
    cases = [
        ('ciel', 'Explique en français pourquoi le ciel est bleu, puis pourquoi il devient rouge au coucher du soleil. Donne une explication précise et accessible.', 256, None),
        ('fibonacci-code', 'Écris une fonction Python fibonacci(n) qui retourne les n premiers nombres de Fibonacci, puis donne un exemple pour n=8. Réponds en français.', 256, None),
        ('calcul', 'Réponds uniquement avec un objet JSON valide contenant ces clés : produit pour 17 multiplié par 23, somme pour 125 plus 375, capitale pour la capitale de la France.', 128,
         {'produit': 391, 'somme': 500, 'capitale': 'Paris'})]
    call(port, 'warmup', [{'role': 'user', 'content': 'Réponds uniquement avec un objet JSON contenant la clé resultat et le nombre 42.'}], 64, {'resultat': 42})
    for rep in range(1, 6):
        for name, prompt, limit, expected in cases:
            label = f'r{rep}-{name}'
            call(port, label, [{'role': 'user', 'content': f'Mesure indépendante {label}.\n' + prompt}], limit, expected)
    for lines in (64, 256, 1024):
        rows = [f'Ligne {i:04d}: le dossier décrit un jardin, des arbres et un chemin de pierre.' for i in range(lines)]
        rows.insert(lines // 2, 'Information prioritaire : le code secret du dossier est LUMIERE-7429.')
        prompt = 'Lis le dossier suivant.\n' + '\n'.join(rows) + '\nRéponds uniquement avec un objet JSON contenant la clé code et le code secret indiqué au milieu du dossier.'
        for rep in (1, 2):
            label = f'dossier-{lines}-r{rep}'
            call(port, label, [{'role': 'user', 'content': f'Mesure indépendante {label}.\n' + prompt}], 80, {'code': 'LUMIERE-7429'})
    write(RUN / STATE['arm'] / 'metrics-apres-debit.json', get(port, '/metrics'))


def wait_ready(port, run_dir=None, seconds=5400):
    end = time.monotonic() + seconds
    last = 0
    while time.monotonic() < end:
        runtime = {}
        if run_dir and (run_dir / 'state.json').exists():
            runtime = read(run_dir / 'state.json')
            if runtime.get('status') == 'erreur':
                raise RuntimeError(runtime.get('error'))
            ready = runtime.get('status') == 'pret'
        else:
            ready = True
        try:
            health = get(port, '/health')
            if health.get('loaded') and ready:
                return health
        except (OSError, ValueError):
            pass
        if time.monotonic() - last > 30:
            last = time.monotonic()
            print(json.dumps({'waiting_port': port, 'runtime': runtime if run_dir else None,
                              'available_ram_gib': round(psutil.virtual_memory().available / 2**30, 2)}), flush=True)
        time.sleep(3)
    raise TimeoutError('Modele pas pret sur le port ' + str(port))


def stop_test():
    record = RUN / 'test-process.json'
    if not record.exists():
        return
    identity = read(record)
    try:
        process = psutil.Process(identity['pid'])
        assert abs(process.create_time() - identity['created']) < .01
        cmd = process.cmdline()
        assert str(RUN / 'nouveau.json').lower() in [s.lower() for s in cmd]
        children = process.children(recursive=True)
        for child in reversed(children):
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        process.terminate()
        _, alive = psutil.wait_procs(children + [process], timeout=15)
        for child in alive:
            child.kill()
    except psutil.NoSuchProcess:
        pass


def functional(port):
    # Same imports and patched server as production. Probes never execute tools.
    schema = {'type': 'function', 'function': {'name': 'bool_probe', 'description': 'Report the requested values.',
              'parameters': {'type': 'object', 'properties': {'background': {'type': 'boolean'}, 'marker': {'type': 'string'}},
                             'required': ['background', 'marker']}}}
    response = call(port, 'outil-booleen', [{'role': 'user', 'content': 'Appelle bool_probe avec background=false et marker="True". Aucun autre texte.'}],
                    160, extra={'tools': [schema], 'tool_choice': {'type': 'function', 'function': {'name': 'bool_probe'}}})
    fn = response['choices'][0]['message']['tool_calls'][0]['function']
    args = json.loads(fn['arguments'])
    assert fn['name'] == 'bool_probe' and args == {'background': False, 'marker': 'True'}, fn
    write(RUN / STATE['arm'] / 'outil-verification.json', {'passed': True, 'arguments': args, 'executed': False})

    import base64
    fixture = ROOT / 'maintenance/2026-10-14-vision/vision-fixture.png'
    data = base64.b64encode(fixture.read_bytes()).decode()
    response = call(port, 'vision', [{'role': 'user', 'content': [
        {'type': 'text', 'text': 'Réponds uniquement avec un objet JSON : code pour le texte écrit dans cette image, rouge pour le nom de la forme rouge et bleu pour le nom de la forme bleue. Noms des formes en français, en minuscules.'},
        {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + data}}]}], 128,
        expected={'code': 'VISION 47', 'rouge': 'cercle', 'bleu': 'carré'})
    write(RUN / STATE['arm'] / 'vision-verification.json', {'passed': True, 'content': response['choices'][0]['message']['content']})

    docs = {}
    for label, subject in [('A', 'imprimerie'), ('B', 'navigation'), ('C', 'botanique')]:
        lines = [f'Dossier {label}, rubrique {subject}, fiche {i:04d}. Cette fiche décrit une observation indépendante, '
                 f'sa date de collecte et sa méthode de classement. Les données sont conservées pour comparaison '
                 f'entre les équipes, avec un identifiant stable et une note explicative pour chaque observation.' for i in range(35)]
        docs[label] = [{'role': 'system', 'content': f'Tu lis le dossier expérimental {label}. Réponds très brièvement en français.'},
                       {'role': 'user', 'content': '\n'.join(lines) + '\nRéponds uniquement : dossier reçu.'}]
    a = call(port, 'cache-A', docs['A'], 32, cache=True)['choices'][0]['message']['content']
    cont = docs['A'] + [{'role': 'assistant', 'content': a}, {'role': 'user', 'content': 'Quel est le sujet du dossier ? Réponds en trois mots au maximum.'}]
    ref = call(port, 'cache-A-reference', cont, 32, cache=True)['choices'][0]['message']['content']
    for label in ('B', 'C'):
        call(port, 'cache-' + label, docs[label], 32, cache=True)
    restored = call(port, 'cache-A-restaure', cont, 32, cache=True)['choices'][0]['message']['content']
    metrics = get(port, '/metrics')
    write(RUN / STATE['arm'] / 'cache-verification.json', {'reference': ref, 'restored': restored,
          'same_content': ref == restored, 'metrics': metrics})
    last = read(RUN / STATE['arm'] / 'results.json')[-1]
    ratio = last['timings'].get('cache_n', 0) / max(last['usage'].get('prompt_tokens', 0), 1)
    assert ref == restored and metrics['conversation_cache']['restores'] >= 1 and ratio > .9, ratio


def baseline():
    if (RUN / 'avant.json').exists():
        raise RuntimeError('Reference deja tentee ; ne pas ecraser les preuves')
    RUN.mkdir(parents=True, exist_ok=True)
    pointer = read(ROOT / 'lanceur/session.json')
    cfg_path = Path(pointer['directory']) / 'strata.json'
    cfg = read(cfg_path)
    assert get(8080, '/health')['loaded']
    assert '0.1.43.1' in cfg['exe']
    write(RUN / 'avant.json', {'fingerprints': fingerprints(), 'config_path': str(cfg_path), 'configuration': cfg,
          'settings': read(ROOT / 'lanceur/reglages.json'), 'console': read(ROOT / 'lanceur/interface.pid.json'),
          'session': pointer, 'metrics': get(8080, '/metrics'), 'old_binary_sha256': digest(cfg['exe'])})
    state(arm='reference-0.1.43.1', phase='preparation')
    worker = threading.Thread(target=observer, daemon=True)
    worker.start()
    try:
        benchmark(8080)
        state(phase='reference-terminee')
    except Exception as error:
        state(phase='reference-incomplete', error=str(error))
        raise
    finally:
        DONE.set()
        worker.join(15)


def compare(retry=False):
    prior = read(RUN / 'avant.json')
    assert read(RUN / 'etat.json')['phase'] in (('reprise-production', 'production-retablie', 'essai-incomplet') if retry else ('reference-terminee',))
    assert fingerprints() == prior['fingerprints'], 'Configuration modifiee depuis la reference'
    if not retry:
        assert not (RUN / 'arret-production.json').exists(), 'Essai deja tente'
    prepared = read(HERE / 'engine-prepared.json')
    assert digest(prepared['exe']) == prepared['exe_sha256']
    state(arm='nouveau-0.1.45.3', phase='preparation')
    worker = threading.Thread(target=observer, daemon=True)
    worker.start()
    stopped = False
    error = None
    try:
        try:
            metrics = get(8080, '/metrics')
        except OSError:
            if not retry:
                raise
            pointer = read(ROOT / 'lanceur/session.json')
            current_dir = Path(pointer['directory'])
            assert read(current_dir / 'state.json')['status'] == 'chargement'
            assert read(current_dir / 'strata.json')['exe'] == prior['configuration']['exe']
            metrics = {'retry_during_managed_recovery_load': True}
        write(RUN / 'metrics-avant-arret.json', metrics)
        # Refuse to interrupt an active user request.
        if metrics.get('live', {}).get('state') not in ('idle', None) or metrics.get('live', {}).get('queued', 0):
            raise RuntimeError('Requete utilisateur active avant arret')
        state(phase='arret-production')
        stopped = True
        write(RUN / 'arret-production.json', control('/api/stop', {}))
        end = time.monotonic() + 120
        while any(r['vram_mib'] > 1024 for r in gpu()):
            if time.monotonic() > end:
                raise RuntimeError('VRAM P100 non liberee')
            time.sleep(2)
        cfg = copy.deepcopy(prior['configuration'])
        cfg['exe'] = prepared['exe']
        cfg['lib_dirs'] = prepared['lib_dirs']
        cfg['port'] = 8081
        cfg['log'] = str(RUN / 'nouveau-engine.log')
        cfg['env']['STRATA_P100_DIAGNOSTIC_SYNC_FILE'] = str(RUN / 'cuda-validation.flag')
        write(RUN / 'nouveau.json', cfg)
        run_dir = RUN / 'test-sessions' / ('nouveau-reprise' if retry else 'nouveau')
        run_dir.mkdir(parents=True)
        command = [str(PY), '-u', str(ROOT / 'lanceur/runtime.py'), '--config', str(RUN / 'nouveau.json'),
                   '--run-dir', str(run_dir), '--floor', '6']
        with (RUN / 'nouveau-supervisor.log').open('wb') as log:
            process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                                       creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
        write(RUN / 'test-process.json', {'pid': process.pid, 'created': psutil.Process(process.pid).create_time(), 'command': command})
        state(phase='chargement-nouveau', test_supervisor_pid=process.pid)
        wait_ready(8081, run_dir)
        write(RUN / 'nouveau-health.json', get(8081, '/health'))
        benchmark(8081)
        functional(8081)
        state(phase='nouveau-teste')
    except BaseException as exc:
        error = str(exc)
        state(phase='essai-incomplet', error=error)
    finally:
        if stopped:
            stop_test()
            state(phase='reprise-production')
            assert fingerprints() == prior['fingerprints'], 'Configuration persistante changee'
            write(RUN / 'reprise-demarrage.json', control('/api/start', prior['settings']))
            pointer = read(ROOT / 'lanceur/session.json')
            prod_dir = Path(pointer['directory'])
            wait_ready(8080, prod_dir)
            state(phase='verification-reprise')
            response = call(8080, 'reprise-calcul', [{'role': 'user', 'content': 'Réponds uniquement avec un objet JSON contenant la clé resultat et le résultat de 43 multiplié par 7.'}], 64, {'resultat': 301})
            after = fingerprints()
            # Last-valid is serialized by the supervisor; compare its content too.
            differences = [name for name in prior['fingerprints'] if after[name] != prior['fingerprints'][name]]
            assert not differences, differences
            assert read(ROOT / 'lanceur/interface.pid.json') == prior['console']
            restored_cfg = read(prod_dir / 'strata.json')
            assert restored_cfg['exe'] == prior['configuration']['exe']
            write(RUN / 'production-retablie.json', {'health': get(8080, '/health'), 'metrics': get(8080, '/metrics'),
                  'fingerprints_identical': True, 'console_identical': True, 'old_engine_restored': True,
                  'session': str(prod_dir), 'calculation': response['choices'][0]['message']['content'], 'test_error': error})
            state(phase='production-retablie', test_error=error)
        DONE.set()
        worker.join(15)
    if error:
        raise RuntimeError(error)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['baseline', 'stabilize', 'compare', 'retry'])
    args = parser.parse_args()
    if args.mode == 'baseline':
        baseline()
    elif args.mode == 'stabilize':
        assert read(RUN / 'etat.json')['phase'] == 'reference-terminee'
        state(arm='reference-0.1.43.1', phase='stabilisation')
        worker = threading.Thread(target=observer, daemon=True)
        worker.start()
        try:
            for rep in (4, 5):
                for name, prompt in [
                    ('ciel', 'Explique en français pourquoi le ciel est bleu, puis pourquoi il devient rouge au coucher du soleil. Donne une explication précise et accessible.'),
                    ('fibonacci-code', 'Écris une fonction Python fibonacci(n) qui retourne les n premiers nombres de Fibonacci, puis donne un exemple pour n=8. Réponds en français.')]:
                    label = f'r{rep}-{name}'
                    call(8080, label, [{'role': 'user', 'content': f'Mesure indépendante {label}.\n' + prompt}])
            state(phase='reference-terminee')
        finally:
            DONE.set()
            worker.join(15)
    else:
        compare(retry=args.mode == 'retry')
