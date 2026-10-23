"""Real Qwen and Phonon over Fred's authenticated HTTP gateway, disposable users."""
import base64
import json
from pathlib import Path
import secrets
import sys
import tempfile
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'lanceur'), str(ROOT / 'client-qwen')]
from remote import AccessStore, serve_gateway
from validate_live_lots6_8 import models


class NoHermes:
    def stream(self, *args): raise AssertionError('Hermes called')
    def select_model(self, *args): raise AssertionError('Hermes called')
    def cancel(self, *args): raise AssertionError('Hermes called')


def main():
    before = models()
    with tempfile.TemporaryDirectory(prefix='fred-phonon-live-') as folder:
        store = AccessStore(folder)
        store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        access = store.issue('Phonon synthetic validation only')
        store.hermes = NoHermes()
        gateway = serve_gateway(store, lambda: (8080, 'qwen3.8-flash-next-iq4-xs', ''), 0)
        threading.Thread(target=gateway.serve_forever, daemon=True).start()
        base = 'http://127.0.0.1:' + str(gateway.server_port)
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + access['token']}

        def post(path, body, timeout=60):
            request_headers = dict(headers)
            if body.get('turn_id'):
                request_headers['X-Qwen-Request'] = body['turn_id']
            return urllib.request.urlopen(urllib.request.Request(base + path,
                json.dumps(body).encode(), request_headers), timeout=timeout)

        def events(response):
            for line in response:
                if line.startswith(b'data: ') and line.strip() != b'data: [DONE]':
                    event = json.loads(line[6:])
                    assert not event.get('error'), event
                    yield event

        def speech(text, cancel=False):
            identifier = secrets.token_hex(16)
            first = None
            count = 0
            finished = False
            started = time.monotonic()
            with post('/v1/voice/speech', {'request_id': identifier, 'text': text[:600], 'stream': True}) as response:
                for event in events(response):
                    assert event['id'] == identifier
                    if event.get('pcm'):
                        assert event['rate'] == 24000
                        count += len(base64.b64decode(event['pcm'], validate=True))
                        if first is None:
                            first = time.monotonic() - started
                            if cancel:
                                with post('/v1/voice/cancel', {'request_id': identifier}) as cancelled:
                                    assert json.load(cancelled)['cancelled']
                    if event.get('done'):
                        assert event['cancelled'] == cancel
                        finished = True
            assert finished and count > 0
            return {'first_chunk_seconds': first, 'audio_seconds': count / 48000, 'cancelled': cancel}

        try:
            store.voice.configure(True)
            assert store.voice.ready.wait(30), store.voice.status()
            assert store.voice.status()['engine'] == 'Phonon 0.4.1'
            request = secrets.token_hex(16)
            started = time.monotonic()
            body = {'voice_conversation': True, 'conversation_id': 'phonon-proof', 'turn_id': request,
                    'messages': [{'role': 'user', 'content': 'Combien font dix-sept fois dix-neuf ? Réponds en une phrase.'}],
                    'stream': True}
            text = ''
            with post('/v1/chat/completions', body, 120) as response:
                for event in events(response):
                    for choice in event.get('choices', []):
                        text += choice.get('delta', {}).get('content', '')
            assert '323' in text or 'trois cent vingt-trois' in text.lower(), text
            generation = time.monotonic() - started
            spoken = speech(text)
            interrupted = speech('Cette phrase doit être interrompue pendant la synthèse de la réponse. ' * 6, cancel=True)
            resumed = speech('La conversation reprend correctement après cette interruption.')
            assert models() == before
            report = {'passed': True, 'engine': store.voice.status()['engine'], 'language': 'fr', 'device': 'cpu',
                      'authenticated_http': True, 'temporary_users_only': True, 'hermes_called': False,
                      'cloud_called': False, 'qwen_processes_preserved': True, 'answer': text,
                      'qwen_generation_seconds': generation, 'speech': spoken, 'interruption': interrupted,
                      'recovery': resumed, 'human_microphone_or_listening_tested': False}
            (OUT / 'live-http.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(report, ensure_ascii=False, indent=2))
        finally:
            store.hermes = None
            gateway.shutdown()
            gateway.server_close()


if __name__ == '__main__':
    main()
