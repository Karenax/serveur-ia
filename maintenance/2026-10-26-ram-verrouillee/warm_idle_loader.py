"""One-off sequential pre-read with the exact loading engine paused, then resumed."""
import json
from pathlib import Path
import subprocess
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def main():
    session = json.loads((ROOT / 'lanceur/session.json').read_text())
    directory = Path(session['directory'])
    state = json.loads((directory / 'state.json').read_text())
    cfg = json.loads((directory / 'strata.json').read_text())
    if state['status'] != 'chargement':
        raise RuntimeError('Prélecture réservée au chargement initial, avant tout calcul.')
    server = psutil.Process(state['server']['pid'])
    if abs(server.create_time() - state['server']['created']) >= .01:
        raise RuntimeError('Identité du serveur modifiée.')
    engines = [p for p in server.children(recursive=True)
               if Path(p.exe()).resolve() == Path(cfg['exe']).resolve() and '--serve' in p.cmdline()]
    if len(engines) != 1:
        raise RuntimeError('Un seul moteur du chargement courant est attendu.')
    engine = engines[0]
    created = engine.create_time()
    record = {'pid': engine.pid, 'created': created, 'session': str(directory), 'started': time.time()}
    engine.suspend()
    try:
        print(json.dumps({'status': 'prelecture_sequentielle', 'pid': engine.pid}), flush=True)
        result = subprocess.run([sys.executable, str(OUT / 'Prelire-Experts.py')], cwd=ROOT,
                                creationflags=subprocess.CREATE_NO_WINDOW, timeout=1200)
        record['reader_exit_code'] = result.returncode
    finally:
        if engine.is_running() and abs(engine.create_time() - created) < .01:
            engine.resume()
            record['resumed'] = True
        record['seconds'] = round(time.time() - record['started'], 1)
        (OUT / 'prelecture-chargeur.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
        print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
