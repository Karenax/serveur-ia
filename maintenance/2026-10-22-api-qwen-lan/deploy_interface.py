"""Load console controls while preserving the running model and private state."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'lanceur'))
from validate_live_lots6_8 import get, models, preserved_files, content_fingerprints, backup_config


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def voice_files():
    return {name: hashlib.sha256((ROOT / 'lanceur' / name).read_bytes()).hexdigest()
            for name in ('voix.json', 'phonon-model.json') if (ROOT / 'lanceur' / name).exists()}


def main():
    assert not (OUT / 'avant-livraison.json').exists(), 'Inspect the previous deployment before retrying'
    assert get('/api/state')['queue']['active'] == 0 and not get('/api/voice')['busy']
    before = {'models': models(), 'files': preserved_files(), 'users': content_fingerprints(),
              'backups': backup_config(get('/api/backups')), 'voice_files': voice_files()}
    write('avant-livraison.json', before)
    spec = importlib.util.spec_from_file_location('previous_delivery', ROOT / 'maintenance/2026-10-21-api-embeddings/livrer.py')
    delivery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(delivery)
    delivery.OUT = OUT
    delivery.restart()
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            if get('/api/remote')['hermes']['service']['available'] and get('/api/knowledge')['engine']['status'] == 'pret':
                break
        except (OSError, KeyError, ValueError):
            pass
        time.sleep(1)
    else:
        raise ValueError('Console services did not become ready')
    state = get('/api/local-network')
    assert state['enabled'] and state['available'] and not state['authentication']
    assert models() == before['models']
    assert preserved_files() == before['files']
    assert content_fingerprints() == before['users']
    assert backup_config(get('/api/backups')) == before['backups']
    assert voice_files() == before['voice_files']
    voice = get('/api/voice')
    write('interface-production.json', {'passed': True, 'model_processes_preserved': True,
          'keys_settings_user_data_preserved': True, 'backups_preserved': True,
          'voice_settings_preserved': True, 'voice_engine': voice['engine'], 'local_network': state})
    print('Console controls deployed; Qwen processes, keys, user data, backups and Phonon settings preserved.')


if __name__ == '__main__':
    main()
