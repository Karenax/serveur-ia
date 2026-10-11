"""Authorized local rollout checks; stores hashes/counts, never conversation text or secrets."""
import argparse
import json
import time
import psutil
from validate_live_lots6_8 import get, post, models, preserved_files, content_fingerprints, backup_config, HOME

REPORT = HOME.parent / 'preuves/eg2-20261011/production-validation.json'


def save(report):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def verified_backup():
    # Existing locally protected credential; never print or persist its value.
    post('/api/backups/create', {})
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        current = get('/api/backups')
        if current['job']['state'] != 'running': break
        time.sleep(.5)
    assert current['job']['state'] == 'succeeded', 'Sauvegarde impossible.'
    archive = next(row for row in current['catalog'] if row['verified'] and row['version'] == 2)
    phrase = (HOME / 'sauvegardes/phrase-recuperation.txt').read_text(encoding='utf-8')
    inspected = post('/api/backups/verify', {'file': archive['file'], 'password': phrase})
    assert inspected['summary']['sha256'] == archive['sha256']
    return {key: archive[key] for key in ('file', 'size', 'sha256', 'version', 'verified')}, inspected['summary']['counts']


def prepare():
    state = get('/api/state')
    assert state['running'] and state['health']['loaded'] and not state['queue']['active']
    report = {'prepared_at': time.strftime('%Y-%m-%d %H:%M:%S %z'), 'contains_secret_values': False,
        'before': {'model_processes': models(), 'preserved_file_sha256': preserved_files(),
        'user_data': content_fingerprints(), 'automatic_backups': backup_config(get('/api/backups'))}}
    report['pre_rollout_backup'], report['pre_rollout_counts'] = verified_backup()
    save(report)
    print(json.dumps({'prepared': True, 'backup_verified': True,
        'model_pids': [p['pid'] for p in report['before']['model_processes']]}))


def activate():
    report = json.loads(REPORT.read_text(encoding='utf-8')); before = report['before']
    assert before['model_processes'] == models(), 'Qwen a changé.'
    assert before['preserved_file_sha256'] == preserved_files(), 'Accès/réglages modifiés.'
    assert before['user_data'] == content_fingerprints(), 'Données modifiées.'
    assert before['automatic_backups'] == backup_config(get('/api/backups'))
    post('/api/knowledge', {'action': 'start'})
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        knowledge = get('/api/knowledge')
        if knowledge['engine']['status'] == 'pret' and knowledge['index']['pending'] == 0 and knowledge['index']['last_sync']: break
        time.sleep(1)
    assert knowledge['engine']['status'] == 'pret', 'EG2 ne démarre pas.'
    assert not knowledge['index']['pending'] and not knowledge['index']['error']
    assert before['model_processes'] == models()
    assert before['user_data'] == content_fingerprints()
    assert before['preserved_file_sha256'] == preserved_files()
    state = get('/api/state'); assert state['running'] and state['health']['loaded']
    report['post_rollout_backup'], report['included_counts'] = verified_backup()
    assert 'personal_memories' in report['included_counts'] and 'knowledge_exclusions' in report['included_counts']
    report.update({'result': 'PASS', 'activated_at': time.strftime('%Y-%m-%d %H:%M:%S %z'),
        'after': {'engine': knowledge['engine'], 'index': knowledge['index'],
        'rss_mib': psutil.Process(knowledge['engine']['pid']).memory_info().rss / 1048576,
        'model_processes': models(), 'user_data_preserved': before['user_data'] == content_fingerprints(),
        'access_and_settings_preserved': before['preserved_file_sha256'] == preserved_files(),
        'automatic_backups_preserved': before['automatic_backups'] == backup_config(get('/api/backups')),
        'qwen_running_and_loaded': True}})
    assert report['after']['user_data_preserved'] and report['after']['access_and_settings_preserved'] and report['after']['automatic_backups_preserved']
    save(report)
    print(json.dumps({'result': 'PASS', 'engine': knowledge['engine'], 'index': knowledge['index'],
        'qwen_pids_preserved': [p['pid'] for p in models()], 'backup_verified': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['prepare', 'activate'])
    {'prepare': prepare, 'activate': activate}[parser.parse_args().action]()
