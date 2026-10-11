"""Run the complete isolated regression suite and retain sanitized evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
PROOFS = ROOT / 'preuves/lots-0-4'
SOURCES = [
    'lanceur/app.py', 'lanceur/operations.py', 'lanceur/backups.py',
    'lanceur/restoration.py', 'lanceur/server_state.py', 'lanceur/workspace.py',
    'lanceur/remote.py', 'lanceur/devices.py', 'lanceur/wireguard_access.py',
    'lanceur/profiles.py', 'lanceur/releases.py', 'client-qwen/client.py',
    'client-qwen/history_sync.py', 'client-qwen/chat.html',
    'lanceur/recovery_signing.py', 'client-qwen/wireguard-bridge/main.go',
    'lanceur/web/maintenance.js', 'lanceur/web/maintenance.css',
    'lanceur/web/index.html', 'lanceur/web/app.js', 'lanceur/web/interface.js',
    'lanceur/web/workspace.js',
    'client-android/app/src/main/java/net/karenax/fred/HistorySync.java',
    'client-android/app/src/main/java/net/karenax/fred/Remote.java',
    'client-android/app/src/main/java/net/karenax/fred/ClientBackend.java',
]


def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


if __name__ == '__main__':
    PROOFS.mkdir(parents=True, exist_ok=True)
    before = hashes()
    started = time.monotonic()
    log = PROOFS / 'regressions-final.log'
    with log.open('w', encoding='utf-8') as stream:
        completed = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'lanceur', '-p', 'test_*.py', '-v'],
            cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    elapsed = round(time.monotonic() - started, 3)
    output = log.read_text(encoding='utf-8')
    count = re.search(r'Ran (\d+) tests? in ([\d.]+)s', output)
    unchanged = before == hashes()
    result = {'created_at': datetime.datetime.now().astimezone().isoformat(),
        'result': 'PASS' if completed.returncode == 0 and unchanged else 'FAIL',
        'exit_code': completed.returncode, 'test_count': int(count[1]) if count else None,
        'elapsed_seconds': elapsed, 'sources_unchanged_during_run': unchanged,
        'source_sha256': before, 'log': log.name}
    (PROOFS / 'regressions-final.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('result', 'test_count', 'elapsed_seconds', 'sources_unchanged_during_run')}))
    raise SystemExit(completed.returncode if unchanged else 2)
