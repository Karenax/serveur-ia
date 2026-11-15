"""Authenticated transport to the private Agent service."""

import http.client
import sqlite3
import json
from urllib.parse import unquote, urlencode, urlsplit

from kiara_shared.agent_auth import issue
from kiara_shared.agent_http import AGENT_RESPONSE_HEADERS
from kiara_shared.history_store import is_agent_project_id
from kiara_shared.thunderbird import PREFIX as THUNDERBIRD_PREFIX, bridge_route
from workspace_types import Conflict, Denied

PREFIX = '/v1/business'
MAX_BODY = 272 * 1024 * 1024


class AgentBridge:
    def __init__(self, port, key, operator_for, thunderbird_device=None):
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError('Port Agent invalide')
        if not isinstance(key, bytes) or len(key) < 32:
            raise ValueError('Clé Agent invalide')
        self.port = port
        self.key = key
        self.operator_for = operator_for
        self.thunderbird_device = thunderbird_device


def project_context(store, owner, project, query):
    if not is_agent_project_id(project):
        raise ValueError('Identifiant de projet invalide.')
    target = f'/internal/kiara/projects/{project}/context?' + urlencode({'q': query[:500]})
    result = project_request(store, owner, 'GET', target)
    memories = project_request(store, owner, 'GET', '/internal/kiara/memories?' + urlencode({'project': project}))
    return {**result, 'memories': [memory['text'] for memory in memories]}


def project_request(store, owner, method, target, data=None):
    bridge = store.agent_bridge
    if bridge is None:
        raise ValueError('Le service Projets de Kiara est indisponible.')
    operator = bridge.operator_for(owner)
    if operator is None:
        raise Denied('Accès aux projets Kiara refusé.')
    timeout = 2 if target == '/internal/kiara/transcriptions' else 30
    connection = http.client.HTTPConnection('127.0.0.1', bridge.port, timeout=timeout)
    try:
        # Private Kiara data follows the device, even if
        # several devices are mapped to the same Agent business operator.
        private = target.startswith('/internal/kiara/') and any(part in target for part in ('/conversations', '/memories'))
        actor = {**operator, 'id': owner} if private else operator
        headers = {'X-Kiara-Agent-Context': issue(bridge.key, method, target, actor)}
        body = None
        if data is not None:
            headers['Content-Type'] = 'application/json'
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        connection.request(method, target, body, headers)
        response = connection.getresponse()
        if response.status in (403, 404):
            raise Denied('Projet introuvable ou accès refusé.')
        if response.status == 409:
            if '/memories' in target:
                raise Conflict('Ce souvenir a changé. Rechargez sa version actuelle.')
            if '/conversations' in target:
                raise Conflict('Discussion ou projet modifié. Actualisez avant de réessayer.')
            raise ValueError('Projet archivé : restaurez-le avant de travailler.')
        if response.status == 422:
            raise ValueError('Vérifiez les informations du projet.')
        limit = (10 if '/conversations?id=' in target else 4) * 1024 * 1024
        payload = response.read(limit + 1)
        if response.status not in (200, 201) or len(payload) > limit:
            raise ValueError('Le service Projets de Kiara est indisponible.')
        result = json.loads(payload)
    except (OSError, http.client.HTTPException, json.JSONDecodeError) as error:
        raise ValueError('Le service Projets de Kiara est indisponible.') from error
    finally:
        connection.close()
    if store.agent_bridge is not bridge or bridge.operator_for(owner) != operator:
        raise Denied('Vos droits d’accès aux projets ont changé.')
    return result


def project_catalogue(store, owner):
    bridge = store.agent_bridge
    if bridge is None:
        return {'state': 'unavailable', 'can_create': False, 'projects': []}
    operator = bridge.operator_for(owner)
    if operator is None:
        return {'state': 'forbidden', 'can_create': False, 'projects': []}
    rows = project_request(store, owner, 'GET', '/api/v1/project-catalogue')
    conversations = project_request(store, owner, 'GET', '/internal/kiara/conversations') if rows else []
    memories = project_request(store, owner, 'GET', '/internal/kiara/memories') if rows else []
    by_project = {}
    for conversation in conversations:
        by_project.setdefault(conversation['project'], []).append(conversation)
    memories_by_project = {}
    for memory in memories:
        memories_by_project.setdefault(memory['project'], []).append(memory)
    if store.agent_bridge is not bridge or bridge.operator_for(owner) != operator:
        raise Denied('Vos droits d’accès aux projets ont changé.')
    return {'state': 'ready', 'can_create': operator['role'] != 'reader' and operator['project_ids'] is None,
            'projects': [{'id': row['id'], 'title': row['title'], 'code': row['code'],
                          'archived': row['status'] == 'archived', 'can_edit': operator['role'] != 'reader',
                          'project_kind': 'managed',
                          'has_knowledge': bool(row['brain_project_id']) if 'brain_project_id' in row else None,
                          'instructions': '', 'documents': [],
                          'conversations': by_project.get(row['id'], []),
                          'memories': memories_by_project.get(row['id'], [])} for row in rows]}


def handle(handler, store):
    if not handler.authorized():
        return
    parsed = urlsplit(handler.path)
    proxy(handler, store, parsed.path[len(PREFIX):], parsed.query, handler.identity,
          lambda: store.authenticate(handler.access_token) == handler.identity)


def proxy(handler, store, path, query, identity, access_valid, *, browser=False, browser_prefix=''):
    with store.lock:
        maintenance = store.maintenance
        if not maintenance:
            store.agent_active += 1
    if maintenance:
        return handler.respond(503, {'error': {'message': 'L’espace de travail Kiara est en maintenance.'}})
    try:
        return _proxy(handler, store, path, query, identity, access_valid, browser=browser, browser_prefix=browser_prefix)
    finally:
        with store.lock:
            store.agent_active -= 1


def _proxy(handler, store, path, query, identity, access_valid, *, browser, browser_prefix):
    bridge = getattr(store, 'agent_bridge', None)
    if bridge is None:
        return handler.respond(503, {'error': {'message': 'L’espace de travail Kiara est indisponible.'}})
    decoded = unquote(path)
    if not path.startswith(('/api/v1/', '/v1/', '/assets/', '/app/')) and path not in ('/app', '/api/v1/session'):
        return handler.respond(404, {'error': {'message': 'Cette fonction Kiara est indisponible.'}})
    if ('\\' in decoded or any(part in ('.', '..') for part in decoded.split('/'))
            or ('/native-capture' in decoded and handler.command != 'GET')
            or decoded.startswith('/api/v1/open-path')):
        return handler.respond(403, {'error': {'message': 'Action locale indisponible.'}})
    if handler.headers.get('Transfer-Encoding') or len(handler.headers.get_all('Content-Length', [])) > 1:
        return handler.respond(400, {'error': {'message': 'Transfert non reconnu.'}})
    connection = None
    try:
        size = int(handler.headers.get('Content-Length', '0'))
        if size < 0 or size > MAX_BODY:
            raise ValueError('Taille invalide')
        operator = bridge.operator_for(identity)
        if operator is None:
            return handler.respond(403, {'error': {'message': 'Accès à l’espace de travail Kiara refusé.'}})
        thunderbird = decoded.startswith(THUNDERBIRD_PREFIX)
        if thunderbird and (
                browser or handler.command != 'POST' or query or not bridge_route(path)
                or identity != bridge.thunderbird_device or operator['role'] == 'reader'):
            return handler.respond(403, {'detail': 'Appareil Thunderbird non autorisé.'})
        reply_route = ((handler.command, path) in {('GET', '/v1/thunderbird/status'),
                                                   ('POST', '/v1/thunderbird/drafts')})
        scoped_thunderbird = (reply_route and not browser and not query and identity == bridge.thunderbird_device
                              and operator['project_ids'] is not None and operator['role'] != 'reader')
        def authorized():
            return (store.agent_bridge is bridge and access_valid() and bridge.operator_for(identity) == operator
                    and (not (thunderbird or scoped_thunderbird) or identity == bridge.thunderbird_device))

        if not authorized():
            return handler.respond(403, {'error': {'message': 'Accès désactivé.'}})
        target = path + ('?' + query if query else '')
        context = ({**operator, 'id': 'kiara-thunderbird', 'project_ids': []} if thunderbird else operator)
        if scoped_thunderbird:
            context = {**operator, 'id': 'kiara-thunderbird-reply'}
        token = issue(bridge.key, handler.command, target, context)
        connection = http.client.HTTPConnection('127.0.0.1', bridge.port, timeout=600)
        connection.putrequest(handler.command, target, skip_accept_encoding=True)
        connection.putheader('X-Kiara-Agent-Context', token)
        connection.putheader('Content-Length', str(size))
        app_page = browser and (path == '/app' or path.startswith('/app/'))
        forwarded = ('Content-Type', 'Accept') if app_page else (
            'Content-Type', 'Accept', 'Range', 'If-Range', 'If-Match', 'If-None-Match')
        for name in forwarded:
            if handler.headers.get(name):
                connection.putheader(name, handler.headers[name])
        connection.endheaders()
        remaining = size
        while remaining:
            if not authorized():
                connection.close()
                return
            chunk = handler.rfile.read(min(65536, remaining))
            if not chunk:
                raise OSError('Requête interrompue')
            if not authorized():
                connection.close()
                return
            connection.send(chunk)
            remaining -= len(chunk)
        response = connection.getresponse()
    except (OSError, ValueError, TypeError, sqlite3.Error, http.client.HTTPException):
        if connection is not None:
            connection.close()
        return handler.respond(503, {'error': {'message': 'L’espace de travail Kiara est indisponible.'}})
    try:
        if not authorized():
            return handler.respond(403, {'error': {'message': 'Accès désactivé.'}})
        page = None
        if (app_page and handler.command == 'GET' and response.status == 200
                and response.getheader('Content-Type', '').startswith('text/html')):
            page = response.read(1024 * 1024 + 1)
            if len(page) > 1024 * 1024:
                return handler.respond(503, {'detail': 'L’espace de travail Kiara est indisponible.'})
            page = page.replace(b'="/assets/', b'="' + browser_prefix.encode('ascii') + b'/assets/')
            if getattr(handler, 'browser_conversation', None):
                page = page.replace(b'<body', b'<body data-kiara-web-conversations="true"', 1)
        if not authorized():
            return handler.respond(403, {'error': {'message': 'Accès désactivé.'}})
        handler.send_response(response.status)
        for name in (*AGENT_RESPONSE_HEADERS, 'Permissions-Policy', 'Referrer-Policy', 'X-Frame-Options'):
            if page is not None and name.lower() in ('content-length', 'etag'):
                continue
            if browser and name == 'Cache-Control':
                handler.send_header(name, 'private, no-store')
                continue
            if browser and name == 'Referrer-Policy':
                handler.send_header(name, 'same-origin')
                continue
            value = response.getheader(name)
            if value:
                handler.send_header(name, value)
        handler.send_header('Connection', 'close')
        if page is not None:
            handler.send_header('Content-Length', str(len(page)))
        handler.end_headers()
        if page is not None:
            handler.wfile.write(page)
            return
        while True:
            if not authorized():
                return
            chunk = response.read1(65536)
            if not chunk:
                return
            if not authorized():
                return
            handler.wfile.write(chunk)
    except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
        return
    finally:
        try:
            response.close()
        finally:
            connection.close()
