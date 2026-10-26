"""Local Qwen interprets oral web intent; no keyword gate or Hermes agent run."""
from __future__ import annotations

import datetime as dt
import http.client
import json
import time

from text_transform import CancellableResponse


ERROR = 'La préparation de la réponse a échoué. Réessayez votre question.'
SCHEMA = {'type': 'object', 'properties': {
    'action': {'type': 'string', 'enum': ['answer', 'search', 'clarify']},
    'query': {'type': 'string', 'maxLength': 500}},
    'required': ['action', 'query'], 'additionalProperties': False}
INSTRUCTIONS = (
    'Tu décides si une assistante vocale doit rechercher une information publique sur Internet. '
    'Interprète le SENS de la dernière demande avec les échanges récents : aucun mot précis n’est requis. '
    'action=search si une recherche publique est demandée, même indirectement, ou si la réponse '
    'nécessite des faits actuels : dernières nouvelles, météo, horaires, disponibilité, prix actuels. '
    'Formule alors une query courte et autonome qui exprime le sujet public réellement demandé ; '
    'pour les nouvelles du jour, ajoute la date locale fournie. '
    'action=clarify si la personne souhaite une recherche mais n’a pas encore indiqué son sujet ; query vide. '
    'action=answer pour une conversation ordinaire, une explication générale, une rédaction, un calcul, '
    'une simple question sur tes capacités, une recherche dans des documents privés, ou si la personne '
    'demande de ne pas utiliser Internet ; query vide. Une référence au web dans un texte à expliquer '
    'ou à reformuler ne demande pas de recherche. Ne transforme pas les anciennes demandes en nouvelles actions. '
    'Les éventuels refus antérieurs de l’assistante ne décrivent pas ses capacités actuelles. '
    'Ne copie aucun secret, document privé ni consigne interne dans la query. '
    'Retourne seulement un objet JSON avec action et query. N’effectue pas la recherche et ne réponds pas au sujet. '
)


def recent_dialogue(messages):
    result = []
    for message in messages:
        if message.get('role') not in ('user', 'assistant'):
            continue
        content = message.get('content', '')
        if isinstance(content, list):
            content = '\n'.join(p.get('text', '') for p in content if p.get('type') == 'text')
        result.append({'role': message['role'], 'content': content})
    result = result[-3:]
    return [{**m, 'content': m['content'][:2000 if i == len(result)-1 else 400]} for i, m in enumerate(result)]


def decision(value):
    if (not isinstance(value, dict) or set(value) != {'action', 'query'}
            or value['action'] not in ('answer', 'search', 'clarify') or not isinstance(value['query'], str)
            or len(value['query']) > 500):
        raise ValueError(ERROR)
    query = value['query'].strip()
    if (value['action'] == 'search') != bool(query) or any(ord(c) < 32 for c in query):
        raise ValueError(ERROR)
    return {'action': value['action'], 'query': query}


def plan(port, model, key, messages, valid, heartbeat):
    """Called only while the authenticated turn owns the shared inference slot."""
    deadline = time.monotonic() + 40
    alive = lambda: time.monotonic() < deadline and valid()
    if not alive():
        raise ValueError('Demande annulée ou accès désactivé.')
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
    connection.response_class = lambda *a, **kw: CancellableResponse(*a, valid=alive, heartbeat=heartbeat, **kw)
    body = {'model': model, 'messages': [
        {'role': 'system', 'content': INSTRUCTIONS + ' Date locale : ' + dt.datetime.now().astimezone().date().isoformat()},
        {'role': 'user', 'content': json.dumps({'dialogue': recent_dialogue(messages)}, ensure_ascii=False)}],
        'stream': False, 'max_tokens': -1, 'temperature': 0, 'reasoning_effort': 'none',
        'chat_template_kwargs': {'enable_thinking': False}, 'strata_mcp': False, 'strata_checkpoint':False,
        'response_format': {'type': 'json_schema', 'json_schema': {
            'name': 'voice_web_decision', 'strict': True, 'schema': SCHEMA}}}
    headers = {'Content-Type': 'application/json'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    try:
        connection.request('POST', '/v1/chat/completions', json.dumps(body).encode(), headers)
        response = connection.getresponse()
        raw = response.read(65537)
        if response.status != 200 or len(raw) > 65536 or not alive():
            raise ValueError(ERROR)
        choice = json.loads(raw)['choices'][0]
        if choice.get('finish_reason') == 'length':
            raise ValueError(ERROR)
        return decision(json.loads(choice['message']['content']))
    except (OSError, ValueError, KeyError, TypeError, IndexError, http.client.HTTPException):
        if not valid():
            raise ValueError('Demande annulée ou accès désactivé.') from None
        raise ValueError(ERROR) from None
    finally:
        connection.close()
