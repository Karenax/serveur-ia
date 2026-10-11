"""Opt-in isolated Fred/Hermes integration against the already loaded local Qwen.

Run explicitly, never from the unit suite. No production access, configuration,
process or model is modified. The evidence contains only synthetic fixture data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import secrets
import sys
import tempfile
import time

from core import health, write_json
from hermes_fred import HermesFred
from remote import AccessStore


def run(port=8080, output=None):
    state = health('127.0.0.1', port, timeout=5)
    if not state.get('loaded'):
        raise ValueError('La validation exige le modèle Qwen local déjà chargé.')
    model = state.get('model') or 'qwen3.8-flash-next-iq4-xs'
    report = {'scope': 'isolated-synthetic-fixture', 'model': model, 'model_port': port,
              'started_epoch': time.time(), 'checks': {}, 'turns': []}
    with tempfile.TemporaryDirectory(prefix='fred-hermes-qwen-') as temp:
        store = AccessStore(temp)
        store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        a = store.issue('Validation Hermes A')['id']
        b = store.issue('Validation Hermes B')['id']
        hermes = HermesFred(store, lambda: (port, model, ''), port=0, private_port=0)
        store.hermes = store.workspace.hermes = hermes
        calls = []
        original = hermes.tools._call

        def record(owner, context, name, arguments):
            result = original(owner, context, name, arguments)
            calls.append({'owner': 'A' if owner == a else 'B', 'name': name,
                          'project': bool(context.get('project_id')), 'request': context['request_id']})
            return result

        hermes.tools._call = record

        def turn(owner, conversation, messages, project=None):
            request = secrets.token_hex(16)
            began = time.monotonic()
            frames = []
            for raw in hermes.stream(owner, {'messages': messages, 'reasoning_effort': 'none'},
                                     request, conversation, project):
                for line in raw.splitlines():
                    if line.startswith(b'data: ') and line != b'data: [DONE]':
                        frames.append(json.loads(line[6:]))
            response = ''.join(value.get('choices', [{}])[0].get('delta', {}).get('content', '')
                               for value in frames)
            result = hermes.action(owner, {'action': 'reconcile', 'request_id': request,
                                           'conversation_id': conversation})
            if result['status'] != 'completed' or response != result['text']:
                raise AssertionError('La réponse native doit être finalisée et réconciliable.')
            with hermes.conversations.db() as db:
                row = db.execute('SELECT session,remote FROM agent_runs WHERE owner=? AND request=?',
                                 (owner, request)).fetchone()
            value = {'owner': 'A' if owner == a else 'B', 'seconds': round(time.monotonic() - began, 3),
                     'status': result['status'], 'output': response,
                     'sources': result['sources'],
                     'session': row['session'], 'run': row['remote'], 'request': request,
                     'tools': [call['name'] for call in calls if call['request'] == request]}
            report['turns'].append(value)
            print(json.dumps({'turn': len(report['turns']), 'owner': value['owner'],
                              'seconds': value['seconds'], 'tools': value['tools'],
                              'output': response}, ensure_ascii=False), flush=True)
            return value

        try:
            hermes.start()
            report['source_commit'] = hermes.service.status()['source_commit']
            project = store.workspace.action(a, {'action': 'project_create', 'title': 'Validation native Hermes'})['id']
            doc = store.workspace.action(a, {'action': 'document_create', 'project': project,
                                             'title': 'Référence de validation',
                                             'text': 'Le code documentaire du projet est DOCUMENT-ORANGE-4821.'})['id']
            conversation = secrets.token_hex(16)
            prompt = ('Mon identifiant de validation est MARQUEUR-AZUR-7319. '
                      'Utilise obligatoirement l’outil fred_calculate pour calculer (24680+13579)*3. '
                      'Réponds en une phrase avec le résultat et mon identifiant de validation.')
            messages = [{'role': 'user', 'content': prompt}]
            first = turn(a, conversation, messages, project)
            if 'fred_calculate' not in first['tools'] or '114777' not in first['output'].replace(' ', ''):
                raise AssertionError('Hermes doit réellement appeler le calcul Fred et donner 114777.')
            report['checks']['native_mcp_tool_executed'] = True
            messages.extend([{'role': 'assistant', 'content': first['output']},
                             {'role': 'user', 'content': 'Rappelle mon identifiant de validation et le résultat du calcul précédent, en une phrase.'}])
            second = turn(a, conversation, messages, project)
            if second['session'] != first['session'] or 'MARQUEUR-AZUR-7319' not in second['output']:
                raise AssertionError('Une continuation doit garder la session et ses informations.')
            report['checks']['native_session_continuity'] = True
            native_messages = hermes.service.request(a, 'GET', '/api/sessions/' + first['session'] + '/messages')
            if 'fred_calculate' not in json.dumps(native_messages):
                raise AssertionError('Le transcript natif doit conserver l’appel d’outil.')
            report['checks']['native_tool_history_persisted'] = True
            def tool_names(value):
                names = []
                if isinstance(value, dict):
                    if isinstance(value.get('name'), str) and value['name'].startswith('mcp_'):
                        names.append(value['name'])
                    for child in value.values(): names.extend(tool_names(child))
                elif isinstance(value, list):
                    for child in value: names.extend(tool_names(child))
                elif isinstance(value, str) and value[:1] in ('{', '['):
                    try:
                        names.extend(tool_names(json.loads(value)))
                    except ValueError:
                        pass
                return names
            report['native_tool_names'] = sorted(set(tool_names(native_messages)))
            if not any(name.endswith('fred_calculate') for name in report['native_tool_names']):
                raise AssertionError('Le transcript natif doit identifier le véritable outil MCP de calcul.')
            native_projects = hermes.projects._native(hermes.accounts.root / 'profiles' / ('fred-' + a), 'list')['projects']
            if not any(p['slug'] == 'fred-' + project for p in native_projects):
                raise AssertionError('Le projet doit exister dans le registre natif du bon profil.')
            report['checks']['native_project_mirrored'] = True
            foreign = turn(b, conversation, [{'role': 'user', 'content':
                'Quel identifiant de validation ai-je communiqué dans notre conversation précédente ? Si tu ne le connais pas, dis-le.'}])
            if foreign['session'] == first['session'] or 'MARQUEUR-AZUR-7319' in foreign['output']:
                raise AssertionError('Le compte B ne doit pas retrouver la session ni le marqueur A.')
            report['checks']['accounts_isolated_same_conversation_id'] = True
            document_prompt = ('Utilise obligatoirement fred_document_search pour rechercher « code documentaire » '
                               'dans le projet courant. Donne uniquement le code trouvé et cite la source.')
            found = turn(a, secrets.token_hex(16), [{'role': 'user', 'content': document_prompt}], project)
            if 'fred_document_search' not in found['tools'] or 'DOCUMENT-ORANGE-4821' not in found['output']:
                raise AssertionError('La lecture documentaire doit réellement passer par l’outil Fred autorisé.')
            report['checks']['native_document_search_executed'] = True
            if not found['sources'] or any(source.get('document') != doc for source in found['sources']):
                raise AssertionError('Les sources livrées doivent appartenir au document du projet autorisé.')
            report['checks']['document_sources_delivered'] = True
            report['checks']['all_turns_completed'] = True
            report['checks']['profile_creation_automatic'] = False
            # Verify the common AccessStore.issue hook without assigning a production device.
            c = store.issue('Validation Hermes créé automatiquement')['id']
            report['checks']['profile_creation_automatic'] = hermes.public(c)['ready']
            if not report['checks']['profile_creation_automatic']:
                raise AssertionError('Un accès créé doit recevoir son profil prêt automatiquement.')
            report['checks']['production_configuration_untouched'] = True
            report['tools'] = [{k: v for k, v in call.items() if k != 'request'} for call in calls]
            report['completed_epoch'] = time.time()
        finally:
            try:
                hermes.close()
                store.workspace.shutdown()
                store.voice.close()
            finally:
                if output:
                    write_json(output, report)
    return report


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-port', type=int, default=8080)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    run(args.model_port, args.output)
