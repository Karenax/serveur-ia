"""Validate the activated oral route and Phonon with fictional input, no history writes."""
import json
from pathlib import Path
import secrets
import re
import sqlite3
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'lanceur'))
from releases import profile
from validate_live_lots6_8 import get, models, preserved_files, content_fingerprints


def agent_run_count():
    path = ROOT / 'lanceur/hermes-fred/fred-integration.db'
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        return db.execute('SELECT COUNT(*) FROM agent_runs').fetchone()[0]


def main():
    state = get('/api/state')
    assert state['health']['loaded'] and not state['queue']['active'] and not state['queue']['waiting']
    assert not get('/api/voice')['busy']
    access = profile(next((ROOT / 'lanceur/clients').glob('*.exe')))
    headers = {'Authorization': 'Bearer ' + access['token'], 'Content-Type': 'application/json', 'X-Fred-Agent-Protocol': '4'}
    before = {'models': models(), 'files': preserved_files(), 'users': content_fingerprints(), 'runs': agent_run_count()}
    request_id = secrets.token_hex(16)
    body = {'voice_conversation': True, 'conversation_id': 'fictional-production-web-' + request_id,
            'turn_id': request_id, 'model': state['health']['model'], 'stream': True,
            'messages': [{'role': 'user', 'content': 'Peux-tu faire une recherche pour moi ?'}, {'role': 'assistant', 'content': 'Je ne peux pas chercher sur Internet, je n’ai pas accès au web.'}, {'role': 'user', 'content': 'cherche internet la derniere actualité sur l’IA'}]}
    request = urllib.request.Request('http://127.0.0.1:8766/v1/chat/completions', json.dumps(body).encode(),
                                    {**headers, 'X-Qwen-Request': request_id})
    start = time.monotonic()
    first = None
    sources = []
    stages = []
    context = None
    text = ''
    done = False
    with urllib.request.urlopen(request, timeout=180) as response:
        for line in response:
            if not line.startswith(b'data: '):
                continue
            raw = line[6:].strip()
            if raw == b'[DONE]':
                done = True
                break
            frame = json.loads(raw)
            assert not frame.get('error'), 'Oral web request failed'
            assert not frame.get('hermes_run'), 'Unexpected agent run'
            if frame.get('hermes_status'):
                stages.append(frame['hermes_status']['message'])
            if frame.get('workspace_sources'):
                sources = frame['workspace_sources']
            if frame.get('voice_context'):
                context = frame['voice_context']
            content = (frame.get('choices') or [{}])[0].get('delta', {}).get('content', '')
            if content and first is None:
                first = time.monotonic() - start
            text += content
    assert done and text.strip() and sources and any(s.get('retrieved') for s in sources)
    assert not re.search(r"(?:n['’]ai pas acc[eè]s|ne peux pas (?:chercher|naviguer|effectuer.*recherche))", text, re.I), 'Unsupported web refusal'

    assert 'Recherche sur Internet…' in stages and 'Lecture des sources…' in stages
    assert context['input_tokens'] + context['output_tokens'] <= 16384
    audio_id = secrets.token_hex(16)
    body = {'request_id': audio_id, 'text': 'La recherche Internet est disponible.', 'stream': True}
    request = urllib.request.Request('http://127.0.0.1:8766/v1/voice/speech', json.dumps(body).encode(), headers)
    audio_start = time.monotonic()
    first_audio = None
    audio_done = False
    with urllib.request.urlopen(request, timeout=60) as response:
        for line in response:
            if not line.startswith(b'data: '):
                continue
            frame = json.loads(line[6:])
            assert frame['id'] == audio_id and not frame.get('error')
            if frame.get('pcm') and first_audio is None:
                first_audio = time.monotonic() - audio_start
            if frame.get('done'):
                assert not frame.get('cancelled')
                audio_done = True
    assert first_audio is not None and audio_done
    assert models() == before['models'] and preserved_files() == before['files']
    assert content_fingerprints() == before['users'] and agent_run_count() == before['runs']
    report = {'passed': True, 'route': 'existing authenticated production gateway; fictional input only',
              'hermes_agent_run_created': False, 'reported_wording_replayed': True, 'old_refusal_overridden': True, 'qwen_processes_preserved': True,
              'keys_settings_user_histories_preserved': True, 'research_stages': stages,
              'web_source_count': sum(s.get('origin') == 'hermes-web' for s in sources),
              'pages_read': sum(bool(s.get('retrieved')) for s in sources), 'oral_context': context,
              'first_answer_text_seconds': round(first, 3), 'answer_characters': len(text),
              'phonon_first_pcm_seconds': round(first_audio, 3), 'phonon_completed': True,
              'limits': 'One public fictional question, no microphone or browser audio playback; not a benchmark.'}
    (OUT / 'production-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
