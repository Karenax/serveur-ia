"""Verify the real Qwen API over the LAN address without authentication."""
import json
from pathlib import Path
import urllib.request

OUT = Path(__file__).resolve().parent
BASE = 'http://192.168.1.41:8080'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

with opener.open(BASE + '/v1/models', timeout=10) as response:
    catalogue = json.load(response)
model = catalogue['data'][0]['id']
assert len(catalogue['data']) == 1 and 'qwen' in model.lower()
request = urllib.request.Request(
    BASE + '/v1/chat/completions',
    json.dumps({'model': model, 'messages': [{'role': 'user', 'content': 'Réponds seulement : OK'}],
                'max_tokens': 16, 'temperature': 0, 'stream': True,
                'chat_template_kwargs': {'enable_thinking': False}}).encode(),
    {'Content-Type': 'application/json'},
)
chunks = []
completed = False
with opener.open(request, timeout=120) as response:
    assert response.status == 200
    for line in response:
        if line.strip() == b'data: [DONE]':
            completed = True
            break
        if line.startswith(b'data: '):
            event = json.loads(line[6:])
            assert not event.get('error'), event.get('error')
            for choice in event.get('choices', []):
                chunks.append(choice.get('delta', {}).get('content') or '')
text = ''.join(chunks)
assert completed and text.strip(), 'Incomplete or empty inference'
result = {'passed': True, 'base_url': BASE + '/v1', 'model': model,
          'authorization_header_sent': False, 'stream_completed': completed,
          'response': text, 'test_origin': 'server using its LAN IPv4 address',
          'other_device_tested': False}
(OUT / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
