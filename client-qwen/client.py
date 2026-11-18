"""Portable WireGuard client exposing an authenticated loopback API and chat."""
from __future__ import annotations
import ctypes
import copy
from collections import deque
import hashlib
import hmac
import io
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler
from fred_http import BoundedHTTPServer, json_body
import json
import os
import re
from pathlib import Path
import secrets
import stat
import subprocess
import struct
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import urllib.error
import urllib.request
from uuid import UUID
from urllib.parse import urlsplit
import time
from updater import VERSION, AGENT_PROTOCOL
from kiara_shared.releases import version as validate_version
from product import APP_NAME, LOCAL_API_PORT, LOCAL_API_LAST_PORT
import history_store
from wg_bridge import Bridge,validate_profile,connection_candidates
from connection_settings import parse as parse_connection_settings, validate_connection_endpoint, HTTPS_ENDPOINT
import app_integrations
import hermes_catalogue
from kiara_shared.agent_http import AGENT_RESPONSE_HEADERS
from kiara_shared.thunderbird import PREFIX as THUNDERBIRD_PREFIX, bridge_route

if sys.platform == 'win32':
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_ubyte))]

def protect(value, decrypt=False):
    if sys.platform.startswith('linux'):
        from linux_support import protect as linux_protect
        return linux_protect(value, decrypt=decrypt)
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
        self.version = VERSION
        self.profile=copy.deepcopy(profile)
        self.url=profile['url']
        self.token = profile['token']
        if not isinstance(self.token, str) or not self.token.startswith('qwen_') or not 50 <= len(self.token) <= 256:
            raise ValueError('Accès serveur invalide.')
        self.mock=opener is not None
        self.bridge=None
        self.bridge_lock=threading.RLock()
        self.check_lock=threading.Lock()
        self.probe_failures=0;self.next_probe=0;self.connection_warning=""
        self.denial_epoch=0;self.denial_state=None
        self.opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        # Default HTTPSHandler verifies the certificate; honor the workplace proxy.
        self.https_opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler(),NoRedirect())
        self.model = ''
        self.models = []
        self.model_capabilities = {}
        self.models_catalogue = {'object':'list','data':[]}
        self.connection_required = connection_required
        self.session = ""
        self.username = ""
        self.expires_epoch = 0
        self.update_state = {"message":"Cliquer sur Vérifier pour rechercher une mise à jour."}
        self.update_lock = threading.Lock()
        self.activity_lock = threading.RLock()
        self.cancelled_requests = deque(maxlen=128)
        self.active_requests = 0
        self.active_inference_requests = 0
        self.applying_update = False
        self.kiara4 = None
        self.window = None
        self.close_guard = None
        self.desktop_update = None
        self.connected = False
        self.reachable = False
        self.error = 'Connexion au serveur IA…'
        self.code = 'connecting'
        self.checked_at = 0
        self.diagnostic = {}
        self.events=deque(maxlen=60);self.bridge_starts=0;self.attempts=0
        self.checking=False;self.last_contact=0;self.response_count=0;self.stream={}
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
                if self.bridge.process.poll() is not None:self.failure('connection_error','Le moteur WireGuard s’est arrêté. Réessayer la connexion.',confirmed=True)
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
            self.probe_failures=0;self.next_probe=0;self.connection_warning=''

    def state(self):
        return {'connection_required':self.connection_required,'connected':self.connected,'reachable':self.reachable,'model':self.model,
                'models':list(self.models),'error':self.error,'code':self.code,
                'endpoint':self.endpoint,'automatic':self.override is None,
                'transport':'https' if self.endpoint==HTTPS_ENDPOINT else 'wireguard',
                'checked_at':self.checked_at,'checking':self.checking,'attempts':self.attempts,
                'bridge_starts':self.bridge_starts,'last_contact':self.last_contact,
                'reconnecting':bool(self.probe_failures),'connection_warning':self.connection_warning,
                'events':list(self.events)[-12:],'stream':dict(self.stream),**self.diagnostic}

    def failure(self,code,message,confirmed=False):
        if code=='model_unloaded' and self.models_catalogue.get('source')=='hermes' and any(row.get('available',True) for row in self.models_catalogue['data']):
            return
        network=code in ('wireguard_unreachable','tunnel_request_failed','connection_error')
        if not network and code not in ('gateway_unavailable','access_denied','access_revoked',
                'access_suspended','access_expired','remote_disabled','model_unloaded','no_models'):return
        if network and self.connected and not confirmed:
            # One failed background request does not disprove a working stream.
            self.connection_warning=message;self.event('request_failed',code=code)
            return
        self.connected=False;self.reachable=not network
        if code in ('access_denied','access_revoked','access_suspended','access_expired','remote_disabled'):
            self.denial_epoch+=1;self.denial_state=(code,message)
        self.code=code;self.error=message;self.checked_at=time.time()
        self.event('connection_failed',code=code)

    def select_model(self,model):
        with self.bridge_lock:
            if model not in self.models:raise ValueError('Ce modèle ne figure pas dans le dernier scan du serveur.')
            self.model=model

    def open(self, path, data=None, request_id=None, *, method=None, content_type='application/json', content_length=None, timeout=None, range_headers=None):
        if not isinstance(path,str) or not path.startswith('/v1/') or any(c in path for c in ('\\','\r','\n')):
            raise ValueError('Route API invalide.')
        business = path.startswith('/v1/business/')
        if method is not None and (not business or method not in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')):
            raise ValueError('Méthode API invalide.')
        if not isinstance(content_type, str) or not content_type or len(content_type) > 512 or any(c in content_type for c in '\r\n'):
            raise ValueError('Type de contenu invalide.')
        if content_length is not None and (not business or type(content_length) is not int or not 0 <= content_length <= 272 * 1024 * 1024):
            raise ValueError('Taille de contenu invalide.')
        range_headers = range_headers or {}
        if range_headers and (not business or method != 'GET' or any(
                name not in ('Range', 'If-Range') or not isinstance(value, str) or len(value) > 512
                or not value.isascii() or any(c in value for c in '\r\n') for name, value in range_headers.items())):
            raise ValueError('Plage de téléchargement invalide.')
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
        headers={**headers, 'User-Agent':'AccesServeurKiara/'+self.version+' ('+('Linux' if sys.platform.startswith('linux') else 'Windows')+'; '+('HTTPS' if https else 'WireGuard')+')', 'Content-Type': content_type,'X-Qwen-Session':self.session,'X-Fred-Agent-Protocol':str(AGENT_PROTOCOL),**({'X-Qwen-Request':request_id} if request_id else {}),**({'Content-Length':str(content_length)} if content_length is not None else {})}, method=method)
        for name, value in range_headers.items():
            request.add_header(name, value)
        try:
            if timeout is None:
                timeout=900 if business or path in ("/v1/chat/completions","/v1/responses") else 120 if path=="/v1/client/download" else 90 if path in ('/v1/voice/max/transcribe','/v1/voice/max/speech') else 60 if path in ("/v1/workspace/action","/v1/history") else 3 if path=="/v1/device" else 90 if path=="/v1/embeddings" else 30
            response=opener.open(request, timeout=timeout)
            with self.activity_lock:self.last_contact=time.time();self.response_count+=1
            self.event('server_response',route=path,status=getattr(response,'status',200))
            return response
        except urllib.error.HTTPError as error:
            # Preserve the response body for callers after inspecting the structured error.
            raw=error.read(65536)
            try:
                detail=json.loads(raw).get('error',{})
                if isinstance(detail,dict) and (not business or detail.get('code') in ('access_denied','access_revoked','access_suspended','access_expired','remote_disabled')):
                    self.failure(detail.get('code'),detail.get('message','Serveur indisponible.'))
            except (ValueError,AttributeError):pass
            response=urllib.error.HTTPError(error.url,error.code,error.reason,error.headers,io.BytesIO(raw))
            error.close()
            raise response from None
        except (OSError,urllib.error.URLError):
            self.failure('connection_error','Connexion au serveur IA interrompue. Vérifier le réseau puis réessayer.')
            raise

    def update(self,apply=False, *, migrate=False):
        managed = getattr(self, 'managed_relay', False)
        if managed and (self.desktop_update is None or migrate):
            raise ValueError('Utilisez l’installateur Kiara pour mettre à jour cette application.')
        if sys.platform.startswith('linux'):
            self.update_state={'busy':False,'available':False,'current':VERSION,
                               'message':'Pour mettre Kiara à jour, installez le nouveau paquet Linux fourni par votre administrateur.'}
            return self.update_state
        if migrate and (sys.platform != 'win32' or not getattr(sys, 'frozen', False) or self.mock or not self.window):
            raise ValueError('Le passage à Kiara 4 est disponible depuis l’EXE personnel Windows.')
        with self.activity_lock:
            if (migrate or managed and apply) and self.active_inference_requests:
                raise ValueError('Attendez la fin de la requête en cours.')
            if self.applying_update:raise ValueError('Installation en cours. Attendre le redémarrage du client.')
            if not self.update_lock.acquire(blocking=False):raise ValueError('Une mise à jour est déjà en cours.')
            if apply:self.applying_update=True
        self.update_state={'busy':True,'message':'Téléchargement et vérification…' if apply else 'Vérification de la version serveur…'}
        def work():
            prepared=False
            try:
                import updater
                if apply:
                    if managed:
                        self.desktop_update.stage(self)
                        prepared = True
                        return
                    if migrate:
                        self.kiara4 = updater.install_kiara4(self)
                        if self.close_guard is not None:
                            self.close_guard['ready'] = True  # The migration route already flushed local data.
                    else:
                        updater.prepare(self,protect)
                    prepared=True
                    self.update_state={'busy':False,'message':'Mise à jour vérifiée. Redémarrage du client…'}
                    if self.window:self.window.destroy()
                else:
                    release=updater.desktop_release(self) if managed else updater.check(self)
                    self.update_state={**release,'busy':False,'message':('Version '+release['version']+' disponible.' if release['available'] else 'Client à jour · '+release['current'])}
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
        # Network I/O must never hold the bridge mutex: audio, cancellation and
        # history uploads can continue while the catalogue probe is slow.
        if not self.check_lock.acquire(blocking=False):return self.state()
        try:self._check()
        finally:self.checking=False;self.check_lock.release()
        return self.state()

    def _check(self):
        if self.connection_required or self.active_requests or self.applying_update:
            return self.state()
        if time.monotonic()<self.next_probe:return
        was_connected=self.connected;responses_before=self.response_count;denial_before=self.denial_epoch
        candidates=list(dict.fromkeys([self.endpoint,*self.candidates]))
        if was_connected and self.probe_failures<2:candidates=[self.endpoint]
        self.checking=True
        code='wireguard_unreachable';diagnostic={}
        for endpoint in candidates:
            if endpoint!=self.endpoint:
                with self.activity_lock,self.bridge_lock:
                    if self.active_requests or self.applying_update:return
                    self._switch_endpoint(endpoint)
            self.attempts+=1;self.event('connection_probe',attempt=self.attempts)
            self.reachable=False
            try:
                with self.open('/v1/models') as response:
                    catalogue=json.load(response);data=catalogue.get('data')
                if not isinstance(data,list):raise ValueError('Liste des modèles invalide dans /v1/models.')
                # Display hints only; older servers may not implement this route.
                if time.time()-getattr(self,'device_reported_at',0)>=60:
                    self.device_reported_at=time.time()
                    try:
                        declaration={'kind':'pc','version':self.version,'transport':'https' if self.endpoint==HTTPS_ENDPOINT else 'wireguard','agent_protocol':AGENT_PROTOCOL}
                        with self.open('/v1/device',json.dumps(declaration).encode()) as response:response.read(2048)
                    except urllib.error.HTTPError as error:
                        if error.code in (401,403):raise
                        error.close()
                    except (OSError,ValueError):pass
                public_models=[row for row in data if isinstance(row,dict) and isinstance(row.get('id'),str) and row['id'].strip() and len(row['id'])<=512]
                embedding_ids={row['id'] for row in public_models if isinstance(row.get('capabilities'),dict) and row['capabilities'].get('embedding') is True}
                models=list(dict.fromkeys(row['id'] for row in public_models if row['id'] not in embedding_ids))
                self.model_capabilities={row['id']:row.get('capabilities',{}) for row in data if isinstance(row,dict) and row.get('id') in models and isinstance(row.get('capabilities',{}),dict)}
                entries=[]
                for row in data:
                    if not isinstance(row,dict) or row.get('id') not in models+list(embedding_ids) or any(entry['id']==row['id'] for entry in entries):continue
                    entry={'id':row['id'],'object':'model','capabilities':row.get('capabilities',{}) if isinstance(row.get('capabilities'),dict) else {}}
                    for field in ('name','label','provider'):
                        if isinstance(row.get(field),str):entry[field]=row[field][:512]
                    if type(row.get('available')) is bool:entry['available']=row['available']
                    entries.append(entry)
                self.models_catalogue={'object':'list','data':entries}
                for field in ('default_model','source'):
                    if isinstance(catalogue.get(field),str):self.models_catalogue[field]=catalogue[field][:512]
                self.models=models;self.reachable=True
                if models:
                    available=[entry['id'] for entry in entries if entry['id'] in models and entry.get('available',True)]
                    if self.model not in available:self.model=catalogue.get('default_model') if catalogue.get('default_model') in available else (available or models)[0]
                    self.connected=True;self.error='';code='ready'
                elif any(entry['id'] in embedding_ids and entry.get('available',True) for entry in entries):
                    self.model='';self.connected=True;self.error='';code='ready'
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
            except (ValueError,KeyError,IndexError,TypeError,AttributeError) as error:
                code='invalid_response';self.reachable=True
                self.error='Le serveur a renvoyé un catalogue invalide. Réessayez dans un instant.'
            except OSError as error:
                code='connection_error'
                self.error=str(error) if isinstance(error,ValueError) else ('Connexion HTTPS impossible : vérifier le réseau, le proxy et le certificat.' if self.endpoint==HTTPS_ENDPOINT else 'Connexion impossible : vérifier l’adresse du serveur et son port UDP.')
            diagnostic=self.bridge.status(self.opener) if self.bridge and not self.mock else {}
            if self.reachable:break
        if code=='ready' and self.denial_epoch!=denial_before:
            code,self.error=self.denial_state;self.connected=False
        if code=='ready':
            self.probe_failures=0;self.next_probe=0;self.connection_warning=''
        elif not self.reachable:
            # Probe failures are consecutive evidence; a concurrent successful
            # request takes precedence over an older, slower failed probe.
            self.probe_failures=0 if self.response_count>responses_before else self.probe_failures+1
            self.next_probe=time.monotonic()+min(30,5*2**min(self.probe_failures,3))
            if was_connected and self.probe_failures<3:
                self.connection_warning=self.error;self.error='';self.connected=True;self.reachable=True;code='ready'
            else:self.connected=False
            self.event('connection_probe_failed',failures=self.probe_failures)
        else:self.connected=False
        if not self.connected:self.models=[];self.model=''
        self.code=code;self.diagnostic=diagnostic;self.checked_at=time.time()

AGENT_OPEN_EXTENSIONS = frozenset({'.pdf', '.docx', '.xlsx', '.csv', '.txt', '.md', '.png', '.jpg',
                                  '.jpeg', '.pptx', '.dwg', '.dxf', '.step', '.stp', '.iges', '.igs', '.sldprt'})


def agent_windows_path(value, roots):
    if not isinstance(value, str) or not 1 <= len(value) <= 2048 or any(ord(char) < 32 for char in value):
        raise ValueError('Chemin de projet invalide.')
    from pathlib import PureWindowsPath
    windows = PureWindowsPath(value)
    if (not windows.is_absolute() or '..' in windows.parts or ':' in value[2:]
            or value.replace('/', '\\').startswith(('\\\\?\\', '\\\\.\\'))):
        raise ValueError('Choisissez un dossier ou un fichier du projet.')
    requested = Path(value)
    # Check the configured prefix before touching a remote filesystem.
    candidates = [Path(root) for root in roots if PureWindowsPath(root).is_absolute()
                  and windows.is_relative_to(PureWindowsPath(root))]
    for root in candidates:
        resolved_root = root.resolve(strict=True)
        resolved = requested.resolve(strict=True)
        if resolved.is_relative_to(resolved_root):
            if resolved.is_dir() or (resolved.is_file() and resolved.suffix.lower() in AGENT_OPEN_EXTENSIONS):
                return resolved
            raise PermissionError('Ce type de fichier ne peut pas être ouvert par Kiara.')
    raise PermissionError('Ce chemin est en dehors des dossiers autorisés sur ce poste.')


def serve_local(remote, key, port=LOCAL_API_PORT, *, managed=False):
    from conversation_service import ConversationService, DictationService
    from advanced_voice import AdvancedVoice, choose_execution
    from max_installation import MaxInstallation, max_home
    linux_system_audio = None
    default_max_home=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'QwenClient/voice-max'
    if sys.platform.startswith('linux'):
        from linux_support import services
        from linux_system_audio import LinuxSystemAudio
        linux_system_audio = LinuxSystemAudio()
        advanced,voice,conversation,wakeword,max_installation=services()
    else:
        advanced=AdvancedVoice(max_home(default_max_home))
        voice=DictationService(Path(getattr(sys, "_MEIPASS", Path(__file__).parent))/"voice")
        conversation=ConversationService(Path(getattr(sys, "_MEIPASS", Path(__file__).parent))/"voice")
        wakeword=ConversationService(Path(getattr(sys, "_MEIPASS", Path(__file__).parent))/"voice",mode='wakeword')
        max_installation=MaxInstallation(advanced.home,remote,advanced,conversation.cache,default_max_home.with_name('voice-max-location.json'))
    voice_control=threading.RLock()
    def max_server_status():
        try:
            started=time.monotonic()
            with remote.open('/v1/voice/max/status') as response:value=json.loads(response.read(65536))
            if value.get('available') and type(value.get('latency_ms')) in (int,float):value['latency_ms']+=(time.monotonic()-started)*1000
            return value
        except (OSError,ValueError):return {'available':False,'message':'Mode Max indisponible sur le serveur'}
    from draft_store import DraftStore
    from history_sync import HistorySync
    drafts=DraftStore(settings_path(remote.profile),protect)
    histories=HistorySync(remote,settings_path(remote.profile).with_suffix('.history.dpapi'),protect)
    agent_cookie = secrets.token_urlsafe(32)
    helper = Path(sys.executable).with_name('kiara-agent-capture.exe')
    desktop_capture = None
    if managed and sys.platform == 'win32' and getattr(sys, 'frozen', False) and helper.is_file():
        from agent_capture import DesktopCapture
        desktop_capture = DesktopCapture(remote, helper, settings_path(remote.profile).with_suffix('.capture'))
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

        def agent_request(self):
            path = urlsplit(self.path).path
            prefixes = ('/api/v1/', '/assets/', '/app/', '/v1/projects/', '/v1/sources/',
                        '/v1/settings/', '/v1/mail/', '/v1/triage/', '/v1/thunderbird/',
                        '/v1/proposals/', '/v1/search/')
            return (path in ('/app', '/v1/settings', '/v1/ingest/default-folder', '/v1/ingest/scan')
                    or path.startswith(prefixes)
                    or re.fullmatch(r'/v1/resolution/[A-Za-z0-9_-]{1,36}/confirm', path) is not None)

        def agent_authorized(self):
            if not self.local_request():
                return False
            try:
                cookie = SimpleCookie()
                cookie.load(self.headers.get('Cookie', ''))
                value = cookie.get('kiara_agent')
                return bool(value and hmac.compare_digest(value.value, agent_cookie))
            except CookieError:
                return False

        def agent_proxy(self):
            bridge = self.path.startswith(THUNDERBIRD_PREFIX)
            if bridge:
                origin = self.headers.get('Origin', '')
                provided = self.headers.get('X-Agent-Thunderbird-Token', '')
                expected = client_settings(remote.profile).get('thunderbird_token', '')
                if (self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}'
                        or (origin and not self.thunderbird_origin())
                        or self.command != 'POST' or not bridge_route(self.path)
                        or not isinstance(expected, str) or not expected or not provided.isascii()
                        or not hmac.compare_digest(provided, expected)):
                    return self.reply(403, {'detail': 'Liaison Thunderbird non appairée.'})
            elif not self.agent_authorized():
                return self.reply(403, {'error': {'message': 'Ouvrez Projets depuis la navigation Kiara.'}})
            if not bridge and self.command not in ('GET', 'HEAD'):
                port = self.server.server_address[1]
                if self.headers.get('Origin') not in (f'http://127.0.0.1:{port}', f'http://localhost:{port}'):
                    return self.reply(403, {'error': {'message': 'Commande locale refusée.'}})
            if not bridge and self.path == '/api/v1/kiara/linux-system-audio' and linux_system_audio:
                if self.command != 'POST':
                    return self.reply(405, {'detail': 'Commande audio indisponible.'})
                try:
                    value = json_body(self, 4096)
                    if set(value) != {'action', 'lease_id'} or value['action'] not in ('start', 'stop'):
                        raise ValueError('Commande audio invalide.')
                    result = linux_system_audio.start(value['lease_id']) if value['action'] == 'start' else linux_system_audio.stop(value['lease_id'])
                    return self.reply(200, result)
                except (OSError, ValueError) as error:
                    return self.reply(400, {'detail': str(error) or 'Boucle audio indisponible.'})
            if managed and sys.platform == 'win32' and self.path == '/api/v1/kiara/thunderbird-extension':
                return self.thunderbird_extension()
            native_path = re.fullmatch(r'/api/v1/meeting-sessions/([0-9a-f-]{36})/native-capture/(status|start|pause|resume|stop)', self.path)
            if desktop_capture and (native_path or self.path == '/api/v1/workspace/native-capture'):
                return self.agent_desktop_capture(native_path)
            lengths = self.headers.get_all('Content-Length', [])
            if self.headers.get('Transfer-Encoding') or len(lengths) > 1:
                return self.reply(400, {'error': {'message': 'Transfert invalide.'}})
            try:
                length = int(lengths[0]) if lengths else 0
                if not 0 <= length <= 272 * 1024 * 1024:
                    raise ValueError('Taille invalide')
            except ValueError:
                return self.reply(413, {'error': {'message': 'Fichier trop volumineux.'}})

            def body():
                remaining = length
                while remaining:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        raise OSError('Transfert interrompu')
                    remaining -= len(chunk)
                    yield chunk

            started = False
            try:
                try:
                    response = remote.open('/v1/business' + self.path, body() if length else None,
                                           method=self.command, content_type=self.headers.get('Content-Type', 'application/json'),
                                           content_length=length, range_headers={name: self.headers[name]
                                               for name in ('Range', 'If-Range') if self.command == 'GET' and name in self.headers})
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    html = None
                    path = urlsplit(self.path).path
                    if self.command == 'GET' and (path == '/app' or path.startswith('/app/')) and response.status == 200:
                        html = response.read(1024 * 1024 + 1)
                        if len(html) > 1024 * 1024 or b'<body>' not in html:
                            raise ValueError('Page Projets invalide.')
                        capture = b' data-kiara-capture="true"' if desktop_capture else b''
                        windows = b' data-kiara-windows="true" data-kiara-device-settings="true"' if sys.platform == 'win32' else b''
                        linux_audio = b' data-kiara-linux-system-audio="true"' if linux_system_audio else b''
                        html = html.replace(b'<body>', b'<body data-kiara-desktop="true" data-kiara-project-conversation="true"' + windows + capture + linux_audio + b'>', 1)
                    self.send_response(response.status if hasattr(response, 'status') else response.code)
                    for name in AGENT_RESPONSE_HEADERS:
                        value = response.headers.get(name)
                        if name == 'Content-Length' and html is not None:
                            value = str(len(html))
                        if value:
                            self.send_header(name, value)
                    self.send_header('Connection', 'close')
                    if bridge and origin:
                        self.send_header('Access-Control-Allow-Origin', origin)
                        self.send_header('Vary', 'Origin')
                    self.end_headers()
                    started = True
                    if html is not None:
                        self.wfile.write(html)
                        return
                    while chunk := response.read1(65536):
                        self.wfile.write(chunk)
                        self.wfile.flush()
            except (OSError, ValueError, urllib.error.URLError):
                if not started:
                    self.reply(503, {'error': {'message': 'Le service Projets est indisponible.'}})

        def thunderbird_extension(self):
            if self.command not in ('GET', 'POST'):
                return self.reply(405, {'detail': 'Commande Thunderbird inconnue.'})
            if self.command == 'POST' and self.server.server_port != LOCAL_API_PORT:
                return self.reply(409, {'detail': 'Le port de Thunderbird est occupé. Libérez le port 17841 puis relancez Kiara.'})
            try:
                from thunderbird_integration import manage
                result = manage(remote.profile, thunderbird_extension_source(), enable=self.command == 'POST', inspect=self.command == 'GET')
            except (OSError, ValueError, KeyError, TypeError) as error:
                return self.reply(400, {'detail': str(error) or 'Installation Thunderbird impossible.'})
            return self.reply(200, result)

        def agent_desktop_capture(self, match):
            sid, operation = match.groups() if match else (None, 'status')
            try:
                if sid and str(UUID(sid)) != sid:
                    raise ValueError('Séance invalide.')
                if operation == 'status' and self.command == 'GET':
                    return self.reply(200, desktop_capture.status(sid))
                if operation != 'status' and self.command == 'POST':
                    values = json_body(self, 8192)
                    with desktop_capture.lock:
                        if operation == 'start' and remote.applying_update:
                            raise ValueError('Attendez le redémarrage de Kiara avant de lancer une capture.')
                        result = desktop_capture.control(sid, operation, values)
                    return self.reply(200, result)
                return self.reply(405, {'detail': 'Commande de capture non disponible.'})
            except urllib.error.HTTPError as error:
                status = error.code
                error.close()
                return self.reply(status, {'detail': 'La séance a changé ou le serveur ne répond pas. Actualisez la séance. Les fragments restent sur ce poste.'})
            except ValueError as error:
                return self.reply(409, {'detail': str(error)})
            except (OSError, KeyError, subprocess.SubprocessError):
                return self.reply(503, {'detail': 'Capture Windows indisponible. Les fragments restent sur ce poste.'})

        def thunderbird_origin(self):
            from re import fullmatch
            return bool(fullmatch(r'moz-extension://[0-9a-fA-F-]{36}', self.headers.get('Origin', '')))

        def do_OPTIONS(self):
            if (not bridge_route(self.path) or not self.thunderbird_origin()
                    or self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}'
                    or self.headers.get('Access-Control-Request-Method') != 'POST'):
                return self.reply(403, {'detail': 'Origine de liaison non autorisée.'})
            self.send_response(204)
            self.send_header('Access-Control-Allow-Origin', self.headers['Origin'])
            self.send_header('Access-Control-Allow-Methods', 'POST')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Agent-Thunderbird-Token')
            self.send_header('Vary', 'Origin')
            self.end_headers()

        def agent_session(self):
            if not self.authorized():
                return
            try:
                json_body(self, 4096)
            except (ValueError, TypeError):
                return self.reply(400, {'error': {'message': 'Demande invalide.'}})
            try:
                with remote.open('/v1/business/api/v1/session') as response:
                    response.read(65536)
            except urllib.error.HTTPError as error:
                status = 403 if error.code in (401, 403) else 503
                error.close()
                return self.reply(status, {'error': {'message': 'Accès aux projets indisponible. Vérifiez la connexion ou contactez votre administrateur.'}})
            except (OSError, ValueError, urllib.error.URLError):
                return self.reply(503, {'error': {'message': 'Projets indisponibles. Vérifiez la connexion puis réessayez.'}})
            data = b'{"url":"/app"}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Set-Cookie', f'kiara_agent={agent_cookie}; Path=/; HttpOnly; SameSite=Strict')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def agent_open_path(self):
            origin = f'http://{self.headers.get("Host", "")}'
            if not self.agent_authorized() or self.headers.get('Origin') != origin:
                return self.reply(403, {'detail': 'Ouvrez Projets depuis la navigation Kiara.'})
            if sys.platform != 'win32':
                return self.reply(403, {'detail': 'Ouvrez ce chemin depuis le poste Windows.'})
            try:
                data = json_body(self, 8192)
                project = data.get('project') if isinstance(data, dict) else None
                if not isinstance(project, str) or str(UUID(project)) != project:
                    raise ValueError('Projet invalide.')
                value = data.get('path')
            except (ValueError, TypeError):
                return self.reply(400, {'detail': 'Projet ou chemin invalide.'})
            try:
                with remote.open(f'/v1/business/api/v1/projects/{project}/network-links') as response:
                    response.read(1024 * 1024)
            except urllib.error.HTTPError as error:
                status = 403 if error.code in (401, 403, 404) else 503
                error.close()
                return self.reply(status, {'detail': 'Vérifiez votre accès au projet avant d’ouvrir ce chemin.'})
            except (OSError, ValueError):
                return self.reply(503, {'detail': 'Connexion au projet indisponible.'})
            try:
                roots = [root for root in os.environ.get('AGENT_OPEN_ROOTS', '').split(';') if root]
                path = agent_windows_path(value, roots)
                os.startfile(str(path))
            except PermissionError as error:
                return self.reply(403, {'detail': str(error) if error.errno is None else 'Accès refusé sur ce poste.'})
            except (OSError, ValueError, RuntimeError):
                return self.reply(422, {'detail': 'Ce fichier ou dossier est inaccessible sur ce poste.'})
            return self.reply(200, {'opened': True})

        def chat(self):
            if not self.local_request():
                return self.reply(403, {'error': {'message': 'Le chat est accessible sur localhost uniquement.'}})
            nonce = secrets.token_urlsafe(24)
            config = json.dumps({'key':key, 'model':remote.model, 'version':remote.version, 'storage':hashlib.sha256(key.encode()).hexdigest()[:20], 'platform':'linux' if sys.platform.startswith('linux') else 'windows'}, ensure_ascii=False).replace('<', '\\u003c')
            template = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'chat.html'
            scripts=('ui.js','attachments.js','corrector.js','selection.js','thinking.js','voice.js','conversation.js','project-conversation.js')+ (('linux_features.js',) if sys.platform.startswith('linux') else ()) + ('portal_conflict_archive.js','portal_conflict_review.js','portal_conflict_library.js','portal_origin_recovery.js','portal_audio_conflict_archive.js','portal_audio_conflict_library.js')
            presentation = ''.join('<script nonce="__NONCE__">'+(template.parent/name).read_text(encoding='utf-8')+'</script>' for name in scripts)
            markdown=''.join('<script nonce="__NONCE__">'+path.read_text(encoding='utf-8').replace('</script','<\\/script')+'</script>' for path in (template.parent/'vendor/markdown-it.min.js',template.parent/'markdown.js'))
            css = ''.join((template.parent/name).read_text(encoding='utf-8') for name in ('ui.css','portal_conflict_library.css'))
            content = template.read_text(encoding='utf-8').replace('</head>',markdown+'</head>').replace('</body>',(template.parent/'workspace.html').read_text(encoding='utf-8')+presentation+'</body>').replace('__UI_CSS__',css).replace('__CONFIG__', config).replace('__NONCE__', nonce).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; connect-src 'self'; img-src data:; media-src blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            if self.agent_request():
                return self.agent_proxy()
            if self.path=='/client/voice/max':
                if not self.authorized():return
                return self.reply(200,{'pc':advanced.status(),'server':max_server_status(),'installation':max_installation.status()})
            if self.path=='/hermes/v1/models':
                if not self.authorized():return
                state=remote.check()
                if not state['connected']:return self.reply(503,{'error':{'message':state['error']}})
                return self.reply(200,hermes_catalogue.catalogue(remote.models_catalogue)[0])
            if self.path == '/client/wakeword':
                if not self.authorized():return
                return self.reply(200,wakeword.status())
            if self.path == '/client/conversation':
                if not self.authorized():return
                return self.reply(200,conversation.status())
            if self.path in ('/', '/chat'):
                try:
                    return self.chat()
                except (FileNotFoundError, UnicodeError):
                    return self.reply(503, {'error': {'message': 'Impossible de charger l’interface. Réinstallez le paquet complet de Kiara.'}})
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
                return self.reply(200,{'version':remote.version,'logged_in':True,'username':'Accès personnel','endpoint':remote.endpoint,'internet_endpoint':remote.profile['wireguard']['endpoint'],'connection':remote.state(),'history':histories.status(),'preferences':client_settings(remote.profile).get('preferences',{}),'update':remote.update_state,'desktop_managed':managed,'kiara4_migration':sys.platform=='win32' and not managed and bool(getattr(sys,'frozen',False)),'local_api':f'http://127.0.0.1:{self.server.server_port}/v1','key':key})
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
            if self.path not in ('/v1/models', '/v1/status','/v1/workspace','/v1/notifications','/v1/voice/status','/v1/agent/state'):
                return self.reply(404, {'error': {'message': 'Route non disponible.'}})
            if not self.authorized():
                return
            if self.path=='/v1/models':
                state=remote.check()
                if not state['connected']:return self.reply(401 if state['code'] in ('access_denied','access_revoked','access_suspended','access_expired','remote_disabled') else 503,{'error':{'code':state['code'],'message':state['error']}})
                if not getattr(remote,'update_checked',False) and remote.profile.get('update_public_key'):
                    remote.update_checked=True;remote.update(False)
                return self.reply(200,copy.deepcopy(remote.models_catalogue))
            self.forward()

        def do_POST(self):
            if self.path in ('/client/project-session', '/client/agent/session'):
                return self.agent_session()
            if self.path == '/api/v1/open-path':
                return self.agent_open_path()
            if self.agent_request():
                return self.agent_proxy()
            hermes_request=self.path=='/hermes/v1/chat/completions'
            if hermes_request:self.path='/v1/chat/completions'
            if self.path not in ('/client/wakeword','/client/capture') and self.path not in ('/v1/embeddings','/v1/chat/completions','/v1/responses','/v1/context', '/v1/cancel','/v1/workspace/action','/v1/notifications/action','/v1/agent/action','/v1/voice/speech','/v1/voice/cancel','/client/conversation','/client/draft','/client/endpoint','/client/preferences','/client/update/check','/client/update/apply','/client/update/kiara4','/client/history','/client/history/sync','/client/history/restore-ack','/client/history/flush','/client/history/recover','/client/integrations/apply','/client/voice','/client/voice/max/test','/client/voice/max/transcribe','/client/voice/max/speech','/client/voice/max/cancel','/client/voice/max/plan','/client/voice/max/install','/client/voice/max/install-cancel','/client/voice/max/detect','/client/voice/max/remove','/client/voice/max/open-folder','/client/voice/max/choose-folder','/client/voice/max/devices','/client/voice/max/gpu'):
                return self.reply(404, {'error': {'message': 'Route non disponible.'}})
            if not self.authorized():
                return
            try:
                maximum = 10*1024*1024 if self.path.startswith('/client/history') or self.path in ('/v1/chat/completions','/v1/responses','/v1/context') else 8*1024*1024 if self.path=='/v1/workspace/action' else 2*1024*1024
                values = json_body(self, maximum)
                if hermes_request:
                    state=remote.check()
                    if not state['connected']:return self.reply(503,{'error':{'message':state['error']}})
                    _,mapping=hermes_catalogue.catalogue(remote.models_catalogue)
                    selected=mapping.get(values.get('model')) if isinstance(values.get('model'),str) else None
                    if selected is None:raise ValueError('Modèle Hermes indisponible. Actualisez la liste.')
                    values['model']=selected
                body = json.dumps(values, ensure_ascii=False).encode('utf-8')
                streaming = bool(values.get('stream'))
            except (OSError, ValueError, AttributeError) as error:
                return self.reply(400, {'error': {'message': str(error)}})
            if self.path.startswith('/client/voice/max/'):
                frames=None;sent=False
                try:
                    suffix=self.path.rsplit('/',1)[1]
                    if suffix in ('plan','install','install-cancel','detect','remove','open-folder','choose-folder','devices','gpu'):
                        if not isinstance(values,dict):raise ValueError('Paramètres d’installation Max invalides.')
                        with voice_control:
                            if suffix!='open-folder' and (conversation.status()['phase'] in ('loading','listening','stopping') or voice.status()['phase'] in ('loading','listening','finishing')):
                                raise ValueError('Terminez le vocal avant de modifier Max.')
                            if suffix=='plan' and not values:return self.reply(200,max_installation.plan())
                            if suffix=='install' and set(values)=={'plan'}:return self.reply(200,max_installation.install(values['plan']))
                            if suffix=='install-cancel' and not values:return self.reply(200,max_installation.cancel())
                            if suffix=='remove' and set(values)=={'confirm'} and values['confirm'] is True:return self.reply(200,max_installation.remove())
                            if suffix=='open-folder' and not values:return self.reply(200,max_installation.open_folder())
                            if suffix=='choose-folder' and not values:return self.reply(200,max_installation.choose_folder())
                            if suffix in ('devices','gpu'):
                                if max_installation.status()['phase'] in ('downloading','verifying','testing'):raise ValueError('Attendez la fin de l’installation Max.')
                                if suffix=='devices' and not values:return self.reply(200,advanced.detect_devices())
                                if suffix=='gpu' and set(values)=={'device'}:return self.reply(200,advanced.set_gpu(values['device']))
                            if suffix=='detect' and not values:
                                max_installation.detect();return self.reply(200,max_installation.status())
                            raise ValueError('Paramètres d’installation Max invalides.')
                    if self.path.endswith('/test'):
                        if not isinstance(values,dict) or set(values)!={'execution'} or values['execution'] not in ('pc','server'):raise ValueError('Choisissez le PC ou le serveur pour le test.')
                        if conversation.status()['phase'] in ('loading','listening','stopping'):raise ValueError('Raccrochez avant de tester le mode Max.')
                        if max_installation.status()['phase'] in ('downloading','verifying','testing'):raise ValueError('Attendez la fin de l’installation Max.')
                        if values['execution']=='server':
                            with remote.open('/v1/voice/max/test',b'{}') as response:return self.reply(200,json.loads(response.read(65536)))
                        return self.reply(200,advanced.test())
                    if not isinstance(values,dict):raise ValueError('Paramètres Max invalides.')
                    state=conversation.status();owner=values.pop('session',None)
                    if not owner or owner!=state['session'] or state.get('quality')!='max':raise ValueError('Cette session Max est terminée.')
                    if state['phase'] not in ('loading','listening') and not self.path.endswith('/cancel'):raise ValueError('Le mode Max est arrêté.')
                    suffix=self.path.rsplit('/',1)[1]
                    if suffix=='transcribe':conversation.asr_request_id=values.get('request_id')
                    if state['execution']=='server':
                        self.path='/v1/voice/max/'+suffix
                        return self.forward(json.dumps(values).encode(),suffix=='speech')
                    valid=lambda:conversation.status()['session']==owner and conversation.status()['phase'] in ('loading','listening')
                    if suffix=='transcribe':return self.reply(200,advanced.transcribe(owner,values,valid))
                    if suffix=='cancel':
                        if set(values)!={'request_id'} or not isinstance(values['request_id'],str):raise ValueError('Annulation Max invalide.')
                        return self.reply(200,advanced.cancel(owner,values['request_id']))
                    frames=advanced.frames(owner,'speak',values,valid);first=next(frames)
                    self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Cache-Control','no-store');self.send_header('Connection','close');self.end_headers();sent=True
                    self.wfile.write(('data: '+json.dumps(first)+'\n\n').encode());self.wfile.flush()
                    for frame in frames:
                        self.wfile.write(('data: '+json.dumps(frame)+'\n\n').encode());self.wfile.flush()
                except urllib.error.HTTPError as error:
                    if not sent:self.reply(error.code,{'error':{'message':'Le mode Max est indisponible sur le serveur. Choisissez Low ou réessayez.'}})
                    error.close()
                except (ValueError,OSError,TypeError,StopIteration) as error:
                    if not sent:self.reply(400,{'error':{'message':str(error) or 'Lecture Max indisponible.'}})
                finally:
                    if frames:frames.close()
                return
            if self.path.startswith('/client/'):
                try:
                    values=json.loads(body)
                    if not isinstance(values,dict):raise ValueError('Paramètres invalides.')
                    if self.path in ('/client/update/apply','/client/update/kiara4','/client/endpoint') and (wakeword.status()['phase'] in ('loading','listening','stopping') or voice.status()['phase'] in ('loading','listening','finishing','cancelling') or conversation.status()['phase'] in ('loading','listening','stopping')):
                        raise ValueError('Terminez la dictée avant de mettre le client à jour.')
                    if self.path=='/client/capture':
                        if values:raise ValueError('La capture ne reçoit pas de coordonnées ni de chemin.')
                        from screen_capture import capture
                        result=capture()
                    elif self.path=='/client/wakeword':
                        with voice_control:
                            if values.get('action')=='start' and (voice.status()['phase'] in ('loading','listening','finishing') or conversation.status()['phase'] in ('loading','listening','stopping')):raise ValueError('Terminez la dictée ou la conversation avant d’activer le mot d’appel.')
                            result=wakeword.action(values)
                    elif self.path=='/client/conversation':
                        with voice_control:
                            current=conversation.status()
                            if values.get('action')=='start' and wakeword.status()['phase'] in ('loading','listening','stopping'):raise ValueError('Arrêtez le mot d’appel avant de démarrer la conversation.')
                            if values.get('action') in ('start','install') and voice.status()['phase'] in ('installing','loading','listening','finishing','stopping','cancelling'):raise ValueError('Terminez la dictée avant de converser.')
                            if values.get('action')=='start' and values.get('quality')=='max':
                                if max_installation.status()['phase'] in ('downloading','verifying','testing'):raise ValueError('Attendez la fin de l’installation Max.')
                                values['execution']=choose_execution(advanced.status(),max_server_status(),values.get('execution','auto'))
                            if values.get('action') in ('stop','cancel') and conversation.status().get('quality')=='max':
                                current=conversation.status();identifier=getattr(conversation,'asr_request_id',None)
                                if identifier and values.get('session')==current['session']:
                                    if current.get('execution')=='pc':advanced.cancel(current['session'],identifier)
                                    else:
                                        try:
                                            with remote.open('/v1/voice/max/cancel',json.dumps({'request_id':identifier}).encode()) as response:response.read(8192)
                                        except OSError:pass
                            result=conversation.action(values)
                            if values.get('action') in ('stop','cancel') and current.get('quality')=='max':
                                if current.get('execution')=='pc':advanced.release(current['session'],current['session'])
                                else:
                                    try:
                                        with remote.open('/v1/voice/max/end',json.dumps({'session':current['session']}).encode()) as response:response.read(8192)
                                    except OSError:pass
                    elif self.path=='/client/voice':
                        with voice_control:
                            if values.get('action') in ('start','install','remove') and wakeword.status()['phase'] in ('loading','listening','stopping'):raise ValueError('Arrêtez le mot d’appel avant de dicter.')
                            if values.get('action') in ('start','install','remove') and conversation.status()['phase'] in ('installing','loading','listening','stopping'):raise ValueError('Raccrochez avant de dicter ou de modifier le modèle vocal.')
                            result=voice.action(values)
                    elif self.path=='/client/integrations/apply':
                        if set(values)-{'app','model'}:raise ValueError('Paramètres d’intégration invalides.')
                        state=remote.check()
                        if not state['connected']:raise ValueError('Connectez le client au serveur et chargez un modèle avant de l’ajouter.')
                        model=values.get('model') or state['model']
                        if model not in state['models']:raise ValueError('Ce modèle n’est plus disponible sur le serveur. Actualisez la liste.')
                        result=app_integrations.install(values.get('app'),f'http://127.0.0.1:{self.server.server_port}/v1',key,model,catalogue=copy.deepcopy(remote.models_catalogue),remote=remote)
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
                    elif self.path=='/client/update/kiara4':
                        if values:raise ValueError('Paramètres de migration invalides.')
                        histories.flush()
                        result=remote.update(True,migrate=True)
                    else:
                        apply = self.path.endswith('/apply')
                        if managed and apply and desktop_capture:
                            with desktop_capture.lock:
                                if desktop_capture.current:
                                    raise ValueError('Terminez l’enregistrement de la réunion avant la mise à jour.')
                                result = remote.update(apply)
                        else:
                            result = remote.update(apply)
                    return self.reply(200,result)
                except urllib.error.HTTPError as error:
                    try:return self.reply(error.code,json.loads(error.read(65536)))
                    finally:error.close()
                except history_store.HistoryConflict as error:return self.reply(409,{'error':{'message':str(error)}})
                except (ValueError,OSError,TypeError) as error:return self.reply(400,{'error':{'message':str(error)}})
            self.forward(body, streaming)

        def agent_write(self):
            if self.agent_request():
                return self.agent_proxy()
            return self.reply(404, {'error': {'message': 'Route non disponible.'}})

        do_PUT = agent_write
        do_PATCH = agent_write
        do_DELETE = agent_write

        def forward(self, body=None, streaming=False):
            sent = False
            inference=self.path in ('/v1/embeddings','/v1/chat/completions','/v1/responses','/v1/workspace/action')
            tracked=self.path!='/v1/cancel'
            chat_stream=streaming and self.path=='/v1/chat/completions'
            if chat_stream:remote.stream={'phase':'requesting','started':time.time(),'last_event':time.time(),'reasoning_chars':0,'answer_chars':0}
            with remote.activity_lock:
                if self.path=='/v1/cancel' and self.headers.get('X-Qwen-Request'):
                    remote.cancelled_requests.append(self.headers.get('X-Qwen-Request'))
                if inference and remote.applying_update:return self.reply(409,{'error':{'message':'Mise à jour en cours. Réessayer après le redémarrage.'}})
                if tracked:remote.active_requests+=1
                if inference:remote.active_inference_requests+=1
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
                        done=False;stream_error=False
                        for line in response:
                            if line.strip()==b'data: [DONE]':done=True
                            if line.startswith(b'data: ') and line.strip()!=b'data: [DONE]':
                                try:
                                    event=json.loads(line[6:])
                                    stream_error=stream_error or bool(event.get('error'))
                                    if self.path=='/v1/responses':
                                        done=done or event.get('type') in ('response.completed','response.incomplete','response.failed')
                                        stream_error=stream_error or event.get('type') in ('response.failed','error')
                                except (ValueError,AttributeError):pass
                            if self.path in ('/v1/voice/speech','/v1/voice/max/speech') and line.startswith(b'data: '):
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
                                        status=event.get('hermes_status')
                                        if isinstance(status,dict):remote.stream['phase']=status.get('phase','working')
                                        if isinstance(event.get('hermes_approval'),dict):remote.stream['phase']='approval'
                                        final=event.get('hermes_answer')
                                        if isinstance(final,dict) and isinstance(final.get('text'),str):remote.stream['answer_chars']=len(final['text'])
                                        reason=delta.get('reasoning_content',delta.get('reasoning',''));content=delta.get('content','')
                                        if isinstance(reason,str) and reason:remote.stream['reasoning_chars']+=len(reason);remote.stream['phase']='thinking'
                                        if isinstance(content,str) and content:remote.stream['answer_chars']+=len(content);remote.stream['phase']='answering'
                                        if choice.get('finish_reason'):remote.stream['finish_reason']=choice['finish_reason']
                                    except (ValueError,TypeError,AttributeError,IndexError):pass
                            self.wfile.write(line)
                            self.wfile.flush()
                        if not done and not stream_error:raise ValueError('Flux interrompu avant la confirmation de fin.')
                        if chat_stream:
                            remote.stream['phase']='failed' if stream_error else 'complete'
                            remote.event('generation_failed' if stream_error else 'generation_complete',reasoning_chars=remote.stream['reasoning_chars'],answer_chars=remote.stream['answer_chars'],finish_reason=remote.stream.get('finish_reason'))
                    else:
                        while True:
                            block = response.read1(65536)
                            if not block:
                                break
                            self.wfile.write(block)
            except (OSError, ValueError, urllib.error.URLError):
                cancelled=chat_stream and self.headers.get('X-Qwen-Request') in remote.cancelled_requests
                if self.path not in ('/v1/voice/speech','/v1/voice/max/speech') and not cancelled:remote.failure('connection_error','Connexion au serveur IA interrompue. Réessayer la requête.',confirmed=chat_stream)
                if not sent:
                    self.reply(503, {'error': {'message': 'Connexion au serveur IA indisponible.'}})
                elif streaming:
                    try:
                        event={'error':{'code':'request_cancelled' if cancelled else 'connection_error','message':'Réponse arrêtée.' if cancelled else 'Connexion interrompue : la réponse peut être incomplète.'}}
                        self.wfile.write(('\n\ndata: '+json.dumps(event,ensure_ascii=False)+'\n\n').encode());self.wfile.flush()
                    except OSError:pass
            finally:
                if chat_stream and remote.stream.get('phase') not in ('complete','failed'):remote.stream['phase']='interrupted';remote.event('generation_interrupted')
                if tracked:
                    with remote.activity_lock:
                        remote.active_requests-=1
                        if inference:remote.active_inference_requests-=1
    server = LocalHTTPServer(('127.0.0.1', port), Handler)
    server.voice = voice
    server.conversation = conversation
    server.wakeword = wakeword
    conversation.max_bridge={'port':server.server_port,'token':key}
    def prepare_max_session():
        state=conversation.status();target=state['execution'];owner=state['session']
        if target=='pc':advanced.warm(owner,owner)
        else:
            with remote.open('/v1/voice/max/warm',json.dumps({'session':owner}).encode()) as response:response.read(65536)
        deadline=time.monotonic()+180
        while not conversation.cancelled.is_set():
            state=advanced.status() if target=='pc' else max_server_status()
            if state.get('loaded'):
                conversation.max_bridge['progressive']=state.get('progressive') is True
                conversation.max_bridge['recognizer']=state.get('recognizer','Parakeet v3 · progressif')
                return
            if state.get('runtime_error'):raise ValueError(state['runtime_error'])
            if not state.get('available') or time.monotonic()>deadline:raise ValueError(state.get('message') or 'Chargement du mode Max trop long. Choisissez Low.')
            conversation.cancelled.wait(.3)
    conversation.max_prepare=prepare_max_session
    def max_capture_models():
        configuration=advanced.configuration();folder=Path(configuration.get('asr','')).resolve()
        if configuration.get('format')==2 and folder.is_relative_to(advanced.home.resolve()) and all((folder/name).is_file() for name in ('silero-vad.onnx','smart-turn.onnx')):return folder
        return conversation.cache
    conversation.max_models=max_capture_models
    server.advanced_voice=advanced
    server.desktop_capture=desktop_capture
    server.linux_system_audio=linux_system_audio
    server.max_installation=max_installation
    server.daemon_threads = True
    if desktop_capture:
        desktop_capture.start_transfer_worker()
    return server

class LocalHTTPServer(BoundedHTTPServer):
    """Bounded workers also cover stalled or unauthorized loopback connections."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,capacity=24,**kwargs)

    def server_close(self):
        if getattr(self, 'desktop_capture', None):self.desktop_capture.close()
        if getattr(self, 'linux_system_audio', None):
            try:self.linux_system_audio.close()
            except ValueError:pass  # The worker also cleans up on relay exit.
        if hasattr(self, "max_installation"):self.max_installation.close()
        if hasattr(self, "conversation"):self.conversation.close()
        if hasattr(self, "wakeword"):self.wakeword.close()
        if hasattr(self, "voice"):self.voice.close()
        if hasattr(self, "advanced_voice"):self.advanced_voice.close()
        super().server_close()

def read_profile(executable=None):
    if sys.platform.startswith('linux'):
        from linux_support import read_profile as linux_profile
        return linux_profile()
    if executable is not None or getattr(sys, 'frozen', False):
        with open(executable or sys.executable, 'rb') as stream:
            if stream.seek(0, 2) < 16:
                raise ValueError('Accès intégré invalide.')
            stream.seek(-16, 2)
            footer = stream.read(16)
            if footer[4:] == b'QWENPROFILE1':
                size = struct.unpack('<I', footer[:4])[0]
                if not 1 <= size <= min(65536, stream.tell() - 16):
                    raise ValueError('Accès intégré invalide.')
                stream.seek(-16 - size, 2)
                profile = json.loads(stream.read(size))
                validate_profile(profile)
                return profile
        if executable is not None:
            raise ValueError('Le fichier choisi ne contient pas de profil Kiara.')
    bundled = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'profil.json'
    # Per-client profile is bundled by the server; no settings or file import on the client.
    if not bundled.exists():
        raise ValueError('Cet EXE ne contient pas encore d’accès. Générer un client depuis la console du serveur.')
    profile = json.loads(bundled.read_text(encoding='utf-8'))
    validate_profile(profile)
    return profile

def settings_path(profile):
    if sys.platform.startswith('linux'):
        from linux_support import settings_path as linux_settings_path
        return linux_settings_path(profile)
    identity = hashlib.sha256((profile['url'] + profile['token']).encode()).hexdigest()[:20]
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'QwenClient' / (identity + '.dpapi')

def client_settings(profile):
    try:
        data=json.loads(protect(settings_path(profile).read_bytes(),decrypt=True))
        if not isinstance(data,dict):return {}
        if data.get('endpoint'):data['endpoint']=validate_connection_endpoint(data['endpoint'])
        return data
    except (OSError,ValueError,KeyError):return {}


class LocalSettingsUnreadable(ValueError):
    """Existing client settings must be preserved until they can be read."""


def read_settings_for_update(profile):
    """Never treat unreadable existing settings as a new, empty profile."""
    path = settings_path(profile)
    try:
        if path.is_symlink():
            raise LocalSettingsUnreadable('Réglages locaux illisibles. Le fichier original est conservé.')
        raw = path.read_bytes()
    except FileNotFoundError:
        return {}
    except OSError as error:
        raise LocalSettingsUnreadable('Réglages locaux illisibles. Le fichier original est conservé.') from error
    try:
        data = json.loads(protect(raw, decrypt=True))
        if not isinstance(data, dict):
            raise ValueError('invalid settings')
        return data
    except (OSError, ValueError, TypeError, UnicodeError, RuntimeError) as error:
        raise LocalSettingsUnreadable('Réglages locaux illisibles. Le fichier original est conservé.') from error


def save_endpoint(profile,endpoint=None):
    from file_lock import locked
    path=settings_path(profile)
    with locked(path):
        values=read_settings_for_update(profile)
        values['connection_selected']=True
        if endpoint:values['endpoint']=validate_connection_endpoint(endpoint)
        else:values.pop('endpoint',None)
        history_store.atomic(path,protect(json.dumps(values)))

def local_key(profile):
    from file_lock import locked
    with locked(settings_path(profile)):return _local_key(profile)

def validate_conversation_drafts(value):
    if not isinstance(value,dict) or len(value)>256 or any(not isinstance(key,str) or not 1<=len(key)<=128 or any(ord(c)<32 for c in key) or not isinstance(text,str) or len(text)>100000 for key,text in value.items()) or len(json.dumps(value,ensure_ascii=False).encode('utf-8'))>1024*1024:
        raise ValueError('Brouillons des conversations trop volumineux ou invalides.')


def save_preferences(profile,values):
    allowed={'theme':('light','dark','system'),'font':('system','humanist','serif','mono'),
             'voice_quality':('low','max'),'voice_execution':('auto','pc','server'),'voice_animation_style':('waves','orb','constellation'),'voice_visual_version':(2,),
             'text_size':('compact','standard','large','extra'),'thinking_effort':('none','minimal','low','medium','high','xhigh','max','ultra','on')}
    if not isinstance(values,dict) or set(values)-set(allowed)-{'thinking','thinking_by_model','sidebar_collapsed','corrector_text','conversation_drafts','voice_interruptions','voice_animation','voice_volume'}:raise ValueError('Réglages invalides.')
    for name,value in values.items():
        if name in allowed and value not in allowed[name]:raise ValueError('Réglage invalide : '+name)
        if name in ('thinking','sidebar_collapsed','voice_interruptions','voice_animation') and type(value) is not bool:raise ValueError('Réglage booléen attendu.')
        if name=='voice_volume' and (type(value) is not int or not 0<=value<=100):raise ValueError('Volume invalide (0 à 100).')
        if name=='voice_visual_version' and (type(value) is not int or value!=2):raise ValueError('Affichage vocal invalide.')
        if name=='corrector_text' and (not isinstance(value,str) or len(value)>100000):raise ValueError('Brouillon du correcteur invalide (100 000 caractères maximum).')
        if name=='conversation_drafts':validate_conversation_drafts(value)
        if name=='thinking_by_model' and (not isinstance(value,dict) or len(value)>512 or any(not isinstance(model,str) or not model.strip() or len(model)>512 or any(ord(c)<32 for c in model) or not isinstance(effort,str) or effort not in allowed['thinking_effort'] for model,effort in value.items())):raise ValueError('Réflexion par modèle invalide.')
    from file_lock import locked
    path=settings_path(profile)
    with locked(path):
        settings=read_settings_for_update(profile)
        if 'conversation_drafts' in values:
            drafts={**settings.get('preferences',{}).get('conversation_drafts',{})}
            for key,text in values['conversation_drafts'].items():
                if text:drafts[key]=text
                else:drafts.pop(key,None)
            validate_conversation_drafts(drafts)
            values={**values,'conversation_drafts':drafts}
        settings['preferences']={**settings.get('preferences',{}),**values}
        settings['preferences'].pop('maximum',None)
        history_store.atomic(path,protect(json.dumps(settings)))
    return {'saved':True}

def _local_key(profile):
    path = settings_path(profile)
    data = read_settings_for_update(profile)
    if 'local_key' in data:
        key = data['local_key']
        if not isinstance(key, str) or len(key) < 32:
            raise LocalSettingsUnreadable('Clé locale illisible. Les réglages originaux sont conservés.')
        return key
    key = 'local_' + secrets.token_urlsafe(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    data['local_key'] = key
    history_store.atomic(path, protect(json.dumps(data)))
    return key

def _prepare_close_linux(window, timeout=90):
    """Await the page's save barrier without eval, which Kiara's CSP forbids."""
    identifier = secrets.token_hex(16)
    token = json.dumps(identifier)
    window.run_js("""(() => {
      const id = %s;
      window.__kiaraCloseGuard = {id, pending: true};
      (async () => {
        let result;
        try {
          if (window.kiaraPrepareClose) await window.kiaraPrepareClose();
          else if (!window.dispatchEvent(new Event('beforeunload', {cancelable:true})))
            throw new Error('Des modifications sont en cours dans Kiara.');
          result = {saved:true};
        } catch (error) { result = {saved:false, message:String((error && error.message) || error)}; }
        if (window.__kiaraCloseGuard?.id === id) window.__kiaraCloseGuard = {id, pending:false, result};
      })();
    })()""" % token)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = window.run_js('JSON.stringify(window.__kiaraCloseGuard || null)')
        if isinstance(value, str):
            try: value = json.loads(value)
            except ValueError: value = None
        if isinstance(value, dict) and value.get('id') == identifier and value.get('pending') is False:
            return value.get('result')
        time.sleep(0.1)
    return {'saved':False, 'message':'La sauvegarde ne répond pas encore.'}


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
            try:
                if sys.platform.startswith('linux'):
                    complete(_prepare_close_linux(window))
                else:
                    window.evaluate_js("(async()=>{try{if(window.kiaraPrepareClose)await window.kiaraPrepareClose();else if(!window.dispatchEvent(new Event('beforeunload',{cancelable:true})))throw new Error('Des modifications sont en cours dans Kiara.');return {saved:true};}catch(e){return {saved:false,message:e.message};}})()",callback=complete)
            except Exception as error:complete({'saved':False,'message':str(error)})
        threading.Thread(target=work,daemon=True).start()
        return False
    window.events.closing+=closing
    return state

def window_geometry():
    """Keep the initial window inside the Windows work area, including scaled displays."""
    # Leave room for the desktop panel and window decorations at 720p.
    width,height=(1100,650) if sys.platform.startswith('linux') else (1200,780)
    if sys.platform == 'win32':
        try:
            area=wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(0x0030,0,ctypes.byref(area),0):
                width=max(400,min(1440,int((area.right-area.left)*0.9)))
                height=max(320,min(960,int((area.bottom-area.top)*0.9)))
        except (AttributeError,OSError):pass
    return {'width':width,'height':height,'min_size':(min(640,width),min(480,height))}

def thunderbird_extension_source():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / 'thunderbird-agent'
    return Path(__file__).resolve().parent.parent / 'agent' / 'extensions' / 'thunderbird-agent'


class LocalOriginPortUnavailable(ValueError):
    """The recorded portal origin cannot be opened without switching ports."""


class LocalOriginIncompatible(ValueError):
    """A fixed integration conflicts with the recorded portal origin."""


def portal_recovery_fixed_port(profile):
    """Keep an existing Thunderbird pairing during a future origin inventory."""
    settings = read_settings_for_update(profile)
    return LOCAL_API_PORT if settings.get('thunderbird_token') else None


def open_local_relay(profile, *, managed=False, required_port=None):
    if managed and sys.platform == 'win32' and (thunderbird_extension_source() / 'manifest.json').is_file():
        from thunderbird_integration import manage
        try:
            manage(profile, thunderbird_extension_source())
        except (OSError, ValueError, KeyError, TypeError):
            pass  # The Thunderbird panel can report the error without blocking Kiara startup.
    settings = read_settings_for_update(profile)
    if settings.get('endpoint'):
        try:
            settings['endpoint'] = validate_connection_endpoint(settings['endpoint'])
        except (ValueError, TypeError):
            # Keep other settings (notably Thunderbird's fixed port) while
            # asking for a valid address; do not change the original file.
            settings.pop('endpoint', None)
            settings['connection_selected'] = False
    remote = Remote(profile, endpoint=settings.get('endpoint'),
                    connection_required=not (settings.get('connection_selected') or settings.get('endpoint')))
    try:
        last_port = LOCAL_API_PORT if settings.get('thunderbird_token') else LOCAL_API_LAST_PORT
        if required_port is not None:
            if type(required_port) is not int or not LOCAL_API_PORT <= required_port <= last_port:
                raise LocalOriginIncompatible('Le port local enregistré est incompatible avec cet accès.')
        key = local_key(profile)
        if required_port is not None:
            try:
                return remote, serve_local(remote, key, required_port, managed=managed)
            except OSError as error:
                raise LocalOriginPortUnavailable(f'Le port local {required_port} est occupé. Fermez l’application qui l’utilise puis réessayez.') from error
        for port in range(LOCAL_API_PORT, last_port + 1):
            try:
                return remote, serve_local(remote, key, port, managed=managed)
            except OSError:
                pass
        if last_port == LOCAL_API_PORT:
            raise ValueError(f'Le port local {LOCAL_API_PORT} de Thunderbird est occupé.')
        raise ValueError(f'Les ports locaux {LOCAL_API_PORT} à {last_port} sont occupés.')
    except BaseException:
        remote.close()
        raise


def relay_profile_path():
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'QwenClient' / 'tauri-profile.dpapi'


def read_relay_profile():
    with relay_profile_path().open('rb') as stream:
        protected = stream.read(131073)
    if len(protected) > 131072:
        raise ValueError('Profil Kiara trop volumineux.')
    profile = json.loads(protect(protected, decrypt=True))
    validate_profile(profile)
    return profile


def select_relay_profile():
    from kiara_shared.profiles import decode_access_code

    print('KIARA_RELAY_SELECT_PROFILE', flush=True)
    root = tk.Tk()
    root.withdraw()
    try:
        while True:
            code = simpledialog.askstring('Connexion à Kiara',
                'Collez le code d’accès fourni par votre administrateur.',
                show='*', parent=root)
            if code is None:
                return None
            try:
                return decode_access_code(code)
            except ValueError:
                messagebox.showerror(APP_NAME, 'Code d’accès invalide. Copiez le code complet puis réessayez.', parent=root)
    finally:
        root.destroy()


def relay_stdio(executable=None, version=VERSION):
    validate_version(version)
    linux = sys.platform.startswith('linux')
    profile_path = None if linux else relay_profile_path()
    profile_can_be_checked = True
    if linux:
        if executable is not None:
            raise ValueError('Utilisez le profil Linux existant pour cet appareil.')
        from linux_support import data_home
        try:
            profile_state = (data_home() / 'profile.enc').lstat()
            profile_can_be_checked = stat.S_ISREG(profile_state.st_mode)
        except FileNotFoundError:
            print('KIARA_RELAY_SELECT_PROFILE', flush=True)
        except OSError:
            profile_can_be_checked = False  # An inaccessible profile is never treated as a fresh one.
        profile = read_profile()
        imported = False
    elif executable is not None:
        profile = read_profile(executable)
        imported = True
    else:
        try:
            profile = read_relay_profile()
            imported = False
        except (OSError, ValueError):
            profile = select_relay_profile()
            imported = True
            if profile is None:
                print('KIARA_RELAY_CANCELLED', flush=True)
                return
    if linux:
        from linux_support import lock_desktop_profile, ProfileAlreadyOpen, ProfileLockError
        lock_target = profile
    else:
        from windows_profile_guard import lock_desktop_profile, ProfileAlreadyOpen, ProfileLockError
        lock_target = settings_path(profile)
    try:
        guard = lock_desktop_profile(lock_target)
    except ProfileAlreadyOpen:
        print('KIARA_RELAY_PROFILE_IN_USE', flush=True)
        return
    except ProfileLockError:
        print('KIARA_RELAY_PROFILE_LOCK_UNAVAILABLE', flush=True)
        return
    print('KIARA_RELAY_PROFILE_LOCKED', flush=True)
    remote = server = worker = None
    control = None
    try:
        from portal_origin_state import read_origin, reserve_fresh_origin, fresh_tauri_storage_absent, OriginStateError, OriginPortsBusy
        origin_settings = settings_path(profile)
        marker = origin_settings.with_suffix('.tauri-origin.json')
        try:
            required_port = read_origin(marker)
        except OriginStateError:
            print('KIARA_RELAY_ORIGIN_INVALID', flush=True)
            return
        recovery_test = os.environ.get('KIARA_TEST_RECOVERY') == '1' or os.environ.get('KIARA_TEST_RECOVERY_FULL') == '1'
        fresh_origin = (profile_can_be_checked and (linux or bool(os.environ.get('LOCALAPPDATA'))) and required_port is None and not recovery_test
                        and fresh_tauri_storage_absent(origin_settings, linux=linux))
        if recovery_test:
            # Explicitly opt-in prototype; the packaged candidates do not
            # include a qualified recovery flow. Never enable for distribution.
            from portal_recovery_stdio import QtLegacyStoragePresent, recovery_assets, resolve_port, resolve_port_full
            from portal_origin_session import OriginSessionError
            from portal_recovery_broker import RecoveryUnavailable
            from relay_control_stream import RelayControlStream
            from portal_migration_job import (MigrationConflict, MigrationRestart, MigrationArchiveUnavailable,
                                              MigrationReceiverUnavailable, MigrationJobError)
            from portal_migration_state import MigrationStateError
            control = RelayControlStream(sys.stdin.buffer)
            try:
                assets_dir = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
                if os.environ.get('KIARA_TEST_RECOVERY_FULL') == '1':
                    required_port = resolve_port_full(profile, control, sys.stdout, assets_dir)
                else:
                    required_port = resolve_port(profile, control, sys.stdout, recovery_assets(assets_dir))
            except LocalSettingsUnreadable:
                print('KIARA_RELAY_SETTINGS_UNREADABLE', flush=True)
                return
            except OriginStateError:
                print('KIARA_RELAY_ORIGIN_INVALID', flush=True)
                return
            except QtLegacyStoragePresent:
                print('KIARA_RELAY_QT_STORAGE', flush=True)
                return
            except MigrationConflict:
                print('KIARA_RELAY_RECOVERY_CONFLICT', flush=True)
                return
            except MigrationRestart:
                print('KIARA_RELAY_RECOVERY_RESTART', flush=True)
                return
            except MigrationArchiveUnavailable:
                print('KIARA_RELAY_ARCHIVE_UNAVAILABLE', flush=True)
                return
            except MigrationReceiverUnavailable:
                print('KIARA_RELAY_RECEIVER_UNAVAILABLE', flush=True)
                return
            except (OriginSessionError, RecoveryUnavailable, MigrationJobError, MigrationStateError, OSError, ValueError):
                print('KIARA_RELAY_RECOVERY_UNAVAILABLE', flush=True)
                return
        if not recovery_test and required_port is None and not fresh_origin:
            from portal_origin_session import resolve_origin, recovery_offer, OriginNeedsRecovery, OriginSessionError
            from portal_recovery_stdio import recovery_assets
            from portal_recovery_broker import RecoveryUnavailable
            from relay_control_stream import RelayControlStream
            try:
                if not profile_can_be_checked or (not linux and not os.environ.get('LOCALAPPDATA')):
                    raise OriginSessionError('Le stockage local ne peut pas être vérifié.')
                try:
                    origin_settings.with_suffix('.tauri-migration').lstat()
                except FileNotFoundError:
                    pass
                else:
                    raise OriginSessionError('Une récupération antérieure doit être vérifiée.')
                fixed = portal_recovery_fixed_port(profile)
                assets_dir = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
                assets = recovery_assets(assets_dir)
                control = RelayControlStream(sys.stdin.buffer)
                def announce_inventory(descriptor):
                    print(recovery_offer(origin_settings.stem, descriptor['token']), flush=True)
                required_port = resolve_origin(marker, assets, announce_inventory, control.cancelled,
                                               fixed_port=fixed, timeout=120)
            except LocalSettingsUnreadable:
                print('KIARA_RELAY_SETTINGS_UNREADABLE', flush=True)
                return
            except OriginNeedsRecovery:
                print('KIARA_RELAY_ORIGIN_MULTIPLE', flush=True)
                return
            except (OriginSessionError, OriginStateError, RecoveryUnavailable, OSError, ValueError):
                print('KIARA_RELAY_RECOVERY_UNAVAILABLE', flush=True)
                return
        if fresh_origin:
            try:
                required_port = reserve_fresh_origin(origin_settings, linux=linux)
            except OriginPortsBusy:
                print('KIARA_RELAY_ORIGIN_BUSY', flush=True)
                return
            except OriginStateError:
                print('KIARA_RELAY_ORIGIN_INVALID', flush=True)
                return
        options = {'managed': not linux}
        if required_port is not None:
            options['required_port'] = required_port
        try:
            remote, server = open_local_relay(profile, **options)
        except LocalOriginPortUnavailable:
            print('KIARA_RELAY_ORIGIN_BUSY', flush=True)
            return
        except LocalOriginIncompatible:
            print('KIARA_RELAY_ORIGIN_INVALID', flush=True)
            return
        except LocalSettingsUnreadable:
            print('KIARA_RELAY_SETTINGS_UNREADABLE', flush=True)
            return
        remote.managed_relay = not linux
        remote.version = version
        if not linux and os.environ.get('KIARA_DESKTOP_UPDATES') == '1':
            from updater import DesktopUpdate
            remote.desktop_update = DesktopUpdate(profile_path.parent / 'desktop-updates', control or sys.stdin.buffer, sys.stdout.buffer)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        if imported:
            history_store.atomic(profile_path, protect(json.dumps(profile, ensure_ascii=False)))
        worker.start()
        print(f'KIARA_RELAY_READY http://127.0.0.1:{server.server_port}/chat {settings_path(profile).stem}', flush=True)
        # Tauri owns the write end. EOF also shuts down the relay if Tauri crashes.
        if remote.desktop_update:
            remote.desktop_update.wait(remote)
        else:
            (control or sys.stdin.buffer).read(1)
    finally:
        try:
            if worker and worker.is_alive():
                server.shutdown()
                worker.join()
            if server:
                server.server_close()
            if remote:
                remote.close()
        finally:
            if guard:
                guard.close()


def main():
    if len(sys.argv) == 4 and sys.argv[1] == '--sync-agent-capture':
        from agent_capture import upload_journal
        try:
            session_id = str(UUID(sys.argv[2]))
            directory = Path(sys.argv[3]).resolve(strict=True)
            if not directory.is_dir():
                raise ValueError('Dossier de capture invalide.')
            profile = read_relay_profile()
            settings = client_settings(profile)
            remote = Remote(profile, endpoint=settings.get('endpoint'),
                            connection_required=not (settings.get('connection_selected') or settings.get('endpoint')))
            try:
                count = sum(1 for _ in upload_journal(remote, directory, session_id))
            finally:
                remote.close()
            print(json.dumps({'acknowledged': count}))
        except (OSError, ValueError) as error:
            print(f'Synchronisation audio interrompue ({type(error).__name__}). Fragments conservés.', file=sys.stderr)
            sys.exit(1)
        return
    if len(sys.argv) in (2, 3) and sys.argv[1] == '--relay-stdio':
        try:
            relay_stdio(Path(sys.argv[2]) if len(sys.argv) == 3 else None,
                       version=os.environ.get('KIARA_DESKTOP_VERSION', VERSION))
        except Exception as error:
            print(f'Impossible de démarrer le relais Kiara ({type(error).__name__}).', file=sys.stderr)
            sys.exit(1)
        return
    if '--self-test' in sys.argv:
        # Packaging smoke check, without a window or a model request.
        urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        raw = b'Qwen client self test'
        assert protect(protect(raw), decrypt=True) == raw
        if '--with-profile' in sys.argv:
            profile=read_profile();validate_profile(profile)
            assert profile.get('version',VERSION)==VERSION, 'Version du profil incompatible avec le binaire.'
        assert (Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'chat.html').is_file()
        assert (Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'workspace.html').is_file()
        assert all((Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / name).is_file() for name in ('ui.css','ui.js'))
        engine=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/('wireguard-bridge' if sys.platform.startswith('linux') else 'wireguard-bridge.exe')
        assert subprocess.run([str(engine),'--self-test'],capture_output=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode==0
        if '--voice-self-test' in sys.argv:
            from conversation_service import DictationService
            resources=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'voice'
            voice=DictationService(resources)
            try:
                session=voice.action({'action':'start'})['session']
                deadline=time.monotonic()+30
                while voice.status()['phase']=='loading' and time.monotonic()<deadline:time.sleep(.05)
                assert voice.status()['phase']=='listening',voice.status()
                voice.action({'action':'stop','session':session})
                while voice.status()['phase']=='finishing' and time.monotonic()<deadline:time.sleep(.05)
                assert voice.status()['phase']=='ready' and voice.status().get('microphone_closed'),voice.status()
            finally:voice.close()
        if '--conversation-self-test' in sys.argv:
            from conversation_service import ConversationService
            resources=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'voice'
            conversation=ConversationService(resources)
            try:
                status=conversation.action({'action':'start'});deadline=time.monotonic()+30
                while conversation.status()['phase']=='loading' and time.monotonic()<deadline:time.sleep(.1)
                assert conversation.status()['phase']=='listening' and (sys.platform.startswith('linux') or conversation.status().get('aec')),conversation.status()
                conversation.action({'action':'mute','session':status['session'],'muted':True})
                while not conversation.status().get('muted') and time.monotonic()<deadline:time.sleep(.05)
                paused=conversation.status();assert paused.get('muted') and paused.get('microphone_closed'),paused
                time.sleep(.25);assert conversation.status()['captured_samples']==paused['captured_samples']
                conversation.action({'action':'mute','session':status['session'],'muted':False})
                while conversation.status().get('muted') and time.monotonic()<deadline:time.sleep(.05)
                assert not conversation.status().get('muted') and not conversation.status().get('microphone_closed'),conversation.status()
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
    if sys.platform.startswith('linux'):
        raise SystemExit('Ouvrez Kiara avec le client Tauri.')
    remote=None;server=None;profile_guard=None
    try:
        import webview
        profile=read_profile()
        if sys.platform.startswith('linux'):
            from linux_support import lock_desktop_profile
            profile_guard=lock_desktop_profile(profile)
        else:
            from windows_profile_guard import lock_desktop_profile
            profile_guard=lock_desktop_profile(settings_path(profile))
        remote,server=open_local_relay(profile)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        window=webview.create_window(APP_NAME+' · '+VERSION,f'http://127.0.0.1:{server.server_port}/chat',background_color='#ffffff',text_select=True,**window_geometry())
        remote.window=window
        remote.close_guard = install_close_guard(window)
        if '--update-ack' in sys.argv:
            def acknowledge():
                path=Path(sys.argv[sys.argv.index('--update-ack')+1])
                read_js = window.run_js if sys.platform.startswith('linux') else window.evaluate_js
                if not read_js("typeof api==='function' && !!document.getElementById('composer') && !!document.getElementById('client-navigation')"):raise ValueError('Interface cliente non initialisée.')
                temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps({'version':VERSION,'ready':True}),encoding='utf-8');temporary.replace(path)
                from updater import cleanup_legacy_update
                threading.Thread(target=cleanup_legacy_update,args=(path,),daemon=True).start()
            window.events.loaded+=acknowledge
        webview.settings['ALLOW_DOWNLOADS']=True
        storage=settings_path(profile).parent/('webview-'+settings_path(profile).stem)
        if '--ui-self-test' in sys.argv:
            def verify_window():
                time.sleep(1)
                try:
                    read_js = window.run_js if sys.platform.startswith('linux') else window.evaluate_js
                    result=read_js("JSON.stringify({title:document.title,login:!!document.getElementById('client-navigation'),update:!!document.getElementById('update-apply'),chat:!!document.getElementById('composer'),state:document.getElementById('account-status').textContent,history:typeof bootstrap==='function',projects:!!document.getElementById('ws-project-list'),assistants:!!document.getElementById('ws-assistants'),textSelection:getComputedStyle(document.body).userSelect,copySelection:!!document.getElementById('copy-selection'),thinkingModes:document.querySelectorAll('#thinking-bar input[type=radio]').length,thinkingInline:document.querySelector('.send-row').contains(document.getElementById('thinking')),documentMenu:!!document.getElementById('ui-context-panel'),attachmentPlus:document.getElementById('attach-file').textContent==='+'})")
                    if isinstance(result,str):result=json.loads(result)
                    assert result['login'] and result['update'] and result['chat'] and result['history'],result
                    assert result['projects'] and not result['assistants'],result
                    assert window.text_select and result['textSelection']!='none' and result['copySelection'],result
                    assert result['thinkingModes']>=1 and result['thinkingInline'] and not result['documentMenu'] and result['attachmentPlus'],result
                    Path(sys.argv[sys.argv.index('--result')+1]).write_text(json.dumps({'ok':True,**result}),encoding='utf-8')
                finally:window.destroy()
            window.events.loaded+=verify_window
        webview.start(gui='qt' if sys.platform.startswith('linux') else 'edgechromium',private_mode=False,storage_path=str(storage))
    except Exception as error:
        hint='\nVérifiez les dépendances Linux et le trousseau de votre session.' if sys.platform.startswith('linux') else '\nSi WebView2 manque, installer Microsoft Edge WebView2 Runtime.'
        if sys.platform.startswith('linux'):
            from linux_support import ProfileLockError
        else:
            from windows_profile_guard import ProfileLockError
        if isinstance(error, ProfileLockError):hint=''
        root=tk.Tk();root.withdraw();messagebox.showerror(APP_NAME,str(error)+hint,parent=root);root.destroy()
    finally:
        if remote:remote.close()
        if server:server.shutdown();server.server_close()
        if remote and remote.kiara4 is not None:
            try:
                subprocess.Popen([str(remote.kiara4), '--profile-exe', str(Path(sys.executable).resolve())],
                                 close_fds=True)
            except OSError as error:
                root=tk.Tk();root.withdraw()
                messagebox.showerror(APP_NAME, 'Kiara 4 est installé. Ouvrez-le depuis le menu Démarrer.\n'+str(error),parent=root)
                root.destroy()
        if profile_guard:profile_guard.close()

if __name__ == '__main__':
    try:main()
    except Exception as error:
        if '--self-test' not in sys.argv:raise
        # A failed packaging check must return to the updater without opening
        # PyInstaller's unhandled-exception dialog and blocking its rollback.
        if '--result' in sys.argv:
            try:Path(sys.argv[sys.argv.index('--result')+1]).write_text(str(error),encoding='utf-8')
            except (OSError,IndexError):pass
        if sys.stderr:print(str(error),file=sys.stderr)
        sys.exit(1)
