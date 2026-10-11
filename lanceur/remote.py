"""Inference-only loopback gateway behind the embedded WireGuard server."""
from __future__ import annotations
import datetime as dt
import hashlib
import hmac
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import secrets
import socket
import select
import shutil
import struct
import subprocess
import threading
import time
from devices import Revocations, fields as device_fields
from scheduler import Scheduler
from accounts import Accounts
from operations import VERSION
from workspace import Workspace, Conflict, Denied
from urllib.parse import urlsplit
from core import HOME, ROOT, PYTHON, HIDDEN, read_json, write_json, health

GATEWAY_PORT = 8766

class GatewayHTTPServer(ThreadingHTTPServer):
    def server_close(self):
        if getattr(self,'workspace',None):self.workspace.shutdown()
        if getattr(self,'voice',None):self.voice.close()
        super().server_close()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workers = threading.BoundedSemaphore(32)

    def process_request(self, request, address):
        if not self.workers.acquire(blocking=False):
            try:
                request.sendall(b'HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except Exception:
            self.workers.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.workers.release()

def secure_url(value):
    if not isinstance(value, str):
        raise ValueError('Adresse privée WireGuard attendue.')
    value = value.strip().rstrip('/')
    parsed = urlsplit(value)
    if value and (parsed.scheme != 'wireguard' or parsed.hostname != '10.77.0.1' or parsed.port != 8766 or parsed.username or parsed.password or parsed.path not in ('', '/v1') or parsed.query or parsed.fragment):
        raise ValueError('L’API distante utilise uniquement wireguard://10.77.0.1:8766.')
    try:
        parsed.port
    except ValueError:
        raise ValueError('Port privé invalide.')
    return value.removesuffix('/v1')

class AccessStore:
    def __init__(self, home=HOME):
        self.home = Path(home)
        home = self.home
        self.path = home / 'acces-distants.json'
        self.lock = threading.RLock()
        self.active = 0
        self.maintenance = False
        self.on_access_changed = None
        self.storage = None
        self.hermes = None
        self.scheduler = Scheduler()
        self.accounts = Accounts(home)
        self.workspace = Workspace(home)
        from voice import VoiceService
        self.voice = VoiceService(home)
        from notifications import Notifications
        self.notifications = Notifications(self.workspace)
        self.seen = read_json(home / 'connexions.json', {})
        self.activity_path = home / 'appareils-activite.json'
        self.activity = read_json(self.activity_path, {})
        self.seen_saved_at = 0
        if not self.path.exists():
            write_json(self.path, {'enabled': False, 'url': '', 'clients': []})
        else:
            data=read_json(self.path)
            changed=False
            for client in data.get('clients',[]):
                for field in ('max_tokens','max_completion_tokens'):
                    if field in client:client.pop(field);changed=True
            if changed:write_json(self.path,data)
        self.revocations = Revocations(home)
        records = read_json(self.path, {})
        for client in records.get('clients', []) + records.get('deleted_clients', []):
            if client.get('revoked'):
                self.revocations.revoke(client['id'], 'migration')

    def _access_changed(self):
        if self.on_access_changed:
            self.on_access_changed()

    def _public_device(self, client, revoked):
        record = {k:v for k,v in client.items() if k != 'hash'}
        declaration = self.activity.get(client['id'], {})
        record.update(revoked=bool(client.get('revoked') or client['id'] in revoked),
                      device_kind=client.get('device_kind', 'unknown'), device_owner=client.get('device_owner', ''),
                      device_version=client.get('device_version', ''), reported_kind=declaration.get('kind', 'unknown'),
                      reported_version=declaration.get('version', ''), last_transport=declaration.get('transport', 'unknown'),
                      last_activity_epoch=self.seen.get(client['id'], declaration.get('epoch')),
                      has_android_profile=bool(client.get('android_profile') and (self.home/'wireguard-prive/profils-restaures.dpapi').is_file()))
        record['status'] = 'revoked' if record['revoked'] else 'suspended' if client.get('suspended') else 'expired' if client.get('expires_epoch') and client['expires_epoch'] <= time.time() else 'authorized'
        return record

    def metadata(self):
        with self.lock:
            data = read_json(self.path, {'enabled': False, 'url': '', 'clients': []})
            revoked = self.revocations.snapshot()['revocations']
            clients = [self._public_device(c, revoked) for c in data['clients']]
            archived = [self._public_device(c, revoked) for c in data.get('deleted_clients', [])]
            if self.storage:
                for client in clients+archived:client['storage']=self.storage.client_status(client['id'])
            if self.hermes:
                for client in clients+archived:client['hermes']=self.hermes.public(client['id'])
        return {**{k:v for k,v in data.items() if k!='deleted_clients'}, 'clients': clients, 'archived_clients': archived, 'maintenance':self.maintenance, 'active': self.active, 'queue': self.scheduler.snapshot(), 'last_connections': dict(self.seen), 'accounts':self.accounts.metadata(), **({'hermes':self.hermes.status()} if self.hermes else {})}

    def configure(self, values):
        if not isinstance(values.get('enabled'), bool):
            raise ValueError('Activation invalide.')
        url = secure_url(values.get('url', ''))
        with self.lock:
            data = read_json(self.path)
            data.update(enabled=values['enabled'], url=url)
            write_json(self.path, data)
            if not values['enabled']:
                for client in data['clients']:
                    self.scheduler.cancel(client['id']);self.accounts.invalidate(client['id'])
                    self.workspace.cancel_owner(client['id'])
            self.audit('remote_enabled' if values['enabled'] else 'remote_disabled')
        self._access_changed()
        return self.metadata()

    def issue(self, name, resume=None, platform='windows'):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or any(ord(c)<32 or ord(c)==127 for c in name):
            raise ValueError('Nom du client attendu, entre 1 et 80 caractères.')
        identity = resume or secrets.token_hex(8)
        token = 'qwen_' + identity + '_' + secrets.token_urlsafe(32)
        client = {'id': identity, 'name': name.strip(), 'created': dt.datetime.now().astimezone().isoformat(),
                  'revoked': False, 'hash': hashlib.sha256(token.encode()).hexdigest()}
        with self.lock:
            data = read_json(self.path)
            if resume:
                previous=next((c for c in data['clients'] if c['id']==resume),None)
                if not previous or not previous.get('hermes_pending') or previous.get('revoked') or previous.get('suspended') or self.revocations.contains(resume):
                    raise ValueError('Seule une création Hermes incomplète peut être reprise.')
                previous['hash']=client['hash'];client=previous
            elif len(data['clients']) >= 100:
                raise ValueError('Maximum de 100 accès enregistrés.')
            else:data['clients'].append(client)
            client['creation_platform']=platform
            if self.hermes:client['hermes_pending']=True
            write_json(self.path, data)
            self.audit('client_created', identity)
        if self.hermes:
            with self.lock:
                pending=read_json(self.path)
                next(c for c in pending['clients'] if c['id']==identity)['hermes_pending']=True
                write_json(self.path,pending)
            try:
                self.hermes.ensure(identity,client['name'])
                with self.lock:
                    pending=read_json(self.path)
                    next(c for c in pending['clients'] if c['id']==identity).pop('hermes_pending',None)
                    write_json(self.path,pending)
            except Exception:
                self.audit('hermes_provisioning_failed',identity)
                raise ValueError('Création Hermes incomplète ; reprenez cette fiche dans la console.') from None
        return {'id': identity, 'name': client['name'], 'token': token, 'url': data['url']}

    def device(self, values):
        update = device_fields(values)
        with self.lock:
            data = read_json(self.path)
            client = next((c for c in data['clients'] if c['id'] == values.get('id')), None)
            if client is None:
                raise ValueError('Appareil inconnu.')
            for field in ('kind', 'owner', 'version'):
                if field in update: client['device_'+field] = update[field]
            if 'name' in update: client['name'] = update['name']
            write_json(self.path, data)
            self.audit('device_configured', client['id'])
        return self.metadata()

    def heartbeat(self, identity, values):
        declaration = device_fields(values, declaration=True)
        with self.lock:
            if not self.valid_owner(identity):
                raise Denied('Accès appareil désactivé.')
            now = time.time()
            self.seen[identity] = now
            self.activity[identity] = {**self.activity.get(identity, {}), **declaration, 'epoch': now}
            write_json(self.activity_path, self.activity)
            write_json(self.home/'connexions.json', self.seen)
            self.seen_saved_at = now
            if self.storage:self.storage.changed()
            return {'id': identity, 'server_epoch': now, 'declared': declaration}

    def valid_owner(self, identity):
        with self.lock:
            if self.maintenance: return False
            data = read_json(self.path, {})
            if not data.get('enabled'): return False
            try:
                if self.revocations.contains(identity): return False
            except (ValueError, OSError): return False
            return any(c['id'] == identity and not c['revoked'] and not c.get('suspended') and (not c.get('expires_epoch') or c['expires_epoch'] > time.time()) for c in data.get('clients', []))

    def set_peer(self, identity, public_key, address):
        with self.lock:
            data=read_json(self.path)
            client=next(c for c in data['clients'] if c['id']==identity)
            client.update(wireguard_public_key=public_key,address=address)
            write_json(self.path,data)

    def rename(self, identity, name):
        if not isinstance(name,str) or not 1<=len(name.strip())<=80 or any(ord(c)<32 or ord(c)==127 for c in name):
            raise ValueError('Nom du client attendu, entre 1 et 80 caractères, sans caractères de contrôle.')
        with self.lock:
            data=read_json(self.path)
            client=next((c for c in data['clients'] if c['id']==identity),None)
            if client is None:raise ValueError('Client inconnu.')
            client['name']=name.strip()
            write_json(self.path,data)
            self.audit('client_renamed',identity)
        return {'message':'Client renommé. Le prochain téléchargement de son EXE utilisera ce nom.'}

    def delete(self, identity):
        # Revoke without nesting the store lock around the tunnel callback.
        self.revoke(identity)
        with self.lock:
            # Revoke first: a write failure must never leave the old EXE authorized.
            data=read_json(self.path)
            record=next(c for c in data['clients'] if c['id']==identity)
            data.setdefault('deleted_clients',[]).append(record)
            data['clients']=[c for c in data['clients'] if c['id']!=identity]
            write_json(self.path,data)
            self.seen.pop(identity,None)
            write_json(self.home/'connexions.json',self.seen)
            self.audit('client_deleted',identity)
        return {'message':'Client supprimé et accès désactivé. Ses conversations et fichiers sont conservés sur le serveur.'}

    def executable(self, name, model, profile_factory=None, resume=None):
        data = self.metadata()
        if not data['url']:
            raise ValueError('Configurer WireGuard avant de générer un client.')
        if profile_factory is None:
            raise ValueError('Le client nécessite son profil WireGuard personnel.')
        source = ROOT / 'client-qwen/dist/Accès serveur Fred.exe'
        if not source.exists():
            raise ValueError('Le client Windows doit d’abord être compilé.')
        from releases import status
        release=status(self.home)
        if not release['verified']:raise ValueError('La version cliente doit être signée et vérifiée avant distribution.')
        access = self.issue(name,resume=resume)
        directory = self.home / 'clients'
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / (access['id'] + '.exe')
        fd,name=tempfile.mkstemp(prefix='client-',suffix='.exe',dir=directory);os.close(fd)
        temporary=Path(name)
        try:
            from signing import public
            from profiles import match
            values={**profile_factory(access), 'version':VERSION, 'protocol':3, 'update_public_key':public(self.home),'client_name':access['name']}
            record=next(c for c in read_json(self.path)['clients'] if c['id']==access['id'])
            match(record,values)
            profile=json.dumps(values,ensure_ascii=False).encode()
            shutil.copyfile(source, temporary)
            with temporary.open('rb') as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=release['release']['sha256']:raise ValueError('Binaire client modifié pendant la préparation.')
            with temporary.open('ab') as stream:
                stream.write(profile)
                stream.write(struct.pack('<I', len(profile)) + b'QWENPROFILE1')
                stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,target)
        except Exception:
            self.revoke(access['id'])
            raise
        finally:temporary.unlink(missing_ok=True)
        return {'id': access['id'], 'name': access['name'], 'download': '/api/remote/client/' + access['id']}

    def revoke(self, identity):
        committed = False
        try:
            with self.lock:
                data = read_json(self.path)
                if not any(client['id'] == identity for client in data['clients']):
                    raise ValueError('Client inconnu.')
                # Commit the monotonic ledger before any fallible metadata mutation.
                self.revocations.revoke(identity)
                committed = True
                self.scheduler.cancel(identity)
                self.accounts.invalidate(identity)
                self.workspace.cancel_owner(identity)
                self.notifications.revoke(identity)
                for client in data['clients']:
                    if client['id'] == identity:client['revoked'] = True
                write_json(self.path, data)
                self.audit('revoke', identity)
        finally:
            if committed:self._access_changed()
        return self.metadata()

    def policy(self, values):
        identity = values.get('id')
        suspended = values.get('suspended', False)
        days = values.get('days')
        if not isinstance(suspended, bool) or (days is not None and (type(days) is not int or not 0 <= days <= 3650)):
            raise ValueError('Politique invalide : durée 0–3650 jours.')
        with self.lock:
            data = read_json(self.path)
            client = next((c for c in data['clients'] if c['id'] == identity), None)
            if client is None: raise ValueError('Client inconnu.')
            client.update(suspended=suspended);client.pop('max_tokens',None)
            if days is not None: client['expires_epoch'] = time.time()+days*86400 if days else None
            write_json(self.path, data)
            self.scheduler.cancel(identity)
            if suspended or (days is not None and days):self.accounts.invalidate(identity)
            if suspended:self.workspace.cancel_owner(identity)
            self.audit('policy', identity)
        self._access_changed()
        return self.metadata()

    def audit(self, event, identity=''):
        with self.lock:
            path = self.home / 'audit.json'
            rows = read_json(path, [])
            rows.append({'epoch': time.time(), 'event': event, 'client': identity})
            write_json(path, rows[-1000:])
            if self.storage:self.storage.changed()

    def denial(self,token):
        if self.maintenance:return 'maintenance','Serveur en maintenance : réessayer après la restauration.'
        digest=hashlib.sha256(token.encode()).hexdigest()
        with self.lock:data=read_json(self.path)
        if not data['enabled']:return 'remote_disabled','Accès distant désactivé sur le serveur.'
        record=next((c for c in data['clients'] if hmac.compare_digest(c['hash'],digest)),None)
        if record:
            try:revoked = self.revocations.contains(record['id'])
            except (ValueError, OSError):return 'access_denied','Registre de sécurité indisponible : accès refusé.'
            if record['revoked'] or revoked:return 'access_revoked','Accès client révoqué sur le serveur.'
            if record.get('suspended'):return 'access_suspended','Compte client suspendu sur le serveur.'
            if record.get('expires_epoch') and record['expires_epoch']<=time.time():return 'access_expired','Accès client expiré.'
            if record.get('hermes_pending'):return 'agent_provisioning','Création de l’assistant en cours ; reprendre la fiche dans la console serveur.'
        return 'access_denied','Accès client invalide.'

    def authenticate(self, token):
        if not isinstance(token, str) or not 20 <= len(token) <= 256:
            return None
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.lock:
            data = read_json(self.path)
            if self.maintenance or not data['enabled']: return None
            try:revoked = self.revocations.snapshot()['revocations']
            except (ValueError, OSError):return None
            for client in data['clients']:
                if client['id'] not in revoked and not client['revoked'] and not client.get('suspended', False) and not client.get('hermes_pending') and (not client.get('expires_epoch') or client['expires_epoch'] > time.time()) and hmac.compare_digest(client['hash'], digest):
                    now = time.time()
                    self.seen[client['id']] = now
                    if now-self.seen_saved_at >= 30:
                        write_json(self.home/'connexions.json', self.seen)
                        self.seen_saved_at = now
                    if self.storage:self.storage.changed()
                    return client['id']
        return None

from chat_attachments import capabilities, validate_parts, normalize_reasoning

def chat_request(value, model):
    if not isinstance(value, dict):
        raise ValueError('Requête de chat invalide.')
    allowed = {'model', 'messages', 'stream', 'max_tokens', 'max_completion_tokens', 'temperature',
               'top_p', 'top_k', 'min_p', 'seed', 'presence_penalty', 'frequency_penalty',
               'repetition_penalty', 'chat_template_kwargs', 'tools', 'tool_choice', 'response_format',
               'parallel_tool_calls', 'stream_options', 'reasoning_effort'}
    if set(value) - allowed:
        raise ValueError('Paramètre non admis par cette passerelle API.')
    messages = value.get('messages')
    if not isinstance(messages, list) or not 1 <= len(messages) <= 1000:
        raise ValueError('Historique de conversation invalide.')
    for message in messages:
        if not isinstance(message, dict) or set(message) - {'role', 'content', 'reasoning_content', 'tool_calls', 'tool_call_id', 'name'} or message.get('role') not in ('system', 'user', 'assistant', 'tool'):
            raise ValueError('Message de conversation invalide.')
        if isinstance(message.get('content'),list):validate_parts(message['content'],message['role'])
        elif not isinstance(message.get('content'), str) and not (message.get('content') is None and isinstance(message.get('tool_calls'), list)):
            raise ValueError('Message texte, image ou appel d’outil attendu.')
        if 'reasoning_content' in message and not isinstance(message['reasoning_content'], str):
            raise ValueError('Texte de réflexion invalide.')
    value = dict(value)
    value['model'] = model
    value['strata_mcp'] = False  # Client-side tools are permitted; no host tools execute through this gateway.
    # Strata explicitly supports -1: generate until EOS or the remaining context.
    # Ignore old clients' output caps, including their default 4096-token ceiling.
    value['max_tokens'] = -1
    value.pop('max_completion_tokens', None)
    if not isinstance(value.get('stream', False), bool):
        raise ValueError('Mode de réponse invalide.')
    template = value.get('chat_template_kwargs', {})
    if not isinstance(template, dict) or set(template) - {'enable_thinking','reasoning_effort'} or ('enable_thinking' in template and not isinstance(template['enable_thinking'], bool)):
        raise ValueError('Réglage de réflexion invalide.')
    if 'reasoning_effort' in value:value['reasoning_effort']=normalize_reasoning(value['reasoning_effort'])
    if 'reasoning_effort' in template:template['reasoning_effort']=normalize_reasoning(template['reasoning_effort'])
    return value

def serve_gateway(store, backend, port=GATEWAY_PORT):
    """backend returns (loopback port, model alias, private upstream API key)."""
    scheduler = store.scheduler
    def valid_owner(owner):
        return store.valid_owner(owner)
    def generate(owner,messages,cancel):
        if store.hermes:return store.hermes.generate(owner,messages,cancel)
        item=None;connection=None;deadline=time.monotonic()+900
        try:
            while item is None:
                if cancel.is_set() or not valid_owner(owner):raise ValueError('Tâche annulée ou accès désactivé.')
                try:item=scheduler.submit(owner,background=True)
                except ValueError:
                    if time.monotonic()>deadline:raise ValueError('File occupée pendant 15 minutes.')
                    cancel.wait(1)
            scheduler.wait(item,lambda:valid_owner(owner) and not cancel.is_set(),lambda position:None)
            upstream_port,model,key=backend()
            if not health('127.0.0.1',upstream_port).get('loaded'):raise ValueError('Modèle arrêté : relancer la tâche après chargement.')
            data=chat_request({'messages':messages,'stream':True,'chat_template_kwargs':{'enable_thinking':False}},model)
            connection=http.client.HTTPConnection('127.0.0.1',upstream_port,timeout=120)
            headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+key} if key else {})}
            connection.request('POST','/v1/chat/completions',json.dumps(data).encode(),headers)
            upstream_socket=connection.sock
            def abort():
                try:upstream_socket.shutdown(socket.SHUT_RDWR)
                except OSError:pass
            with scheduler.condition:
                item['abort']=abort
                if item['cancelled']:abort()
            # Cancellation also closes a blocked read when the model emits no tokens.
            def monitor():
                while not cancel.wait(.5):
                    if item.get('finished'):return
                    if not valid_owner(owner) or time.monotonic()>deadline:cancel.set();break
                if not item.get('finished'):abort()
            threading.Thread(target=monitor,daemon=True).start()
            response=connection.getresponse()
            if response.status!=200:raise ValueError('Moteur indisponible ('+str(response.status)+').')
            result='';complete=False
            for line in iter(lambda:response.readline(2*1024*1024),b''):
                if cancel.is_set() or item['cancelled']:raise ValueError('Tâche annulée.')
                scheduler.progress(item)
                if line.strip()==b'data: [DONE]':complete=True;break
                if line.startswith(b'data: '):
                    value=json.loads(line[6:])
                    if value.get('error'):raise ValueError('Erreur du moteur pendant la tâche.')
                    part=value.get('choices',[{}])[0].get('delta',{}).get('content','')
                    if isinstance(part,str):result+=part
                    if len(result)>500000:raise ValueError('Résultat trop volumineux.')
            if not complete:raise ValueError('Génération interrompue avant confirmation de fin.')
            item['succeeded']=True
            return result
        finally:
            if item:item['finished']=True;scheduler.finish(item)
            if connection:connection.close()
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(30)

        def log_message(self, *args):
            pass

        def respond(self, code, data):
            content = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(content)

        def authorized(self, session=True):
            if store.maintenance:
                self.respond(503, {'error': {'code':'maintenance','message':'Serveur en maintenance : réessayer après la restauration.'}})
                return False
            # Native client; arbitrary browser pages cannot submit authenticated commands.
            if self.headers.get('Origin'):
                self.respond(403, {'error': {'message': 'Utiliser le client Windows ou un client API.'}})
                return False
            key = self.headers.get('Authorization', '')
            identity = store.authenticate(key[7:]) if key.startswith('Bearer ') else None
            if not identity:
                code,message=store.denial(key[7:] if key.startswith('Bearer ') else '')
                self.respond(401, {'error': {'code':code,'message':message}})
                return False
            self.session = self.headers.get('X-Qwen-Session','')
            self.identity = identity
            self.access_token = key[7:]
            return True

        def do_GET(self):
            if self.path == '/v1/agent/state':
                if not self.authorized():return
                return self.respond(200,store.hermes.status(self.identity) if store.hermes else {'enabled':False,'available':False,'runs':[]})
            if self.path in ('/v1/client/android/release', '/v1/client/android/download'):
                if not self.authorized(): return
                from android_releases import status as android_status
                try:
                    release, source = android_status()
                except ValueError as error:
                    return self.respond(503, {'error': {'message': str(error)}})
                if self.path.endswith('/release'):
                    return self.respond(200, release)
                with source.open('rb') as stream:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/vnd.android.package-archive')
                    self.send_header('Content-Length', str(os.fstat(stream.fileno()).st_size))
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    while chunk := stream.read(65536):
                        if store.authenticate(self.access_token) != self.identity: return
                        self.wfile.write(chunk)
                return
            if self.path == '/v1/voice/status':
                if not self.authorized():return
                return self.respond(200,store.voice.status())
            if self.path == '/v1/notifications':
                if not self.authorized(): return
                try:
                    with store.lock:
                        if store.authenticate(self.access_token) != self.identity: raise Denied('Accès désactivé.')
                        result = store.notifications.snapshot(self.identity)
                    return self.respond(200, result)
                except Denied as error: return self.respond(403, {'error': {'message': str(error)}})
                except (ValueError, OSError, TypeError) as error: return self.respond(400, {'error': {'message': str(error)}})
            if self.path=='/v1/history':
                if not self.authorized():return
                return self.respond(200,store.workspace.history_read(self.identity))
            if self.path=='/v1/workspace':
                if not self.authorized():return
                return self.respond(200,store.workspace.snapshot(self.identity))
            if self.path in ('/v1/client/release','/v1/client/download'):
                if not self.authorized():return
                from releases import status
                release=status(store.home)
                if not release['verified']:return self.respond(503, {'error':{'message':'Version serveur absente ou invalide.'}})
                if self.path.endswith('/release'):
                    record=next((c for c in store.metadata()['clients'] if c['id']==self.identity),{})
                    return self.respond(200,{**release['release'],'client_name':record.get('name','Client')})
                source=ROOT/'client-qwen/dist/Accès serveur Fred.exe'
                self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Content-Length',str(source.stat().st_size));self.send_header('Cache-Control','no-store');self.end_headers()
                with source.open('rb') as stream:shutil.copyfileobj(stream,self.wfile)
                return
            if self.path == '/v1/status':
                if not self.authorized(): return
                return self.respond(200, {'version': VERSION, 'protocol': 3, 'agent_protocol':4, 'queue': scheduler.snapshot(self.identity)})
            if urlsplit(self.path).path != '/v1/models' or urlsplit(self.path).query:
                return self.respond(404, {'error': {'message': 'Route non disponible.'}})
            if not self.authorized():
                return
            upstream_port, model, _ = backend()
            live = health('127.0.0.1', upstream_port)
            if not live.get('loaded'):
                return self.respond(503, {'error': {'code':'model_unloaded', 'message': 'Serveur connecté, mais le modèle n’est pas chargé. Le lancer dans la console serveur.'}})
            live_model=live.get('model')
            if isinstance(live_model,str) and live_model:model=live_model
            self.respond(200, {'object': 'list', 'data': [{'id': model, 'object': 'model', 'owned_by': 'local', 'capabilities': capabilities(live)}]})

        def do_POST(self):
            if self.path == '/v1/agent/action':
                if not self.authorized():return
                try:
                    if not store.hermes:raise ValueError('Les agents ne sont pas activés sur ce serveur.')
                    if self.headers.get('Transfer-Encoding') or not self.headers.get('Content-Type','').startswith('application/json'):raise ValueError('JSON attendu.')
                    length=int(self.headers.get('Content-Length','0'))
                    if not 1<=length<=8192:raise ValueError('Action agent limitée à 8 Ko.')
                    value=json.loads(self.rfile.read(length))
                    if store.authenticate(self.access_token)!=self.identity:raise Denied('Accès désactivé.')
                    return self.respond(200,store.hermes.action(self.identity,value))
                except Conflict as error:return self.respond(409,{'error':{'message':str(error)}})
                except Denied as error:return self.respond(403,{'error':{'message':str(error)}})
                except (ValueError,OSError,TypeError):return self.respond(400,{'error':{'message':'Cette demande agent ne peut pas être traitée.'}})
            if self.path in ('/v1/voice/speech','/v1/voice/cancel'):
                if not self.authorized():return
                frames=None;sent=False
                try:
                    if self.headers.get('Transfer-Encoding') or not self.headers.get('Content-Type','').startswith('application/json'):raise ValueError('JSON attendu.')
                    length=int(self.headers.get('Content-Length','0'))
                    if not 1<=length<=8192:raise ValueError('Requête vocale limitée à 8 Ko.')
                    value=json.loads(self.rfile.read(length))
                    if self.path.endswith('/cancel'):
                        if not isinstance(value,dict) or set(value)!={'request_id'} or not isinstance(value['request_id'],str):raise ValueError('Annulation vocale invalide.')
                        return self.respond(200,store.voice.cancel(self.identity,value['request_id']))
                    frames=store.voice.stream(self.identity,value,lambda:store.authenticate(self.access_token)==self.identity)
                    self.send_response(200);self.send_header('Content-Type','text/event-stream')
                    self.send_header('Cache-Control','no-store');self.send_header('Connection','close');self.end_headers();sent=True
                    for frame in frames:
                        self.wfile.write(('data: '+json.dumps(frame,ensure_ascii=False)+'\n\n').encode('utf-8'));self.wfile.flush()
                except BlockingIOError as error:
                    if not sent:self.respond(429,{'error':{'message':str(error)}})
                except (ValueError,OSError,TypeError,PermissionError) as error:
                    if not sent:self.respond(400,{'error':{'message':str(error)}})
                finally:
                    if frames:frames.close()
                return
            if self.path == '/v1/notifications/action':
                if not self.authorized(): return
                try:
                    if self.headers.get('Transfer-Encoding') or not self.headers.get('Content-Type', '').startswith('application/json'):
                        raise ValueError('JSON attendu.')
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 1 <= length <= 65536: raise ValueError('Notifications : requête limitée à 64 Ko.')
                    value = json.loads(self.rfile.read(length))
                    with store.lock:
                        if store.authenticate(self.access_token) != self.identity: raise Denied('Accès désactivé.')
                        result = store.notifications.action(self.identity, value)
                    return self.respond(200, result)
                except Conflict as error: return self.respond(409, {'error': {'message': str(error)}})
                except Denied as error: return self.respond(403, {'error': {'message': str(error)}})
                except (ValueError, OSError, TypeError) as error: return self.respond(400, {'error': {'message': str(error)}})
            if self.path == '/v1/device':
                if not self.authorized():return
                try:
                    if self.headers.get('Transfer-Encoding') or not self.headers.get('Content-Type', '').startswith('application/json'):
                        raise ValueError('JSON attendu.')
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 1 <= length <= 2048: raise ValueError('Déclaration appareil limitée à 2 Ko.')
                    value = json.loads(self.rfile.read(length))
                    with store.lock:
                        if store.authenticate(self.access_token) != self.identity: raise Denied('Accès désactivé.')
                        result = store.heartbeat(self.identity, value)
                    return self.respond(200, result)
                except Denied as error:return self.respond(403, {'error': {'message': str(error)}})
                except (ValueError, OSError, TypeError) as error:return self.respond(400, {'error': {'message': str(error)}})
            if self.path=='/v1/history':
                if not self.authorized():return
                try:
                    if self.headers.get('Transfer-Encoding') or not self.headers.get('Content-Type','').startswith('application/json'):raise ValueError('JSON attendu.')
                    length=int(self.headers.get('Content-Length','0'))
                    if not 1<=length<=10*1024*1024:raise ValueError('Historique limité à 9 Mo.')
                    value=json.loads(self.rfile.read(length))
                    with store.lock:
                        if store.authenticate(self.access_token)!=self.identity:raise Denied('Accès désactivé.')
                        result=store.workspace.history_write(self.identity,value)
                    return self.respond(200,result)
                except Conflict as error:return self.respond(409,{'error':{'code':'history_conflict','message':str(error)}})
                except Denied as error:return self.respond(403,{'error':{'message':str(error)}})
                except (ValueError,OSError,TypeError) as error:return self.respond(400,{'error':{'message':str(error)}})
            if self.path=='/v1/workspace/action':
                if not self.authorized():return
                try:
                    if self.headers.get('Transfer-Encoding') or not self.headers.get('Content-Type','').startswith('application/json'):raise ValueError('JSON attendu.')
                    length=int(self.headers.get('Content-Length','0'))
                    if not 1<=length<=8*1024*1024:raise ValueError('Requête limitée à 8 Mo.')
                    value=json.loads(self.rfile.read(length))
                    prepared=store.workspace.prepare_upload(self.identity,value)
                    # Serialize access validation and mutations with suspension/revocation.
                    with store.lock:
                        if store.authenticate(self.access_token)!=self.identity:raise Denied('Accès désactivé.')
                        result=store.workspace.action(self.identity,value,prepared)
                    return self.respond(200,result)
                except Conflict as error:return self.respond(409,{'error':{'message':str(error)}})
                except Denied as error:return self.respond(403,{'error':{'message':str(error)}})
                except (ValueError,OSError,TypeError,ImportError) as error:return self.respond(400,{'error':{'message':str(error)}})
            if self.path == '/v1/cancel':
                if not self.authorized(): return
                if store.hermes:
                    try:return self.respond(200,store.hermes.cancel(self.identity,self.headers.get('X-Qwen-Request') or None))
                    except ValueError as error:return self.respond(400,{'error':{'message':str(error)}})
                scheduler.cancel(self.identity,self.headers.get('X-Qwen-Request') or None)
                return self.respond(200, {'cancelled': True})
            if self.path not in ('/v1/chat/completions','/v1/context'):
                return self.respond(404, {'error': {'message': 'Route non disponible.'}})
            if not self.authorized():
                return
            if self.headers.get('Transfer-Encoding') or not self.headers.get('Content-Type', '').startswith('application/json'):
                return self.respond(415, {'error': {'message': 'Corps JSON attendu.'}})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 1 <= length <= 10 * 1024 * 1024:
                    raise ValueError('Requête trop volumineuse (maximum 2 Mo).')
                upstream_port, model, key = backend()
                raw=json.loads(self.rfile.read(length))
                if not isinstance(raw,dict):raise ValueError('Requête invalide.')
                conversation=raw.pop('conversation_id',None)
                turn=raw.pop('turn_id',None)
                raw.pop('history_revision',None)
                if isinstance(raw.get('messages'),list):
                    for message in raw['messages']:
                        if isinstance(message,dict):message.pop('turn_id',None)
                project=raw.pop('project_id',None);raw.pop('assistant_id',None);document=raw.pop('document_id',None)
                data = chat_request(raw, model);sources=[]
                if not (store.hermes and self.path=='/v1/chat/completions') and (project or document or getattr(store.workspace,'knowledge',None)):
                    data['messages'],sources=store.workspace.context(self.identity,data['messages'],project,document)
            except (OSError, ValueError, TypeError, KeyError) as error:
                return self.respond(400, {'error': {'message': str(error)}})
            live=health('127.0.0.1', upstream_port)
            if not live.get('loaded'):
                return self.respond(503, {'error': {'code':'model_unloaded', 'message': 'Serveur connecté, mais le modèle n’est pas chargé. Le lancer dans la console serveur.'}})
            if any(isinstance(m.get('content'),list) and any(p.get('type')=='image_url' for p in m['content']) for m in data['messages']) and live.get('images') is not True:
                return self.respond(400,{'error':{'code':'image_not_supported','message':'Le modèle chargé ne dispose pas de la vision. Choisissez un modèle avec prise en charge des images.'}})
            live_model=live.get('model')
            if isinstance(live_model,str) and live_model:data['model']=live_model
            if store.hermes and self.path=='/v1/chat/completions':
                request=self.headers.get('X-Qwen-Request') or turn or secrets.token_hex(16)
                if turn and turn!=request:return self.respond(400,{'error':{'message':'Identité d’envoi incohérente.'}})
                if not conversation:return self.respond(409,{'error':{'code':'client_update_required','message':'Mettez à jour le client pour utiliser votre assistant Hermes.'}})
                stream=None;sent=False
                try:
                    stream=store.hermes.stream(self.identity,data,request,conversation,project,document)
                    answer=[];reasoning=[];final_sources=[]
                    for block in stream:
                        if store.authenticate(self.access_token)!=self.identity:raise Denied('Accès désactivé.')
                        if data.get('stream'):
                            if not sent:
                                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Cache-Control','no-store');self.send_header('Connection','close');self.end_headers();sent=True
                            self.wfile.write(block);self.wfile.flush()
                        elif block.strip()!=b'data: [DONE]':
                            event=json.loads(block[6:])
                            if event.get('workspace_sources'):final_sources=event['workspace_sources']
                            for choice in event.get('choices',[]):
                                delta=choice.get('delta',{});answer.append(delta.get('content',''));reasoning.append(delta.get('reasoning_content',''))
                    if not data.get('stream'):self.respond(200,{'id':'chatcmpl-'+request,'object':'chat.completion','choices':[{'index':0,'message':{'role':'assistant','content':''.join(answer),'reasoning_content':''.join(reasoning)},'finish_reason':'stop'}],'workspace_sources':final_sources})
                except BlockingIOError as error:
                    if not sent:self.respond(429,{'error':{'message':str(error)}})
                except (OSError,ValueError,TypeError,RuntimeError) as error:
                    if sent:
                        try:self.wfile.write(('data: '+json.dumps({'error':{'message':'L’assistant a été interrompu. Reconnectez-vous pour retrouver son état.'}})+'\n\n').encode());self.wfile.flush()
                        except OSError:pass
                    else:self.respond(503,{'error':{'code':'agent_unavailable','message':'Votre assistant est indisponible. Vérifiez son état dans la console serveur.'}})
                finally:
                    if stream:stream.close()
                return
            if self.path == '/v1/context':
                # Use the backend tokenizer without starting an inference or joining its queue.
                effort=data.get('reasoning_effort','none')
                count_request={'model':data['model'],'messages':[],
                               'output_config':{'effort':effort}}
                if effort=='none':count_request['thinking']={'type':'disabled'}
                systems=[];has_images=False
                for message in data['messages']:
                    if message['role']=='system':
                        systems.append(message['content']);continue
                    content=message['content']
                    if isinstance(content,list):
                        has_images|=any(part.get('type')=='image_url' for part in content)
                        content=''.join(part['text'] for part in content if part.get('type')=='text')
                    if message.get('reasoning_content'):
                        content=[{'type':'thinking','thinking':message['reasoning_content']},{'type':'text','text':content}]
                    count_request['messages'].append({'role':message['role'],'content':content})
                if systems:count_request['system']='\n'.join(systems)
                counter=http.client.HTTPConnection('127.0.0.1',upstream_port,timeout=10)
                try:
                    headers={'Content-Type':'application/json'}
                    if key:headers['Authorization']='Bearer '+key
                    counter.request('GET','/props',headers=headers)
                    props_response=counter.getresponse();props=json.loads(props_response.read())
                    capacity=props.get('default_generation_settings',{}).get('n_ctx')
                    counter.request('POST','/v1/messages/count_tokens',body=json.dumps(count_request),headers=headers)
                    counted=counter.getresponse();result=json.loads(counted.read())
                    tokens=result.get('input_tokens')
                    if props_response.status!=200 or counted.status!=200 or type(capacity) is not int or capacity<=0 or type(tokens) is not int or tokens<0:
                        raise ValueError('Comptage du contexte indisponible.')
                    return self.respond(200,{'tokens':tokens,'capacity':capacity,'estimated':has_images or bool(store.hermes),'model':data['model'],**({'scope':'visible_history','agent_context':True} if store.hermes else {})})
                except (OSError,ValueError,http.client.HTTPException):
                    return self.respond(503,{'error':{'message':'Comptage du contexte indisponible.'}})
                finally:counter.close()
            try:
                item = scheduler.submit(self.identity,self.headers.get('X-Qwen-Request') or None)
            except ValueError as error:
                return self.respond(429, {'error': {'message': str(error)}})
            connection = None
            headers_sent = False
            active_registered = False
            try:
                # Context extraction and model health checks can outlive a
                # suspension/revocation. Commit the first private response only
                # while that access is still valid, serialized with revocation.
                with store.lock:
                    if item['cancelled'] or store.authenticate(self.access_token) != self.identity:
                        raise Denied('Demande annulée ou accès désactivé.')
                    store.active += 1
                    active_registered = True
                    if data.get('stream'):
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/event-stream')
                        self.send_header('Cache-Control', 'no-store')
                        self.send_header('Connection', 'close')
                        self.end_headers()
                        headers_sent = True
                        if sources:
                            self.wfile.write(('data: '+json.dumps({'workspace_sources':sources},ensure_ascii=False)+'\n\n').encode());self.wfile.flush()
                def heartbeat(position):
                    if select.select([self.connection], [], [], 0)[0] and self.connection.recv(1, socket.MSG_PEEK) == b'':
                        raise OSError('Client déconnecté.')
                    if headers_sent:
                        self.wfile.write((': qwen-queue '+json.dumps({'position': position})+'\n\n').encode())
                        self.wfile.flush()
                scheduler.wait(item, lambda: store.authenticate(self.access_token) == self.identity, heartbeat)
                heartbeat(0)
                store.audit('inference_started', self.identity)
                # Fixed local destination. No user URL, forwarded identity or remote API key reaches Strata.
                connection = http.client.HTTPConnection('127.0.0.1', upstream_port, timeout=120)
                headers = {'Content-Type': 'application/json'}
                if key:
                    headers['Authorization'] = 'Bearer ' + key
                # A second check covers access changes while the request was
                # queued. Keep network I/O outside the access mutex so an
                # unavailable engine cannot delay a later revocation.
                with store.lock:
                    if item['cancelled'] or store.authenticate(self.access_token) != self.identity:
                        raise Denied('Demande annulée ou accès désactivé.')
                connection.request('POST', '/v1/chat/completions', json.dumps(data).encode(), headers)
                upstream_socket = connection.sock
                def abort():
                    try: upstream_socket.shutdown(socket.SHUT_RDWR)
                    except OSError: pass
                with scheduler.condition:
                    item['abort'] = abort
                    if item['cancelled']: abort()
                response = connection.getresponse()
                if headers_sent and response.status != 200:
                    raise ValueError('Le moteur a refusé la demande ('+str(response.status)+').')
                if not headers_sent:
                    self.send_response(response.status)
                    self.send_header('Content-Type', 'text/event-stream' if data.get('stream') and response.status == 200 else 'application/json; charset=utf-8')
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                headers_sent = True
                complete = False
                if data.get('stream') and response.status == 200:
                    while True:
                        if item['cancelled'] or not store.authenticate(self.access_token):
                            raise ValueError('Demande annulée ou accès désactivé.')
                        line = response.readline(2 * 1024 * 1024)
                        if not line:
                            break
                        if item['cancelled'] or not store.authenticate(self.access_token):
                            raise ValueError('Demande annulée ou accès désactivé.')
                        if line.strip() == b'data: [DONE]': complete = True
                        if line.startswith(b'data: '):
                            try:
                                event=json.loads(line[6:])
                                if event.get('error'):item['backend_error']=True
                                if isinstance(event.get('usage'),dict):
                                    tokens=event['usage'].get('completion_tokens')
                                    if isinstance(tokens,int) and tokens >= 0:
                                        seconds=max(time.time()-item['started'],.001)
                                        scheduler.last_tokens_per_second=round(tokens/seconds,2)
                            except (ValueError,AttributeError): pass
                        scheduler.progress(item)
                        self.wfile.write(line)
                        self.wfile.flush()
                else:
                    while True:
                        block = response.read1(65536)
                        if not block:
                            break
                        if item['cancelled'] or not store.authenticate(self.access_token):raise ValueError('Session expirée ou demande annulée.')
                        scheduler.progress(item)
                        self.wfile.write(block)
                    complete = response.status == 200
                if data.get('stream') and not complete:raise ValueError('Réponse interrompue avant la fin du flux.')
                item['succeeded'] = complete and not item.get('backend_error')
            except (OSError, ValueError, http.client.HTTPException) as error:
                if headers_sent:
                    try:
                        self.wfile.write(('data: '+json.dumps({'error': {'message': str(error)}})+'\n\n').encode())
                        self.wfile.flush()
                    except OSError: pass
                if not headers_sent:
                    if store.authenticate(self.access_token) != self.identity:
                        code, message = store.denial(self.access_token)
                        self.respond(503 if code == 'maintenance' else 401, {'error': {'code': code, 'message': message}})
                    else:
                        self.respond(503, {'error': {'message': 'Le modèle local est indisponible ou ne répond pas.'}})
            finally:
                if connection:
                    connection.close()
                if active_registered:
                    with store.lock:
                        store.active -= 1
                scheduler.finish(item)
    server = GatewayHTTPServer(('127.0.0.1', port), Handler)
    server.workspace=store.workspace
    server.voice=store.voice
    store.workspace.start(generate,valid_owner)
    server.daemon_threads = True
    return server
