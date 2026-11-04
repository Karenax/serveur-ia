"""Stateless Responses transport for Codex; tools always run on the client.

Use Strata's native Responses dialect rather than translating or buffering its
events. Only the configured loopback model is reachable through this route.
"""
import http.client
import json
import select
import socket
import threading
import time

from http_boundary import json_body
from kiara_shared.attachments import image_data


class RequestError(ValueError):
    def __init__(self, message, param=None):
        super().__init__(message)
        self.param = param


class UpstreamError(RequestError):
    def __init__(self, message, status, code, param=None):
        super().__init__(message, param)
        self.status, self.code = status, code


def error_body(message, code='invalid_request_error', param=None):
    return {'error': {'message': message, 'type': code, 'code': code, 'param': param}}


def responses_request(raw):
    if not isinstance(raw, dict):
        raise RequestError('Objet JSON attendu.')
    allowed = {'model', 'input', 'instructions', 'tools', 'tool_choice', 'parallel_tool_calls',
               'stream', 'store', 'max_output_tokens', 'reasoning', 'text', 'include',
               'temperature', 'top_p', 'metadata', 'prompt_cache_key', 'prompt_cache_retention',
               'service_tier', 'safety_identifier', 'user', 'truncation', 'client_metadata'}
    unknown = set(raw) - allowed
    if unknown:
        raise RequestError('Paramètre Responses non pris en charge.', sorted(unknown)[0])
    if not isinstance(raw.get('model'), str) or not raw['model']:
        raise RequestError('Identifiant de modèle attendu.', 'model')
    for name in ('stream', 'store', 'parallel_tool_calls'):
        if name in raw and type(raw[name]) is not bool:
            raise RequestError('Option booléenne attendue.', name)
    limit = raw.get('max_output_tokens')
    if limit is not None and (type(limit) is not int or limit < 1):
        raise RequestError('Limite de sortie positive attendue.', 'max_output_tokens')
    if 'instructions' in raw and raw['instructions'] is not None and not isinstance(raw['instructions'], str):
        raise RequestError('Instructions texte attendues.', 'instructions')
    items = raw.get('input')
    if not isinstance(items, str) and not (isinstance(items, list) and 1 <= len(items) <= 4000):
        raise RequestError('Texte ou historique Responses attendu.', 'input')
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                raise RequestError('Élément de conversation invalide.', 'input')
            for name in ('content', 'output'):
                parts = item.get(name)
                if isinstance(parts, list):
                    for part in parts:
                        if not isinstance(part, dict):
                            raise RequestError('Contenu invalide.', 'input')
                        if part.get('type') in ('input_image', 'image_url'):
                            url = part.get('image_url')
                            if isinstance(url, dict): url = url.get('url')
                            image_data(url)  # Never let Strata fetch URLs or server files.
    tools = raw.get('tools', [])
    if not isinstance(tools, list) or len(tools) > 512:
        raise RequestError('Liste d’outils invalide.', 'tools')
    def check_tools(values, depth=0):
        if depth > 4:
            raise RequestError('Espaces de noms trop imbriqués.', 'tools')
        for tool in values:
            if not isinstance(tool, dict) or tool.get('type') not in ('function', 'custom', 'namespace'):
                raise RequestError('Seuls les outils exécutés par le client sont disponibles.', 'tools')
            if tool['type'] == 'namespace':
                nested = tool.get('tools')
                if not isinstance(nested, list):
                    raise RequestError('Espace de noms invalide.', 'tools')
                check_tools(nested, depth + 1)
    check_tools(tools)
    for item in items if isinstance(items, list) else []:
        if item.get('type') == 'additional_tools':
            extra = item.get('tools', [])
            if not isinstance(extra, list): raise RequestError('Liste d’outils invalide.', 'input')
            check_tools(extra)
    # No server-side history is exposed, shared or persisted by this API.
    return dict(raw, store=False)


def handle(handler, store, backend):
    if not handler.authorized(): return
    if handler.headers.get('Transfer-Encoding') or not handler.headers.get('Content-Type', '').startswith('application/json'):
        return handler.respond(415, error_body('Corps JSON attendu.'))
    from core import health
    from hermes_models import ModelUnavailable
    from workspace import Denied
    try:
        data = responses_request(json_body(handler, 10 * 1024 * 1024))
        port, native_model, key = backend()
        selection = None
        if store.hermes and hasattr(store.hermes, 'select_model'):
            selection = store.hermes.select_model(handler.identity, data['model'])
            if not selection.get('local', True):
                return handler.respond(400, error_body('Cette route Responses est réservée à Qwen local.', 'model_not_supported', 'model'))
        elif data['model'] not in ('fred-qwen', native_model):
            return handler.respond(404, error_body('Modèle inconnu.', 'model_not_found', 'model'))
        live = health('127.0.0.1', port)
        if not live.get('loaded'):
            return handler.respond(503, error_body('Le modèle local n’est pas chargé.', 'model_unavailable'))
        public_model = selection['id'] if selection else data['model']
    except Denied as error:
        return handler.respond(403, error_body(str(error), 'model_access_denied'))
    except ModelUnavailable as error:
        return handler.respond(503, error_body(str(error), 'model_unavailable'))
    except (ValueError, TypeError, OSError) as error:
        return handler.respond(400, error_body(str(error), param=getattr(error, 'param', None)))

    try:
        item = store.scheduler.submit(handler.identity, handler.headers.get('X-Qwen-Request') or None, concurrent=True)
    except ValueError as error:
        return handler.respond(429, error_body(str(error), 'rate_limit_exceeded'))

    scheduler = store.scheduler
    connection = None
    sent = False
    active = False
    stopped = threading.Event()
    monitor = None
    response_id = 'resp_' + item['id']
    last_sequence = -1

    def valid():
        return (not item['cancelled'] and store.authenticate(handler.access_token) == handler.identity
                and (selection is None or not hasattr(store.hermes, 'models') or store.hermes.models.valid(handler.identity, selection)))

    def disconnected():
        return bool(select.select([handler.connection], [], [], 0)[0] and handler.connection.recv(1, socket.MSG_PEEK) == b'')

    def heartbeat(position=None):
        if disconnected(): raise OSError('Client déconnecté.')
        if sent:
            handler.wfile.write(b': kiara-keepalive\n\n'); handler.wfile.flush()

    def start(status=200):
        nonlocal sent
        handler.send_response(status)
        handler.send_header('Content-Type', 'text/event-stream' if data.get('stream') and status == 200 else 'application/json; charset=utf-8')
        handler.send_header('Cache-Control', 'no-store')
        handler.send_header('X-Content-Type-Options', 'nosniff')
        handler.send_header('Connection', 'close')
        handler.end_headers()
        sent = True

    try:
        with store.lock:
            if not valid(): raise ValueError('Accès désactivé.')
            store.active += 1; active = True
            if data.get('stream'): start()
        scheduler.wait(item, valid, heartbeat)
        heartbeat()
        if not valid(): raise ValueError('Accès désactivé.')
        store.audit('inference_started', handler.identity)
        headers = {'Content-Type': 'application/json'}
        if key: headers['Authorization'] = 'Bearer ' + key
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=120)
        connection.connect()
        upstream_socket = connection.sock
        def abort():
            try: upstream_socket.shutdown(socket.SHUT_RDWR)
            except OSError: pass
        with scheduler.condition:
            item['abort'] = abort
            if item['cancelled']: abort()
        def watch():
            deadline = time.monotonic() + 900
            while not stopped.wait(.5):
                try: cancelled = not valid() or disconnected() or time.monotonic() > deadline
                except OSError: cancelled = True
                if cancelled:
                    scheduler.cancel(handler.identity, item['id']); return
        monitor = threading.Thread(target=watch, daemon=True); monitor.start()
        connection.request('POST', '/v1/responses', json.dumps(data).encode(), headers)
        response = connection.getresponse()
        if not valid(): raise ValueError('Accès désactivé.')
        if response.status != 200:
            body = response.read(65536)
            try: detail = json.loads(body).get('error', {})
            except (ValueError, AttributeError): detail = {}
            # Engine details stay in server diagnostics; keep useful error codes.
            store.inference_failure(response.status, str(detail.get('message', 'Responses refusé.')), item['id'])
            code = detail.get('code') or 'upstream_error'
            raise UpstreamError('Le moteur local a refusé la demande Responses (' + str(code) + ').', response.status, code, detail.get('param'))
        if data.get('stream'):
            terminal = False
            while True:
                line = response.readline(2 * 1024 * 1024 + 1)
                if not line: break
                if len(line) > 2 * 1024 * 1024: raise ValueError('Événement Responses trop volumineux.')
                if not valid(): raise ValueError('Demande annulée ou accès désactivé.')
                if line.startswith(b'data: '):
                    event = json.loads(line[6:])
                    if type(event.get('sequence_number')) is int: last_sequence = event['sequence_number']
                    kind = event.get('type')
                    envelope = event.get('response', {})
                    if isinstance(event.get('response'), dict):
                        envelope['model'] = public_model
                        line = b'data: ' + json.dumps(event, ensure_ascii=False).encode() + b'\n'
                    response_id = envelope.get('id', response_id)
                    if kind in ('response.completed', 'response.incomplete', 'response.failed', 'error'):
                        terminal = True
                        item['succeeded'] = kind == 'response.completed' and envelope.get('status') == 'completed'
                scheduler.progress(item)
                handler.wfile.write(line); handler.wfile.flush()
            if not terminal: raise ValueError('Flux Responses interrompu avant sa confirmation de fin.')
        else:
            body = response.read(16 * 1024 * 1024 + 1)
            if len(body) > 16 * 1024 * 1024: raise ValueError('Réponse trop volumineuse.')
            if not valid(): raise ValueError('Demande annulée ou accès désactivé.')
            result = json.loads(body)
            result['model'] = public_model
            item['succeeded'] = result.get('status') == 'completed'
            start()
            handler.wfile.write(json.dumps(result, ensure_ascii=False).encode()); handler.wfile.flush()
    except (OSError, ValueError, TypeError, http.client.HTTPException) as error:
        item['succeeded'] = False
        body = (error_body(str(error), error.code, error.param) if isinstance(error, UpstreamError)
                else error_body('Demande Responses interrompue ou refusée.', 'responses_failed'))
        try:
            if sent and data.get('stream'):
                event = {'type': 'response.failed', 'sequence_number': last_sequence + 1,
                         'response': {'id': response_id, 'object': 'response', 'status': 'failed', 'output': [], 'error': body['error']}}
                handler.wfile.write(('\n\nevent: response.failed\ndata: ' + json.dumps(event) + '\n\n').encode()); handler.wfile.flush()
            elif not sent: handler.respond(error.status if isinstance(error, UpstreamError) else 503, body)
        except OSError: pass
    finally:
        stopped.set()
        if connection: connection.close()
        if monitor: monitor.join(timeout=2)
        if active:
            with store.lock: store.active -= 1
        scheduler.finish(item)
