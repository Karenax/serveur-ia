"""Local operations; encrypted portable backups and opt-in startup."""
import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import threading
import time
from cryptography.fernet import Fernet, InvalidToken
from core import ROOT, read_json, write_json

VERSION = '3.5.30'
FILES = ['reglages.json', 'reglages-par-defaut.json', 'derniers-reglages-valides.json', 'base-strata.json', 'acces-distants.json', 'wireguard.json', 'comptes.json', 'exploitation.json', 'voix.json', 'hermes-integration.json', 'hermes-models.json']

def cipher(password, salt):
    if not isinstance(password, str) or not 12 <= len(password) <= 1024:
        raise ValueError('Phrase de sauvegarde : 12 à 1024 caractères.')
    return Fernet(base64.urlsafe_b64encode(hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600000, 32)))


def registered_profile_ids(files):
    """The snapshot registry defines profile ownership, including archived devices."""
    from profiles import validate_access
    access = files.get('acces-distants.json')
    if access is None: return set()
    validate_access(access)
    return {record['id'] for record in access['clients'] + access.get('deleted_clients', [])}

class Operations:
    def __init__(self, controller):
        self.controller = controller
        self.path = controller.home / 'exploitation.json'
        self.attempts = [t for t in read_json(controller.home/'relances.json', []) if time.time()-t<3600]
        self.desired = False
        self.last_error = ''
        self.hermes_lock = threading.RLock()
        self.hermes_pause = None
        from backups import BackupManager
        from restoration import RestoreManager
        self.backups = BackupManager(controller)
        self.restorations = RestoreManager(controller)

    @contextmanager
    def _hermes_quiesce_lock(self, restoring):
        if restoring:
            # Active model calls may still need the controller while stopping.
            with self.hermes_lock: yield
            return
        token = self.hermes_pause
        if token is not None and token['thread'] != threading.get_ident():
            raise ValueError('Une sauvegarde ou restauration Hermes est déjà en cours.')
        # Legacy synchronous commands already own the controller lock. Follow
        # their order, but never retain it while waiting for restore admission.
        with self.controller.lock:
            if not self.hermes_lock.acquire(blocking=False):
                raise ValueError('Une sauvegarde ou restauration Hermes est déjà en cours.')
            try: yield
            finally: self.hermes_lock.release()

    def hermes_quiesce(self, restoring=False):
        """Freeze profile writers before snapshots; close the facade for restore."""
        with self._hermes_quiesce_lock(restoring):
            if self.hermes_pause is not None:
                if self.hermes_pause['thread'] != threading.get_ident():
                    raise ValueError('Une sauvegarde ou restauration Hermes est déjà en cours.')
                self.hermes_pause['depth'] += 1
                return self.hermes_pause
            facade = getattr(self.controller, 'hermes', None)
            if facade is None: return None
            facade.lock.acquire()
            accounts_lock = getattr(facade.accounts, 'lock', None)
            token = {'facade': facade, 'started': bool(facade.started), 'depth': 1, 'thread': threading.get_ident(),
                     'restoring': restoring, 'admission_paused': getattr(facade.conversations, 'admission_paused', False),
                     'accounts_lock': accounts_lock, 'accounts_acquired': False, 'snapshot_locks': []}
            try:
                with facade.conversations.lock:
                    if facade.conversations.active and not restoring:
                        raise ValueError('Attendez la fin des conversations avant de sauvegarder Hermes.')
                    facade.conversations.admission_paused = True
                if not restoring:
                    c = self.controller
                    # Preserve the Fred lock order: revocation holds remote's
                    # lock before updating Workspace jobs.
                    for lock in (c.lock, c.wireguard.lock, c.remote.lock, c.remote.accounts.lock):
                        lock.acquire(); token['snapshot_locks'].append(lock)
                    # Native project mirroring writes files outside Hermes runs.
                    # Keep its lock before Workspace's lock to follow its own order.
                    projects = getattr(facade, 'projects', None)
                    for lock in ([projects.lock] if projects else []) + [c.remote.workspace.lock]:
                        lock.acquire(); token['snapshot_locks'].append(lock)
                    if c.remote.workspace.running:
                        raise ValueError('Attendez la fin des tâches avant de sauvegarder Hermes.')
                # The native supervisor takes service -> accounts while
                # rebuilding its profiles, so a snapshot follows that order.
                service_lock = getattr(facade.service, 'lock', None)
                if service_lock:
                    service_lock.acquire(); token['snapshot_locks'].append(service_lock)
                if restoring:
                    facade.close()
                    deadline = time.monotonic() + 40
                    while True:
                        with facade.conversations.lock: active = bool(facade.conversations.active)
                        if not active: break
                        if time.monotonic() >= deadline:
                            raise ValueError('Les conversations Hermes ne sont pas encore arrêtées ; restauration refusée.')
                        time.sleep(.05)
                    # A run may still be binding its native project while it
                    # unwinds; only freeze project writers after it has exited.
                    projects = getattr(facade, 'projects', None)
                    if projects:
                        projects.lock.acquire(); token['snapshot_locks'].append(projects.lock)
                if accounts_lock:
                    accounts_lock.acquire(); token['accounts_acquired'] = True
                if not restoring: facade.service.close()
                self.hermes_pause = token
                return token
            except BaseException:
                if restoring:
                    # The restore coordinator rebuilds the closed facade even
                    # when preparation fails before a journal is applied.
                    self.hermes_pause = token
                    raise
                facade.conversations.admission_paused = token['admission_paused']
                if token['accounts_acquired']: accounts_lock.release()
                for lock in reversed(token['snapshot_locks']): lock.release()
                facade.lock.release()
                raise

    def hermes_resume(self, token, restored=False):
        with self.hermes_lock:
            if token is not None and not token.get('released'):
                token['depth'] -= 1
                if token['depth'] > 0: return
            try:
                if restored:
                    c = self.controller
                    callback = getattr(c, 'recreate_hermes', None)
                    start = bool(token and token['started'])
                    if callback:
                        callback(start=start)
                    else:
                        from hermes_fred import HermesFred, configured
                        config = configured(c.home)
                        facade = HermesFred(c.remote, c.remote_backend, port=config.get('port', 8643),
                                            private_port=config.get('private_port', 8768)) if config else None
                        c.hermes = c.remote.hermes = c.remote.workspace.hermes = facade
                        if facade and start: facade.start()
                elif token is not None:
                    facade = token['facade']
                    try:
                        if token['started']: facade.service.start()
                    finally:
                        facade.conversations.admission_paused = token['admission_paused']
            finally:
                if token is not None:
                    if not token.get('released'):
                        if token['accounts_acquired']: token['accounts_lock'].release()
                        for lock in reversed(token['snapshot_locks']): lock.release()
                        token['facade'].lock.release()
                self.hermes_pause = None

    def hermes_release_closed(self, token):
        """A failed restore stays closed but recovery may run on another thread."""
        with self.hermes_lock:
            if token is not None and not token.get('released'):
                if token['accounts_acquired']: token['accounts_lock'].release()
                for lock in reversed(token['snapshot_locks']): lock.release()
                token['facade'].lock.release()
                token['released'] = True
            self.hermes_pause = None

    @contextmanager
    def hermes_snapshot(self):
        token = self.hermes_quiesce()
        try: yield
        finally: self.hermes_resume(token)

    def hermes_export(self, owners):
        from hermes_backup import HermesBackup
        root = self.controller.home / 'hermes-fred'
        return HermesBackup(root).export(owners) if root.exists() else None

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
                self.notification_tick()
                self.backups.tick()
                if c.remote.maintenance:
                    time.sleep(1)
                    continue
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

    def notification_tick(self):
        """Publish durable operational alerts without exposing paths or error content."""
        remote = self.controller.remote
        if getattr(remote, 'maintenance', False): return
        notifications = getattr(remote, 'notifications', None)
        if notifications is None: return
        state = self.backups.status()
        job = state.get('job', {})
        if job.get('state') == 'failed':
            identity = str(job.get('id') or job.get('started_at') or 'unknown')
            notifications.publish('admin', 'backup_failed', 'backup_failed:' + identity)
            if any(word in state.get('last_error', '').lower() for word in ('espace', 'plein')):
                notifications.publish('admin', 'storage_low', 'backup_storage:' + identity)
        for record in state.get('catalog', []):
            if record.get('secondary', {}).get('status') == 'error':
                notifications.publish('admin', 'backup_copy_failed', 'backup_copy:' + record['id'])
        restore = self.restorations.status()
        if restore.get('state') in ('failed', 'recovery_failed'):
            detail = restore.get('job', restore)
            identity = str(detail.get('id') or detail.get('started') or 'unknown')
            notifications.publish('admin', 'restore_failed', 'restore_failed:' + identity)

    def backup(self, password):
        c = self.controller
        with self.hermes_snapshot(), c.lock, c.wireguard.lock, c.remote.lock, c.remote.workspace.lock:
            content = {name:read_json(c.home/name) for name in FILES if (c.home/name).exists()}
            registered = registered_profile_ids(content)
            if c.wireguard.vault_path.exists(): content['vault'] = c.wireguard.vault()
            clients = c.home/'clients'
            from wg_crypto import protect
            saved=c.wireguard.directory/'profils-restaures.dpapi'
            profiles = json.loads(protect(saved.read_bytes(),decrypt=True)) if saved.exists() else {}
            if not isinstance(profiles,dict):raise ValueError('Registre des profils personnels illisible.')
            profiles = {identity:profile for identity,profile in profiles.items() if identity in registered}
            signing=c.wireguard.directory/'signature.dpapi'
            if signing.exists():content['signing_seed']=base64.b64encode(protect(signing.read_bytes(),decrypt=True)).decode()
            if clients.exists():
                import struct
                for exe in clients.glob('*.exe'):
                    if len(exe.stem)!=16 or any(c not in '0123456789abcdef' for c in exe.stem):continue
                    if exe.stem not in registered or exe.stat().st_size<16:continue
                    with exe.open('rb') as f:
                        f.seek(-16, 2); footer=f.read(16)
                        if footer[4:] == b'QWENPROFILE1':
                            size=struct.unpack('<I', footer[:4])[0]
                            if 0 < size <= 65536 and size+16<=exe.stat().st_size:
                                f.seek(-16-size, 2); profiles[exe.stem]=json.loads(f.read(size))
            content['profiles']=profiles
            content['workspace']=c.remote.workspace.backup()
            hermes = self.hermes_export(registered)
            if hermes is not None: content['hermes'] = hermes
            web_key=c.home/'recherche-web.dpapi'
            if web_key.exists():content['web_key']=base64.b64encode(protect(web_key.read_bytes(),decrypt=True)).decode()
            salt=secrets.token_bytes(16)
            encrypted=cipher(password,salt).encrypt(json.dumps({'version':1,'files':content}).encode())
            directory=c.home/'sauvegardes';directory.mkdir(exist_ok=True)
            target=directory/(time.strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)+'.qwenbackup')
            from wg_crypto import private_directory
            private_directory(directory)
            from tempfile import NamedTemporaryFile
            with NamedTemporaryFile(dir=directory, suffix='.tmp', delete=False) as stream:
                temporary=Path(stream.name)
                stream.write(b'QWENBACKUP1'+salt+encrypted);stream.flush();os.fsync(stream.fileno())
            try:os.replace(temporary,target)
            finally:temporary.unlink(missing_ok=True)
        return {'file':str(target), 'message':'Sauvegarde chiffrée créée.'}

    def restore(self, data):
        return self.restorations.restore_sync(data, guided=False)

    def _restore_legacy(self, data, *, package=None):
        c=self.controller
        if c.processes() or c.supervisor(c.current_run()) or c.remote.metadata()['enabled']:
            raise ValueError('Arrêter le modèle et désactiver WireGuard avant la restauration.')
        if package is None:
            path=Path(data.get('file',''))
            if path.stat().st_size>400*1024*1024:raise ValueError('Sauvegarde trop volumineuse.')
            blob=path.read_bytes()
            if not blob.startswith(b'QWENBACKUP1'): raise ValueError('Format de sauvegarde invalide.')
            try: package=json.loads(cipher(data.get('password'),blob[11:27]).decrypt(blob[27:]))
            except (InvalidToken, ValueError): raise ValueError('Sauvegarde invalide ou phrase incorrecte.')
            del blob
        files=package.get('files',{})
        if package.get('version') != 1 or not isinstance(files,dict) or set(files)-set(FILES+['vault','profiles','signing_seed','workspace','web_key','hermes']):
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
            if not isinstance(files.get('profiles',{}),dict):raise ValueError('Profils invalides.')
            from profiles import validate_access,match,public_key
            access=validate_access(files['acces-distants.json']) if 'acces-distants.json' in files else {'clients':[]}
            records={record['id']:record for record in access['clients']+access.get('deleted_clients',[])}
            from hermes_backup import HermesBackup
            hermes_backup = HermesBackup(c.home / 'hermes-fred')
            if 'hermes' in files: hermes_backup.validate(files['hermes'], set(records))
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
            original_owners=registered_profile_ids({name:read_json(c.home/name) for name in FILES if (c.home/name).exists()})
            original_hermes=self.hermes_export(original_owners)
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
                if 'hermes' in files or original_hermes is not None:
                    hermes_backup.restore(files.get('hermes', {'version': 1, 'files': {}}), set(records))
                if web_raw is not None:(c.home/'recherche-web.dpapi').write_bytes(protect(web_raw))
                elif 'workspace' in files:(c.home/'recherche-web.dpapi').unlink(missing_ok=True)
                c.base=read_json(c.base_path)
                with c.remote.accounts.lock:c.remote.accounts.sessions.clear();c.remote.accounts.failures.clear()
            except Exception:
                c.remote.workspace.restore(base64.b64decode(original_workspace))
                if original_hermes is not None or 'hermes' in files:
                    hermes_backup.restore(original_hermes or {'version': 1, 'files': {}}, original_owners)
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
