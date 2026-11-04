"""Check the restored service using a synthetic image, preserving historical reports."""
import base64
import argparse
import json
from pathlib import Path
import time
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=HERE / 'production-after-58180.json')
    options = parser.parse_args()
    target = options.output
    if target.exists():
        raise FileExistsError(target)
    with HTTP.open('http://127.0.0.1:8080/health', timeout=5) as response:
        health = json.load(response)
    assert health.get('loaded') and health.get('images'), health
    fixture = ROOT / 'maintenance/2026-10-14-vision/vision-fixture.png'
    content = [
        {'type': 'text', 'text': 'Lis le code écrit en haut de l’image et indique la forme rouge et la forme bleue. Réponds brièvement en français.'},
        {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(fixture.read_bytes()).decode()}},
    ]
    payload = {'model': health['model'], 'messages': [{'role': 'user', 'content': content}],
               'temperature': 0, 'max_tokens': 192, 'stream': False,
               'chat_template_kwargs': {'enable_thinking': False}}
    request = urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions', json.dumps(payload).encode(),
                                     {'Content-Type': 'application/json'})
    start = time.monotonic()
    with HTTP.open(request, timeout=600) as response:
        result = json.load(response)
    answer = result['choices'][0]['message']['content']
    text = answer.lower()
    passed = '47' in text and ('cercle' in text or 'rond' in text) and ('carré' in text or 'carre' in text)
    pointer = json.loads((ROOT / 'lanceur/session.json').read_text(encoding='utf-8-sig'))
    config = json.loads((Path(pointer['directory']) / 'strata.json').read_text(encoding='utf-8-sig'))
    report = {'health': health, 'seconds': time.monotonic() - start, 'answer': answer, 'passed': passed,
              'usage': result.get('usage'), 'timings': result.get('timings'), 'config': config}
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True), flush=True)
    assert passed, answer


if __name__ == '__main__':
    main()
