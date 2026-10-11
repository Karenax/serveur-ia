"""Record hashes and process identities without copying protected contents."""
import hashlib
import json
import sys
from pathlib import Path
import psutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
paths = ['client-android/dist/Acces-serveur-Fred-Android.apk', 'client-qwen/dist/Accès serveur Fred.exe',
         'lanceur/acces-distants.json', 'lanceur/wireguard.json', 'lanceur/reglages.json',
         'lanceur/wireguard-prive/secrets.dpapi', 'lanceur/wireguard-prive/signature.dpapi']
def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
value = {'files': {p: digest(ROOT / p) for p in paths},
         'models': [{'pid': pid, 'created': psutil.Process(pid).create_time()} for pid in (8200, 14628)]}
name = 'after' if '--after' in sys.argv else 'before'
if name == 'after':
    before = json.loads((OUT / 'before.json').read_text(encoding='utf-8'))
    checks = {p: value['files'][p] == h for p, h in before['files'].items() if p != paths[1]}
    checks['model_processes'] = before['models'] == value['models']
    value['preserved'] = checks
    assert all(checks.values()), checks
(OUT / (name + '.json')).write_text(json.dumps(value, indent=2), encoding='utf-8')
print(name, 'recorded; protected values omitted')
