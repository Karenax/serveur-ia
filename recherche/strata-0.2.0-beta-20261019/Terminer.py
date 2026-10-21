"""Matched short series without thermal cutoffs; functional probes; restore old engine."""
from pathlib import Path
import subprocess
import threading
import time
import socket

import psutil
import Campagne as c


def observe_without_cooling():
    c.HOT.clear()
    return c.gpu()


def stop_previous_controller():
    found = []
    for process in psutil.process_iter(['pid', 'cmdline', 'create_time']):
        try:
            cmd = process.info['cmdline'] or []
            args = [part for part in cmd if Path(part).name == 'Continuer.py']
            if args and (Path(process.cwd()) / args[0]).resolve() == c.HERE / 'Continuer.py':
                found.append({'pid': process.pid, 'created': process.create_time()})
        except psutil.Error:
            pass
    c.write(c.RUN / 'reprise-sans-seuil.json', {'user_instruction': 'Continue tests; reaching 80 C is acceptable as on the old engine.',
            'stopped_previous_controllers': found})
    for identity in found:
        try:
            process = psutil.Process(identity['pid'])
            assert abs(process.create_time() - identity['created']) < .01
            process.terminate()
            process.wait(15)
        except psutil.NoSuchProcess:
            pass


def series(port):
    rows = [f'Ligne {i:04d}: le dossier décrit un jardin, des arbres et un chemin de pierre.' for i in range(1024)]
    rows.insert(512, 'Information prioritaire : le code secret du dossier est LUMIERE-7429.')
    prompt = 'Lis le dossier suivant.\n' + '\n'.join(rows) + '\nRéponds uniquement avec un objet JSON contenant la clé code et le code secret indiqué au milieu du dossier.'
    c.call(port, 'chauffe-document', [{'role': 'user', 'content': 'Mesure indépendante chauffe-document.\n' + prompt}], 80, {'code': 'LUMIERE-7429'})
    for rep in (1, 2, 3):
        for name, prompt in [
            ('ciel', 'Explique en français pourquoi le ciel est bleu, puis pourquoi il devient rouge au coucher du soleil. Donne une explication précise et accessible.'),
            ('fibonacci-code', 'Écris une fonction Python fibonacci(n) qui retourne les n premiers nombres de Fibonacci, puis donne un exemple pour n=8. Réponds en français.')]:
            label = f'serie-r{rep}-{name}'
            c.call(port, label, [{'role': 'user', 'content': f'Mesure indépendante {label}.\n' + prompt}])
    c.write(c.RUN / c.STATE['arm'] / 'metrics-apres-serie.json', c.get(port, '/metrics'))


def main():
    prior = c.read(c.RUN / 'avant.json')
    assert c.fingerprints() == prior['fingerprints']
    stop_previous_controller()
    c.cool = observe_without_cooling
    error = None
    stopped = False
    monitor = None
    try:
        c.state(arm='reference-sans-seuil', phase='attente-reference', temperature_cutoff=None, cooling_between_requests=False)
        monitor = threading.Thread(target=c.observer, daemon=True)
        monitor.start()
        pointer = c.read(c.ROOT / 'lanceur/session.json')
        c.wait_ready(8080, Path(pointer['directory']))
        assert c.get(8080, '/metrics').get('live', {}).get('state') in ('idle', None)
        series(8080)
        c.DONE.set()
        monitor.join(15)
        monitor = None
        stopped = True
        c.state(phase='arret-reference')
        c.write(c.RUN / 'arret-reference-sans-seuil.json', c.control('/api/stop', {}))
        deadline = time.monotonic() + 120
        while any(r['vram_mib'] > 1024 for r in c.gpu()):
            if time.monotonic() > deadline:
                raise RuntimeError('P100 VRAM not released')
            time.sleep(2)
        c.DONE.clear()
        c.state(arm='nouveau-sans-seuil', phase='chargement-nouveau', temperature_cutoff=None, cooling_between_requests=False)
        monitor = threading.Thread(target=c.observer, daemon=True)
        monitor.start()
        run_dir = c.RUN / 'test-sessions' / 'nouveau-sans-seuil'
        run_dir.mkdir(parents=True, exist_ok=False)
        cfg_path = c.RUN / 'nouveau.json'
        command = [str(c.PY), '-u', str(c.ROOT / 'lanceur/runtime.py'), '--config', str(cfg_path),
                   '--run-dir', str(run_dir), '--floor', '6']
        with (c.RUN / 'supervisor-sans-seuil.log').open('wb') as log:
            process = subprocess.Popen(command, cwd=c.ROOT, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                                       creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
        c.write(c.RUN / 'test-process-sans-seuil.json', {'pid': process.pid, 'created': psutil.Process(process.pid).create_time(), 'command': command})
        c.write(c.RUN / 'test-process.json', c.read(c.RUN / 'test-process-sans-seuil.json'))
        c.wait_ready(8081, run_dir)
        series(8081)
        c.functional(8081)
        c.state(phase='nouveau-teste-sans-seuil')
    except BaseException as exc:
        error = str(exc)
        c.state(phase='essai-incomplet', error=error)
    finally:
        try:
            if stopped:
                c.stop_test()
                c.state(phase='reprise-production')
                assert c.fingerprints() == prior['fingerprints']
                c.write(c.RUN / 'demarrage-production-final.json', c.control('/api/start', prior['settings']))
                pointer = c.read(c.ROOT / 'lanceur/session.json')
                prod_dir = Path(pointer['directory'])
                c.wait_ready(8080, prod_dir)
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
                        'test_port_closed': True, 'temperature_cutoff': None})
                c.state(phase='production-retablie', test_error=error)
        finally:
            c.DONE.set()
            if monitor:
                monitor.join(15)
    if error:
        raise RuntimeError(error)


if __name__ == '__main__':
    main()
