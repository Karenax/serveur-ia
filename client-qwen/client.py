"""Portable WireGuard client exposing an authenticated loopback API and chat."""
from __future__ import annotations
import ctypes
import copy
from collections import deque
from ctypes import wintypes
import hashlib
import hmac
import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import struct
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import urllib.error
import urllib.request
import time
from updater import VERSION
from product import APP_NAME, LOCAL_API_PORT, LOCAL_API_LAST_PORT
import history_store
from urllib.parse import urlsplit
from wg_bridge import Bridge,validate_profile,validate_endpoint,connection_candidates
from connection_settings import parse as parse_connection_settings, validate_connection_endpoint, HTTPS_ENDPOINT
import app_integrations

class Blob(ctypes.Structure):
    _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_ubyte))]

def protect(value, decrypt=False):
    raw = value if isinstance(value, bytes) else value.encode()
    buffer = ctypes.create_string_buffer(raw)
    source = Blob(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    destination = Blob()
    dll = ctypes.WinDLL('crypt32', use_last_error=True)
    function = dll.CryptUnprotectData if decrypt else dll.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(destination)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(destination.pbData, destination.cbData)
    finally:
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree.restype = ctypes.c_void_p
        kernel.LocalFree(destination.pbData)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None

class Remote:
    def __init__(self, profile, opener=None, endpoint=None, connection_required=False):
        validate_profile(profile)
        self.profile=copy.deepcopy(profile)
        self.url=profile['url']
        self.token = profile['token']
        if not isinstance(self.token, str) or not self.token.startswith('qwen_') or not 50 <= len(self.token) <= 256:
            raise ValueError('Accès serveur invalide.')
        self.mock=opener is not None
        self.bridge=None
        self.bridge_lock=threading.RLock()
        self.opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        # Default HTTPSHandler verifies the certificate; honor the workplace proxy.
        self.https_opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler(),NoRedirect())
        self.model = ''
        self.models = []
        self.model_capabilities = {}
        self.connection_required = connection_required
        self.session = ""
        self.username = ""
        self.expires_epoch = 0
        self.update_state = {"message":"Cliquer sur Vérifier pour rechercher une mise à jour."}
        self.update_lock = threading.Lock()
        self.activity_lock = threading.RLock()
        self.active_requests = 0
        self.applying_update = False
        self.window = None
        self.connected = False
        self.reachable = False
        self.error = 'Connexion au serveur IA…'
        self.code = 'connecting'
        self.checked_at = 0
        self.diagnostic = {}
        self.events=deque(maxlen=60);self.bridge_starts=0;self.attempts=0
        self.checking=False;self.last_contact=0;self.stream={}
        self.override=validate_connection_endpoint(endpoint) if endpoint else None
        self.candidates=[self.override] if self.override else connection_candidates(profile)
        self.endpoint=self.candidates[0]
        if self.connection_required:
            self.code='connection_selection_required';self.error='Choisissez le mode de connexion.'

    def _switch_endpoint(self,endpoint):
        if self.bridge:self.bridge.close();self.bridge=None
        self.endpoint=endpoint;self.diagnostic={}
        self.event('endpoint_selected')

    def event(self,name,**values):
        self.events.append({'time':time.time(),'event':name,'endpoint':self.endpoint,**values})

    def refresh_diagnostic(self):
        if self.mock or not self.bridge_lock.acquire(blocking=False):return
        try:
            if self.bridge:
                if self.bridge.process.poll() is not None:self.failure('connection_error','Le moteur WireGuard s’est arrêté. Réessayer la connexion.')
                else:self.diagnostic=self.bridge.status(self.opener)
        finally:self.bridge_lock.release()

    def set_endpoint(self,endpoint=None):
        endpoint=validate_connection_endpoint(endpoint) if endpoint else None
        with self.activity_lock, self.bridge_lock:
            if self.active_requests or self.applying_update:
                raise ValueError('Attendre la fin de la génération ou de la mise à jour avant de changer d’adresse.')
            self.connection_required=False
            self.override=endpoint
            self.candidates=[endpoint] if endpoint else connection_candidates(self.profile)
            self._switch_endpoint(self.candidates[0])
            self.connected=False;self.reachable=False
            self.model='';self.models=[]
            self.error='Connexion au serveur IA…'
            self.code='connecting';self.checked_at=0;self.diagnostic={}

    def state(self):
        return {'connection_required':self.connection_required,'connected':self.connected,'reachable':self.reachable,'model':self.model,
                'models':list(self.models),'error':self.error,'code':self.code,
                'endpoint':self.endpoint,'automatic':self.override is None,
                'transport':'https' if self.endpoint==HTTPS_ENDPOINT else 'wireguard',
                'checked_at':self.checked_at,'checking':self.checking,'attempts':self.attempts,
                'bridge_starts':self.bridge_starts,'last_contact':self.last_contact,
                'events':list(self.events)[-12:],'stream':dict(self.stream),**self.diagnostic}

    def failure(self,code,message):
        network=code in ('wireguard_unreachable','tunnel_request_failed','connection_error')
        if not network and code not in ('gateway_unavailable','access_denied','access_revoked',
                'access_suspended','access_expired','remote_disabled','model_unloaded','no_models'):return
        self.connected=False;self.reachable=not network
        self.code=code;self.error=message;self.checked_at=time.time()
        self.event('connection_failed',code=code)

    def select_model(self,model):
        with self.bridge_lock:
            if model not in self.models:raise ValueError('Ce modèle ne figure pas dans le dernier scan du serveur.')
            self.model=model

    def open(self, path, data=None, request_id=None):
        if not isinstance(path,str) or not path.startswith('/v1/') or any(c in path for c in ('\\','\r','\n')):
            raise ValueError('Route API invalide.')
        with self.bridge_lock:
            if self.connection_required:raise ValueError('Choisissez le mode de connexion avant de contacter le serveur.')
            https=self.endpoint==HTTPS_ENDPOINT
            if not self.mock and not https:
                if self.bridge and self.bridge.process.poll() is not None:
                    self.bridge.close();self.bridge=None
                if self.bridge is None:
                    profile=copy.deepcopy(self.profile)
                    profile['wireguard']['endpoint']=self.endpoint
                    self.bridge=Bridge(profile)
                    self.bridge_starts+=1;self.event('wireguard_started',number=self.bridge_starts)
            url=HTTPS_ENDPOINT if https else self.url if self.mock else self.bridge.url
            headers={'Authorization':'Bearer '+self.token} if self.mock or https else {'X-Qwen-Bridge':self.bridge.key}
            opener=self.https_opener if https else self.opener
        # Capture the URL and its matching secret together; a reconnect may replace the bridge.
        request = urllib.request.Request(url + path, data=data,
            headers={**headers, 'User-Agent':'AccesServeurFred/'+VERSION+' (Windows; '+('HTTPS' if https else 'WireGuard')+')', 'Content-Type': 'application/json','X-Qwen-Session':self.session,**({'X-Qwen-Request':request_id} if request_id else {})})
        try:
            response=opener.open(request, timeout=900 if path=="/v1/chat/completions" else 120 if path=="/v1/client/download" else 60 if path in ("/v1/workspace/action","/v1/history") else 3 if path=="/v1/device" else 30)
            self.last_contact=time.time();self.event('server_response',route=path,status=getattr(response,'status',200))
            return response
        except urllib.error.HTTPError as error:
            # Preserve the response body for callers after inspecting the structured error.
            raw=error.read(65536)
            try:
                detail=json.loads(raw).get('error',{})
                if isinstance(detail,dict):self.failure(detail.get('code'),detail.get('message','Serveur indisponible.'))
            except (ValueError,AttributeError):pass
            response=urllib.error.HTTPError(error.url,error.code,error.reason,error.headers,io.BytesIO(raw))
            error.close()
            raise response from None
        except (OSError,urllib.error.URLError):
            self.failure('connection_error','Connexion au serveur IA interrompue. Vérifier le réseau puis réessayer.')
            raise

    def update(self,apply=False):
        with self.activity_lock:
            if self.applying_update:raise ValueError('Installation en cours. Attendre le redémarrage du client.')
            if not self.update_lock.acquire(blocking=False):raise ValueError('Une mise à jour est déjà en cours.')
            if apply:self.applying_update=True
        self.update_state={'busy':True,'message':'Téléchargement et vérification…' if apply else 'Vérification de la version serveur…'}
        def work():
            prepared=False
            try:
                import updater
                if apply:
                    updater.prepare(self,protect)
                    prepared=True
                    self.update_state={'busy':False,'message':'Mise à jour vérifiée. Redémarrage du client…'}
                    if self.window:self.window.destroy()
                else:
                    release=updater.check(self)
                    self.update_state={**release,'busy':False,'message':('Version '+release['version']+' disponible.' if release['available'] else 'Client à jour · '+VERSION)}
            except Exception as error:self.update_state={'busy':False,'message':str(error),'error':True}
            finally:
                with self.activity_lock:
                    if not prepared:self.applying_update=False
                self.update_lock.release()
        threading.Thread(target=work,daemon=True).start()
        return self.update_state

    def close(self):
        with self.bridge_lock:
            if self.bridge:self.bridge.close();self.bridge=None

    def check(self):
        with self.bridge_lock:
            if self.connection_required or self.active_requests or self.applying_update:
                return self.state()
            candidates=list(dict.fromkeys([self.endpoint,*self.candidates]))
            self.checking=True
            code='wireguard_unreachable';diagnostic={}
            for endpoint in candidates:
                if endpoint!=self.endpoint:self._switch_endpoint(endpoint)
                self.attempts+=1;self.event('connection_probe',attempt=self.attempts)
                self.connected=False;self.reachable=False
                try:
                    with self.open('/v1/models') as response:
                        data=json.load(response).get('data')
                    if not isinstance(data,list):raise ValueError('Liste des modèles invalide dans /v1/models.')
                    # Display hints only; older servers may not implement this route.
                    if time.time()-getattr(self,'device_reported_at',0)>=60:
                        self.device_reported_at=time.time()
                        try:
                            declaration={'kind':'pc','version':VERSION,'transport':'https' if self.endpoint==HTTPS_ENDPOINT else 'wireguard'}
                            with self.open('/v1/device',json.dumps(declaration).encode()) as response:response.read(2048)
                        except urllib.error.HTTPError as error:
                            if error.code in (401,403):raise
                            error.close()
                        except (OSError,ValueError):pass
                    models=list(dict.fromkeys(row['id'] for row in data if isinstance(row,dict) and isinstance(row.get('id'),str) and row['id'].strip() and len(row['id'])<=512))
                    self.model_capabilities={row['id']:row.get('capabilities',{}) for row in data if isinstance(row,dict) and row.get('id') in models and isinstance(row.get('capabilities',{}),dict)}
                    self.models=models;self.reachable=True
                    if models:
                        if self.model not in models:self.model=models[0]
                        self.connected=True;self.error='';code='ready'
                    else:
                        self.model='';self.error='Serveur joint, mais aucun modèle accessible n’est annoncé par /v1/models.';code='no_models'
                except urllib.error.HTTPError as error:
                    try: detail=json.loads(error.read(65536)).get('error',{})
                    except (OSError,ValueError,AttributeError):detail={}
                    finally:error.close()
                    if not isinstance(detail,dict):detail={}
                    code=detail.get('code','http_'+str(error.code))
                    message=detail.get('message','')
                    if not isinstance(message,str):message=''
                    if error.code==401:
                        code=detail.get('code','access_denied');self.error=message or 'Serveur joint, mais accès désactivé ou révoqué.';self.reachable=True
                        if code=='login_required':self.session='';self.username=''
                    elif code=='model_unloaded' or 'modèle n’est pas chargé' in message:
                        code='model_unloaded';self.error='Serveur connecté, mais modèle non chargé. Le lancer dans la console serveur.';self.reachable=True
                    elif code in ('wireguard_unreachable','tunnel_request_failed') or 'serveur WireGuard' in message:
                        if code not in ('wireguard_unreachable','tunnel_request_failed'):code='wireguard_unreachable'
                        self.error=message or 'Aucune réponse WireGuard : vérifier adresse, port UDP, pare-feu ou accès client.'
                    else:
                        self.error=message if isinstance(message,str) and message else 'Le serveur a répondu avec une erreur HTTP '+str(error.code)+'.'
                        self.reachable=True
                except (OSError,ValueError,KeyError,IndexError,TypeError,AttributeError) as error:
                    code='connection_error'
                    self.error=str(error) if isinstance(error,ValueError) else ('Connexion HTTPS impossible : vérifier le réseau, le proxy et le certificat.' if self.endpoint==HTTPS_ENDPOINT else 'Connexion impossible : vérifier l’adresse du serveur et son port UDP.')
                diagnostic=self.bridge.status(self.opener) if self.bridge and not self.mock else {}
                if self.reachable:break
            if not self.connected:self.models=[];self.model=''
            self.code=code;self.diagnostic=diagnostic;self.checked_at=time.time();self.checking=False
            return self.state()

def serve_local(remote, key, port=LOCAL_API_PORT):
    from local_voice import VoiceService
    voice=VoiceService(Path(getattr(sys, "_MEIPASS", Path(__file__).parent))/"voice")
    from conversation_service import ConversationService
    conversation=ConversationService(Path(getattr(sys, "_MEIPASS", Path(__file__).parent))/"voice")
    from draft_store import DraftStore
    from history_sync import HistorySync
    drafts=DraftStore(settings_path(remote.profile),protect)
    histories=HistorySync(remote,settings_path(remote.profile).with_suffix('.history.dpapi'),protect)
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(30)

        def log_message(self, *args):
            pass

        def reply(self, code, value):
            data = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(data)

        def authorized(self):
            port = self.server.server_address[1]
            if not self.local_request():
                self.reply(403, {'error': {'message': 'Utiliser une application API locale avec la clé affichée.'}})
                return False
            actual = self.headers.get('Authorization', '')
            if not hmac.compare_digest(actual, 'Bearer ' + key):
                self.reply(401, {'error': {'message': 'Clé API locale requise ; elle est affichée dans '+APP_NAME+'.'}})
                return False
            return True

        def local_request(self):
            port = self.server.server_address[1]
            hosts = (f'127.0.0.1:{port}', f'localhost:{port}')
            return self.headers.get('Host') in hosts and self.headers.get('Origin') in (None, *(f'http://{host}' for host in hosts))

        def chat(self):
            if not self.local_request():
                return self.reply(403, {'error': {'message': 'Le chat est accessible sur localhost uniquement.'}})
            nonce = secrets.token_urlsafe(24)
            config = json.dumps({'key':key, 'model':remote.model, 'version':VERSION, 'storage':hashlib.sha256(key.encode()).hexdigest()[:20]}, ensure_ascii=False).replace('<', '\\u003c')
            template = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'chat.html'
            presentation = ''.join('<script nonce="__NONCE__">'+(template.parent/name).read_text(encoding='utf-8')+'</script>' for name in ('ui.js','attachments.js','corrector.js','selection.js','thinking.js','voice.js','conversation.js'))
            markdown=''.join('<script nonce="__NONCE__">'+path.read_text(encoding='utf-8').replace('</script','<\\/script')+'</script>' for path in (template.parent/'vendor/markdown-it.min.js',template.parent/'markdown.js'))
            content = template.read_text(encoding='utf-8').replace('</head>',markdown+'</head>').replace('</body>',(template.parent/'workspace.html').read_text(encoding='utf-8')+presentation+'</body>').replace('__UI_CSS__',(template.parent/'ui.css').read_text(encoding='utf-8')).replace('__CONFIG__', config).replace('__NONCE__', nonce).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; connect-src 'self'; img-src data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            if self.path == '/client/conversation':
                if not self.authorized():return
                return self.reply(200,conversation.status())
            if self.path in ('/', '/chat'):
                return self.chat()
            if self.path == '/client/voice':
                if not self.authorized():return
                return self.reply(200,voice.status())
            if self.path == '/client/integrations':
                if not self.authorized():return
                return self.reply(200,{'apps':app_integrations.detect()})
            if self.path == '/client/state':
                if not self.authorized():return
                histories.schedule()
                remote.refresh_diagnostic()
                return self.reply(200,{'version':VERSION,'logged_in':True,'username':'Accès personnel','endpoint':remote.endpoint,'internet_endpoint':remote.profile['wireguard']['endpoint'],'connection':remote.state(),'history':histories.status(),'preferences':client_settings(remote.profile).get('preferences',{}),'update':remote.update_state,'local_api':f'http://127.0.0.1:{self.server.server_port}/v1','key':key})
            if self.path == '/client/history':
                if not self.authorized():return
                try:return self.reply(200,histories.read())
                except history_store.HistoryError as error:return self.reply(500,{'error':{'message':str(error),'code':'history_unreadable'}})
                except OSError as error:return self.reply(500,{'error':{'message':str(error)}})
            if self.path=='/client/draft':
                if not self.authorized():return
                try:
                    return self.reply(200,drafts.read())
                except (OSError,ValueError):return self.reply(500,{'error':{'message':'Brouillon local illisible : le fichier est conservé.'}})
            if self.path not in ('/v1/models', '/v1/status','/v1/workspace','/v1/notifications','/v1/voice/status'):
                return self.reply(404, {'error': {'message': 'Route non disponible.'}})
            if not self.authorized():
                return
            if self.path=='/v1/models':
                state=remote.check()
                if not state['connected']:return self.reply(401 if state['code'] in ('access_denied','access_revoked','access_suspended','access_expired','remote_disabled') else 503,{'error':{'code':state['code'],'message':state['error']}})
                if not getattr(remote,'update_checked',False) and remote.profile.get('update_public_key'):
                    remote.update_checked=True;remote.update(False)
                return self.reply(200,{'object':'list','data':[{'id':model,'object':'model','capabilities':remote.model_capabilities.get(model,{})} for model in state['models']]})
            self.forward()

        def do_POST(self):
            if self.path not in ('/v1/chat/completions','/v1/context', '/v1/cancel','/v1/workspace/action','/v1/notifications/action','/v1/voice/speech','/v1/voice/cancel','/client/conversation','/client/draft','/client/endpoint','/client/preferences','/client/update/check','/client/update/apply','/client/history','/client/history/sync','/client/history/restore-ack','/client/history/flush','/client/history/recover','/client/integrations/apply','/client/voice'):
                return self.reply(404, {'error': {'message': 'Route non disponible.'}})
            if not self.authorized():
                return
            try:
                if self.headers.get('Transfer-Encoding') or not self.headers.get('Content-Type', '').startswith('application/json'):
                    raise ValueError('Corps JSON attendu.')
                length = int(self.headers.get('Content-Length', '0'))
                if not 1 <= length <= (10*1024*1024 if self.path.startswith('/client/history') or self.path in ('/v1/chat/completions','/v1/context') else 8*1024*1024 if self.path=='/v1/workspace/action' else 2*1024*1024):
                    raise ValueError('Requête trop volumineuse (maximum 2 Mo).')
                body = self.rfile.read(length)
                streaming = bool(json.loads(body).get('stream'))
            except (OSError, ValueError, AttributeError) as error:
                return self.reply(400, {'error': {'message': str(error)}})
            if self.path.startswith('/client/'):
                try:
                    values=json.loads(body)
                    if not isinstance(values,dict):raise ValueError('Paramètres invalides.')
                    if self.path in ('/client/update/apply','/client/endpoint') and (voice.status()['phase'] in ('loading','listening','finishing','cancelling') or conversation.status()['phase'] in ('loading','listening','stopping')):
                        raise ValueError('Terminez la dictée avant de mettre le client à jour.')
                    if self.path=='/client/conversation':
                        if values.get('action')=='start' and voice.status()['phase'] in ('loading','listening','finishing','cancelling'):raise ValueError('Terminez la dictée avant de converser.')
                        result=conversation.action(values)
                    elif self.path=='/client/voice':
                        if values.get('action')=='start' and conversation.status()['phase'] in ('loading','listening','stopping'):raise ValueError('Raccrochez avant de dicter.')
                        result=voice.action(values)
                    elif self.path=='/client/integrations/apply':
                        if set(values)-{'app','model'}:raise ValueError('Paramètres d’intégration invalides.')
                        state=remote.check()
                        if not state['connected']:raise ValueError('Connectez le client au serveur et chargez un modèle avant de l’ajouter.')
                        model=values.get('model') or state['model']
                        if model not in state['models']:raise ValueError('Ce modèle n’est plus disponible sur le serveur. Actualisez la liste.')
                        result=app_integrations.install(values.get('app'),f'http://127.0.0.1:{self.server.server_port}/v1',key,model)
                    elif self.path=='/client/endpoint':
                        endpoint=values.get('endpoint') or None
                        if endpoint:endpoint=parse_connection_settings(endpoint)
                        with remote.activity_lock:
                            if remote.active_requests or remote.applying_update:raise ValueError('Attendre la fin des requêtes API avant de changer d’adresse.')
                            save_endpoint(remote.profile,endpoint);remote.set_endpoint(endpoint);result={'endpoint':remote.endpoint}
                    elif self.path=='/client/history':
                        result=histories.write(values.get('history'),values.get('revision',''))
                    elif self.path=='/client/history/sync':
                        result=histories.synchronize(values.get('initial'))
                    elif self.path=='/client/history/restore-ack':result=histories.acknowledge_restore(values.get('confirm'))
                    elif self.path=='/client/history/flush':result=histories.flush()
                    elif self.path=='/client/preferences':result=save_preferences(remote.profile,values)
                    elif self.path=='/client/history/recover':
                        result=history_store.recover(settings_path(remote.profile).with_suffix('.history.dpapi'),protect,values.get('history'))
                    elif self.path=='/client/draft':
                        result=drafts.write(values.get('draft'))
                    else:result=remote.update(self.path.endswith('/apply'))
                    return self.reply(200,result)
                except urllib.error.HTTPError as error:
                    try:return self.reply(error.code,json.loads(error.read(65536)))
                    finally:error.close()
                except history_store.HistoryConflict as error:return self.reply(409,{'error':{'message':str(error)}})
                except (ValueError,OSError,TypeError) as error:return self.reply(400,{'error':{'message':str(error)}})
            self.forward(body, streaming)

        def forward(self, body=None, streaming=False):
            sent = False
            inference=self.path in ('/v1/chat/completions','/v1/workspace/action')
            tracked=self.path!='/v1/cancel'
            chat_stream=streaming and self.path=='/v1/chat/completions'
            if chat_stream:remote.stream={'phase':'requesting','started':time.time(),'last_event':time.time(),'reasoning_chars':0,'answer_chars':0}
            with remote.activity_lock:
                if inference and remote.applying_update:return self.reply(409,{'error':{'message':'Mise à jour en cours. Réessayer après le redémarrage.'}})
                if tracked:remote.active_requests+=1
            try:
                try:
                    response = remote.open(self.path, body,self.headers.get("X-Qwen-Request"))
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    self.send_response(response.status if hasattr(response, 'status') else response.code)
                    self.send_header('Content-Type', 'text/event-stream' if streaming and response.status == 200 else 'application/json; charset=utf-8')
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    sent = True
                    if streaming and response.status == 200:
                        done=False
                        for line in response:
                            if line.strip()==b'data: [DONE]':done=True
                            if self.path=='/v1/voice/speech' and line.startswith(b'data: '):
                                try:done=done or bool(json.loads(line[6:]).get('done'))
                                except (ValueError,AttributeError):pass
                            if chat_stream:
                                remote.stream['last_event']=time.time()
                                if line.startswith(b': qwen-queue '):
                                    try:
                                        position=json.loads(line[len(b': qwen-queue '):]).get('position',0)
                                        remote.stream.update(phase='queued' if position else 'waiting_model',position=position)
                                    except (ValueError,AttributeError):pass
                                elif line.startswith(b'data: ') and not done:
                                    try:
                                        event=json.loads(line[6:]);choice=(event.get('choices') or [{}])[0];delta=choice.get('delta') or {}
                                        reason=delta.get('reasoning_content',delta.get('reasoning',''));content=delta.get('content','')
                                        if isinstance(reason,str) and reason:remote.stream['reasoning_chars']+=len(reason);remote.stream['phase']='thinking'
                                        if isinstance(content,str) and content:remote.stream['answer_chars']+=len(content);remote.stream['phase']='answering'
                                        if choice.get('finish_reason'):remote.stream['finish_reason']=choice['finish_reason']
                                    except (ValueError,TypeError,AttributeError,IndexError):pass
                            self.wfile.write(line)
                            self.wfile.flush()
                        if not done:raise ValueError('Flux interrompu avant la confirmation de fin.')
                        if chat_stream:remote.stream['phase']='complete';remote.event('generation_complete',reasoning_chars=remote.stream['reasoning_chars'],answer_chars=remote.stream['answer_chars'],finish_reason=remote.stream.get('finish_reason'))
                    else:
                        while True:
                            block = response.read1(65536)
                            if not block:
                                break
                            self.wfile.write(block)
            except (OSError, ValueError, urllib.error.URLError):
                if self.path!='/v1/voice/speech':remote.failure('connection_error','Connexion au serveur IA interrompue. Réessayer la requête.')
                if not sent:
                    self.reply(503, {'error': {'message': 'Connexion au serveur IA indisponible.'}})
                elif streaming:
                    try:
                        self.wfile.write(b'\n\ndata: {"error":{"code":"connection_error","message":"Connexion interrompue : la reponse peut etre incomplete."}}\n\n');self.wfile.flush()
                    except OSError:pass
            finally:
                if chat_stream and remote.stream.get('phase')!='complete':remote.stream['phase']='interrupted';remote.event('generation_interrupted')
                if tracked:
                    with remote.activity_lock:remote.active_requests-=1
    server = LocalHTTPServer(('127.0.0.1', port), Handler)
    server.voice = voice
    server.conversation = conversation
    server.daemon_threads = True
    return server

class LocalHTTPServer(ThreadingHTTPServer):
    """Bounded workers also cover stalled or unauthorized loopback connections."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.workers=threading.BoundedSemaphore(24)

    def server_close(self):
        if hasattr(self, "conversation"):self.conversation.close()
        if hasattr(self, "voice"):self.voice.close()
        super().server_close()

    def process_request(self,request,address):
        if not self.workers.acquire(blocking=False):
            try:request.sendall(b'HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
            finally:self.shutdown_request(request)
            return
        try:super().process_request(request,address)
        except Exception:self.workers.release();raise

    def process_request_thread(self,request,address):
        try:super().process_request_thread(request,address)
        finally:self.workers.release()

def read_profile():
    if getattr(sys, 'frozen', False):
        with open(sys.executable, 'rb') as stream:
            stream.seek(-16, 2)
            footer = stream.read(16)
            if footer[4:] == b'QWENPROFILE1':
                size = struct.unpack('<I', footer[:4])[0]
                if not 1 <= size <= 65536:
                    raise ValueError('Accès intégré invalide.')
                stream.seek(-16 - size, 2)
                profile = json.loads(stream.read(size))
                validate_profile(profile)
                return profile
    bundled = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'profil.json'
    # Per-client profile is bundled by the server; no settings or file import on the client.
    if not bundled.exists():
        raise ValueError('Cet EXE ne contient pas encore d’accès. Générer un client depuis la console du serveur.')
    profile = json.loads(bundled.read_text(encoding='utf-8'))
    validate_profile(profile)
    return profile

def settings_path(profile):
    identity = hashlib.sha256((profile['url'] + profile['token']).encode()).hexdigest()[:20]
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'QwenClient' / (identity + '.dpapi')

def client_settings(profile):
    try:
        data=json.loads(protect(settings_path(profile).read_bytes(),decrypt=True))
        if not isinstance(data,dict):return {}
        if data.get('endpoint'):data['endpoint']=validate_connection_endpoint(data['endpoint'])
        return data
    except (OSError,ValueError,KeyError):return {}

def save_endpoint(profile,endpoint=None):
    from file_lock import locked
    path=settings_path(profile)
    with locked(path):
        values=client_settings(profile)
        values['connection_selected']=True
        if endpoint:values['endpoint']=validate_connection_endpoint(endpoint)
        else:values.pop('endpoint',None)
        history_store.atomic(path,protect(json.dumps(values)))

def local_key(profile):
    from file_lock import locked
    with locked(settings_path(profile)):return _local_key(profile)

def save_preferences(profile,values):
    allowed={'theme':('light','dark','system'),'font':('system','humanist','serif','mono'),
             'text_size':('compact','standard','large','extra'),'thinking_effort':('none','low','medium','high')}
    if not isinstance(values,dict) or set(values)-set(allowed)-{'thinking','sidebar_collapsed','corrector_text'}:raise ValueError('Réglages invalides.')
    for name,value in values.items():
        if name in allowed and value not in allowed[name]:raise ValueError('Réglage invalide : '+name)
        if name in ('thinking','sidebar_collapsed') and type(value) is not bool:raise ValueError('Réglage booléen attendu.')
        if name=='corrector_text' and (not isinstance(value,str) or len(value)>100000):raise ValueError('Brouillon du correcteur invalide (100 000 caractères maximum).')
    from file_lock import locked
    path=settings_path(profile)
    with locked(path):
        settings=client_settings(profile);settings['preferences']={**settings.get('preferences',{}),**values}
        settings['preferences'].pop('maximum',None)
        history_store.atomic(path,protect(json.dumps(settings)))
    return {'saved':True}

def _local_key(profile):
    path = settings_path(profile)
    try:
        data = client_settings(profile)
        key = data['local_key']
        if not isinstance(key, str) or len(key) < 32:
            raise ValueError()
        return key
    except (OSError, ValueError, KeyError):
        key = 'local_' + secrets.token_urlsafe(32)
        path.parent.mkdir(parents=True, exist_ok=True)
        data=client_settings(profile);data['local_key']=key
        history_store.atomic(path,protect(json.dumps(data)))
        return key

def install_close_guard(window):
    """Flush the full history before WebView closes, including histories over 64 KiB."""
    state={'ready':False,'pending':False}
    def closing():
        if state['ready']:return True
        if state['pending']:return False
        state['pending']=True
        def work():
            def complete(result):
                if not isinstance(result,dict):result={'saved':False,'message':'Enregistrement non confirmé.'}
                if result.get('saved') or window.create_confirmation_dialog(APP_NAME,'Historique non enregistré : '+result.get('message','')+'\nExportez vos conversations pour les conserver. Fermer quand même ?'):
                    state['ready']=True;window.destroy()
                else:state['pending']=False
            try:window.evaluate_js("(async()=>{try{await window.voiceFinishForClose?.();controller?.abort();if(busy)await api('/v1/cancel',{}, {'X-Qwen-Request':requestId});await uiPersistPreferences();await flushHistory();await api('/client/history/flush',{});return {saved:true};}catch(e){return {saved:false,message:e.message};}})()",callback=complete)
            except Exception as error:complete({'saved':False,'message':str(error)})
        threading.Thread(target=work,daemon=True).start()
        return False
    window.events.closing+=closing
    return state

def window_geometry():
    """Keep the initial window inside the Windows work area, including scaled displays."""
    width,height=1200,780
    try:
        area=wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030,0,ctypes.byref(area),0):
            width=max(400,min(1440,int((area.right-area.left)*0.9)))
            height=max(320,min(960,int((area.bottom-area.top)*0.9)))
    except (AttributeError,OSError):pass
    return {'width':width,'height':height,'min_size':(min(640,width),min(480,height))}

def main():
    if '--self-test' in sys.argv:
        # Packaging smoke check, without a window or a model request.
        raw = b'Qwen client self test'
        assert protect(protect(raw), decrypt=True) == raw
        if '--with-profile' in sys.argv:
            profile=read_profile();validate_profile(profile)
            assert profile.get('version',VERSION)==VERSION, 'Version du profil incompatible avec le binaire.'
        assert (Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'chat.html').is_file()
        assert (Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'workspace.html').is_file()
        assert all((Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / name).is_file() for name in ('ui.css','ui.js'))
        engine=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'wireguard-bridge.exe'
        assert subprocess.run([str(engine),'--self-test'],capture_output=True,timeout=10,creationflags=0x08000000).returncode==0
        if '--voice-self-test' in sys.argv:
            from local_voice import VoiceService, NativeEngine
            resources=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'voice'
            voice=VoiceService(resources)
            voice._verify()
            native=NativeEngine(resources,voice.model)
            try:
                deadline=time.monotonic()+30
                while native.status()['phase']=='loading' and time.monotonic()<deadline:time.sleep(.05)
                assert native.status()['phase']=='listening',native.status()
                native.feed(b'\0'*3200);native.stop()
                while native.status()['phase']=='finishing' and time.monotonic()<deadline:time.sleep(.05)
                assert native.status()['phase']=='ready' and native.status()['text']=='',native.status()
            finally:native.close();voice.close()
        if '--conversation-self-test' in sys.argv:
            from conversation_service import ConversationService
            resources=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'voice'
            conversation=ConversationService(resources)
            try:
                status=conversation.action({'action':'start'});deadline=time.monotonic()+30
                while conversation.status()['phase']=='loading' and time.monotonic()<deadline:time.sleep(.1)
                assert conversation.status()['phase']=='listening' and conversation.status().get('aec'),conversation.status()
                time.sleep(.5);conversation.action({'action':'stop','session':status['session']})
                while conversation.status()['phase']=='stopping' and time.monotonic()<deadline:time.sleep(.1)
                assert conversation.status()['phase']=='stopped',conversation.status()
            finally:conversation.close()
        if '--result' in sys.argv:
            Path(sys.argv[sys.argv.index('--result')+1]).write_text(APP_NAME+' self-test OK', encoding='utf-8')
        else:
            print(APP_NAME+' self-test OK')
        return
    if '--apply-update' in sys.argv:
        plan=Path(sys.argv[sys.argv.index('--apply-update')+1])
        try:
            import updater
            updater.apply(plan,protect,read_profile)
        except Exception as error:
            plan.with_name('error.txt').write_text(str(error),encoding='utf-8')
            root=tk.Tk();root.withdraw();messagebox.showerror('Mise à jour '+APP_NAME,str(error),parent=root);root.destroy()
        return
    remote=None;server=None
    try:
        import webview
        profile=read_profile()
        settings=client_settings(profile)
        remote=Remote(profile,endpoint=settings.get('endpoint'),connection_required=not (settings.get('connection_selected') or settings.get('endpoint')))
        key=local_key(profile)
        for port in range(LOCAL_API_PORT,LOCAL_API_LAST_PORT+1):
            try:server=serve_local(remote,key,port);break
            except OSError:pass
        if server is None:raise ValueError(f'Les ports locaux {LOCAL_API_PORT} à {LOCAL_API_LAST_PORT} sont occupés.')
        threading.Thread(target=server.serve_forever,daemon=True).start()
        window=webview.create_window(APP_NAME+' · '+VERSION,f'http://127.0.0.1:{server.server_port}/chat',background_color='#ffffff',text_select=True,**window_geometry())
        remote.window=window
        install_close_guard(window)
        if '--update-ack' in sys.argv:
            def acknowledge():
                path=Path(sys.argv[sys.argv.index('--update-ack')+1])
                if not window.evaluate_js("typeof api==='function' && !!document.getElementById('composer') && !!document.getElementById('client-navigation')"):raise ValueError('Interface cliente non initialisée.')
                temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps({'version':VERSION,'ready':True}),encoding='utf-8');temporary.replace(path)
            window.events.loaded+=acknowledge
        webview.settings['ALLOW_DOWNLOADS']=True
        storage=settings_path(profile).parent/('webview-'+settings_path(profile).stem)
        if '--ui-self-test' in sys.argv:
            def verify_window():
                time.sleep(1)
                try:
                    result=window.evaluate_js("JSON.stringify({title:document.title,login:!!document.getElementById('client-navigation'),update:!!document.getElementById('update-apply'),chat:!!document.getElementById('composer'),state:document.getElementById('account-status').textContent,history:typeof bootstrap==='function',projects:!!document.getElementById('ws-project-list'),tasks:!!document.getElementById('ws-jobs'),assistants:!!document.getElementById('ws-assistants'),textSelection:getComputedStyle(document.body).userSelect,copySelection:!!document.getElementById('copy-selection'),thinkingModes:document.querySelectorAll('#thinking-bar input[type=radio]').length,thinkingInline:document.querySelector('.send-row').contains(document.getElementById('thinking')),documentMenu:!!document.getElementById('ui-context-panel'),attachmentPlus:document.getElementById('attach-file').textContent==='+'})")
                    if isinstance(result,str):result=json.loads(result)
                    assert result['login'] and result['update'] and result['chat'] and result['history'],result
                    assert result['projects'] and result['tasks'] and not result['assistants'],result
                    assert window.text_select and result['textSelection']!='none' and result['copySelection'],result
                    assert result['thinkingModes']==4 and result['thinkingInline'] and not result['documentMenu'] and result['attachmentPlus'],result
                    Path(sys.argv[sys.argv.index('--result')+1]).write_text(json.dumps({'ok':True,**result}),encoding='utf-8')
                finally:window.destroy()
            window.events.loaded+=verify_window
        webview.start(gui='edgechromium',private_mode=False,storage_path=str(storage))
    except Exception as error:
        root=tk.Tk();root.withdraw();messagebox.showerror(APP_NAME,str(error)+'\nSi WebView2 manque, installer Microsoft Edge WebView2 Runtime.',parent=root);root.destroy()
    finally:
        if remote:remote.close()
        if server:server.shutdown();server.server_close()

if __name__ == '__main__':main()
