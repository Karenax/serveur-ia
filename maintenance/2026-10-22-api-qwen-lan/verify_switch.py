"""Exercise the authorized LAN switch, then restore the original active mode."""
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'lanceur'))
from validate_live_lots6_8 import get, post, models, preserved_files


def wait_for(enabled):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        state = get('/api/local-network')
        if not state['pending']:
            if state.get('error'):
                raise ValueError(state['error'])
            if state['enabled'] == enabled and (enabled or not state['can_disable']):
                return state
        time.sleep(1)
    raise ValueError('Windows validation timeout; inspect the console before retrying')


def lan_available():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open('http://192.168.1.41:8080/v1/models', timeout=2) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def main():
    before = {'models': models(), 'files': preserved_files()}
    assert get('/api/local-network')['enabled']
    assert get('/api/state')['queue']['active'] == 0
    assert not get('/api/voice')['busy']
    result = {'passed': False, 'restored_active': False}
    changed = False
    try:
        post('/api/local-network', {'enabled': False})
        disabled = wait_for(False)
        changed = True
        for _ in range(10):
            if not lan_available():
                break
            time.sleep(.5)
        assert not lan_available(), 'LAN listener should be closed'
        with urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=5) as response:
            assert json.load(response)['loaded']
        assert models() == before['models']
        result.update(disabled=disabled, lan_closed=True, qwen_still_loaded=True)
    finally:
        if changed or not get('/api/local-network')['enabled']:
            post('/api/local-network', {'enabled': True})
            result['restored'] = wait_for(True)
        result['restored_active'] = get('/api/local-network')['enabled']
        (OUT / 'switch-production.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    assert lan_available()
    assert models() == before['models'] and preserved_files() == before['files']
    result.update(passed=True, lan_reopened=True, model_processes_preserved=True, keys_settings_preserved=True)
    (OUT / 'switch-production.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Real Windows switch verified: LAN closed, Qwen stayed loaded, LAN restored active.')


if __name__ == '__main__':
    main()
