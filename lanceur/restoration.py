"""Guided restoration, durable rollback and explicit client resynchronization."""
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import threading
import time
from core import read_json, write_json
from wg_crypto import private_directory, protect


def atomic(path, raw):
    import tempfile
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=path.name+'.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def allowed_paths(home):
    from operations import FILES
    return set(FILES + ['wireguard-prive/secrets.dpapi', 'wireguard-prive/profils-restaures.dpapi',
                       'wireguard-prive/signature.dpapi', 'recherche-web.dpapi',
                       'espaces-prives/espaces.sqlite3', 'sauvegardes/catalogue.json','appareils-activite.json', 'hermes-fred'])


def recover(home):
    """Called before opening the database or accepting HTTP requests."""
    home = Path(home)
    journal_path = home / 'securite' / 'restauration.json'
    if not journal_path.exists():return None
    journal = read_json(journal_path)
    if not isinstance(journal, dict):raise ValueError('Journal de restauration illisible ; démarrage refusé.')
    if journal.get('state') != 'applying':return journal
    source = home / 'securite' / 'retour-restauration.dpapi'
    try:
        originals = json.loads(protect(source.read_bytes(), decrypt=True))
        if not isinstance(originals, dict) or set(originals) - allowed_paths(home):raise ValueError('Chemins de retour invalides.')
        decoded = {name: base64.b64decode(raw, validate=True) if raw is not None else None for name,raw in originals.items()}
        for name, raw in decoded.items():
            if name == 'hermes-fred': continue
            path = home / name
            if name == 'espaces-prives/espaces.sqlite3':
                for suffix in ('-wal','-shm'):Path(str(path)+suffix).unlink(missing_ok=True)
            if raw is None:path.unlink(missing_ok=True)
            else:atomic(path, raw)
        if 'hermes-fred' in decoded:
            from hermes_backup import HermesBackup
            from operations import registered_profile_ids
            access_raw = decoded.get('acces-distants.json')
            files = {'acces-distants.json': json.loads(access_raw)} if access_raw else {}
            owners = registered_profile_ids(files)
            package = json.loads(decoded['hermes-fred']) if decoded['hermes-fred'] is not None else {'version': 1, 'files': {}}
            HermesBackup(home / 'hermes-fred').restore(package, owners)
        journal.update(state='recovered',phase='rollback',active=False,finished=time.time(),
                       message='Restauration interrompue : état antérieur récupéré, accès distant désactivé.')
        access=read_json(home/'acces-distants.json')
        if isinstance(access,dict):write_json(home/'acces-distants.json',{**access,'enabled':False})
        write_json(journal_path,journal)
        return journal
    except Exception as error:
        raise RuntimeError('Retour après interruption impossible ; démarrage refusé et fichiers conservés.') from error


def validate_package(controller, package):
    from operations import FILES
    from core import validate
    from profiles import validate_access, match, public_key
    from wireguard_access import validate_settings
    if not isinstance(package,dict) or package.get('version')!=1 or not isinstance(package.get('files'),dict):
        raise ValueError('Contenu de sauvegarde invalide.')
    files=package['files']
    if set(files)-set(FILES+['vault','profiles','signing_seed','workspace','web_key','hermes']):raise ValueError('Contenu de sauvegarde invalide.')
    for name in ('reglages.json','reglages-par-defaut.json','derniers-reglages-valides.json'):
        if name in files:validate(files[name])
    for name in ('base-strata.json','exploitation.json'):
        if name in files and not isinstance(files[name],dict):raise ValueError('Configuration invalide.')
    if 'voix.json' in files and (not isinstance(files['voix.json'],dict) or set(files['voix.json'])!={'enabled'} or type(files['voix.json']['enabled']) is not bool):raise ValueError('Configuration vocale invalide.')
    if 'hermes-integration.json' in files:
        config = files['hermes-integration.json']
        if (not isinstance(config, dict) or type(config.get('enabled')) is not bool or
                set(config) - {'enabled', 'port', 'private_port', 'version'} or
                any(type(config.get(key, default)) is not int or not 1 <= config.get(key, default) <= 65535
                    for key,default in [('port',8643),('private_port',8768)]) or
                config.get('port',8643) == config.get('private_port',8768) or
                ('version' in config and config['version'] != 1)):
            raise ValueError('Configuration Hermes sauvegardée invalide.')
    if 'hermes-models.json' in files:
        from hermes_models import normalize_policy
        normalize_policy(files['hermes-models.json'])
    accounts=files.get('comptes.json',[])
    if not isinstance(accounts,list):raise ValueError('Comptes invalides.')
    for account in accounts:
        try:
            valid=isinstance(account,dict) and type(account.get('enabled')) is bool and len(bytes.fromhex(account.get('salt','')))==16 and len(bytes.fromhex(account.get('password_hash','')))==64
        except (ValueError,TypeError):valid=False
        if not valid:raise ValueError('Compte sauvegardé invalide.')
    vault=files.get('vault')
    if vault is not None:
        if not isinstance(vault,dict) or not isinstance(vault.get('peers'),dict):raise ValueError('Coffre WireGuard invalide.')
        for key in [vault.get('private_key'),*vault['peers'].values()]:
            if not isinstance(key,str) or len(base64.b64decode(key,validate=True))!=32:raise ValueError('Clé WireGuard invalide.')
    settings=files.get('wireguard.json',{})
    if settings:
        if not isinstance(settings,dict):raise ValueError('Configuration WireGuard invalide.')
        if settings.get('public_host'):validate_settings(settings)
        elif type(settings.get('listen_port')) is not int or not 1<=settings['listen_port']<=65535:raise ValueError('Port WireGuard invalide.')
    access=validate_access(files['acces-distants.json']) if 'acces-distants.json' in files else {'clients':[]}
    records={r['id']:r for r in access['clients']+access.get('deleted_clients',[])}
    if 'hermes' in files:
        from hermes_backup import HermesBackup
        HermesBackup(controller.home / 'hermes-fred').validate(files['hermes'], set(records))
    if 'workspace' in files:controller.remote.workspace.validate_backup(files['workspace'],set(records))
    profiles=files.get('profiles',{})
    if not isinstance(profiles,dict):raise ValueError('Profils invalides.')
    server_key=settings.get('public_key')
    if vault and server_key and public_key(vault['private_key'])!=server_key:raise ValueError('Clés serveur incompatibles.')
    for identity,profile in profiles.items():
        if identity not in records or not vault or identity not in vault['peers']:raise ValueError('Profil sans accès ou clé partagée.')
        match(records[identity],profile,server_key,vault['peers'][identity])
    if 'web_key' in files:
        if not 1<=len(base64.b64decode(files['web_key'],validate=True))<=500:raise ValueError('Clé de recherche invalide.')
    seed=base64.b64decode(files['signing_seed'],validate=True) if 'signing_seed' in files else None
    if seed is not None:
        if len(seed)!=32:raise ValueError('Clé de signature invalide.')
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        pinned=base64.b64encode(Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)).decode()
        if any(p.get('update_public_key') and p['update_public_key']!=pinned for p in profiles.values()):raise ValueError('Signature incompatible avec les profils.')
    return files


class RestoreManager:
    def __init__(self, controller):
        self.controller=controller
        self.lock=threading.Lock()
        self.previews={}
        self.thread=None
        self.callbacks=None
        self.job=read_json(controller.home/'securite'/'restauration.json',{}) or {}

    def status(self):
        return {'state':self.job.get('state','idle'),'phase':self.job.get('phase',''),
                'active':bool(self.job.get('active')), 'message':self.job.get('message','Aucune restauration en cours.'),
                'retry_allowed':self.job.get('state')=='applying' and not self.lock.locked(),
                'job':dict(self.job)}

    def preview(self, data):
        inspected=self.controller.operations.backups.inspect(data)
        validate_package(self.controller,inspected['package'])
        password=self.controller.operations.backups.resolve_password(data.get('password'))
        path=Path(inspected['summary']['file'])
        token=secrets.token_urlsafe(32)
        self.previews={k:v for k,v in self.previews.items() if v['expires_at']>time.time()}
        with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest!=inspected['summary']['sha256']:raise ValueError('La sauvegarde a changé pendant sa vérification ; réessayez.')
        self.previews[token]={'file':str(path.resolve()),'sha256':digest,
                              'password_hash':hashlib.sha256(password.encode()).hexdigest(),'expires_at':time.time()+300}
        return {'summary':inspected['summary'],'restore_token':token,'expires_at':self.previews[token]['expires_at'],
                'effects':['Interruption des accès et arrêt coordonné du modèle.',
                           'Point de retour automatique avant toute modification.',
                           'Accès distant désactivé après restauration.',
                           'Reprise explicite des historiques dans les clients.']}

    def start(self, data):
        if data.get('confirm') is not True:raise ValueError('Confirmer la restauration et son interruption du service.')
        if not self.lock.acquire(False):raise ValueError('Une restauration est déjà en cours.')
        try:
            preview=self.previews.pop(data.get('restore_token'),None)
            password=self.controller.operations.backups.resolve_password(data.get('password'))
            inspected=self.controller.operations.backups.inspect(data)
            with Path(inspected['summary']['file']).open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            if not preview or preview['expires_at']<time.time() or preview['sha256']!=digest or inspected['summary']['sha256']!=digest or preview['file']!=str(Path(inspected['summary']['file']).resolve()) or preview['password_hash']!=hashlib.sha256(password.encode()).hexdigest():
                raise ValueError('Vérifiez à nouveau la sauvegarde avant de la restaurer.')
            validate_package(self.controller,inspected['package'])
            self.job={'id':secrets.token_hex(12),'state':'preparing','phase':'validation','active':True,'started':time.time(),'message':'Restauration préparée.'}
            def worker():
                try:self._restore(data, inspected, password, True)
                except Exception:
                    if self.job.get('state')=='applying':
                        self.job.update(phase='recovery_failed',active=True,message='Retour incomplet : accès bloqués. Corrigez le stockage puis réessayez le retour.')
                    else:self.job.update(state='failed',active=False,finished=time.time(),message='Restauration refusée ou interrompue ; état précédent conservé ou récupéré.')
                    write_json(self.controller.home/'securite'/'restauration.json',self.job)
                finally:self.lock.release()
            self.thread=threading.Thread(target=worker,daemon=True,name='fred-restore');self.thread.start()
            return self.status()
        except Exception:self.lock.release();raise

    def restore_sync(self, data, guided=False):
        if not self.lock.acquire(False):raise ValueError('Une restauration est déjà en cours.')
        try:
            c=self.controller
            if not guided and (c.processes() or c.supervisor(c.current_run()) or c.remote.metadata()['enabled']):
                raise ValueError('Arrêter le modèle et désactiver WireGuard avant la restauration.')
            inspected=c.operations.backups.inspect(data)
            password=c.operations.backups.resolve_password(data.get('password'))
            validate_package(c,inspected['package'])
            self.job={'id':secrets.token_hex(12),'state':'preparing','active':True,'started':time.time(),'message':'Préparation de la restauration.'}
            return self._restore(data,inspected,password,guided)
        except Exception:
            if self.job.get('state')=='preparing':
                self.job.update(state='failed',active=False,finished=time.time(),message='Restauration refusée avant modification ; état précédent conservé.')
                write_json(self.controller.home/'securite'/'restauration.json',self.job)
            elif self.job.get('state')=='applying':
                self.job.update(phase='recovery_failed',active=True,message='Retour incomplet : accès bloqués. Corrigez le stockage puis réessayez le retour.')
                write_json(self.controller.home/'securite'/'restauration.json',self.job)
            raise
        finally:self.lock.release()

    def _restore(self, data, inspected, password, guided):
        c=self.controller
        # Prevent backup workers and restores from collecting mixed generations.
        with c.operations.backups.exclusive():
            import shutil
            if shutil.disk_usage(c.home).free < len(json.dumps(inspected['package']).encode())*3+16*1024*1024:
                raise ValueError('Espace disque insuffisant pour la restauration et son point de retour.')
            current_access=read_json(c.remote.path,{})
            from server_state import installation_id
            archive_origin=inspected.get('security',{}).get('installation_id')
            current_id=installation_id(c.home)
            files=inspected['package']['files']
            if archive_origin:trusted_registry=archive_origin==current_id
            else:
                archived_records={r['id']:r for r in files.get('acces-distants.json',{}).get('clients',[])}
                current_records=current_access.get('clients',[])+current_access.get('deleted_clients',[])
                trusted_registry=bool(files.get('wireguard.json',{}).get('public_key') and files['wireguard.json']['public_key']==c.wireguard.settings().get('public_key') and any(r['id'] in archived_records and r['hash']==archived_records[r['id']]['hash'] for r in current_records))
            with c.lock:
                c.remote.maintenance=True;c.remote.workspace.maintenance=True
                c.operations.desired=False
            workspace=c.remote.workspace
            generation_callback,valid_callback=workspace.generation,workspace.valid
            self.callbacks=(generation_callback,valid_callback)
            journal=c.home/'securite'/'restauration.json'
            staging=c.home/'securite'/'retour-restauration.dpapi'
            private_directory(journal.parent)
            hermes_token = None
            try:
                hermes_token = c.operations.hermes_quiesce(restoring=True)
                for record in c.remote.metadata()['clients']:
                    c.remote.scheduler.cancel(record['id'])
                workspace.shutdown()
                c.voice.close()
                if guided:
                    c.wireguard.deactivate()
                    c.stop()
                if c.processes() or c.supervisor(c.current_run()) or c.remote.metadata()['enabled']:
                    raise ValueError('Le modèle et les accès doivent être arrêtés avant restauration.')
                with c.lock,c.wireguard.lock,c.remote.lock,workspace.lock:
                    original_workspace=base64.b64decode(workspace.backup())
                    originals={name:base64.b64encode((c.home/name).read_bytes()).decode() if (c.home/name).is_file() else None for name in allowed_paths(c.home) if name != 'hermes-fred'}
                    originals['espaces-prives/espaces.sqlite3']=base64.b64encode(original_workspace).decode()
                    from operations import registered_profile_ids
                    original_hermes = c.operations.hermes_export(registered_profile_ids({'acces-distants.json': current_access}))
                    originals['hermes-fred'] = base64.b64encode(json.dumps(original_hermes).encode()).decode() if original_hermes is not None else None
                    atomic(staging,protect(json.dumps(originals).encode()))
                    del originals, original_workspace, original_hermes
                    self.job.update(state='applying',phase='restore',message='Restauration des données ; accès fermés.')
                    write_json(journal,self.job)
                    # Reuse validation and the portable return archive without
                    # re-encoding/encrypting/decrypting the accepted package.
                    result=c.operations._restore_legacy({'password':password}, package=inspected['package'])
                    extras=inspected.get('extras',{})
                    # Only explicitly supported configuration; never restore journals or DPAPI automation credentials.
                    for name,value in extras.items():
                        if name in ('derniers-reglages-valides.json','appareils-activite.json'):write_json(c.home/name,value)
                    if 'appareils-activite.json' in extras:c.remote.activity=extras['appareils-activite.json']
                    if 'sauvegardes-planification.json' in extras:
                        schedule=extras['sauvegardes-planification.json']
                        c.operations.backups.configure({**{key:schedule[key] for key in ('time','frequency','weekday','retention') if key in schedule},'enabled':False})
                    security=inspected.get('security',{})
                    if 'revocations.json' in security:c.remote.revocations.merge(security['revocations.json'])
                    if not trusted_registry:
                        access=read_json(c.remote.path)
                        for record in access['clients']:record['suspended']=True
                        write_json(c.remote.path,access)
                    if hasattr(c.operations.backups,'register_legacy'):
                        c.operations.backups.register_legacy(result['rollback'],password=password)
                    from server_state import new_generation
                    new_generation(c.home)
                    c.base=read_json(c.base_path)
                    c.operations.desired=False
                    self.job.update(state='completed',phase='complete',active=False,finished=time.time(),result=result,
                                    message='Restauration vérifiée. Accès distant désactivé ; reprise explicite des clients requise.')
                    write_json(journal,self.job)
                    return result
            except BaseException:
                if self.job.get('state')=='applying':
                    recover(c.home)
                    self.job=read_json(journal)
                    c.base=read_json(c.base_path)
                    c.operations.backups.data=read_json(c.operations.backups.path)
                    c.remote.activity=read_json(c.remote.activity_path,{})
                c.operations.desired=False
                raise
            finally:
                hermes_token = hermes_token or c.operations.hermes_pause
                if self.job.get('state')!='applying':c.remote.maintenance=False;workspace.maintenance=False
                if generation_callback and not self.job.get('state')=='applying':workspace.start(generation_callback,valid_callback)
                if self.job.get('state') != 'applying':
                    c.operations.hermes_resume(hermes_token, restored=bool(hermes_token and hermes_token['restoring']) or self.job.get('state') in ('completed', 'recovered'))
                else:
                    # Retain the closed facade and admission block until durable recovery succeeds.
                    self.hermes_token = hermes_token
                    c.operations.hermes_release_closed(hermes_token)

    def recover_now(self):
        c=self.controller
        if not self.lock.acquire(False):raise ValueError('Une restauration est déjà en cours.')
        try:
            with c.operations.backups.exclusive():
                self.job=recover(c.home) or {}
                if self.job.get('state')=='recovered':
                    c.base=read_json(c.base_path);c.operations.backups.data=read_json(c.operations.backups.path)
                    c.remote.activity=read_json(c.remote.activity_path,{})
                    c.remote.maintenance=False;c.remote.workspace.maintenance=False
                    if self.callbacks and self.callbacks[0]:c.remote.workspace.start(*self.callbacks)
                    c.operations.hermes_resume(getattr(self, 'hermes_token', None), restored=True)
                    self.hermes_token = None
                return self.status()
        finally:self.lock.release()
