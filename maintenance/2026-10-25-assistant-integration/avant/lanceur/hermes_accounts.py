"""Kiara-owned, resumable Hermes profiles and Windows-protected service credentials.

The installed Hermes home is never read or cloned. Profile .env files are a private
runtime projection required by the native multiplexer; the durable authority is
the DPAPI blob in Kiara's registry. They are removed when the supervised service stops.
"""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import tempfile
import time
from urllib.parse import urlsplit

from core import HOME, write_json
from wg_crypto import protect, private_directory

CONFIG_VERSION = 5
_OWNER = re.compile(r'[a-z0-9][a-z0-9_-]{0,55}\Z')
_STATES = {'provisioning', 'ready', 'error', 'suspended', 'revoked', 'archived'}


def profile_name(owner):
    if not isinstance(owner, str) or not _OWNER.fullmatch(owner):
        raise ValueError('Identité d’accès Kiara invalide.')
    return 'fred-' + owner


def _local_url(value, label):
    parsed = urlsplit(str(value))
    if (parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', '::1'}
            or not parsed.port or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError(f'{label} doit désigner un service HTTP privé local.')
    return str(value).rstrip('/')


def _digest(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


class HermesAccounts:
    def __init__(self, home=HOME, inference_url='http://127.0.0.1:8768/v1',
                 mcp_url='http://127.0.0.1:8768/mcp', model='fred-qwen', *,
                 authorized=None, profile_factory=None, protector=protect,
                 protect_directory=private_directory):
        self.home = Path(home)
        self.root = self.home / 'hermes-fred'
        self.path = self.root / 'fred-integration.db'
        self.inference_url = _local_url(inference_url, 'L’inférence Hermes')
        self.mcp_url = _local_url(mcp_url, 'Les outils Hermes') if mcp_url else ''
        self.model = str(model)
        if not self.model or len(self.model) > 128 or any(ord(c) < 32 for c in self.model):
            raise ValueError('Alias de modèle Hermes invalide.')
        self.authorized = authorized or (lambda owner: True)
        self.profile_factory = profile_factory
        self.protector = protector
        self.protect_directory = protect_directory
        self.lock = threading.RLock()
        self.models = None
        if self.root.exists() and self.root.resolve() != self.root.absolute():
            raise ValueError('La racine Hermes Kiara doit être un dossier privé réel.')
        protect_directory(self.root)
        with self._db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS hermes_bindings (
                    owner TEXT PRIMARY KEY, profile TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL, config_version INTEGER NOT NULL DEFAULT 0,
                    secrets BLOB NOT NULL, inference_hash TEXT NOT NULL UNIQUE,
                    tool_hash TEXT NOT NULL UNIQUE, attempts INTEGER NOT NULL DEFAULT 0,
                    error TEXT NOT NULL DEFAULT '', updated REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS hermes_settings (
                    name TEXT PRIMARY KEY, secret BLOB NOT NULL);
            ''')

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA busy_timeout=15000')
        try:
            with db:
                yield db
        finally:
            db.close()

    def _seal(self, value):
        return self.protector(json.dumps(value, separators=(',', ':')).encode())

    def _unseal(self, value):
        return json.loads(self.protector(bytes(value), decrypt=True))

    def gateway_key(self):
        with self.lock, self._db() as db:
            row = db.execute('SELECT secret FROM hermes_settings WHERE name=?', ('gateway_key',)).fetchone()
            if row:
                return self._unseal(row['secret'])['key']
            key = secrets.token_urlsafe(48)
            db.execute('INSERT INTO hermes_settings VALUES (?,?)', ('gateway_key', self._seal({'key': key})))
            return key

    def _row(self, owner):
        profile_name(owner)
        with self._db() as db:
            return db.execute('SELECT * FROM hermes_bindings WHERE owner=?', (owner,)).fetchone()

    def credentials(self, owner):
        row = self._row(owner)
        if not row:
            raise ValueError('Profil Hermes non provisionné.')
        return {'profile': row['profile'], **self._unseal(row['secrets'])}

    def public(self, owner):
        row = self._row(owner)
        if not row:
            return {'state': 'missing', 'ready': False, 'profile': profile_name(owner), 'config_version': 0}
        return {key: row[key] for key in ('profile', 'state', 'config_version', 'attempts', 'error')} | {
            'ready': row['state'] == 'ready' and row['config_version'] == CONFIG_VERSION}

    def enabled(self, owner):
        return self.public(owner)['ready'] and bool(self.authorized(owner))

    def authenticate_private(self, token, kind):
        column = {'inference': 'inference_hash', 'tool': 'tool_hash', 'mcp': 'tool_hash'}.get(kind)
        if not column or not isinstance(token, str) or not 24 <= len(token) <= 256:
            return None
        with self._db() as db:
            row = db.execute(f'SELECT owner,state,config_version FROM hermes_bindings WHERE {column}=?',
                             (_digest(token),)).fetchone()
        if row and row['state'] == 'ready' and row['config_version'] == CONFIG_VERSION and self.authorized(row['owner']):
            return row['owner']
        return None

    def config(self, owner=None, port=8643, selection=None):
        tools = ['memory', 'skills', 'todo'] if owner else []
        if owner and self.mcp_url: tools.append('web')
        config = {
            'model': {'default': self.model, 'provider': 'custom', 'base_url': self.inference_url,
                      'api_mode': 'chat_completions', 'key_env': 'FRED_INFERENCE_KEY',
                      'context_length': 262144},
            'agent': {'max_turns': 12, 'run_budget_seconds': 900, 'gateway_timeout': 900,
                      'local_stream_stale_timeout': 900},
            'platforms': {'api_server': {'enabled': True, 'host': '127.0.0.1', 'port': port}},
            'gateway': {'multiplex_profiles': True, 'auto_multiplex_migration': False,
                        'allow_all_users': False, 'honor_system_proxy': False,
                        'api_server': {'max_concurrent_runs': 4}},
            'platform_toolsets': {'api_server': tools},
            'memory': {'provider': 'builtin'},
            'security': {'allow_lazy_installs': False},
            'skills': {'inline_shell': False},
            'curator': {'enabled': False},
            'smart_model_routing': {'enabled': False},
            'fallback_model': None,
            'compression': {'enabled': True},
            'display': {'interim_assistant_messages': True},
            'terminal': {'cwd': str(self.root / 'profiles' / profile_name(owner) / 'workspace') if owner else str(self.root)},
        }
        # Follow only the selected run's main route, with no other-provider fallback.
        # Main credentials are minted centrally; personal refresh tokens are never cloned.
        config['auxiliary'] = {name: {'provider': 'main', 'timeout': 900, 'fallback_chain': []}
                               for name in ('compression', 'vision', 'approval', 'mcp', 'skills_hub',
                                            'curator', 'title_generation', 'memory_query_rewrite')}
        config['auxiliary']['title_generation'].update(enabled=False, model_upgrade_enabled=False)
        config['auxiliary']['refine'] = {'enabled': False}
        if selection:
            # The auxiliary main route is explicit, so native Hermes' auto mode
            # otherwise replaces images with a lossy auxiliary description.
            config['agent']['image_input_mode'] = 'native' if selection.get('capabilities',{}).get('images') else 'text'
            config['model']['supports_vision'] = selection.get('capabilities',{}).get('images') is True
        if selection and not selection.get('local'):
            # Some native auxiliary entry points do not receive main_runtime.
            # An explicit named route keeps them on this account's selected
            # provider, with key_cmd rather than copying a provider credential.
            for name,value in config['auxiliary'].items():
                if name!='refine':value.update(provider=selection['native_provider'],
                    model=selection['native_model'],api_mode=selection['api_mode'])
        if owner and self.mcp_url:
            config['mcp_servers'] = {'fred': {'url': self.mcp_url,
                'headers': {'Authorization': 'Bearer ${FRED_TOOL_KEY}'}, 'connect_timeout': 10,
                'request_timeout': 60}}
        if owner and self.models:config.update(self.models.profile_config(owner,request_id=selection.get('_fred_request_id') if selection else None))
        return config

    def _write_env(self, directory, values):
        path = directory / '.env'
        if path.is_symlink():
            raise ValueError('Projection des secrets Hermes invalide.')
        raw = ''.join(f'{name}={value}\n' for name, value in values.items())
        descriptor, name = tempfile.mkstemp(prefix='.fred-env-', suffix='.tmp', dir=directory)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    def materialize(self, owner, port=8643, selection=None):
        with self.lock:
            credentials = self.credentials(owner)
            directory = self.root / 'profiles' / credentials['profile']
            self._check_profile_directory(directory)
            if (not directory.is_dir() or directory.is_symlink()
                    or directory.resolve().parent != (self.root.resolve() / 'profiles')):
                raise ValueError('Dossier de profil Hermes indisponible.')
            write_json(directory / 'config.yaml', self.config(owner, port,selection))
            self._write_env(directory, {'API_SERVER_KEY': credentials['api_key'],
                                       'FRED_INFERENCE_KEY': credentials['inference_key'],
                                       'FRED_TOOL_KEY': credentials['tool_key'],
                                       'FRED_WEB_URL': self.mcp_url,
                                       'FRED_PROVIDER_URL': self.inference_url+'/provider/credential'})
            return directory

    def _check_profile_directory(self, directory):
        profiles = self.root / 'profiles'
        if profiles.exists() and (profiles.is_symlink() or profiles.resolve() != self.root.resolve() / 'profiles'):
            raise ValueError('Répertoire de profils Hermes invalide.')
        if directory.exists() and (directory.is_symlink() or directory.resolve().parent != self.root.resolve() / 'profiles'):
            raise ValueError('Dossier de profil Hermes invalide.')

    def ensure(self, owner, name='', *, port=8643):
        """Idempotently provision one native profile; does not start Hermes or the model."""
        profile = profile_name(owner)
        with self.lock:
            row = self._row(owner)
            if row and row['state'] in {'revoked', 'archived'}:
                return self.public(owner)
            if not self.authorized(owner):
                if row:
                    self.set_state(owner, 'suspended')
                return self.public(owner)
            directory = self.root / 'profiles' / profile
            if (row and row['state'] == 'ready' and row['config_version'] == CONFIG_VERSION
                    and directory.is_dir() and not directory.is_symlink()
                    and directory.resolve().parent == self.root.resolve() / 'profiles'
                    and (directory / 'config.yaml').is_file() and (directory / '.env').is_file()):
                return self.public(owner)
            if not row:
                credentials = {kind: secrets.token_urlsafe(48)
                               for kind in ('api_key', 'inference_key', 'tool_key')}
                with self._db() as db:
                    db.execute('INSERT INTO hermes_bindings(owner,profile,state,secrets,inference_hash,tool_hash,updated) VALUES (?,?,?,?,?,?,?)',
                               (owner, profile, 'provisioning', self._seal(credentials),
                                _digest(credentials['inference_key']), _digest(credentials['tool_key']), time.time()))
            with self._db() as db:
                db.execute('UPDATE hermes_bindings SET state=?,attempts=attempts+1,error=?,updated=? WHERE owner=?',
                           ('provisioning', '', time.time(), owner))
            try:
                self._check_profile_directory(directory)
                if self.profile_factory:
                    self.profile_factory(self, owner, port)
                else:
                    from hermes_service import create_native_profile
                    create_native_profile(self, owner, port)
                self.materialize(owner, port)
                with self._db() as db:
                    db.execute('UPDATE hermes_bindings SET state=?,config_version=?,error=?,updated=? WHERE owner=?',
                               ('ready', CONFIG_VERSION, '', time.time(), owner))
            except Exception:
                # Exceptions may contain credentials/provider details. Persist only the bounded stage.
                with self._db() as db:
                    db.execute('UPDATE hermes_bindings SET state=?,error=?,updated=? WHERE owner=?',
                               ('error', 'Création du profil Hermes incomplète ; reprise nécessaire.', time.time(), owner))
                raise ValueError('Création du profil Hermes incomplète ; reprise nécessaire.') from None
            return self.public(owner)

    def set_state(self, owner, state):
        if state not in _STATES:
            raise ValueError('État Hermes invalide.')
        with self.lock, self._db() as db:
            db.execute('UPDATE hermes_bindings SET state=?,updated=? WHERE owner=?', (state, time.time(), owner))
        return self.public(owner)

    def owners(self, ready_only=False):
        with self._db() as db:
            return [row['owner'] for row in db.execute('SELECT owner FROM hermes_bindings' +
                    (' WHERE state="ready"' if ready_only else '') + ' ORDER BY owner')]

    def migrate(self, clients, *, port=8643):
        report = {'ready': [], 'skipped': [], 'errors': []}
        for client in clients:
            owner = client['id']
            if (client.get('revoked') or client.get('suspended') or client.get('archived')
                    or not self.authorized(owner)
                    or (client.get('expires_epoch') and client['expires_epoch'] <= time.time())):
                report['skipped'].append(owner)
                row = self._row(owner)
                if row and row['state'] not in {'revoked', 'archived'}:
                    self.set_state(owner, 'revoked' if client.get('revoked') else 'archived' if client.get('archived') else 'suspended')
                continue
            try:
                value = self.ensure(owner, client.get('name', ''), port=port)
                report['ready' if value['ready'] else 'skipped'].append(owner)
            except ValueError:
                report['errors'].append(owner)
        return report

    def clear_runtime_secrets(self):
        with self.lock:
            if not self.path.is_file():
                return
            for directory in [self.root] + [self.root / 'profiles' / profile_name(owner) for owner in self.owners()]:
                if directory != self.root and (directory.is_symlink()
                        or directory.resolve().parent != self.root.resolve() / 'profiles'):
                    continue
                path = directory / '.env'
                if path.exists() and not path.is_symlink():
                    path.unlink()
