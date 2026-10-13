"""Private per-client files, automatically materialized from Fred's committed state.

The shared database retains transactional authority. Each dedicated directory is
a consistent standalone client database plus readable exports, never an input
that can silently overwrite live conversations or access permissions.
"""
import atexit
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import struct
import tempfile
import threading
import time
from core import read_json
from wg_crypto import private_directory, protect

TABLES = ('client_histories', 'projects', 'documents', 'chunks', 'memories',
          'policies', 'conversations', 'jobs', 'events', 'document_index',
          'document_sources', 'notifications', 'notification_preferences',
          'notification_subscriptions', 'notification_deliveries',
          'personal_memories', 'knowledge_exclusions')


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode('utf-8')


def checksum(raw): return hashlib.sha256(raw).hexdigest()


def atomic(path, raw):
    descriptor, name = tempfile.mkstemp(prefix='.' + path.name + '-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


class ClientStorage:
    def __init__(self, store):
        self.store = store; self.workspace = store.workspace
        self.root = store.home / 'donnees-clients'
        self.lock = threading.RLock(); self.gate = threading.Lock()
        self.dirty = threading.Event(); self.dirty.set()
        self.halt = threading.Event(); self.thread = None
        self.states = {}; self.error = ''; self.last_sync = None
        self.observed = {}
        self.pending_owners = None
        self.verified_at = {}
        self.workspace.storage_changed = self.changed
        atexit.register(self.close)

    def changed(self, owner=None):
        with self.lock:
            if owner is None: self.pending_owners = None
            elif self.pending_owners is not None: self.pending_owners.add(owner)
            self.dirty.set()

    def directory(self, identity):
        if not isinstance(identity, str) or not re.fullmatch('[0-9a-f]{16}', identity):
            raise ValueError('Identifiant du dossier client invalide.')
        path = self.root / identity
        self.safe(path)
        return path

    def safe(self, path):
        # Reject junctions/symlinks at every component, including the managed root.
        path = Path(path)
        try: relative = path.relative_to(self.root)
        except ValueError: raise ValueError('Chemin hors du stockage des clients.')
        if any(part in ('.', '..') for part in relative.parts) or not path.resolve().is_relative_to(self.root.resolve()):
            raise ValueError('Chemin hors du stockage des clients.')
        current = self.root
        for part in ('', *relative.parts):
            if part: current = current / part
            if current.is_symlink() or (current.exists() and getattr(current.lstat(), 'st_file_attributes', 0) & 0x400):
                raise ValueError('Lien de dossier interdit dans le stockage client.')
        return path

    def start(self):
        if self.thread and self.thread.is_alive(): return
        self.halt.clear()
        self.thread = threading.Thread(target=self.run, daemon=True, name='fred-client-storage')
        self.thread.start()

    def close(self):
        self.halt.set()
        if self.thread and self.thread is not threading.current_thread(): self.thread.join(timeout=2)

    def run(self):
        next_sync = 0
        while not self.halt.wait(.5):
            if self.workspace.maintenance: continue
            if self.dirty.is_set() or time.monotonic() >= next_sync:
                next_sync = time.monotonic() + 15
                try: self.synchronize(incremental=True)
                except (OSError, ValueError, sqlite3.Error):
                    with self.lock: self.error = 'Dossiers clients en attente : vérifier les droits et l’espace disque.'
                    self.halt.wait(2)

    def profile(self, record, saved):
        identity = record['id']; profile = saved.get(identity)
        if profile is None:
            path = self.store.home / 'clients' / (identity + '.fred-android')
            if path.is_file():
                if path.stat().st_size > 65536: raise ValueError('Profil trop volumineux.')
                profile = read_json(path)
            else:
                path = path.with_suffix('.exe')
                if path.is_file() and path.stat().st_size >= 16:
                    with path.open('rb') as stream:
                        stream.seek(-16, 2); footer = stream.read(16)
                        if footer[4:] == b'QWENPROFILE1':
                            length = struct.unpack('<I', footer[:4])[0]
                            if not 0 < length <= 65536 or length + 16 > path.stat().st_size:
                                raise ValueError('Profil personnel invalide.')
                            stream.seek(-16 - length, 2); profile = json.loads(stream.read(length))
        if profile is not None:
            from profiles import match
            match(record, profile)
            profile = {**profile, 'client_name': record['name']}
        return profile

    def snapshot(self, *, incremental=False, pending=None):
        # Same lock order as backup/restoration: access registry, then workspace.
        with self.store.lock, self.workspace.db() as db:
            registry = read_json(self.store.path)
            records = [(c, False) for c in registry['clients']] + [(c, True) for c in registry.get('deleted_clients', [])]
            revoked = self.store.revocations.snapshot()['revocations']
            from server_state import generation
            epoch = generation(self.store.home)['id']
            path = self.store.home / 'wireguard-prive/profils-restaures.dpapi'
            saved = json.loads(protect(path.read_bytes(), decrypt=True)) if path.is_file() else {}
            if not isinstance(saved, dict): raise ValueError('Registre des profils illisible.')
            result = []
            reset_id = db.execute("SELECT value FROM settings WHERE key='history_reset_id'").fetchone()[0]
            for client, archived in records:
                identity = client['id']
                metadata = self.store._public_device(client, revoked)
                metadata['archived'] = archived
                metadata.pop('storage', None)
                profile_file = self.store.home/'clients'/(identity+'.exe')
                profile_stamp = profile_file.stat().st_mtime_ns if profile_file.is_file() else 0
                token = (self.workspace.full_revision,self.workspace.owner_revisions.get(identity,0),
                         epoch,reset_id,checksum(encoded(metadata)),profile_stamp,path.stat().st_mtime_ns if path.is_file() else 0)
                if (incremental and pending is not None and identity not in pending and self.observed.get(identity)==token
                        and time.monotonic()-self.verified_at.get(identity,0)<300):
                    continue
                self.directory(client['id'])
                rows = {table: [dict(r) for r in db.execute('SELECT * FROM ' + table + ' WHERE owner=? ORDER BY rowid', (client['id'],))] for table in TABLES}
                job_ids = {row['id'] for row in rows['jobs']}
                settings = [dict(r) for r in db.execute('SELECT * FROM settings ORDER BY key')
                    if r['key'] == 'history_reset_id' or (r['key'].startswith('job_attempt:') and r['key'][12:] in job_ids)]
                result.append({'client': metadata, 'rows': rows, 'settings': settings,
                    'generation': epoch, 'profile': self.profile(client, saved), '_revision':token})
            return result

    @staticmethod
    def database(snapshot):
        from workspace import initialize_database
        db = sqlite3.connect(':memory:')
        try:
            initialize_database(db)
            for table in TABLES:
                for row in snapshot['rows'][table]:
                    names = list(row)
                    db.execute('INSERT INTO ' + table + '(' + ','.join(names) + ') VALUES(' + ','.join('?' for _ in names) + ')', list(row.values()))
            for row in snapshot['settings']: db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', (row['key'], row['value']))
            db.commit()
            return db.serialize()
        finally: db.close()

    def content(self, snapshot):
        rows = snapshot['rows']; files = {}
        def json_file(name, value): files[name] = encoded(value)
        client = snapshot['client']; owner = client['id']
        json_file('client.json', client)
        policy = json.loads(rows['policies'][0]['settings']) if rows['policies'] else {}
        from workspace import DEFAULT_LIMITS
        json_file('configuration.json', {'client': client, 'limites': {**DEFAULT_LIMITS, **policy},
            'preferences_notifications': rows['notification_preferences'], 'abonnements': rows['notification_subscriptions'],
            'configuration_locale': 'Les réglages et brouillons non synchronisés restent sur l’appareil.'})
        history = rows['client_histories'][0] if rows['client_histories'] else {'owner': owner, 'revision': 0, 'updated': None, 'history': '{"conversations":[],"currentId":""}'}
        json_file('historique.json', {**history, 'history': json.loads(history['history'])})
        for name, tables in [('memoires.json', ('memories', 'personal_memories')), ('taches.json', ('jobs',)),
            ('notifications.json', ('notifications', 'notification_deliveries')), ('evenements.json', ('events',)),
            ('references.json', ('document_sources', 'document_index', 'knowledge_exclusions'))]:
            json_file(name, {table: rows[table] for table in tables})
        for project in rows['projects']:
            json_file('projets/' + project['id'] + '/projet.json', project)
        for document in rows['documents']:
            prefix = 'projets/' + document['project'] + '/documents/' + document['id'] + '/'
            self.safe(self.directory(owner) / prefix)
            json_file(prefix + 'document.json', {k: v for k, v in document.items() if k not in ('original', 'text')})
            files[prefix + 'contenu.txt'] = document['text'].encode('utf-8')
            if document['original'] is not None:
                extension = document['kind'] if document['kind'] in ('pdf', 'docx', 'md', 'txt') else 'bin'
                files[prefix + 'original.' + extension] = document['original']
        conversations = {c['id']: {**c, 'messages': json.loads(c['messages'])} for c in rows['conversations']}
        for c in json.loads(history['history'])['conversations']:
            if c['id'] not in conversations: conversations[c['id']] = c
        for identity, conversation in conversations.items():
            json_file('conversations/' + checksum(identity.encode()) + '.json', conversation)
        files['donnees.sqlite3'] = self.database(snapshot)
        return files

    def publish(self, snapshot):
        identity = snapshot['client']['id']; directory = self.directory(identity)
        normalized = {**{k:v for k,v in snapshot.items() if k!='_revision'}, 'rows': {table: [{k: ('sha256:' + checksum(v)) if isinstance(v, bytes) else v for k, v in row.items()} for row in rows] for table, rows in snapshot['rows'].items()}}
        signature = checksum(encoded(normalized))
        previous = read_json(directory / 'dossier.json', {})
        if previous.get('signature') == signature:
            valid = True
            for name, expected in previous.get('files', {}).items():
                path = self.safe(directory / name)
                if not path.is_file() or checksum(path.read_bytes()) != expected: valid = False; break
            if valid and previous.get('files'):
                with self.lock: self.states[identity] = self.summary(identity, previous)
                return True
        files = self.content(snapshot)
        if snapshot['profile'] is not None:
            files['profil-connexion.dpapi'] = protect(encoded(snapshot['profile']))
        if self.workspace.maintenance or read_json(self.store.home / 'securite/generation.json')['id'] != snapshot['generation']:
            self.changed(); return False
        self.safe(self.root)
        if not self.root.exists(): private_directory(self.root)
        if not directory.exists(): private_directory(directory)
        hashes = {}
        for name, raw in files.items():
            path = self.safe(directory / name); path.parent.mkdir(parents=True, exist_ok=True)
            hashes[name] = checksum(raw)
            if not path.is_file() or checksum(path.read_bytes()) != hashes[name]: atomic(path, raw)
        # Remove only files listed in our previous manifest; preserve operator files.
        for name in previous.get('files', {}).keys() - files.keys():
            path = self.safe(directory / name)
            if path.is_file(): path.unlink()
        manifest = {'version': 1, 'id': identity, 'updated': time.time(), 'signature': signature,
            'generation': snapshot['generation'], 'files': hashes, 'bytes': sum(len(v) for v in files.values()),
            'counts': {table: len(rows) for table, rows in snapshot['rows'].items()},
            'conversations_exportees': sum(name.startswith('conversations/') for name in files),
            'mode': 'synchronized_files', 'transaction_database': str(self.workspace.path.resolve())}
        if self.workspace.maintenance or read_json(self.store.home / 'securite/generation.json')['id'] != snapshot['generation']:
            self.changed(); return False
        atomic(directory / 'dossier.json', encoded(manifest))
        with self.lock: self.states[identity] = self.summary(identity, manifest)
        return True

    def summary(self, identity, manifest):
        return {'path': str(self.directory(identity).resolve()), 'database': str((self.directory(identity) / 'donnees.sqlite3').resolve()),
            'updated': manifest.get('updated'), 'bytes': manifest.get('bytes', 0), 'counts': manifest.get('counts', {}),
            'conversations': manifest.get('conversations_exportees', 0), 'status': 'ready' if manifest else 'pending'}

    def client_status(self, identity):
        with self.lock:
            result = dict(self.states.get(identity) or self.summary(identity, {}))
            return result

    def status(self):
        with self.lock:
            return {'root': str(self.root.resolve()), 'transaction_database': str(self.workspace.path.resolve()),
                'clients': dict(self.states), 'last_sync': self.last_sync, 'error': self.error,
                'mode': 'synchronized_files', 'automatic': bool(self.thread and self.thread.is_alive())}

    def synchronize(self, *, incremental=False):
        with self.gate:
            if self.workspace.maintenance: raise ValueError('Serveur en maintenance.')
            with self.lock:
                pending = None if self.pending_owners is None else set(self.pending_owners)
                self.pending_owners = set(); self.dirty.clear()
            snapshots = self.snapshot(incremental=incremental,pending=pending)
            failed = False
            for snapshot in snapshots:
                if self.workspace.maintenance: return self.status()
                identity = snapshot['client']['id']
                try:
                    if not self.publish(snapshot): return self.status()
                    self.observed[identity] = snapshot['_revision']
                    self.verified_at[identity] = time.monotonic()
                except (OSError,ValueError,sqlite3.Error) as error:
                    if not incremental: raise
                    failed = True
                    message = 'Schéma du dossier client incompatible ; synchronisation à reprendre.' if isinstance(error,sqlite3.Error) else 'Dossier client en attente : vérifier les droits et le stockage.'
                    with self.lock:self.states[identity] = {**self.summary(identity,{}),'status':'error','error':message}
                    self.changed(identity)
            with self.lock:
                self.last_sync = time.time(); self.error = 'Certains dossiers clients attendent une synchronisation.' if failed else ''
            return self.status()
