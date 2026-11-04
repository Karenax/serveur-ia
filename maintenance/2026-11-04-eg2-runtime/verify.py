"""Exercise the real EG2 model through Kiara and the Windows client's local API."""
import base64
import json
import math
from pathlib import Path
import secrets
import struct
import sys
import tempfile
import threading
import time
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'lanceur'), str(ROOT / 'client-qwen')]
from releases import profile
from validate_live_lots6_8 import get, models
import client


def main():
    before = json.loads((OUT / 'before.json').read_text(encoding='utf-8'))
    access = json.loads((ROOT / 'lanceur/acces-distants.json').read_text(encoding='utf-8'))
    active = {row['id'] for row in access['clients'] if not row['revoked']}
    values = next(profile(path) for path in (ROOT / 'lanceur/clients').glob('*.exe') if path.stem in active)
    headers = {'Authorization': 'Bearer ' + values['token'], 'Content-Type': 'application/json',
        'X-Fred-Agent-Protocol': '4', 'User-Agent': 'AccesServeurKiara/' + client.VERSION + ' (Windows; HTTPS)'}
    report = {'synthetic_text_only': True, 'checks': []}

    def check(base, name, extra_headers, encoding='float', mode='document', batch=False):
        body = {'model': 'google/embeddinggemma-2',
            'input': ['Le serveur conserve les documents du projet.', 'Un rappel est prévu demain.']
                if batch else 'Comment retrouver un document dans Kiara ?',
            'encoding_format': encoding, 'input_type': mode}
        request = urllib.request.Request(base + '/v1/embeddings', json.dumps(body).encode(), extra_headers)
        started = time.monotonic()
        with urllib.request.urlopen(request, timeout=60) as response:
            assert response.status == 200
            result = json.load(response)
        assert result['model'] == body['model']
        assert len(result['data']) == (2 if batch else 1)
        for row in result['data']:
            vector = row['embedding'] if encoding == 'float' else struct.unpack('<768f', base64.b64decode(row['embedding']))
            assert len(vector) == 768 and all(math.isfinite(v) for v in vector)
            assert .98 < math.sqrt(sum(v * v for v in vector)) < 1.02
        assert result['usage']['prompt_tokens'] > 0
        report['checks'].append({'path': name, 'http': 200, 'encoding': encoding, 'mode': mode,
            'vectors': len(result['data']), 'dimensions': 768, 'normalized': True,
            'prompt_tokens': result['usage']['prompt_tokens'], 'seconds': round(time.monotonic() - started, 3)})
        print(name + ': HTTP 200, normalized vectors with 768 dimensions.', flush=True)

    check('http://127.0.0.1:8766', 'authenticated_gateway_batch', headers, batch=True)
    check(client.HTTPS_ENDPOINT.rsplit('/v1', 1)[0] if client.HTTPS_ENDPOINT.endswith('/v1') else client.HTTPS_ENDPOINT,
        'public_https_query', headers, encoding='base64', mode='query')
    remote = client.Remote(values, endpoint=client.HTTPS_ENDPOINT)
    local = None
    try:
        with tempfile.TemporaryDirectory(prefix='kiara-eg2-check-') as temporary:
            with patch.object(client, 'settings_path', return_value=Path(temporary) / 'local.dpapi'):
                remote.check()
                assert remote.connected, remote.error
                key = secrets.token_urlsafe(32)
                local = client.serve_local(remote, key, port=0)
                threading.Thread(target=local.serve_forever, daemon=True).start()
                check('http://127.0.0.1:' + str(local.server_port), 'windows_local_api_over_https',
                    {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
                local.shutdown(); local.server_close(); local = None
    finally:
        if local: local.shutdown(); local.server_close()
        remote.close()
    report['engine'] = get('/api/knowledge')['engine']
    assert report['engine']['status'] == 'pret'
    assert models() == before['models'], 'Qwen process changed'
    report['qwen_processes_preserved'] = True
    report['passed'] = True
    (OUT / 'production.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__': main()
