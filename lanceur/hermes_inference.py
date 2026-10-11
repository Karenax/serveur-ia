"""Private Hermes provider and MCP ingress; only model calls reserve the GPU."""
from __future__ import annotations
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import socket
import threading
import time
from core import health


class HermesPrivateServer:
    def __init__(self, store, backend, *, port=0):
        self.store, self.backend = store, backend
        self.accounts = self.conversations = self.tools = None
        self.models = None
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass

            def respond(self, status, body):
                raw = json.dumps(body, ensure_ascii=False).encode()
                try:
                    self.send_response(status)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Content-Length', str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                except OSError: pass

            def authorized(self, kind):
                value = self.headers.get('Authorization', '')
                token = value[7:] if value.startswith('Bearer ') else ''
                return outer.accounts.authenticate_private(token, kind) if outer.accounts else None

            def body(self, maximum=10 * 1024 * 1024):
                if self.headers.get('Transfer-Encoding') or not self.headers.get('Content-Type', '').startswith('application/json'):
                    raise ValueError('JSON attendu.')
                length = int(self.headers.get('Content-Length', '0'))
                if not 1 <= length <= maximum: raise ValueError('Requête trop volumineuse.')
                result = json.loads(self.rfile.read(length))
                if not isinstance(result, dict): raise ValueError('Objet JSON attendu.')
                return result

            def do_GET(self):
                owner = self.authorized('inference')
                if not owner or not outer.store.valid_owner(owner):
                    return self.respond(401, {'error': {'message': 'Fournisseur privé non autorisé.'}})
                port, model, key = outer.backend()
                if self.path == '/v1/models':
                    return self.respond(200, {'object': 'list', 'data': [{'id': 'fred-qwen', 'object': 'model', 'owned_by': 'fred-local'}]})
                if self.path == '/health':
                    return self.respond(200, {'loaded': bool(health('127.0.0.1', port).get('loaded'))})
                return self.respond(404, {'error': {'message': 'Route privée non disponible.'}})

            def do_POST(self):
                if self.path=='/v1/provider/credential':
                    owner=self.authorized('inference')
                    context=outer.conversations.context(owner) if owner and outer.conversations else None
                    if not context or not outer.conversations.valid(owner,context) or not outer.models:
                        return self.respond(401,{'error':{'message':'Aucune demande fournisseur autorisée.'}})
                    try:
                        value=self.body(4096)
                        selection=context.get('model_selection',{})
                        if set(value)!={'model_id'} or value['model_id']!=selection.get('id'):
                            raise ValueError('Modèle fournisseur non autorisé.')
                        credential=outer.models.credential(owner,selection)
                        if not outer.conversations.valid(owner,context):raise ValueError('Demande désactivée.')
                        return self.respond(200,credential)
                    except Exception:return self.respond(403,{'error':{'message':'Connexion au fournisseur non autorisée ou indisponible.'}})
                if self.path == '/mcp':
                    owner = self.authorized('tool')
                    if not owner: return self.respond(401, {'error': 'Outil non autorisé.'})
                    try:
                        result = outer.tools.dispatch(owner, outer.conversations.context(owner), self.body(2 * 1024 * 1024))
                        if result is None:
                            try:
                                self.send_response(202); self.send_header('Content-Length', '0'); self.end_headers()
                            except OSError: pass
                        else: self.respond(200, result)
                    except (ValueError, OSError, TypeError): self.respond(400, {'error': 'Appel d’outil invalide.'})
                    return
                if self.path != '/v1/chat/completions': return self.respond(404, {'error': {'message': 'Route privée non disponible.'}})
                owner = self.authorized('inference')
                context = outer.conversations.context(owner) if owner and outer.conversations else None
                if not context or not outer.conversations.valid(owner, context):
                    return self.respond(401, {'error': {'message': 'Aucune demande agent autorisée.'}})
                if outer.models and not context.get('model_selection',{}).get('local'):
                    return self.respond(403, {'error': {'message': 'Ce tour utilise un autre fournisseur.'}})
                item = connection = None
                sent = False
                try:
                    data = self.body()
                    messages = data.get('messages')
                    if not isinstance(messages, list) or not 1 <= len(messages) <= 2000: raise ValueError('Messages invalides.')
                    # Every destination/model/auth choice belongs to Fred; this
                    # endpoint cannot proxy URLs or execute Strata host tools.
                    allowed = {'messages', 'stream', 'max_tokens', 'max_completion_tokens', 'temperature', 'top_p',
                               'top_k', 'min_p', 'seed', 'presence_penalty', 'frequency_penalty',
                               'repetition_penalty', 'chat_template_kwargs', 'tools', 'tool_choice',
                               'response_format', 'parallel_tool_calls', 'stream_options', 'reasoning_effort'}
                    data = {k: v for k, v in data.items() if k in allowed}
                    from hermes_reasoning import enforce_local_reasoning
                    data=enforce_local_reasoning(data,context.get('reasoning_request'))
                    data['strata_mcp'] = False
                    cap = data.pop('max_completion_tokens', data.get('max_tokens', 8192))
                    data['max_tokens'] = min(16384, cap) if type(cap) is int and cap > 0 else 8192
                    with outer.conversations.lock:
                        context['model_calls'] += 1
                        if context['model_calls'] > 24: raise ValueError('Limite d’appels au modèle atteinte.')
                    item = outer.store.scheduler.submit(owner, background=context.get('background', False))
                    outer.store.scheduler.wait(item,
                        lambda: outer.conversations.valid(owner, context),
                        lambda position: context.update(inference_phase='queued' if position else 'thinking'))
                    context['inference_phase'] = 'thinking'
                    port, model, key = outer.backend()
                    state = health('127.0.0.1', port)
                    if not state.get('loaded'): raise ValueError('Le modèle local n’est pas chargé.')
                    data['model'] = state.get('model') or model
                    headers = {'Content-Type': 'application/json'}
                    if key: headers['Authorization'] = 'Bearer ' + key
                    remaining = max(1, outer.conversations.timeout - (time.monotonic() - context['created']))
                    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=min(900, remaining))
                    if not outer.conversations.valid(owner, context): raise PermissionError('Demande désactivée.')
                    connection.request('POST', '/v1/chat/completions', json.dumps(data).encode(), headers)
                    upstream = connection.sock

                    def abort():
                        try: upstream.shutdown(socket.SHUT_RDWR)
                        except (OSError, AttributeError): pass

                    with outer.store.scheduler.condition:
                        item['abort'] = abort
                        if item['cancelled']: abort()
                    response = connection.getresponse()
                    self.send_response(response.status)
                    self.send_header('Content-Type', 'text/event-stream' if data.get('stream') and response.status == 200 else 'application/json')
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Connection', 'close')
                    self.end_headers(); sent = True
                    if data.get('stream') and response.status == 200:
                        finished = False
                        while True:
                            line = response.readline(2 * 1024 * 1024)
                            if not line: break
                            if item['cancelled'] or not outer.conversations.valid(owner, context): raise PermissionError('Demande désactivée.')
                            if line.startswith(b'data: ') and line.strip() != b'data: [DONE]':
                                try:
                                    event = json.loads(line[6:])
                                    usage = event.get('usage', {})
                                    if isinstance(usage, dict): context['tokens'] += max(0, usage.get('completion_tokens', 0))
                                    if event.get('error'): item['backend_error'] = True
                                except (ValueError, TypeError): pass
                            self.wfile.write(line); self.wfile.flush()
                            outer.store.scheduler.progress(item)
                            if line.strip() == b'data: [DONE]': finished = True
                        if not finished: raise ValueError('Flux du modèle interrompu.')
                    else:
                        total = 0
                        while True:
                            block = response.read1(65536)
                            if not block: break
                            total += len(block)
                            if total > 8 * 1024 * 1024: raise ValueError('Réponse du moteur trop volumineuse.')
                            if item['cancelled'] or not outer.conversations.valid(owner, context): raise PermissionError('Demande désactivée.')
                            self.wfile.write(block); self.wfile.flush(); outer.store.scheduler.progress(item)
                    item['succeeded'] = response.status == 200 and not item.get('backend_error')
                except (ValueError, OSError, TypeError, http.client.HTTPException) as error:
                    if not sent:
                        try: self.respond(503, {'error': {'message': 'Le fournisseur local n’a pas pu terminer la génération.'}})
                        except OSError: pass
                    elif data.get('stream'):
                        try:
                            self.wfile.write(b'data: {"error":{"message":"Le fournisseur local a interrompu la generation."}}\n\n')
                            self.wfile.flush()
                        except OSError: pass
                finally:
                    context['inference_phase'] = ''
                    if connection: connection.close()
                    if item: outer.store.scheduler.finish(item)

        self.server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
        self.server.daemon_threads = True
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)
        self.thread = None

    def start(self):
        if self.thread and self.thread.is_alive(): return
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name='fred-hermes-private')
        self.thread.start()

    def close(self):
        if self.thread: self.server.shutdown()
        self.server.server_close()
