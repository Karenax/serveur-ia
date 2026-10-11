"""Explicit direct-corrector smoke test against the already loaded local Qwen.

Uses a disposable Fred account and gateway; no production history is written.
Run from the repository with the Strata virtualenv, after unit tests pass.
"""
import hashlib
import json
from pathlib import Path
import secrets
import sys
import tempfile
import threading
import time
import urllib.request

import psutil
from core import BASE_PATH, HOME, ROOT, health, process_identity, read_json, same_process
from remote import AccessStore, serve_gateway


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class UnavailableHermes:
    def stream(self, *args, **kwargs):
        raise AssertionError('The text corrector must not call Hermes.')

    def cancel(self, *args, **kwargs):
        raise AssertionError('The text corrector must not cancel a Hermes run.')


def main():
    if '--run' not in sys.argv:
        raise SystemExit('Explicit run required: validate_text_transform_native.py --run')
    with urllib.request.urlopen('http://127.0.0.1:8765/api/remote', timeout=10) as response:
        state = json.load(response)
    if state['active'] or state['queue']['active'] or state['queue']['waiting']:
        raise ValueError('Wait for current production requests before this smoke test.')
    before = health()
    if not before.get('loaded'):
        raise ValueError('Qwen must already be loaded; this validation never starts it.')
    listeners = {c.pid for c in psutil.net_connections(kind='tcp')
                 if c.laddr and c.laddr.port == 8080 and c.status == 'LISTEN'}
    if len(listeners) != 1:
        raise ValueError('The loaded Qwen process must be identified unambiguously.')
    engine = psutil.Process(listeners.pop())
    models = [process_identity(engine)]
    parent = engine.parent()
    if parent and parent.name().lower() == 'python.exe':
        models.append(process_identity(parent))
    config = read_json(BASE_PATH, {})
    for process in (engine, parent):
        if not process:
            continue
        command = process.cmdline()
        if '--config' in command:
            config = read_json(command[command.index('--config') + 1], config)
            break
    hashes = {name: digest(HOME / name) for name in ('acces-distants.json', 'reglages.json')}
    checks = []
    with tempfile.TemporaryDirectory(prefix='fred-direct-corrector-') as directory:
        store = AccessStore(Path(directory))
        store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        access = store.issue('Direct corrector smoke test')
        store.hermes = UnavailableHermes()
        store.workspace.context = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError('The corrector must not search documents or memories.'))
        gateway = serve_gateway(store, lambda: (int(config.get('port', 8080)),
                                 before.get('model', 'local'), config.get('api_key', '')), 0)
        thread = threading.Thread(target=gateway.serve_forever, daemon=True)
        thread.start()
        try:
            for mode in ('correct', 'professional', 'friendly'):
                started = time.monotonic()
                body = {'text_transform': {'mode': mode, 'text':
                        'Bonjour, je vous envoi le document demain. Merci de votre aide.'},
                        'stream': True}
                request = urllib.request.Request(
                    f'http://127.0.0.1:{gateway.server_port}/v1/chat/completions',
                    json.dumps(body).encode(), headers={'Authorization': 'Bearer ' + access['token'],
                    'Content-Type': 'application/json', 'X-Qwen-Request': secrets.token_hex(16)})
                answer = []; done = False; first = None
                with urllib.request.urlopen(request, timeout=120) as response:
                    assert response.status == 200
                    assert response.headers.get_content_type() == 'text/event-stream'
                    for line in response:
                        if line.strip() == b'data: [DONE]':
                            done = True
                            break
                        if not line.startswith(b'data: '):
                            continue
                        event = json.loads(line[6:])
                        if event.get('error'):
                            raise ValueError('Direct inference failed: ' + str(event['error']))
                        for choice in event.get('choices', []):
                            content = choice.get('delta', {}).get('content', '')
                            if content:
                                if first is None:
                                    first = time.monotonic() - started
                                answer.append(content)
                text = ''.join(answer).strip()
                assert done and text, 'A complete, nonempty corrected text is required.'
                checks.append({'mode': mode, 'complete': done, 'answer': text,
                               'first_text_seconds': round(first, 3),
                               'total_seconds': round(time.monotonic() - started, 3)})
                print(json.dumps({'mode': mode, 'complete': done,
                                  'characters': len(text)}, ensure_ascii=False), flush=True)
        finally:
            gateway.shutdown()
            gateway.server_close()
            thread.join(timeout=5)
    after = health()
    preserved = {'model_processes': all(same_process(model) for model in models),
                 'model_loaded': bool(after.get('loaded')),
                 'model_name': after.get('model') == before.get('model'),
                 'access_and_settings': all(digest(HOME / name) == value
                                           for name, value in hashes.items())}
    assert all(preserved.values()), 'Production model, access and settings must remain unchanged.'
    result = {'passed': True, 'scope': 'disposable-account-and-gateway',
              'provider': 'already-loaded-local-Qwen', 'hermes': 'unavailable-stub-never-called',
              'document_and_memory_context': 'never-called', 'production_history_modified': False,
              'timing': 'single smoke run; not a comparative benchmark',
              'checks': checks, 'preserved': preserved}
    proof = ROOT / 'preuves/direct-corrector-20261011/native-validation.json'
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'passed': True, 'modes': len(checks), 'preserved': preserved}), flush=True)


if __name__ == '__main__':
    main()
