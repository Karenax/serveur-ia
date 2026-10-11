"""Safe local rollout evidence: per-client row digests and preserved live service."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from client_storage import TABLES, checksum
from validate_live_lots6_8 import get, post, models, preserved_files, content_fingerprints, backup_config, HOME
from validate_live_eg2 import verified_backup

REPORT = HOME.parent / 'preuves/dossiers-clients-20261011/production-validation.json'


def save(report):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def row_digest(rows):
    safe = [[v.hex() if isinstance(v, bytes) else v for v in row] for row in rows]
    return hashlib.sha256(json.dumps(safe, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def prepare():
    state = get('/api/state'); assert state['running'] and not state['queue']['active']
    before = {'models': models(), 'preserved_files': preserved_files(), 'user_data': content_fingerprints(),
        'backups': backup_config(get('/api/backups')), 'knowledge': get('/api/knowledge')}
    backup, counts = verified_backup()
    save({'prepared_at': time.strftime('%Y-%m-%d %H:%M:%S %z'), 'before': before,
        'pre_rollout_backup': backup, 'pre_rollout_counts': counts, 'contains_secret_values': False})
    print(json.dumps({'prepared': True, 'backup_verified': True, 'model_pids': [p['pid'] for p in before['models']]}))


def activate():
    report = json.loads(REPORT.read_text(encoding='utf-8')); before = report['before']
    assert before['models'] == models() and before['preserved_files'] == preserved_files()
    assert before['user_data'] == content_fingerprints()
    post('/api/client-storage', {'action': 'sync'})
    state = get('/api/client-storage'); assert not state['error'] and state['automatic']
    registry = get('/api/remote'); clients = registry['clients'] + registry['archived_clients']
    checks = []
    with closing(sqlite3.connect((HOME / 'espaces-prives/espaces.sqlite3').as_uri() + '?mode=ro', uri=True)) as original:
        for client in clients:
            folder = Path(client['storage']['path']); manifest = json.loads((folder / 'dossier.json').read_text(encoding='utf-8'))
            assert folder.parent.resolve() == (HOME / 'donnees-clients').resolve()
            assert manifest['id'] == client['id'] and client['storage']['status'] == 'ready'
            assert all(checksum((folder / name).read_bytes()) == digest for name, digest in manifest['files'].items())
            rows = {}
            with closing(sqlite3.connect((folder / 'donnees.sqlite3').as_uri() + '?mode=ro', uri=True)) as copy:
                assert copy.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
                for table in TABLES:
                    expected = original.execute('SELECT * FROM ' + table + ' WHERE owner=? ORDER BY rowid', (client['id'],)).fetchall()
                    actual = copy.execute('SELECT * FROM ' + table + ' ORDER BY rowid').fetchall()
                    assert expected == actual, 'Écart dans la base individuelle : ' + table
                    rows[table] = {'count': len(actual), 'sha256': row_digest(actual)}
            checks.append({'id': client['id'], 'path': str(folder), 'bytes': manifest['bytes'],
                'managed_files': len(manifest['files']), 'all_file_hashes_verified': True, 'tables': rows})
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        knowledge = get('/api/knowledge')
        if knowledge['engine']['status'] == 'pret': break
        time.sleep(.5)
    assert knowledge['engine']['enabled'] and knowledge['engine']['status'] == 'pret'
    current = get('/api/state'); assert current['running'] and current['health']['loaded']
    assert before['models'] == models() and before['preserved_files'] == preserved_files()
    assert before['user_data'] == content_fingerprints() and before['backups'] == backup_config(get('/api/backups'))
    backup, counts = verified_backup()
    report.update({'result': 'PASS', 'activated_at': time.strftime('%Y-%m-%d %H:%M:%S %z'),
        'root': state['root'], 'clients': checks, 'post_rollout_backup': backup, 'included_counts': counts,
        'qwen_processes_preserved': True, 'user_data_preserved': True, 'access_settings_and_backup_schedule_preserved': True,
        'eg2_ready': True, 'storage_automatic': True})
    save(report)
    print(json.dumps({'result': 'PASS', 'root': state['root'], 'clients': len(checks),
        'qwen_preserved': True, 'eg2_ready': True, 'backup_verified': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['prepare', 'activate'])
    {'prepare': prepare, 'activate': activate}[parser.parse_args().action]()
