"""Validate IQ3_S after loading; keep the server running for interactive tests."""
import datetime
import json
from pathlib import Path
import time
import urllib.request

root = Path(__file__).resolve().parent
config = json.loads((root / 'strata-iq3-p100-hybride.json').read_text(encoding='utf-8-sig'))
archive = root / 'comparatifs' / ('iq3-s-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
archive.mkdir(parents=True)
(root / 'comparatif-iq3-courant.txt').write_text(str(archive), encoding='utf-8')
url = 'http://127.0.0.1:8080'

def save(name, value):
    (archive / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def request(prompt, tokens):
    payload = dict(model=config['model_name'], messages=[dict(role='user', content=prompt)],
                   max_tokens=tokens, temperature=0, seed=42, cache_prompt=False,
                   chat_template_kwargs=dict(enable_thinking=False))
    req = urllib.request.Request(url + '/v1/chat/completions',
        data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=600) as response:
        answer = json.load(response)
    if not answer.get('usage', {}).get('completion_tokens', 0):
        raise RuntimeError('No completion tokens returned')
    return dict(request=payload, response=answer, elapsed_seconds=time.monotonic()-start)

save('configuration.json', config)
deadline = time.monotonic() + 90*60
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(url + '/health', timeout=5) as response:
            health = json.load(response)
        if health.get('loaded') and health.get('model') == config['model_name']:
            break
    except Exception:
        pass
    time.sleep(5)
else:
    raise RuntimeError('IQ3_S loading timeout (90 minutes)')
save('health.json', health)
save('warmup.json', request('Réponds en français : combien font deux plus deux ?', 1))
Path(config['env']['STRATA_P100_DIAGNOSTIC_SYNC_FILE']).unlink(missing_ok=True)
print('Initialisation CUDA validée.', flush=True)
prompts = json.loads((root / 'protocole-comparatif-q4.json').read_text(encoding='utf-8-sig'))['prompts']
for label, prompt in zip(('ciel', 'fibonacci'), prompts[:2]):
    result = request(prompt, 256)
    save(label + '.json', result)
    print(label + ': ' + json.dumps(result['response'], ensure_ascii=False), flush=True)
save('validation.json', dict(status='ok', tests=['warmup', 'ciel', 'fibonacci']))
print('IQ3_S validé ; serveur laissé actif. Résultats : ' + str(archive), flush=True)
