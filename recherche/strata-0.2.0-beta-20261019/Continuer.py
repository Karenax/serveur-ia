"""Resume the isolated test with matched post-document decode probes, then restore."""
import json
from pathlib import Path
import socket
import threading
import time

import psutil

import Campagne as c


def stop_controller():
    script = c.HERE / 'Campagne.py'
    found = []
    for process in psutil.process_iter(['pid', 'cmdline', 'create_time']):
        try:
            cmd = process.info['cmdline'] or []
            if not cmd or cmd[-1] != 'retry':
                continue
            candidates = [part for part in cmd if Path(part).name == 'Campagne.py']
            if not candidates:
                continue
            assert (Path(process.cwd()) / candidates[0]).resolve() == script
            found.append({'pid': process.pid, 'created': process.create_time(), 'cmd': cmd})
        except psutil.NoSuchProcess:
            pass
    assert found, 'No isolated campaign controller to resume'
    c.write(c.RUN / 'continuation-controller.json', {'stopped_controllers': found,
            'reason': 'Match the reference decode sequence: repetition 3, documents, repetitions 4 and 5.'})
    for identity in found:
        try:
            process = psutil.Process(identity['pid'])
            assert abs(process.create_time() - identity['created']) < .01
            process.terminate()
            process.wait(15)
        except psutil.NoSuchProcess:
            pass


def main():
    prior = c.read(c.RUN / 'avant.json')
    assert c.fingerprints() == prior['fingerprints']
    identity = c.read(c.RUN / 'test-process.json')
    process = psutil.Process(identity['pid'])
    assert abs(process.create_time() - identity['created']) < .01
    assert str(c.RUN / 'nouveau.json') in process.cmdline()
    assert c.get(8081, '/health')['loaded']
    stop_controller()
    c.state(arm='nouveau-0.1.45.3', phase='continuation-isolee')
    monitor = threading.Thread(target=c.observer, daemon=True)
    monitor.start()
    error = None
    try:
        end = time.monotonic() + 900
        while c.get(8081, '/metrics').get('live', {}).get('state') not in ('idle', None):
            if time.monotonic() > end:
                raise RuntimeError('Previous test request did not complete')
            time.sleep(2)
        for lines in (64, 256, 1024):
            rows = [f'Ligne {i:04d}: le dossier décrit un jardin, des arbres et un chemin de pierre.' for i in range(lines)]
            rows.insert(lines // 2, 'Information prioritaire : le code secret du dossier est LUMIERE-7429.')
            prompt = 'Lis le dossier suivant.\n' + '\n'.join(rows) + '\nRéponds uniquement avec un objet JSON contenant la clé code et le code secret indiqué au milieu du dossier.'
            for rep in (1, 2):
                label = f'dossier-{lines}-r{rep}'
                records = c.read(c.RUN / c.STATE['arm'] / 'results.json')
                if any(r['name'] == label and r['thermally_valid'] and r['quality_pass'] for r in records):
                    continue
                c.call(8081, label, [{'role': 'user', 'content': f'Mesure indépendante {label}.\n' + prompt}], 80, {'code': 'LUMIERE-7429'})
        c.write(c.RUN / c.STATE['arm'] / 'metrics-apres-debit.json', c.get(8081, '/metrics'))
        for rep in (4, 5):
            for name, prompt in [
                ('ciel', 'Explique en français pourquoi le ciel est bleu, puis pourquoi il devient rouge au coucher du soleil. Donne une explication précise et accessible.'),
                ('fibonacci-code', 'Écris une fonction Python fibonacci(n) qui retourne les n premiers nombres de Fibonacci, puis donne un exemple pour n=8. Réponds en français.')]:
                prefix = f'r{rep}-{name}'
                c.call(8081, 'post-doc-' + prefix,
                       [{'role': 'user', 'content': f'Mesure indépendante {prefix}.\n' + prompt}])
        c.functional(8081)
        c.state(phase='nouveau-teste')
    except BaseException as exc:
        error = str(exc)
        c.state(phase='essai-incomplet', error=error)
    finally:
        try:
            c.stop_test()
            c.state(phase='reprise-production')
            assert c.fingerprints() == prior['fingerprints']
            c.write(c.RUN / 'reprise-demarrage-finale.json', c.control('/api/start', prior['settings']))
            pointer = c.read(c.ROOT / 'lanceur/session.json')
            prod_dir = Path(pointer['directory'])
            c.wait_ready(8080, prod_dir)
            c.state(phase='verification-reprise')
            response = c.call(8080, 'reprise-calcul', [{'role': 'user', 'content': 'Réponds uniquement avec un objet JSON contenant la clé resultat et le résultat de 43 multiplié par 7.'}], 64, {'resultat': 301})
            assert c.fingerprints() == prior['fingerprints']
            assert c.read(c.ROOT / 'lanceur/interface.pid.json') == prior['console']
            cfg = c.read(prod_dir / 'strata.json')
            assert cfg['exe'] == prior['configuration']['exe'] and c.digest(cfg['exe']) == prior['old_binary_sha256']
            with socket.socket() as probe:
                assert probe.connect_ex(('127.0.0.1', 8081)) != 0
            c.write(c.RUN / 'production-retablie.json', {'health': c.get(8080, '/health'), 'metrics': c.get(8080, '/metrics'),
                    'fingerprints_identical': True, 'console_identical': True, 'old_engine_restored': True,
                    'session': str(prod_dir), 'calculation': response['choices'][0]['message']['content'], 'test_error': error,
                    'test_port_closed': True})
            c.state(phase='production-retablie', test_error=error)
        finally:
            c.DONE.set()
            monitor.join(15)
    if error:
        raise RuntimeError(error)


if __name__ == '__main__':
    main()
