"""Exercise native Hermes web and real Qwen through an isolated oral HTTP gateway."""
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
sys.path.insert(0, str(ROOT / 'lanceur'))
from remote import AccessStore, serve_gateway
from validate_live_lots6_8 import get, models


class NoAgent:
    def stream(self, *args):
        raise AssertionError('An oral search must not start an agent run')

    def select_model(self, *args):
        raise AssertionError('An oral search must keep local Qwen')


def main():
    state = get('/api/state')
    assert state['health']['loaded'] and not state['queue']['active'] and not state['queue']['waiting']
    before = models()
    with tempfile.TemporaryDirectory(prefix='fred-oral-web-proof-') as scratch:
        store = AccessStore(scratch)
        store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        access = store.issue('Fictional oral search validation')
        store.hermes = NoAgent()
        with store.workspace.db() as db:
            db.execute('INSERT OR REPLACE INTO policies(owner,settings) VALUES(?,?)',
                       (access['id'], json.dumps({'web': True})))
        server = serve_gateway(store, lambda: (8080, state['health']['model'], ''), 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        request_id = secrets.token_hex(16)
        body = {'voice_conversation': True, 'conversation_id': 'fictional-web-proof', 'turn_id': request_id,
                'messages': [{'role': 'user', 'content': 'Cherche sur Internet le site officiel de SearXNG et explique en une phrase à quoi il sert.'}], 'stream': True}
        request = urllib.request.Request(f'http://127.0.0.1:{server.server_port}/v1/chat/completions',
                    json.dumps(body).encode(), {'Authorization': 'Bearer ' + access['token'],
                    'Content-Type': 'application/json', 'X-Qwen-Request': request_id})
        start = time.monotonic()
        first = None
        sources = []
        contexts = []
        phases = []
        answer = ''
        done = False
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                for line in response:
                    if not line.startswith(b'data: '):
                        continue
                    raw = line[6:].strip()
                    if raw == b'[DONE]':
                        done = True
                        break
                    event = json.loads(raw)
                    assert not event.get('error'), event.get('error')
                    assert not event.get('hermes_run'), 'Unexpected agent run'
                    if event.get('hermes_status'):
                        phases.append({'message': event['hermes_status']['message'], 'seconds': round(time.monotonic() - start, 3)})
                    if event.get('workspace_sources'):
                        sources = event['workspace_sources']
                    if event.get('voice_context'):
                        contexts.append(event['voice_context'])
                    text = (event.get('choices') or [{}])[0].get('delta', {}).get('content', '')
                    if text and first is None:
                        first = time.monotonic() - start
                    answer += text
        finally:
            server.shutdown(); server.server_close(); thread.join(5)
        assert done and answer.strip() and sources
        assert any(s.get('retrieved') for s in sources)
        assert contexts[-1]['input_tokens'] + contexts[-1]['output_tokens'] <= 16384
        assert models() == before
        report = {'passed': True, 'scope': 'temporary isolated account and gateway; actual public web tools and already loaded local Qwen',
                  'hermes_agent_called': False, 'qwen_processes_preserved': True,
                  'first_answer_text_seconds': round(first, 3), 'total_seconds': round(time.monotonic() - start, 3),
                  'phases': phases, 'oral_context': contexts[-1], 'answer': answer,
                  'sources': [{'url': s['url'], 'title': s['title'], 'retrieved': s['retrieved']} for s in sources],
                  'limits': 'No microphone, recognition or browser audio playback; one fictional public question, not a latency benchmark.'}
        (OUT / 'native-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
