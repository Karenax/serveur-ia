"""Verify deployed boolean tool calls and cache without executing any returned tool."""
import importlib.util
import json
from pathlib import Path
import time
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('cache_measure',
    ROOT / 'maintenance/2026-10-16-diagnostic-opencode/mesurer_cache.py')
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)
measure.OUT = HERE / 'validation-cache'
measure.OUT.mkdir(exist_ok=True)
measure.LINE_COUNT = 50
measure.REPORT['purpose'] = 'Cache regression after Python tool-parser fix; 20 slots, 30 GiB budget'

def main():
    measure.main()
    m = measure.get('/metrics')
    assert m['engine']['conversation_cache_slots'] == 20
    assert m['engine']['conversation_cache_mib'] == 30720
    results = []
    for stream, expected in [(False, True), (True, False)]:
        payload = {'model': m['engine']['model'], 'stream': stream, 'max_tokens': 160,
            'temperature': 0, 'seed': 42, 'strata_mcp': False,
            'chat_template_kwargs': {'enable_thinking': False},
            'messages': [{'role': 'user', 'content':
                f'Appelle bool_probe avec background={str(expected).lower()} et marker="True". '
                'Le champ marker contient le texte True. Aucun autre texte.'}],
            'tools': [{'type': 'function', 'function': {'name': 'bool_probe',
                'description': 'Test de sérialisation ; cet outil ne sera pas exécuté.',
                'parameters': {'type': 'object', 'properties': {
                    'background': {'type': 'boolean'}, 'marker': {'type': 'string'}},
                    'required': ['background', 'marker']}}}],
            'tool_choice': {'type': 'function', 'function': {'name': 'bool_probe'}}}
        req = urllib.request.Request(measure.BASE + '/v1/chat/completions',
            data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
        started = time.monotonic()
        with measure.OPENER.open(req, timeout=300) as response:
            if stream:
                arguments = ''
                name = ''
                for raw in response:
                    line = raw.decode().strip()
                    if not line.startswith('data: ') or line == 'data: [DONE]':
                        continue
                    event = json.loads(line[6:])
                    for choice in event.get('choices', []):
                        for tool in choice.get('delta', {}).get('tool_calls', []):
                            fn = tool.get('function', {})
                            arguments += fn.get('arguments', '')
                            name += fn.get('name', '')
            else:
                result = json.load(response)
                fn = result['choices'][0]['message']['tool_calls'][0]['function']
                arguments = fn['arguments']
                name = fn['name']
        args = json.loads(arguments)
        assert name == 'bool_probe', name
        assert args['background'] is expected, args
        assert args['marker'] == 'True', args
        results.append({'stream': stream, 'arguments': args,
                        'wall_seconds': round(time.monotonic() - started, 3)})
        print('LIVE_TOOL ' + json.dumps(results[-1]), flush=True)
    final = {'passed': True, 'tool_calls_executed': False, 'results': results,
             'engine': measure.get('/metrics')['engine'],
             'cache': measure.get('/metrics')['conversation_cache']}
    (HERE / 'validation-outils-live.json').write_text(json.dumps(final, indent=2), encoding='utf-8')
    print('Boolean tool calls and cache verified on the live model.', flush=True)

if __name__ == '__main__':
    main()
