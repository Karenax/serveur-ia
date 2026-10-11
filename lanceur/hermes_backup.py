"""Portable snapshots of Fred's dedicated Hermes state, never personal Hermes.

The caller must quiesce Fred runs and the Hermes gateway while collecting files,
and close the gateway and integration databases before restoring. Archives are
plaintext mappings intended ONLY for Fred's existing encrypted backup envelope.
"""
from __future__ import annotations

import base64
from contextlib import closing
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import stat
import tempfile
import time

from wg_crypto import private_directory, protect

MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
MAX_FILES = 8192
ROOT_FILES = frozenset({'config.yaml', '.no-bundled-skills', 'SOUL.md', 'profile.yaml',
                        'active_profile', 'integration.sqlite3', 'accounts.sqlite3', 'secrets.dpapi',
                        'registry.sqlite3', 'integration.json', 'gateway-config.json', 'fred-integration.db'})
PROFILE_FILES = frozenset({'config.yaml', '.no-bundled-skills', 'profile.yaml',
                           'SOUL.md', 'AGENTS.md', 'state.db', 'projects.db'})
PROFILE_DIRS = frozenset({'memories', 'sessions', 'skills', 'plans', 'workspace'})
PROFILE_RE = re.compile(r'fred-([a-f0-9]{16})')
WINDOWS_RESERVED = re.compile(r'(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', re.I)


def _parts(name):
    if not isinstance(name, str) or len(name) > 700 or '\\' in name:
        raise ValueError('Chemin de sauvegarde Hermes invalide.')
    path = PurePosixPath(name)
    parts = path.parts
    if (not parts or path.is_absolute() or path.as_posix() != name or
            any(p in ('.', '..') or p.endswith((' ', '.')) or WINDOWS_RESERVED.fullmatch(p) or
                re.search(r'[<>:"|?*\x00-\x1f]', p) for p in parts)):
        raise ValueError('Chemin de sauvegarde Hermes invalide.')
    return parts


def _allowed(name, owners, root_files):
    parts = _parts(name)
    if len(parts) == 1:
        return parts[0] in root_files
    if len(parts) < 3 or parts[0] != 'profiles':
        return False
    match = PROFILE_RE.fullmatch(parts[1])
    if not match or match[1] not in owners:
        return False
    return (len(parts) == 3 and parts[2] in PROFILE_FILES) or (len(parts) > 3 and parts[2] in PROFILE_DIRS)


def _linked(path):
    return path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())


def _remove_stage(path, parent):
    if path.resolve().parent != parent.resolve() or not path.name.startswith('.hermes-fred-restore-') or _linked(path):
        raise ValueError('Répertoire temporaire Hermes hors du périmètre prévu.')
    shutil.rmtree(path)


def _checked(root, name):
    path = root
    for component in _parts(name):
        path = path / component
        if _linked(path):
            raise ValueError('Lien de fichiers interdit dans la sauvegarde Hermes.')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Chemin hors de l’espace Hermes Fred.')
    return path


SECRET_COLUMNS = (('hermes_bindings', 'secrets'), ('hermes_settings', 'secret'))


def _rewrap(db, decrypt):
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table, column in SECRET_COLUMNS:
        if table not in tables: continue
        columns = {r[1] for r in db.execute('PRAGMA table_info(' + table + ')')}
        if column not in columns: raise ValueError('Schéma des secrets Hermes incompatible.')
        for identity, raw in db.execute('SELECT rowid,' + column + ' FROM ' + table).fetchall():
            if raw is None: continue
            if not isinstance(raw, bytes) or not 1 <= len(raw) <= 65536:
                raise ValueError('Secret Hermes sauvegardé invalide.')
            db.execute('UPDATE ' + table + ' SET ' + column + '=? WHERE rowid=?',
                       (protect(raw, decrypt=decrypt), identity))
    if not decrypt and 'agent_runs' in tables:
        columns = {r[1] for r in db.execute('PRAGMA table_info(agent_runs)')}
        if 'state' in columns:
            db.execute("UPDATE agent_runs SET state='interrupted' WHERE state NOT IN ('completed','failed','cancelled','interrupted')")


def _snapshot(path):
    """SQLite's backup API includes committed WAL data without copying sidecars."""
    started = time.monotonic()
    def progress(status, remaining, total):
        if time.monotonic() - started > 10:
            raise ValueError('Base Hermes occupée ; réessayez la sauvegarde.')
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)) as source:
        with closing(sqlite3.connect(':memory:')) as destination:
            source.backup(destination, pages=256, progress=progress, sleep=.05)
            if destination.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('Base Hermes endommagée ; sauvegarde refusée.')
            if path.name == 'fred-integration.db': _rewrap(destination, decrypt=True)
            destination.commit()
            raw = destination.serialize()
            # A standalone snapshot must not depend on a WAL sidecar.
            return raw[:18] + b'\x01\x01' + raw[20:]


def _validate_database(raw, owners=None, registry=False):
    if not raw.startswith(b'SQLite format 3\x00'):
        raise ValueError('Base Hermes sauvegardée invalide.')
    with closing(sqlite3.connect(':memory:')) as db:
        try:
            db.deserialize(raw)
            if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('Base Hermes sauvegardée endommagée.')
            if registry:
                for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
                    if not re.fullmatch('[a-zA-Z0-9_]+', table): raise ValueError('Schéma Hermes invalide.')
                    columns = {r[1] for r in db.execute('PRAGMA table_info(' + table + ')')}
                    if 'owner' in columns:
                        identities = {r[0] for r in db.execute('SELECT DISTINCT owner FROM ' + table)}
                        if identities - owners: raise ValueError('Registre Hermes contenant un accès inconnu.')
                tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                for table, column in SECRET_COLUMNS:
                    if table in tables:
                        for (secret,) in db.execute('SELECT ' + column + ' FROM ' + table):
                            if secret is not None and (not isinstance(secret, bytes) or not 1 <= len(secret) <= 65536):
                                raise ValueError('Secret Hermes sauvegardé invalide.')
        except sqlite3.Error:
            raise ValueError('Base Hermes sauvegardée invalide.') from None


class HermesBackup:
    def __init__(self, root, root_files=ROOT_FILES):
        self.root = Path(root).absolute()
        # This deliberately cannot be pointed at ~/.hermes or the installation.
        if self.root.name != 'hermes-fred' or _linked(self.root):
            raise ValueError('La sauvegarde doit cibler la racine dédiée hermes-fred.')
        self.root_files = frozenset(root_files)
        if any(len(_parts(name)) != 1 for name in self.root_files):
            raise ValueError('Liste de fichiers racine Hermes invalide.')

    @staticmethod
    def _owners(owners):
        owners = set(owners)
        if len(owners) > 10000 or any(not isinstance(o, str) or not re.fullmatch('[a-f0-9]{16}', o) for o in owners):
            raise ValueError('Identités Fred de sauvegarde invalides.')
        return owners

    def export(self, owners):
        owners = self._owners(owners); files = {}; total = 0
        if not self.root.exists():
            return {'version': 1, 'files': files}
        _checked(self.root, 'config.yaml')
        candidates = [name for name in sorted(self.root_files) if (self.root / name).exists()]
        for owner in sorted(owners):
            directory = _checked(self.root, 'profiles/fred-' + owner)
            if not directory.exists():
                continue
            for current, directories, names in os.walk(directory, followlinks=False):
                for child in list(directories):
                    child_path = Path(current) / child
                    if _linked(child_path):
                        raise ValueError('Lien interdit dans un profil Hermes Fred.')
                    relative = child_path.relative_to(directory)
                    if relative.parts[0] not in PROFILE_DIRS:
                        directories.remove(child)
                for name in names:
                    relative = (Path(current) / name).relative_to(self.root).as_posix()
                    if _allowed(relative, owners, self.root_files):
                        candidates.append(relative)
        for name in candidates:
            path = _checked(self.root, name)
            metadata = path.stat()
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_FILE:
                raise ValueError('Fichier Hermes trop volumineux ou non régulier.')
            if path.suffix in ('.db', '.sqlite3'):
                raw = _snapshot(path); kind = 'registry' if path.name == 'fred-integration.db' else 'sqlite'
            else:
                raw = path.read_bytes(); kind = 'dpapi' if path.suffix == '.dpapi' else 'file'
                after = path.stat()
                if (metadata.st_size, metadata.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise ValueError('Profil Hermes modifié pendant la sauvegarde ; réessayez.')
                if kind == 'dpapi': raw = protect(raw, decrypt=True)
            total += len(raw)
            if len(raw) > MAX_FILE or total > MAX_TOTAL or len(files) >= MAX_FILES:
                raise ValueError('Limite de sauvegarde Hermes atteinte (64 Mo).')
            files[name] = {'kind': kind, 'sha256': hashlib.sha256(raw).hexdigest(),
                           'bytes': len(raw), 'data': base64.b64encode(raw).decode('ascii')}
        return {'version': 1, 'files': files}

    def validate(self, package, owners):
        owners = self._owners(owners)
        if (not isinstance(package, dict) or set(package) != {'version', 'files'} or package.get('version') != 1 or
                not isinstance(package.get('files'), dict) or len(package['files']) > MAX_FILES):
            raise ValueError('Sauvegarde Hermes invalide.')
        decoded = {}; total = 0; folded = set()
        for name, value in package['files'].items():
            if not _allowed(name, owners, self.root_files) or name.casefold() in folded:
                raise ValueError('Fichier Hermes absent du périmètre Fred.')
            folded.add(name.casefold())
            if (not isinstance(value, dict) or set(value) != {'kind', 'sha256', 'bytes', 'data'} or
                    type(value.get('bytes')) is not int or not 0 <= value['bytes'] <= MAX_FILE or
                    not isinstance(value.get('data'), str) or len(value['data']) > (MAX_FILE * 4 // 3 + 4)):
                raise ValueError('Fichier Hermes sauvegardé invalide.')
            suffix = PurePosixPath(name).suffix
            kind = ('registry' if name == 'fred-integration.db' else 'dpapi' if suffix == '.dpapi' else
                    'sqlite' if suffix in ('.db', '.sqlite3') else 'file')
            if value.get('kind') != kind:
                raise ValueError('Type de fichier Hermes sauvegardé invalide.')
            try: raw = base64.b64decode(value['data'], validate=True)
            except (ValueError, TypeError): raise ValueError('Encodage de fichier Hermes invalide.') from None
            total += len(raw)
            if (len(raw) != value['bytes'] or total > MAX_TOTAL or
                    hashlib.sha256(raw).hexdigest() != value.get('sha256')):
                raise ValueError('Intégrité de fichier Hermes sauvegardé invalide.')
            if kind in ('sqlite', 'registry'):
                _validate_database(raw, owners, registry=kind == 'registry')
            decoded[name] = raw
        return decoded

    def restore(self, package, owners):
        """Replace a CLOSED dedicated root; rollback journal is owned by Fred."""
        decoded = self.validate(package, owners)
        self.root.parent.mkdir(parents=True, exist_ok=True)
        if _linked(self.root) or self.root.resolve() == self.root.parent.resolve():
            raise ValueError('Racine de restauration Hermes invalide.')
        stage = Path(tempfile.mkdtemp(prefix='.hermes-fred-restore-', dir=self.root.parent))
        previous = self.root.parent / (stage.name + '-previous')
        try:
            private_directory(stage)
            for name, raw in decoded.items():
                path = _checked(stage, name)
                path.parent.mkdir(parents=True, exist_ok=True)
                kind = package['files'][name]['kind']
                if kind == 'registry':
                    with closing(sqlite3.connect(':memory:')) as db:
                        db.deserialize(raw); _rewrap(db, decrypt=False); db.commit(); raw = db.serialize()
                path.write_bytes(protect(raw) if kind == 'dpapi' else raw)
            if self.root.exists(): os.replace(self.root, previous)
            try: os.replace(stage, self.root)
            except BaseException:
                if previous.exists(): os.replace(previous, self.root)
                raise
            if previous.exists(): _remove_stage(previous, self.root.parent)
        finally:
            if stage.exists(): _remove_stage(stage, self.root.parent)
        return {'files': len(decoded), 'bytes': sum(map(len, decoded.values()))}
