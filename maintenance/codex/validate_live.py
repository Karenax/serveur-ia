"""Explicit live qualification against loaded Qwen, using only a temporary access.

No production account, history or Codex configuration is changed. Reports contain
synthetic prompts/results and request field names, never authentication headers.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'lanceur'))
from remote import AccessStore, serve_gateway
import gateway_responses
from core import HIDDEN, health


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--agents', action='store_true')
    parser.add_argument('--edit', action='store_true')
    args = parser.parse_args()
    if not health(port=args.port).get('loaded'): raise RuntimeError('Charger Qwen avant ce test explicite.')
    binary = shutil.which('codex')
    if not binary: raise RuntimeError('Codex CLI est requis.')
    report = {'codex': subprocess.check_output([binary, '--version'], text=True).strip(), 'requests': []}
    with tempfile.TemporaryDirectory(prefix='kiara-codex-qualification-') as temporary:
        home = Path(temporary)
        fixture = home/'preuve.txt'; expected = 'KIARA-' + secrets.token_hex(6)
        fixture.write_text(expected, encoding='utf-8')
        store = AccessStore(home/'server')
        store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        access = store.issue('Qualification Codex temporaire')
        server = serve_gateway(store, lambda: (args.port, 'qwen3.8-flash-next-iq4-xs', ''), 0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        original = gateway_responses.responses_request
        def capture(raw):
            report['requests'].append({'model': raw.get('model'), 'fields': sorted(raw), 'input_types': sorted({v.get('type','message') for v in raw.get('input',[]) if isinstance(v,dict)}),
                                       'tool_types': sorted({t.get('type','') for t in raw.get('tools',[])}),
                                       'input_characters': len(json.dumps(raw.get('input'))), 'tool_characters': len(json.dumps(raw.get('tools'))),
                                       'items': [{'type': v.get('type',v.get('role')), 'characters': len(json.dumps(v)),
                                                  **({'name': v.get('name'), 'arguments': v.get('arguments',v.get('input')), 'call_id': v.get('call_id')} if v.get('type') in ('function_call','custom_tool_call') else {}),
                                                  **({'output_tail': str(v.get('output'))[-500:]} if v.get('type')=='function_call_output' else {})}
                                                 for v in raw.get('input',[]) if isinstance(v,dict)]})
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            return original(raw)
        env = dict(os.environ, KIARA_API_KEY=access['token'])
        base = 'http://127.0.0.1:' + str(server.server_port) + '/v1'
        command = [binary, 'exec', '--ignore-user-config', '--ignore-rules', '--ephemeral', '--skip-git-repo-check',
                   '-C', str(home), '--json', '-c', 'model_provider="kiara"', '-m', 'fred-qwen',
                   '-c', 'model_providers.kiara={name="Kiara",base_url="'+base+'",env_key="KIARA_API_KEY",wire_api="responses",requires_openai_auth=false,stream_idle_timeout_ms=900000}',
                   '-c', 'model_catalog_json='+json.dumps(str(Path(__file__).with_name('qwen-models.json')).replace('\\','/')),
                   '-c', 'web_search="disabled"', '-c', 'model_reasoning_effort="none"',
                   '-c', 'approval_policy="never"', '-s', 'danger-full-access', '-c', 'agents.enabled='+str(args.agents).lower(),
                   '-c', 'features.apps=false', '-c', 'features.plugins=false',
                   '-c', 'agents.max_concurrent_threads_per_session=2', '-c', 'agents.default_subagent_model="fred-qwen"',
                   '-c', 'agents.default_subagent_reasoning_effort="none"']
        prompt = ('Lis le fichier preuve.txt avec un outil du PC et réponds uniquement avec son contenu exact. Ne le devine pas.'
                  if not args.agents else 'Crée deux sous-agents indépendants sans historique hérité. Demande au premier de lire preuve.txt avec un outil du PC et au second de calculer 17*19. Attends leurs résultats et réponds avec le contenu exact du fichier suivi du résultat du calcul.')
        if args.edit:
            prompt = 'Lis preuve.txt avec un outil du PC, puis utilise obligatoirement apply_patch pour créer resultat.txt avec exactement ce contenu. Ne modifie aucun autre fichier. Réponds avec le contenu copié.'
        started = time.monotonic()
        try:
            with patch.object(gateway_responses, 'responses_request', capture):
                result = subprocess.run(command+[prompt], env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300, creationflags=HIDDEN)
            report.update(returncode=result.returncode, seconds=round(time.monotonic()-started,2), stdout=result.stdout, stderr=result.stderr,
                          queue=store.scheduler.snapshot(), expected=expected)
            events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
            answers = [v['item']['text'] for v in events if v.get('type')=='item.completed' and v.get('item',{}).get('type')=='agent_message']
            report['final_answer'] = answers[-1] if answers else ''
            spawns = [v['item'] for v in events if v.get('type')=='item.completed' and v.get('item',{}).get('tool')=='spawn_agent']
            report['spawned_agents'] = [target for spawn in spawns for target in spawn.get('receiver_thread_ids',[])]
            report['passed'] = (result.returncode == 0 and expected in report['final_answer'] and len(report['requests']) >= 2
                                and all(row['model']=='fred-qwen' for row in report['requests'])
                                and (not args.agents or len(set(report['spawned_agents'])) == 2 and '323' in report['final_answer']))
            if args.edit:
                written = home/'resultat.txt'
                report['file_content_correct'] = written.is_file() and written.read_text(encoding='utf-8').strip()==expected
                report['custom_patch_called'] = any(item.get('type')=='custom_tool_call' and item.get('name')=='apply_patch' for row in report['requests'] for item in row['items'])
                report['passed'] = report['passed'] and report['file_content_correct'] and report['custom_patch_called']
        except subprocess.TimeoutExpired as error:
            report.update(passed=False, error='Codex qualification timeout', seconds=round(time.monotonic()-started,2),
                          stdout=(error.stdout or b'').decode('utf-8',errors='replace'), stderr=(error.stderr or b'').decode('utf-8',errors='replace'))
        finally:
            store.scheduler.cancel(access['id'])
            server.shutdown(); server.server_close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('codex', 'passed', 'seconds', 'final_answer', 'spawned_agents') if k in report}, ensure_ascii=True))
    if not report['passed']: raise SystemExit(1)


if __name__ == '__main__': main()
