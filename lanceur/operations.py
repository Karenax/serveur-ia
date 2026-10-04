"""Local operations; encrypted portable backups and opt-in startup."""
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import threading
import time
from cryptography.fernet import Fernet, InvalidToken
from core import ROOT, HOME, PYTHON, HIDDEN, read_json, write_json

VERSION = '3.5.1'
FILES = ['reglages.json', 'reglages-par-defaut.json', 'base-strata.json', 'acces-distants.json', 'wireguard.json', 'comptes.json', 'exploitation.json']

def cipher(password, salt):
    if not isinstance(password, str) or not 12 <= len(password) <= 1024:
        raise ValueError('Phrase de sauvegarde : 12 à 1024 caractères.')
    return Fernet(base64.urlsafe_b64encode(hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600000, 32)))

class Operations:
    def __init__(self, controller):
        self.controller = controller
        self.path = controller.home / 'exploitation.json'
        self.attempts = [t for t in read_json(controller.home/'relances.json', []) if time.time()-t<3600]
        self.desired = False
        self.last_error = ''

    def settings(self):
        return read_json(self.path, {'autoload': False, 'restart': False})

    def configure(self, data):
        if not all(isinstance(data.get(k), bool) for k in ('autoload', 'restart')):
            raise ValueError('Options oui/non attendues.')
        write_json(self.path, {k:data[k] for k in ('autoload','restart')})
        return self.status()

    def startup(self, enabled):
        if not isinstance(enabled, bool): raise ValueError('Activation invalide.')
        import winreg
        command = 'powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+str(ROOT/'Start-Interface-Qwen.ps1')+'" -SansNavigateur'
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
            if enabled: winreg.SetValueEx(key, 'QwenServer', 0, winreg.REG_SZ, command)
            else:
                try: winreg.DeleteValue(key, 'QwenServer')
                except FileNotFoundError: pass
        return self.status()

    def status(self):
        startup = False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
                startup = bool(winreg.QueryValueEx(key, 'QwenServer')[0])
        except (OSError, ImportError): pass
        return {**self.settings(), 'startup': startup, 'version': VERSION, 'protocol': 3,
                'restart_attempts': len(self.attempts), 'error': self.last_error}

    def watch(self,preserve_state=False):
        self.desired = (self.settings()['autoload'] and not preserve_state) or bool(self.controller.processes())
        initial_load = self.settings()['autoload'] and not preserve_state
        unhealthy = 0
        while True:
            try:
                c = self.controller
                with c.remote.lock:
                    write_json(c.home/'connexions.json', dict(c.remote.seen))
                c.remote.scheduler.expire()
                with c.lock:
                    if self.desired and not c.processes() and not c.supervisor(c.current_run()):
                        self.attempts = [t for t in self.attempts if time.time()-t < 3600]
                        if len(self.attempts) >= 3:
                            self.last_error = 'Trois tentatives en une heure : relance automatique suspendue.'
                        elif initial_load or self.settings()['restart']:
                            initial_load = False
                            self.attempts.append(time.time())
                            write_json(c.home/'relances.json',self.attempts)
                            c.start(read_json(c.home/'derniers-reglages-valides.json',c.settings()))
                    if self.desired and self.settings()['restart'] and c.current_run().get('status') == 'pret' and c.processes():
                        from core import health
                        port = c.remote_backend()[0]
                        unhealthy = 0 if health('127.0.0.1', port).get('loaded') else unhealthy+1
                        if unhealthy >= 5 and not c.remote.scheduler.snapshot()['active']:
                            c.stop()
                            self.desired = True
                            unhealthy = 0
                if c.wireguard.settings().get('public_host') and c.remote.metadata()['enabled'] and (not c.wireguard.engine or not c.wireguard.engine.running()):
                    c.wireguard.activate(c.gateway is not None)
            except Exception as error:
                self.last_error = str(error)
            time.sleep(30)

    def backup(self, password):
        c = self.controller
        with c.lock, c.wireguard.lock, c.remote.lock, c.remote.workspace.lock:
            content = {name:read_json(c.home/name) for name in FILES if (c.home/name).exists()}
            if c.wireguard.vault_path.exists(): content['vault'] = c.wireguard.vault()
            clients = c.home/'clients'
            from wg_crypto import protect
            saved=c.wireguard.directory/'profils-restaures.dpapi'
            profiles = json.loads(protect(saved.read_bytes(),decrypt=True)) if saved.exists() else {}
            signing=c.wireguard.directory/'signature.dpapi'
            if signing.exists():content['signing_seed']=base64.b64encode(protect(signing.read_bytes(),decrypt=True)).decode()
            if clients.exists():
                import struct
                for exe in clients.glob('*.exe'):
                    with exe.open('rb') as f:
                        f.seek(-16, 2); footer=f.read(16)
                        if footer[4:] == b'QWENPROFILE1':
                            size=struct.unpack('<I', footer[:4])[0]
                            if 0 < size <= 65536:
                                f.seek(-16-size, 2); profiles[exe.stem]=json.loads(f.read(size))
            content['profiles']=profiles
            content['workspace']=c.remote.workspace.backup()
            web_key=c.home/'recherche-web.dpapi'
            if web_key.exists():content['web_key']=base64.b64encode(protect(web_key.read_bytes(),decrypt=True)).decode()
            salt=secrets.token_bytes(16)
            encrypted=cipher(password,salt).encrypt(json.dumps({'version':1,'files':content}).encode())
            directory=c.home/'sauvegardes';directory.mkdir(exist_ok=True)
            target=directory/(time.strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)+'.qwenbackup')
            target.write_bytes(b'QWENBACKUP1'+salt+encrypted)
        return {'file':str(target), 'message':'Sauvegarde chiffrée créée.'}

    def restore(self, data):
        c=self.controller
        if c.processes() or c.supervisor(c.current_run()) or c.remote.metadata()['enabled']:
            raise ValueError('Arrêter le modèle et désactiver WireGuard avant la restauration.')
        path=Path(data.get('file',''))
        if path.stat().st_size>400*1024*1024:raise ValueError('Sauvegarde trop volumineuse.')
        blob=path.read_bytes()
        if not blob.startswith(b'QWENBACKUP1'): raise ValueError('Format de sauvegarde invalide.')
        try: package=json.loads(cipher(data.get('password'),blob[11:27]).decrypt(blob[27:]))
        except (InvalidToken, ValueError): raise ValueError('Sauvegarde invalide ou phrase incorrecte.')
        files=package.get('files',{})
        if package.get('version') != 1 or not isinstance(files,dict) or set(files)-set(FILES+['vault','profiles','signing_seed','workspace','web_key']):
            raise ValueError('Contenu de sauvegarde invalide.')
        from core import validate
        for name in ('reglages.json','reglages-par-defaut.json'):
            if name in files: validate(files[name])
        from wg_crypto import private_directory, protect
        # All checks and mutations share the same lock as model start and remote activation.
        with c.lock, c.wireguard.lock, c.remote.lock, c.remote.workspace.lock:
            if c.processes() or c.supervisor(c.current_run()) or c.remote.metadata()['enabled']:
                raise ValueError('Arrêter le modèle et désactiver WireGuard avant la restauration.')
            if 'comptes.json' in files:
                if not isinstance(files['comptes.json'],list):raise ValueError('Comptes invalides.')
                for account in files['comptes.json']:
                    if not isinstance(account,dict) or not isinstance(account.get('enabled'),bool) or len(bytes.fromhex(account.get('salt','')))!=16 or len(bytes.fromhex(account.get('password_hash','')))!=64:raise ValueError('Compte sauvegardé invalide.')
            if 'vault' in files:
                def validate_key(value):
                    if not isinstance(value,str) or len(base64.b64decode(value,validate=True))!=32:raise ValueError("Clé WireGuard invalide.")
                vault=files['vault']
                if not isinstance(vault,dict) or not isinstance(vault.get('peers'),dict):raise ValueError('Coffre WireGuard invalide.')
                validate_key(vault.get('private_key'))
                for key in vault['peers'].values():validate_key(key)
            if 'wireguard.json' in files:
                from wireguard_access import validate_settings
                values=files['wireguard.json']
                if not isinstance(values,dict):raise ValueError('Configuration WireGuard invalide.')
                if values.get('public_host'):validate_settings(values)
                elif type(values.get('listen_port')) is not int or not 1<=values['listen_port']<=65535:raise ValueError('Port WireGuard invalide.')
            import sys
            sys.path.insert(0,str(ROOT/'client-qwen'))
            from wg_bridge import validate_profile
            if not isinstance(files.get('profiles',{}),dict):raise ValueError('Profils invalides.')
            from profiles import validate_access,match,public_key
            access=validate_access(files['acces-distants.json']) if 'acces-distants.json' in files else {'clients':[]}
            records={record['id']:record for record in access['clients']}
            workspace_raw=c.remote.workspace.validate_backup(files['workspace'],set(records)) if 'workspace' in files else None
            web_raw=base64.b64decode(files['web_key'],validate=True) if 'web_key' in files else None
            if web_raw is not None and not 1<=len(web_raw)<=500:raise ValueError('Clé de recherche sauvegardée invalide.')
            server_key=files.get('wireguard.json',{}).get('public_key') or None
            if 'vault' in files and server_key and public_key(files['vault']['private_key'])!=server_key:raise ValueError('Le coffre ne correspond pas à la clé publique du serveur.')
            for identity,profile in files.get('profiles',{}).items():
                if identity not in records:raise ValueError('Profil sauvegardé sans destinataire enregistré.')
                psk=files.get('vault',{}).get('peers',{}).get(identity)
                if psk is None:raise ValueError('Clé partagée absente du coffre pour ce client.')
                match(records[identity],profile,server_key,psk)
            seed=base64.b64decode(files['signing_seed'],validate=True) if 'signing_seed' in files else None
            if seed is not None and len(seed)!=32:raise ValueError('Clé de signature invalide.')
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
            pinned=base64.b64encode(Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)).decode() if seed is not None else None
            for profile in files.get('profiles',{}).values():
                if profile.get('update_public_key') and profile['update_public_key']!=pinned:raise ValueError('Signature serveur incompatible avec les clients sauvegardés.')
            previous=self.backup(data.get('password'))
            private_directory(c.wireguard.directory)
            targets=[c.home/name for name in FILES]+[c.wireguard.vault_path,c.wireguard.directory/'profils-restaures.dpapi',c.wireguard.directory/'signature.dpapi',c.home/'recherche-web.dpapi']
            originals={path:path.read_bytes() if path.exists() else None for path in targets}
            original_workspace=c.remote.workspace.backup()
            old_desired=self.desired;self.desired=False
            try:
                for name in FILES:
                    if name in files:
                        value=files[name]
                        if name=='acces-distants.json':value={**value,'enabled':False}
                        write_json(c.home/name,value)
                if 'vault' in files:c.wireguard.save_vault(files['vault'])
                (c.wireguard.directory/'profils-restaures.dpapi').write_bytes(protect(json.dumps(files.get('profiles',{})).encode()))
                if seed is not None:(c.wireguard.directory/'signature.dpapi').write_bytes(protect(seed))
                if workspace_raw is not None:c.remote.workspace.restore(workspace_raw)
                if web_raw is not None:(c.home/'recherche-web.dpapi').write_bytes(protect(web_raw))
                elif 'workspace' in files:(c.home/'recherche-web.dpapi').unlink(missing_ok=True)
                c.base=read_json(c.base_path)
                with c.remote.accounts.lock:c.remote.accounts.sessions.clear();c.remote.accounts.failures.clear()
            except Exception:
                c.remote.workspace.restore(base64.b64decode(original_workspace))
                for path,raw in originals.items():
                    if raw is None:path.unlink(missing_ok=True)
                    else:path.write_bytes(raw)
                c.base=read_json(c.base_path);self.desired=old_desired
                raise
        return {'message':'Configuration restaurée, accès distant désactivé. Une sauvegarde de retour a été créée.', 'rollback':previous['file']}

    def diagnostic(self):
        c=self.controller
        state=c.state()
        host=c.wireguard.settings().get('public_host','')
        try: addresses=sorted({v[4][0] for v in socket.getaddrinfo(host,None)}) if host else []
        except OSError: addresses=[]
        return {'version':VERSION,'status':state['status'],'ram':state['ram'],'gpus':state['gpus'],
                'queue':c.remote.scheduler.snapshot(), 'dns':{'host':host,'addresses':addresses},
                'wireguard':c.wireguard.status(), 'operations':self.status(),
                'actions': ['Configurer un nom DNS ou une IP publique.' if not host else 'Vérifier la redirection UDP de la box depuis un autre réseau.',
                            'Lancer le modèle.' if state['status']=='arrete' else 'Consulter le journal local si le moteur ne répond pas.']}
