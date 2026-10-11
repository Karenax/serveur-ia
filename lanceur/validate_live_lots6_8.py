"""Deploy the authorized lots 6/8 locally and retain evidence without secret values."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
HOME = ROOT / 'lanceur'
EVIDENCE = ROOT / 'preuves/lots-6-8'
sys.path.insert(0, str(HOME))
import psutil

BASE = 'http://127.0.0.1:8765'
REPORT = EVIDENCE / 'production-validation.json'
PHRASE = HOME / 'sauvegardes/phrase-recuperation.txt'
VERSION = '3.5.18'
STAGED = ROOT / 'toolchain/releases-staging/windows-3.5.18'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        return json.load(response)


def post(path, data):
    with urllib.request.urlopen(BASE, timeout=5) as response:
        html = response.read().decode('utf-8')
    token = re.search(r'name="launcher-token" content="([^"]+)"', html).group(1)
    request = urllib.request.Request(BASE + path, json.dumps(data).encode(),
        {'Content-Type': 'application/json', 'Origin': BASE, 'X-Launcher-Token': token})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def preserved_files():
    names = ('acces-distants.json', 'wireguard.json', 'reglages.json',
             'wireguard-prive/secrets.dpapi', 'wireguard-prive/signature.dpapi')
    return {name: digest(HOME / name) for name in names if (HOME / name).exists()}


def models():
    result = []
    for process in psutil.process_iter(['pid', 'create_time', 'cmdline']):
        try:
            command = process.info['cmdline'] or []
            if '-m' in command and 'serve.server' in command:
                result.append({'pid': process.pid, 'created': process.info['create_time']})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return sorted(result, key=lambda item: item['pid'])


def content_fingerprints():
    """Hash logical user rows, ignoring additive indexes and runtime worker leases."""
    path = HOME / 'espaces-prives/espaces.sqlite3'
    result = {}
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=20) as db:
        for table in ('client_histories', 'projects', 'documents', 'memories',
                      'conversations', 'policies', 'jobs'):
            rows = db.execute('SELECT * FROM ' + table + ' ORDER BY 1').fetchall()
            converted = [[value.hex() if isinstance(value, bytes) else value for value in row] for row in rows]
            encoded = json.dumps(converted, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            result[table] = {'count': len(rows), 'sha256': hashlib.sha256(encoded).hexdigest()}
    return result


def backup_config(value):
    config = value['config']
    return {key: config[key] for key in ('enabled', 'time', 'frequency', 'weekday',
        'destination', 'secondary_destination', 'retention', 'secret_configured')}


def save(report):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def assert_preserved(report, check_backup=True):
    before = report['before']
    assert before['model_processes'] == models(), 'Loaded model process changed'
    assert before['preserved_file_sha256'] == preserved_files(), 'Existing access/settings changed'
    assert before['user_data'] == content_fingerprints(), 'Existing user rows changed'
    if check_backup:
        assert before['automatic_backups'] == backup_config(get('/api/backups')), 'Backup configuration changed'


def prepare():
    assert get('/health')['service'] == 'qwen-launcher'
    assert PHRASE.is_file(), 'Existing recovery phrase required'
    phrase = PHRASE.read_text(encoding='utf-8')
    assert len(phrase) >= 20
    before = {'model_processes': models(), 'preserved_file_sha256': preserved_files(),
        'user_data': content_fingerprints(), 'automatic_backups': backup_config(get('/api/backups'))}
    assert before['model_processes'], 'Expected model is not running'
    initial = post('/api/backup', {'password': phrase})
    archive = Path(initial['file'])
    report = {'prepared_at': time.strftime('%Y-%m-%d %H:%M:%S %z'), 'before': before,
        'pre_rollout_backup': {'file': str(archive), 'bytes': archive.stat().st_size, 'sha256': digest(archive)},
        'contains_secret_values': False}
    save(report)
    assert_preserved(report)
    print(json.dumps({'prepared': True, 'backup_bytes': archive.stat().st_size,
        'model_pids': [item['pid'] for item in before['model_processes']]}))


def promote():
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    assert_preserved(report, check_backup=False)
    built = json.loads((EVIDENCE / 'windows-release.json').read_text(encoding='utf-8'))
    staged = STAGED / 'Accès serveur Fred.exe'
    assert built['version'] == VERSION and built['self_test'] == 'PASS'
    assert digest(staged) == built['sha256']
    previous = ROOT / 'toolchain/releases-staging/windows-before-lots6-8'
    previous.mkdir(parents=True, exist_ok=True)
    directory = ROOT / 'client-qwen/dist'
    for name in (staged.name, 'release.json'):
        current = directory / name
        saved = previous / name
        if current.exists() and not saved.exists():
            shutil.copyfile(current, saved)
    # The operator stops only the verified console and its WireGuard child first.
    engine = ROOT / 'client-qwen/wireguard-bridge.exe'
    if not (previous / engine.name).exists():
        shutil.copyfile(engine, previous / engine.name)
    shutil.copyfile(STAGED / engine.name, engine)
    temporary = directory / 'lots6-8-release.tmp'
    shutil.copyfile(staged, temporary)
    temporary.replace(directory / staged.name)
    import releases
    release = releases.manifest(HOME)
    assert releases.status(HOME)['verified']
    report['windows_release'] = {'version': release['version'], 'sha256': release['sha256'],
        'bytes': release['bytes'], 'signature_verified': True, 'self_test': 'PASS',
        'wireguard_sha256': digest(engine)}
    save(report)
    print(json.dumps(report['windows_release']))


def activate():
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    assert get('/health')['service'] == 'qwen-launcher'
    assert_preserved(report)
    state = get('/api/state')
    assert state['running'] and state['health']['loaded']
    released = get('/api/releases')
    assert released['verified'] and released['server_version'] == VERSION
    maintenance = get('/api/maintenance')
    assert not maintenance.get('active', False)
    notifications = get('/api/notifications')
    assert notifications['delivery']['mode'] == 'connected' and notifications['delivery']['push'] is False
    prepared = post('/api/releases/prepare', {})
    phrase = PHRASE.read_text(encoding='utf-8')
    post('/api/backups/create', {'password': phrase})
    for _ in range(120):
        current = get('/api/backups')
        if current['job']['state'] != 'running':
            break
        time.sleep(0.5)
    assert current['job']['state'] == 'succeeded', 'Backup creation failed'
    archive = next(record for record in current['catalog'] if record['verified'] and record['version'] == 2)
    verified = post('/api/backups/verify', {'file': archive['file'], 'password': phrase})
    assert verified['summary']['sha256'] == archive['sha256']
    assert 'document_sources' in verified['summary']['counts']
    assert 'notifications' in verified['summary']['counts']
    assert_preserved(report)
    report.update({'activated_at': time.strftime('%Y-%m-%d %H:%M:%S %z'), 'result': 'PASS',
        'automatic_backups': {**backup_config(current), 'next_run': current['next_run']},
        'initial_verified_backup': {key: archive[key] for key in ('file', 'size', 'sha256', 'created_at', 'version', 'verified')},
        'included_counts': verified['summary']['counts'],
        'notifications': {'item_count': len(notifications['items']), 'delivery': notifications['delivery'],
            'preferences_revision': notifications['preferences']['revision'], 'retention': notifications['retention']},
        'after': {'model_processes': models(), 'preserved_file_sha256': preserved_files(),
            'user_data': content_fingerprints(), 'model_running': state['running'], 'model_health': state['health'],
            'maintenance': maintenance}, 'personal_clients_updated': prepared['count'],
        'restoration_on_production': 'not performed; validated on isolated fixtures'})
    save(report)
    print(json.dumps({'result': 'PASS', 'server_version': VERSION, 'next_run': current['next_run'],
        'verified_backup_bytes': archive['size'], 'model_pids': [item['pid'] for item in models()]}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'promote', 'activate'])
    {'prepare': prepare, 'promote': promote, 'activate': activate}[parser.parse_args().action]()
