"""Run the complete isolated regression suite and retain sanitized evidence."""
import datetime
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
PROOFS = ROOT / 'preuves/lots-6-8'
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

SOURCES.extend([
    'lanceur/notifications.py', 'lanceur/web/notifications.js', 'lanceur/web/notifications.css',
    'client-qwen/workspace.html', 'client-qwen/ui.js', 'client-qwen/ui.css',
    'client-qwen/updater.py', 'client-qwen/Build-Client.ps1', 'client-qwen/product-version.txt',
    'client-android/app/build.gradle', 'client-android/app/src/main/AndroidManifest.xml',
    'client-android/Build-Android.ps1', 'client-android/scripts/Prepare-Assets.py',
])
SOURCES.extend(path.relative_to(ROOT).as_posix() for path in sorted((ROOT/'client-android/app/src/main/java').rglob('*.java')))
SOURCES = list(dict.fromkeys(SOURCES))
SOURCES.extend(path.relative_to(ROOT).as_posix() for path in sorted((ROOT/'client-android/mobile-ui').glob('*')) if path.is_file())
NETWORK_MODULES = {'test_accounts_updates', 'test_remote', 'test_restoration_clients', 'test_wireguard_stable'}



def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def flatten(suite):
    import unittest
    for value in suite:
        if isinstance(value, unittest.TestSuite):
            yield from flatten(value)
        else:
            yield value


def worker(group):
    import unittest
    suite = unittest.defaultTestLoader.discover(str(ROOT/'lanceur'), pattern='test_*.py')
    selected = [case for case in flatten(suite)
                if (case.__class__.__module__ in NETWORK_MODULES) == (group == 'network')]
    if not selected:
        raise RuntimeError('Empty regression partition')
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(selected))
    return 0 if result.wasSuccessful() else 1


def run_group(group):
    log = PROOFS / ('regressions-' + group + '.log')
    started = time.monotonic()
    with log.open('w', encoding='utf-8') as stream:
        completed = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--group', group],
            cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    output = log.read_text(encoding='utf-8')
    count = re.search(r'Ran (\d+) tests? in ([\d.]+)s', output)
    return {'group': group, 'exit_code': completed.returncode,
            'test_count': int(count[1]) if count else None,
            'elapsed_seconds': round(time.monotonic()-started, 3), 'log': log.name}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--group', choices=['network', 'data'])
    arguments = parser.parse_args()
    if arguments.group:
        raise SystemExit(worker(arguments.group))
    PROOFS.mkdir(parents=True, exist_ok=True)
    before = hashes()
    test_paths = sorted((ROOT/'lanceur').glob('test_*.py'))
    tests_before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in test_paths}
    started = time.monotonic()
    log = PROOFS / 'regressions-final.log'
    # Each partition runs in its own interpreter and disposable fixtures.
    # No process-local monkeypatch, port or storage is shared between groups.
    with ThreadPoolExecutor(max_workers=2) as pool:
        groups = list(pool.map(run_group, ('network', 'data')))
    with log.open('w', encoding='utf-8') as stream:
        for group in groups:
            stream.write('Regression partition: '+group['group']+'\n')
            stream.write((PROOFS/group['log']).read_text(encoding='utf-8'))
            stream.write('\n')
    elapsed = round(time.monotonic() - started, 3)
    tests_after = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((ROOT/'lanceur').glob('test_*.py'))}
    unchanged = before == hashes() and tests_before == tests_after
    exit_code = max(group['exit_code'] for group in groups)
    count = sum(group['test_count'] for group in groups) if all(group['test_count'] is not None for group in groups) else None
    result = {'created_at': datetime.datetime.now().astimezone().isoformat(),
        'result': 'PASS' if exit_code == 0 and unchanged and count else 'FAIL',
        'exit_code': exit_code, 'test_count': count, 'parallel_workers': 2, 'groups': groups,
        'elapsed_seconds': elapsed, 'sources_unchanged_during_run': unchanged,
        'source_sha256': before, 'test_source_sha256': tests_before, 'log': log.name}
    (PROOFS / 'regressions-final.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('result', 'test_count', 'elapsed_seconds', 'sources_unchanged_during_run')}))
    raise SystemExit(exit_code if unchanged else 2)
