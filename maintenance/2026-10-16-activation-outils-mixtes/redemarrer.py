"""Restart only the managed Strata service, preserving the console and settings."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('launcher_api',
    ROOT / 'maintenance/2026-10-16-diagnostic-opencode/activer_cache.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)

def fingerprints():
    names = ['lanceur/base-strata.json', 'strata-iq4-p100-hybride.json', 'lanceur/reglages.json',
             'lanceur/reglages-par-defaut.json', 'lanceur/exploitation.json', 'lanceur/hermes-models.json',
             'lanceur/acces-distants.json', 'lanceur/wireguard.json']
    return {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in names if (ROOT / n).exists()}

def main():
    if (OUT / 'avant.json').exists():
        raise RuntimeError('Restart already attempted; inspect saved evidence before retrying')
    source = json.loads((ROOT / 'maintenance/2026-10-16-outils-mixtes/source.json').read_text())
    assert hashlib.sha256(Path(source['source']).read_bytes()).hexdigest() == source['sha256_after']
    settings = api.validate(api.read_json(ROOT / 'lanceur/reglages.json'), check_paths=True)
    before = {'fingerprints': fingerprints(), 'console': api.read_json(ROOT / 'lanceur/interface.pid.json'),
              'session': api.read_json(ROOT / 'lanceur/session.json'),
              'metrics': api.get('http://127.0.0.1:8080/metrics'), 'parser_sha256': source['sha256_after']}
    assert before['metrics']['engine']['conversation_cache_slots'] == 20
    assert before['metrics']['engine']['conversation_cache_mib'] == 30720
    api.write_json(OUT / 'avant.json', before)
    print('Stopping only Strata through the console...', flush=True)
    api.write_json(OUT / 'arret.json', api.post('/api/stop', {}))
    print('Read-only sequential warming of expert files...', flush=True)
    reader = OUT / 'prelire.py'
    assert reader.is_file()
    result = subprocess.run([sys.executable, '-u', str(reader)], cwd=ROOT,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    print('Warming exit code: ' + str(result.returncode), flush=True)
    print('Starting Strata with the existing settings...', flush=True)
    result = api.post('/api/start', settings)
    api.write_json(OUT / 'demarrage.json', result)
    assert api.read_json(ROOT / 'lanceur/interface.pid.json') == before['console']
    assert fingerprints() == before['fingerprints'], 'Persistent settings changed unexpectedly'
    print(json.dumps(result), flush=True)

if __name__ == '__main__':
    main()
