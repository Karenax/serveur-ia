"""Exercise KV streaming beyond its resident window on the managed service."""
import json
from pathlib import Path
import time
import urllib.request

HERE = Path(__file__).resolve().parent
OUT = HERE / 'default-architecture'


def main():
    target = OUT / 'context-streaming.json'
    if target.exists():
        raise FileExistsError(target)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:8080/health', timeout=5) as response:
        health = json.load(response)
    assert health['loaded'] and health['max_context'] == 262144, health
    document = '\n'.join(f'Dossier {i:04d}: le jardin contient des arbres, des fleurs et un chemin de pierre.' for i in range(1200))
    prompt = ('Lis ce dossier fictif de validation.\n' + document +
              '\nLe code à restituer est JARDIN-5832. Réponds uniquement avec ce code.')
    payload = {'model': health['model'], 'messages': [{'role': 'user', 'content': prompt}],
               'temperature': 0, 'max_tokens': 32, 'cache_prompt': False, 'stream': False,
               'chat_template_kwargs': {'enable_thinking': False}}
    request = urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions', json.dumps(payload).encode(),
                                     {'Content-Type': 'application/json'})
    start = time.monotonic()
    with opener.open(request, timeout=900) as response:
        result = json.load(response)
    text = result['choices'][0]['message']['content']
    timings = result['timings']
    passed = 'JARDIN-5832' in text and timings['prompt_n'] > 20480 and timings.get('cache_n', 0) == 0
    report = {'health': health, 'seconds': time.monotonic() - start, 'answer': text, 'passed': passed,
              'usage': result.get('usage'), 'timings': timings,
              'scope': 'Configured capacity 262144; exercised prompt beyond 20480 resident cells, not full-capacity stress test'}
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True), flush=True)
    assert passed, report


if __name__ == '__main__':
    main()
