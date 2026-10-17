"""Read a synthetic image through Qwen and an isolated native Hermes account."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import secrets
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'lanceur'))
from core import health
from hermes_fred import HermesFred
from remote import AccessStore
from validate_live_lots6_8 import backup_config, get, preserved_files
from encoder_trial import memory


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def content():
    data = base64.b64encode((OUT / 'vision-fixture.png').read_bytes()).decode()
    return [{'type': 'text', 'text': 'Lis le code écrit en haut de l’image et indique la forme rouge et la forme bleue. Réponds brièvement en français.'},
            {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + data}}]


def check(answer):
    text = answer.lower()
    assert '47' in text and ('cercle' in text or 'rond' in text) and ('carré' in text or 'carre' in text), answer


def direct():
    state = health('127.0.0.1', 8080, timeout=5)
    assert state.get('loaded') and state.get('images')
    payload = {'model': state['model'], 'messages': [{'role': 'user', 'content': content()}],
               'temperature': 0, 'max_tokens': 192, 'stream': False,
               'chat_template_kwargs': {'enable_thinking': False}}
    request = urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions',
        json.dumps(payload).encode(), {'Content-Type': 'application/json'})
    before = memory()
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=600) as response:
        result = json.load(response)
    answer = result['choices'][0]['message']['content']
    report = {'health': state, 'seconds': round(time.monotonic() - started, 3), 'answer': answer,
              'usage': result.get('usage'), 'timings': result.get('timings'), 'before': before,
              'after': memory(), 'passed': False}
    save('direct.json', report)
    check(answer)
    report['passed'] = True
    save('direct.json', report)
    print(json.dumps(report, ensure_ascii=False), flush=True)


def text():
    payload = {'model': 'qwen3.8-flash-next-iq4-xs', 'messages': [{'role': 'user',
        'content': 'Combien font 17 multiplié par 19 ? Réponds uniquement avec le nombre.'}],
        'temperature': 0, 'max_tokens': 32, 'stream': False,
        'chat_template_kwargs': {'enable_thinking': False}}
    request = urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions',
        json.dumps(payload).encode(), {'Content-Type': 'application/json'})
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.load(response)
    answer = result['choices'][0]['message']['content']
    report = {'seconds': round(time.monotonic() - started, 3), 'answer': answer,
              'usage': result.get('usage'), 'timings': result.get('timings'), 'passed': answer.strip() == '323'}
    save('text-after.json', report)
    assert report['passed'], answer
    print(json.dumps(report, ensure_ascii=False), flush=True)


def hermes():
    state = health('127.0.0.1', 8080, timeout=5)
    assert state.get('loaded') and state.get('images')
    report = {'scope': 'isolated-synthetic-fixture', 'passed': False}
    with tempfile.TemporaryDirectory(prefix='fred-hermes-vision-') as temp:
        store = AccessStore(temp)
        store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        owner = store.issue('Validation vision isolée')['id']
        agent = HermesFred(store, lambda: (8080, state['model'], ''), port=0, private_port=0)
        store.hermes = store.workspace.hermes = agent
        try:
            agent.start()
            request, conversation = secrets.token_hex(16), secrets.token_hex(16)
            began = time.monotonic()
            frames = []
            for raw in agent.stream(owner, {'model': 'fred-qwen',
                'messages': [{'role': 'user', 'content': content()}], 'reasoning_effort': 'none'}, request, conversation):
                for line in raw.splitlines():
                    if line.startswith(b'data: ') and line != b'data: [DONE]':
                        frames.append(json.loads(line[6:]))
            answer = ''.join(frame.get('choices', [{}])[0].get('delta', {}).get('content', '') for frame in frames)
            result = agent.action(owner, {'action': 'reconcile', 'request_id': request, 'conversation_id': conversation})
            report.update(seconds=round(time.monotonic() - began, 3), answer=answer, status=result['status'])
            save('hermes.json', report)
            assert result['status'] == 'completed' and answer == result['text']
            check(answer)
            report['passed'] = True
        finally:
            agent.close()
            store.workspace.shutdown()
            store.voice.close()
            save('hermes.json', report)
    print(json.dumps(report, ensure_ascii=False), flush=True)


def protected():
    before = json.loads((OUT / 'before.json').read_text())
    current = preserved_files()
    assert current == before['protected_files'], 'Access, keys or settings changed'
    assert backup_config(get('/api/backups')) == before['backup_schedule']
    state = health('127.0.0.1', 8080, timeout=5)
    assert state.get('loaded') and state.get('images')
    pointer = json.loads((ROOT / 'lanceur/session.json').read_text(encoding='utf-8-sig'))
    launch = json.loads((Path(pointer['directory']) / 'state.json').read_text(encoding='utf-8-sig'))
    base = json.loads((ROOT / 'lanceur/base-strata.json').read_text(encoding='utf-8-sig'))
    with Path(base['exe']).open('rb') as stream:
        engine_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    assert engine_hash == '6ce44b68442b8d2330ee8634abb4e364e17185d2474816627ec74aaa34d2a0b1'
    report = {'passed': True, 'protected_files': current, 'backup_schedule_preserved': True,
              'health': state, 'memory': memory(),
              'text_engine_sha256': engine_hash,
              'startup_status': launch['status'], 'ready_seconds': launch.get('ready_seconds')}
    save('production.json', report)
    print('Production: images enabled, access, keys, settings and backup schedule preserved.', flush=True)


def catalogue():
    sys.path.insert(0, str(ROOT / 'client-qwen'))
    import client
    import releases
    profile = releases.profile(ROOT / 'lanceur/clients/0402a094eeb03bdc.exe')
    remote = client.Remote(profile, endpoint=client.HTTPS_ENDPOINT)
    try:
        with remote.open('/v1/models') as response:
            rows = json.load(response)['data']
        local = next(row for row in rows if row['id'] == 'fred-qwen')
        assert local['capabilities']['images'] and local['capabilities']['vision']
        save('catalogue.json', {'passed': True, 'transport': 'https', 'model_count': len(rows), 'local_model': local})
        print('HTTPS catalogue: local Qwen advertises images and vision.', flush=True)
    finally:
        remote.close()


def finish():
    pointer = json.loads((ROOT / 'lanceur/session.json').read_text(encoding='utf-8-sig'))
    path = Path(pointer['directory']) / 'state.json'
    deadline = time.monotonic() + 3600
    while time.monotonic() < deadline:
        state = json.loads(path.read_text(encoding='utf-8-sig'))
        if state['status'] == 'erreur':
            raise RuntimeError(state.get('error', 'Model startup failed'))
        if state['status'] == 'pret':
            break
        time.sleep(2)
    else:
        raise TimeoutError('Model startup did not finish within an hour')
    for phase in (text, direct, hermes, catalogue, protected):
        print('Starting verification: ' + phase.__name__, flush=True)
        phase()


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['direct', 'text', 'hermes', 'protected', 'catalogue', 'finish'])
    globals()[parser.parse_args().phase]()
