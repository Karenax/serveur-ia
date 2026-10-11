"""Server-side verified backups, durable schedules and encrypted portable archives.

Only the administrative loopback API calls this module. Passwords never enter
the JSON catalogue: automation uses the Windows user's DPAPI vault. The archive
itself is independent of that vault and can be recovered with its phrase.
"""
from __future__ import annotations

import base64
import copy
from contextlib import contextmanager
import datetime as dt
import errno
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import sqlite3
import struct
import tempfile
import threading
import time

from cryptography.fernet import InvalidToken
from core import read_json, write_json
from operations import FILES, VERSION, cipher, registered_profile_ids
from wg_crypto import private_directory, protect

HEADER = b'FREDBACKUP2'
LEGACY_HEADER = b'QWENBACKUP1'
MAX_ARCHIVE = 400 * 1024 * 1024
MAX_JSON = 4 * 1024 * 1024
EXTRA_FILES = ('derniers-reglages-valides.json', 'appareils-activite.json')
DEFAULT_RETENTION = {'daily': 7, 'weekly': 4, 'monthly': 6}
EXCLUDED = ['Modèles, caches et binaires reconstructibles',
            'Réglages et brouillons des clients non synchronisés',
            'Clé Android de signature : récupération séparée',
            'Sessions en cours et état des processus']
MANAGED_NAME = re.compile(r'^fred-\d{8}-\d{6}-[0-9a-f]{24}\.qwenbackup$')


def _iso(timestamp):
    return dt.datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec='seconds') if timestamp else ''


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _atomic_bytes(path, raw):
    path = Path(path)
    descriptor, name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def _hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): digest.update(block)
    return digest.hexdigest()


def _read_json_checked(path, limit=MAX_JSON):
    path = Path(path)
    if path.stat().st_size > limit: raise ValueError('Configuration de sauvegarde trop volumineuse.')
    try: return json.loads(path.read_text(encoding='utf-8-sig'))
    except (ValueError, UnicodeError): raise ValueError('Configuration à sauvegarder illisible.') from None


def _message(error):
    # Never persist a raw exception: paths, tokens and JSON values may be in it.
    if isinstance(error, OSError) and error.errno == errno.ENOSPC:
        return 'Espace disque insuffisant. La dernière sauvegarde valide est conservée.'
    if isinstance(error, PermissionError): return 'Destination inaccessible : vérifier les droits du compte serveur.'
    if isinstance(error, InvalidToken): return 'Sauvegarde invalide ou phrase incorrecte.'
    return 'Sauvegarde non achevée. Vérifier la destination, la phrase et les données ; les sauvegardes précédentes sont conservées.'


def _manifest(package, extras, security):
    items = {**{'files/' + k: v for k, v in package['files'].items()},
             **{'extras/' + k: v for k, v in extras.items()},
             **{'security/' + k: v for k, v in security.items()}}
    return {name: {'bytes': len(_canonical(value)), 'sha256': hashlib.sha256(_canonical(value)).hexdigest()}
            for name, value in sorted(items.items())}


class BackupManager:
    def __init__(self, controller):
        self.controller = controller
        self.home = Path(controller.home)
        self.directory = self.home / 'sauvegardes'
        private_directory(self.directory)
        self.path = self.directory / 'catalogue.json'
        self.secret_path = self.directory / 'automatisation.dpapi'
        self.lock = threading.RLock()
        self.gate = threading.Lock()
        self.exclusive_owner = None
        self.closed = threading.Event()
        self.thread = None
        self.last_retry_check = 0
        default = {'version': 1, 'config': {'enabled': False, 'time': '03:00', 'frequency': 'daily',
                   'weekday': 0, 'destination': str(self.directory.resolve()), 'secondary_destination': '',
                   'retention': copy.deepcopy(DEFAULT_RETENTION)}, 'catalog': [], 'next_due': 0,
                   'last_success': 0, 'last_error': '', 'retry_due': 0,
                   'job': {'state': 'idle', 'phase': '', 'message': ''}}
        self.data = read_json(self.path, default)
        if not isinstance(self.data, dict) or self.data.get('version') != 1:
            raise ValueError('Catalogue de sauvegardes illisible ; conserver le fichier pour récupération.')
        self.data = {**default, **self.data}
        if not isinstance(self.data['catalog'], list) or not isinstance(self.data['config'], dict):
            raise ValueError('Catalogue de sauvegardes invalide.')
        if self.data['job'].get('state') == 'running':
            self.data['job'].update(state='failed', phase='interrupted', finished_at=_iso(time.time()),
                                    message='Sauvegarde interrompue par l’arrêt du serveur ; nouvel essai prévu.')
            self.data['last_error'] = self.data['job']['message']
            if self.data['job'].get('kind') == 'automatic': self.data['retry_due'] = time.time()
        # A completed atomic archive can precede the catalogue update after a power failure.
        self._reconcile()
        self._save()

    def _save(self):
        write_json(self.path, self.data)

    def _reconcile(self):
        destination = Path(self.data['config']['destination'])
        if not destination.is_dir(): return
        known = {record.get('file') for record in self.data['catalog']}
        for path in destination.glob('*.qwenbackup'):
            if str(path.resolve()) not in known:
                with path.open('rb') as stream: header = stream.read(11)
                if header not in (HEADER, LEGACY_HEADER) or path.stat().st_size > MAX_ARCHIVE: continue
                identity = path.stem.rsplit('-', 1)[1] if MANAGED_NAME.fullmatch(path.name) else hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:24]
                stamp = path.stat().st_mtime
                self.data['catalog'].append({'id': identity, 'file': str(path.resolve()),
                    'timestamp': stamp, 'created_at': _iso(stamp), 'kind': 'recovered', 'protected': True,
                    'version': 2 if header == HEADER else 1, 'size': path.stat().st_size, 'sha256': _hash_file(path), 'verified': False,
                    'summary': {'included': [], 'excluded': EXCLUDED, 'counts': {}},
                    'secondary': {'status': 'disabled', 'file': '', 'attempts': 0, 'error': ''}})

    @staticmethod
    def next_due(config, now):
        hour, minute = map(int, config['time'].split(':'))
        current = dt.datetime.fromtimestamp(now)
        due = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if config['frequency'] == 'weekly':
            due += dt.timedelta(days=(config['weekday'] - due.weekday()) % 7)
            if due.timestamp() <= now: due += dt.timedelta(days=7)
        elif due.timestamp() <= now: due += dt.timedelta(days=1)
        return due.timestamp()

    def status(self):
        with self.lock:
            result = copy.deepcopy(self.data)
        result['config']['secret_configured'] = self.secret_path.exists()
        result['next_run'] = _iso(result.pop('next_due', 0)) if result['config']['enabled'] else ''
        result['last_success'] = _iso(result['last_success'])
        result.pop('retry_due', None)
        result['catalog'] = sorted(result['catalog'], key=lambda r: r['timestamp'], reverse=True)
        result['recovery_phrase_required'] = result['config']['enabled'] and not self.secret_path.exists()
        result['server_required'] = True
        return result

    def configure(self, data):
        if not isinstance(data, dict): raise ValueError('Paramètres de sauvegarde attendus.')
        with self.lock:
            if (self.gate.locked() or getattr(self.controller.remote, 'maintenance', False)) and self.exclusive_owner != threading.get_ident():
                raise ValueError('Attendre la sauvegarde en cours avant de modifier sa programmation.')
            cfg = copy.deepcopy(self.data['config'])
            for name in ('enabled', 'time', 'frequency', 'weekday', 'destination', 'secondary_destination', 'retention'):
                if name in data: cfg[name] = copy.deepcopy(data[name])
            if type(cfg['enabled']) is not bool: raise ValueError('Activation de sauvegarde invalide.')
            if not isinstance(cfg['time'], str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', cfg['time']):
                raise ValueError('Heure de sauvegarde attendue au format HH:MM.')
            if cfg['frequency'] not in ('daily', 'weekly') or type(cfg['weekday']) is not int or not 0 <= cfg['weekday'] <= 6:
                raise ValueError('Fréquence de sauvegarde invalide.')
            if not isinstance(cfg['retention'], dict) or set(cfg['retention']) != set(DEFAULT_RETENTION):
                raise ValueError('Conservation quotidienne, hebdomadaire et mensuelle attendue.')
            if any(type(value) is not int or not 0 <= value <= 365 for value in cfg['retention'].values()):
                raise ValueError('Conservation attendue entre 0 et 365 points par catégorie.')
            for name in ('destination', 'secondary_destination'):
                if not isinstance(cfg[name], str) or len(cfg[name]) > 2048: raise ValueError('Destination de sauvegarde invalide.')
                if not cfg[name] and name == 'secondary_destination': continue
                target = Path(cfg[name])
                if not target.is_absolute(): raise ValueError('Choisir un dossier de sauvegarde avec un chemin absolu.')
                cfg[name] = str(target.resolve())
            if cfg['secondary_destination'] and cfg['secondary_destination'] == cfg['destination']:
                raise ValueError('La seconde copie nécessite un dossier différent.')
            password = data.get('password')
            if password:
                cipher(password, b'\x00' * 16)  # Same recovery-phrase limits as the portable format.
            if cfg['enabled'] and not password and not self.secret_path.exists():
                raise ValueError('Définir une phrase de récupération avant d’activer les sauvegardes automatiques.')
            # The encrypted second copy may target a disconnected NAS. It is retried later.
            private_directory(Path(cfg['destination']))
            previous_secret = self.secret_path.read_bytes() if self.secret_path.exists() else None
            try:
                if password: _atomic_bytes(self.secret_path, protect(password.encode('utf-8')))
                previous = self.data
                self.data = {**self.data, 'config': cfg,
                             'next_due': self.next_due(cfg, time.time()) if cfg['enabled'] else 0,
                             'retry_due': 0}
                self._save()
            except Exception:
                if 'previous' in locals(): self.data = previous
                if previous_secret is None: self.secret_path.unlink(missing_ok=True)
                else: _atomic_bytes(self.secret_path, previous_secret)
                raise
        return self.status()

    def _capture(self):
        c = self.controller
        with c.operations.hermes_snapshot(), c.lock, c.wireguard.lock, c.remote.lock, c.remote.accounts.lock, c.remote.workspace.lock:
            files = {name: _read_json_checked(self.home / name) for name in FILES if (self.home / name).exists()}
            registered = registered_profile_ids(files)
            if c.wireguard.vault_path.exists(): files['vault'] = c.wireguard.vault()
            saved = c.wireguard.directory / 'profils-restaures.dpapi'
            profiles = json.loads(protect(saved.read_bytes(), decrypt=True)) if saved.exists() else {}
            if not isinstance(profiles, dict): raise ValueError('Registre des profils personnels illisible.')
            profiles = {identity: profile for identity, profile in profiles.items() if identity in registered}
            signing = c.wireguard.directory / 'signature.dpapi'
            if signing.exists(): files['signing_seed'] = base64.b64encode(protect(signing.read_bytes(), decrypt=True)).decode()
            clients = self.home / 'clients'
            if clients.exists():
                for path in clients.iterdir():
                    if not re.fullmatch(r'[0-9a-f]{16}', path.stem): continue
                    if path.stem not in registered: continue
                    if path.suffix == '.fred-android': profiles[path.stem] = _read_json_checked(path, 65536)
                    elif path.suffix == '.exe' and path.stat().st_size >= 16:
                        with path.open('rb') as stream:
                            stream.seek(-16, 2); footer = stream.read(16)
                            if footer[4:] != b'QWENPROFILE1': continue
                            size = struct.unpack('<I', footer[:4])[0]
                            if not 0 < size <= 65536 or size + 16 > path.stat().st_size:
                                raise ValueError('Profil personnel à sauvegarder invalide.')
                            stream.seek(-16 - size, 2); profiles[path.stem] = json.loads(stream.read(size))
            files['profiles'] = profiles
            files['workspace'] = c.remote.workspace.backup()
            hermes = c.operations.hermes_export(registered)
            if hermes is not None: files['hermes'] = hermes
            web_key = self.home / 'recherche-web.dpapi'
            if web_key.exists(): files['web_key'] = base64.b64encode(protect(web_key.read_bytes(), decrypt=True)).decode()
            extras = {name: _read_json_checked(self.home / name) for name in EXTRA_FILES if name not in FILES and (self.home / name).exists()}
            # Portable policy, never the machine-bound DPAPI secret or running-job catalogue.
            extras['sauvegardes-planification.json'] = copy.deepcopy(self.data['config'])
            security = {}
            ledger = self.home / 'securite' / 'revocations.json'
            if ledger.exists(): security['revocations.json'] = _read_json_checked(ledger)
            from server_state import installation_id
            security['installation_id'] = installation_id(self.home)
        return {'version': 1, 'files': files}, extras, security

    def _summary(self, package, extras, security, version, created_at=''):
        from restoration import validate_package
        validate_package(self.controller, package)
        if 'revocations.json' in security:
            from devices import Revocations
            Revocations.validate(security['revocations.json'])
        if 'installation_id' in security and (not isinstance(security['installation_id'], str) or not re.fullmatch('[0-9a-f]{32}', security['installation_id'])):
            raise ValueError('Origine de sauvegarde invalide.')
        if 'derniers-reglages-valides.json' in extras:
            from core import validate
            validate(extras['derniers-reglages-valides.json'])
        activity = extras.get('appareils-activite.json', {})
        if not isinstance(activity, dict) or len(activity) > 10000 or any(not isinstance(key, str) or not re.fullmatch('[0-9a-f]{16}', key) or not isinstance(value, dict) for key, value in activity.items()):
            raise ValueError('Activité des appareils sauvegardée invalide.')
        policy = extras.get('sauvegardes-planification.json')
        if policy is not None:
            if (not isinstance(policy, dict) or type(policy.get('enabled')) is not bool
                or not isinstance(policy.get('time'), str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', policy['time'])
                or policy.get('frequency') not in ('daily', 'weekly')
                or type(policy.get('weekday')) is not int or not 0 <= policy['weekday'] <= 6
                or not isinstance(policy.get('retention'), dict) or set(policy['retention']) != set(DEFAULT_RETENTION)
                or any(type(value) is not int or not 0 <= value <= 365 for value in policy['retention'].values())):
                raise ValueError('Programmation sauvegardée invalide.')
        files = package['files']
        counts = {'profiles': len(files.get('profiles', {})), 'accounts': len(files.get('comptes.json', []))}
        if 'hermes' in files:
            counts['hermes_files'] = len(files['hermes']['files'])
            counts['hermes_profiles'] = len({name.split('/')[1] for name in files['hermes']['files'] if name.startswith('profiles/')})
        if 'workspace' in files:
            access = files.get('acces-distants.json', {})
            owners = {r['id'] for r in access.get('clients', []) + access.get('deleted_clients', [])}
            raw = self.controller.remote.workspace.validate_backup(files['workspace'], owners)
            memory = sqlite3.connect(':memory:')
            try:
                memory.deserialize(raw)
                for table in ('projects', 'documents', 'memories', 'conversations', 'jobs', 'client_histories', 'policies'):
                    counts[table] = memory.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
                counts['document_original_bytes'] = memory.execute('SELECT COALESCE(SUM(length(original)),0) FROM documents').fetchone()[0]
                tables = {row[0] for row in memory.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                for table in ('document_sources', 'notifications', 'notification_preferences', 'notification_subscriptions', 'personal_memories', 'knowledge_exclusions'):
                    if table in tables:
                        counts[table] = memory.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
            finally: memory.close()
        # Profiles are secrets. Validate correlation but expose only their number.
        from profiles import validate_access, match, public_key
        if 'acces-distants.json' in files:
            access = validate_access(files['acces-distants.json'])
            records = {r['id']: r for r in access['clients'] + access.get('deleted_clients', [])}
            server_key = files.get('wireguard.json', {}).get('public_key')
            for identity, profile in files.get('profiles', {}).items():
                if identity not in records: raise ValueError('Profil sauvegardé sans destinataire enregistré.')
                psk = files.get('vault', {}).get('peers', {}).get(identity)
                if psk is None: raise ValueError('Clé partagée absente du coffre sauvegardé.')
                match(records[identity], profile, server_key, psk)
            if files.get('vault') and server_key and public_key(files['vault']['private_key']) != server_key:
                raise ValueError('Coffre incompatible avec la configuration WireGuard.')
        return {'version': version, 'created_at': created_at, 'counts': counts,
                'included': sorted(list(files) + list(extras)), 'excluded': copy.deepcopy(EXCLUDED),
                'revocation_ledger': 'revocations.json' in security, 'verified': True,
                'effects': ['Restauration complète des données du serveur',
                            'Accès distant désactivé et sessions invalidées',
                            'Tâches en attente : relance manuelle nécessaire',
                            'Révocations actuelles conservées ; programmation restaurée désactivée']}

    def _decode(self, blob, password, key=None):
        if len(blob) > MAX_ARCHIVE or len(blob) < 28: raise ValueError('Sauvegarde trop volumineuse ou tronquée.')
        version = 2 if blob.startswith(HEADER) else 1 if blob.startswith(LEGACY_HEADER) else 0
        if not version: raise ValueError('Format de sauvegarde invalide.')
        try:
            document = json.loads((key or cipher(password, blob[11:27])).decrypt(blob[27:]))
        except (InvalidToken, ValueError, UnicodeError, TypeError):
            raise ValueError('Sauvegarde invalide ou phrase incorrecte.') from None
        if not isinstance(document, dict): raise ValueError('Contenu de sauvegarde invalide.')
        if version == 2:
            package = document.get('package'); extras = document.get('extras', {}); security = document.get('security', {})
            if document.get('version') != 2 or not isinstance(extras, dict) or not isinstance(security, dict):
                raise ValueError('Contenu de sauvegarde invalide.')
            if set(extras) - set(EXTRA_FILES + ('sauvegardes-planification.json',)) or set(security) - {'revocations.json', 'installation_id'}:
                raise ValueError('Configuration supplémentaire inconnue.')
        else: package = document; extras = {}; security = {}
        if not isinstance(package, dict) or package.get('version') != 1 or not isinstance(package.get('files'), dict):
            raise ValueError('Contenu de sauvegarde invalide.')
        if set(package['files']) - set(FILES + ['vault', 'profiles', 'signing_seed', 'workspace', 'web_key', 'hermes']):
            raise ValueError('Fichier de sauvegarde inconnu.')
        if version == 2 and document.get('manifest') != _manifest(package, extras, security):
            raise ValueError('Manifeste de sauvegarde endommagé.')
        summary = self._summary(package, extras, security, version, document.get('created_at', ''))
        return {'summary': summary, 'package': package, 'extras': extras, 'security': security}

    def resolve(self, data):
        if not isinstance(data, dict): raise ValueError('Sauvegarde à sélectionner.')
        if data.get('id'):
            with self.lock:
                record = next((r for r in self.data['catalog'] if r.get('id') == data['id']), None)
            if record is None: raise ValueError('Sauvegarde absente du catalogue.')
            return Path(record['file'])
        if not isinstance(data.get('file'), str) or not data['file']: raise ValueError('Choisir un fichier de sauvegarde.')
        path = Path(data['file'])
        if not path.is_absolute(): raise ValueError('Chemin de sauvegarde absolu attendu.')
        return path

    def inspect(self, data):
        path = self.resolve(data)
        # Bind the validated plaintext and public fingerprint to the same immutable bytes.
        with path.open('rb') as stream:
            if os.fstat(stream.fileno()).st_size > MAX_ARCHIVE: raise ValueError('Sauvegarde trop volumineuse.')
            blob = stream.read(MAX_ARCHIVE + 1)
        if len(blob) > MAX_ARCHIVE: raise ValueError('Sauvegarde trop volumineuse.')
        result = self._decode(blob, self.resolve_password(data))
        result['summary'].update(file=str(path.resolve()), size=len(blob), sha256=hashlib.sha256(blob).hexdigest())
        # Adoption is explicit: recovered archives are never retention candidates before verification.
        with self.lock:
            record = next((r for r in self.data['catalog'] if r.get('file') == str(path.resolve())), None)
            if record:
                record.update(verified=True, summary=result['summary'], sha256=result['summary']['sha256'])
                self._save()
        return result

    def resolve_password(self, data):
        """Internal only; callers must never include this result in an API response."""
        password = data.get('password') if isinstance(data, dict) else data
        if password: return password
        try: return protect(self.secret_path.read_bytes(), decrypt=True).decode('utf-8')
        except (OSError, UnicodeError): raise ValueError('Saisir la phrase de récupération de cette sauvegarde.') from None

    def setup_automatic(self):
        """Explicit operator setup; the response contains a private path, never the phrase."""
        recovery = self.directory / 'phrase-recuperation.txt'
        private_directory(self.directory)
        existing = self.resolve_password(None) if self.secret_path.exists() else None
        if recovery.exists():
            if recovery.stat().st_size > 8192: raise ValueError('Fichier de récupération trop volumineux.')
            password = recovery.read_text(encoding='utf-8')
            cipher(password, b'\x00' * 16)
            if existing is not None and not hmac.compare_digest(password.encode(), existing.encode()):
                raise ValueError('La phrase de récupération enregistrée ne correspond pas au secret automatique ; vérifier les fichiers avant activation.')
        else:
            password = existing if existing is not None else secrets.token_urlsafe(36)
            _atomic_bytes(recovery, password.encode('utf-8'))
        result = self.configure({'enabled': True, 'password': password})
        result['recovery_file'] = str(recovery.resolve())
        result['message'] = 'Sauvegardes automatiques activées. Conserver une copie indépendante du fichier de récupération privé.'
        return result

    @contextmanager
    def exclusive(self):
        """Coordinate a restoration with manual and scheduled backup workers."""
        if not self.gate.acquire(blocking=False): raise ValueError('Une opération de sauvegarde est déjà en cours.')
        self.exclusive_owner = threading.get_ident()
        try: yield
        finally:
            self.exclusive_owner = None
            self.gate.release()

    def register_legacy(self, file, kind='rollback', protected=True, password=None):
        path = Path(file).resolve()
        if not path.is_file() or path.stat().st_size > MAX_ARCHIVE: raise ValueError('Point de retour introuvable ou trop volumineux.')
        summary = self._decode(path.read_bytes(), self.resolve_password(password))['summary'] if password else {
            'counts': {}, 'included': [], 'excluded': copy.deepcopy(EXCLUDED)}
        timestamp = path.stat().st_mtime
        record = {'id': hashlib.sha256(str(path).encode()).hexdigest()[:24], 'file': str(path),
                  'timestamp': timestamp, 'created_at': _iso(timestamp), 'kind': kind, 'protected': bool(protected),
                  'version': 1, 'size': path.stat().st_size, 'sha256': _hash_file(path), 'verified': bool(password),
                  'summary': summary, 'secondary': {'status': 'disabled', 'file': '', 'attempts': 0, 'error': ''}}
        with self.lock:
            self.data['catalog'] = [r for r in self.data['catalog'] if r['file'] != str(path)] + [record]
            self._save()
        return copy.deepcopy(record)

    def _phase(self, phase, message):
        with self.lock:
            if self.data['job'].get('state') == 'running':
                self.data['job'].update(phase=phase, message=message)
                self._save()

    def _create(self, password, kind='manual', protected=False):
        if kind not in ('manual', 'automatic', 'rollback', 'pre_restore'): raise ValueError('Type de sauvegarde invalide.')
        salt = secrets.token_bytes(16); key = cipher(password, salt)
        self._phase('snapshot', 'Instantané cohérent des données et des réglages.')
        package, extras, security = self._capture()
        timestamp = time.time()
        created = _iso(timestamp)
        summary = self._summary(package, extras, security, 2, created)
        document = {'version': 2, 'server_version': VERSION, 'created_at': created,
                    'package': package, 'extras': extras, 'security': security,
                    'manifest': _manifest(package, extras, security)}
        raw = _canonical(document)
        with self.lock: destination = Path(self.data['config']['destination'])
        private_directory(destination)
        if shutil.disk_usage(destination).free < len(raw) * 2 + 1024 * 1024:
            raise OSError(errno.ENOSPC, 'Sauvegarde')
        self._phase('encrypt', 'Chiffrement de l’archive portable.')
        blob = HEADER + salt + key.encrypt(raw)
        if len(blob) > MAX_ARCHIVE: raise ValueError('Sauvegarde trop volumineuse.')
        identity = secrets.token_hex(12)
        target = destination / ('fred-' + dt.datetime.fromtimestamp(timestamp).strftime('%Y%m%d-%H%M%S') + '-' + identity + '.qwenbackup')
        temporary = target.with_suffix('.verification.tmp')
        try:
            _atomic_bytes(temporary, blob)
            self._phase('verify', 'Vérification du chiffrement, du manifeste et de la base SQLite.')
            self._decode(temporary.read_bytes(), password, key=key)
            digest = hashlib.sha256(blob).hexdigest()
            if _hash_file(temporary) != digest: raise ValueError('Archive modifiée pendant sa vérification.')
            os.replace(temporary, target)
        finally: temporary.unlink(missing_ok=True)
        record = {'id': identity, 'file': str(target.resolve()), 'timestamp': timestamp, 'created_at': created,
                  'kind': kind, 'protected': bool(protected or kind in ('rollback', 'pre_restore')), 'version': 2,
                  'size': len(blob), 'sha256': digest, 'verified': True, 'summary': summary,
                  'secondary': {'status': 'disabled', 'file': '', 'attempts': 0, 'error': ''}}
        with self.lock:
            secondary = self.data['config']['secondary_destination']
            if secondary: record['secondary'].update(status='pending', next_retry=0, destination=secondary)
            self.data['catalog'].append(record)
            self.data.update(last_success=timestamp, last_error='')
            self._save()
        if secondary:
            self._phase('copy', 'Création de la seconde copie chiffrée.')
            self._copy(record)
        self._phase('retention', 'Conservation des points vérifiés et des points de retour.')
        self.prune()
        return {'id': identity, 'file': str(target.resolve()), 'message': 'Sauvegarde chiffrée créée et vérifiée.',
                'secondary': copy.deepcopy(record['secondary'])}

    def create(self, password, kind='manual', protected=False):
        if getattr(self.controller.remote, 'maintenance', False): raise ValueError('Serveur en maintenance ; sauvegarde suspendue.')
        if not self.gate.acquire(blocking=False): raise ValueError('Une opération de sauvegarde est déjà en cours.')
        try: return self._create(password, kind, protected)
        except Exception as error: raise ValueError(_message(error)) from None
        finally: self.gate.release()

    def start(self, data):
        if self.closed.is_set(): raise ValueError('Le service de sauvegardes est arrêté.')
        if getattr(self.controller.remote, 'maintenance', False): raise ValueError('Serveur en maintenance ; sauvegarde suspendue.')
        if not isinstance(data, dict): raise ValueError('Paramètres de sauvegarde attendus.')
        password = self.resolve_password(data)
        cipher(password, b'\x00' * 16)
        if not self.gate.acquire(blocking=False): raise ValueError('Une opération de sauvegarde est déjà en cours.')
        try:
            with self.lock:
                self.data['job'] = {'id': secrets.token_hex(12), 'state': 'running', 'phase': 'waiting',
                    'message': 'Sauvegarde démarrée côté serveur.', 'started_at': _iso(time.time()),
                    'finished_at': '', 'kind': data.get('kind', 'manual')}
                self._save()
            self.thread = threading.Thread(target=self._worker, args=(password, data.get('kind', 'manual'), bool(data.get('protected', False))),
                                           name='fred-backup', daemon=True)
            self.thread.start()
        except Exception:
            self.gate.release(); raise
        return self.status()

    def _worker(self, password, kind, protected):
        try:
            result = self._create(password, kind, protected)
            with self.lock:
                self.data['job'].update(state='succeeded', phase='complete', message=result['message'], result=result, finished_at=_iso(time.time()))
                self.data['retry_due'] = 0
                self._save()
        except Exception as error:
            with self.lock:
                message = _message(error)
                self.data['job'].update(state='failed', phase='failed', message=message, finished_at=_iso(time.time()))
                self.data['last_error'] = message
                if kind == 'automatic': self.data['retry_due'] = time.time() + 300
                self._save()
        finally:
            password = None
            self.gate.release()

    def _copy(self, record):
        secondary = record['secondary']
        secondary['attempts'] += 1
        source = Path(record['file'])
        destination = Path(secondary['destination'])
        target = destination / source.name
        temporary = target.with_suffix('.copy.tmp')
        try:
            # No plaintext is written on the NAS. Failure cannot invalidate the local archive.
            destination.mkdir(parents=True, exist_ok=True)
            if _hash_file(source) != record['sha256']: raise ValueError('Archive source endommagée.')
            if shutil.disk_usage(destination).free < record['size'] + 1024 * 1024: raise OSError(errno.ENOSPC, 'Seconde copie')
            with source.open('rb') as reader, temporary.open('wb') as writer:
                shutil.copyfileobj(reader, writer, 1024 * 1024); writer.flush(); os.fsync(writer.fileno())
            if _hash_file(temporary) != record['sha256'] or temporary.stat().st_size != record['size']:
                raise ValueError('Seconde copie endommagée.')
            os.replace(temporary, target)
            secondary.update(status='copied', file=str(target.resolve()), error='', next_retry=0)
        except Exception as error:
            secondary.update(status='error', error='Seconde copie non réalisée. La sauvegarde locale reste valide.',
                             next_retry=time.time() + min(3600, 60 * 2 ** min(secondary['attempts'], 6)))
        finally:
            try: temporary.unlink(missing_ok=True)
            except OSError: pass
            with self.lock: self._save()

    def prune(self):
        with self.lock:
            candidates = sorted([r for r in self.data['catalog'] if r.get('verified') and r.get('kind') == 'automatic'],
                                key=lambda r: r['timestamp'], reverse=True)
            if not candidates: return []
            keep = {candidates[0]['id']}
            rules = self.data['config']['retention']
            for category, count in rules.items():
                buckets = []
                for record in candidates:
                    stamp = dt.datetime.fromtimestamp(record['timestamp'])
                    bucket = stamp.strftime('%Y-%m-%d') if category == 'daily' else stamp.strftime('%G-%V') if category == 'weekly' else stamp.strftime('%Y-%m')
                    if bucket not in buckets and len(buckets) < count:
                        buckets.append(bucket); keep.add(record['id'])
            removed = []
            for record in candidates:
                if record['id'] in keep or record.get('protected'): continue
                # A failed copy remains eligible for retries; never delete its sole source.
                if record.get('secondary', {}).get('status') in ('pending', 'error'): continue
                path = Path(record['file'])
                if not MANAGED_NAME.fullmatch(path.name): continue
                try:
                    if path.exists() and _hash_file(path) != record['sha256']: continue
                    secondary = record.get('secondary', {})
                    second_path = Path(secondary['file']) if secondary.get('file') else None
                    if second_path and (second_path.name != path.name or not MANAGED_NAME.fullmatch(second_path.name)): continue
                    path.unlink(missing_ok=True)
                    if second_path and second_path.exists() and _hash_file(second_path) == record['sha256']:
                        second_path.unlink()
                    self.data['catalog'].remove(record); removed.append(record['id'])
                except OSError:
                    self.data['last_error'] = 'Nettoyage incomplet ; certains points précédents sont conservés.'
            if removed: self._save()
            return removed

    def tick(self, now=None):
        if self.closed.is_set(): return False
        if getattr(self.controller.remote, 'maintenance', False): return False
        now = time.time() if now is None else now
        if self.gate.locked(): return False
        with self.lock:
            cfg = copy.deepcopy(self.data['config'])
            due = self.data['retry_due'] or self.data['next_due']
        if cfg['enabled'] and due and now >= due:
            try:
                password = protect(self.secret_path.read_bytes(), decrypt=True).decode('utf-8')
                with self.lock:
                    self.data['next_due'] = self.next_due(cfg, now)
                    self.data['retry_due'] = 0
                    self._save()
                self.start({'password': password, 'kind': 'automatic'})
                return True
            except Exception as error:
                with self.lock:
                    self.data['last_error'] = 'Sauvegarde automatique indisponible : vérifier la phrase protégée et la destination.'
                    self.data['retry_due'] = now + 300
                    self._save()
                return False
        if now - self.last_retry_check < 30: return False
        self.last_retry_check = now
        if not self.gate.acquire(blocking=False): return False
        try:
            with self.lock:
                pending = [r for r in self.data['catalog'] if r.get('verified') and r.get('secondary', {}).get('status') in ('pending', 'error')
                           and r['secondary'].get('next_retry', 0) <= now]
            if pending:
                self.thread = threading.Thread(target=self._retry_copy, args=(pending[0],), name='fred-backup-copy', daemon=True)
                self.thread.start()
                return True
        except Exception:
            self.gate.release(); raise
        if not pending: self.gate.release()
        return False

    def _retry_copy(self, record):
        try: self._copy(record); self.prune()
        finally: self.gate.release()

    def close(self, timeout=10):
        self.closed.set()
        if self.thread and self.thread is not threading.current_thread(): self.thread.join(timeout)

