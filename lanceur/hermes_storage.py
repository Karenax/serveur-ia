"""Accounted Hermes data and bounded in-flight storage reservations."""
from contextlib import closing
from pathlib import Path
import sqlite3
import threading
import time

MAX_TURN_BYTES = 8 * 1024 * 1024
JOURNAL_DAYS = 1
RECOVERY_DAYS = 30


class HermesStorage:
    def __init__(self, workspace):
        self.workspace = workspace
        self.root = Path(workspace.home) / 'hermes-fred'
        self.lock = threading.RLock()
        self.reservations = {}

    def _journal(self, owner):
        path = self.root / 'fred-integration.db'
        if not path.is_file(): return 0
        with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)) as db:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            total = 0
            for table, columns in (('agent_runs', 'input,messages,output,reasoning,sources,fingerprint'),
                                   ('agent_conversations', 'visible,scope')):
                if table not in tables: continue
                expression = '+'.join('length(CAST(' + column + ' AS BLOB))' for column in columns.split(','))
                total += db.execute('SELECT COALESCE(SUM(' + expression + '),0) FROM ' + table +
                    (' WHERE owner=?' if owner else ''), (owner,) if owner else ()).fetchone()[0]
        native = self.root / 'runs_idempotency.db'
        if native.is_file():
            with closing(sqlite3.connect(native.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)) as db:
                if db.execute("SELECT 1 FROM sqlite_master WHERE name='run_idempotency'").fetchone():
                    if owner:
                        db.execute('ATTACH DATABASE ? AS fred', (path.resolve().as_uri() + '?mode=ro',))
                        total += db.execute('SELECT COALESCE(SUM(length(CAST(status_json AS BLOB))),0) FROM run_idempotency WHERE run_id IN (SELECT remote FROM fred.agent_runs WHERE owner=?)', (owner,)).fetchone()[0]
                    else:
                        pages = db.execute('PRAGMA page_count').fetchone()[0] - db.execute('PRAGMA freelist_count').fetchone()[0]
                        total += pages * db.execute('PRAGMA page_size').fetchone()[0]
        return total

    def usage(self, owner=None, *, reservations=True):
        total = self._journal(owner)
        profiles = self.root / 'profiles'
        if profiles.is_symlink() or (hasattr(profiles,'is_junction') and profiles.is_junction()):
            raise ValueError('Lien interdit dans le stockage Hermes.')
        directories = [profiles / ('fred-' + owner)] if owner else list(profiles.glob('fred-*'))
        for directory in directories:
            if not directory.exists(): continue
            if directory.is_symlink() or (hasattr(directory, 'is_junction') and directory.is_junction()):
                raise ValueError('Lien interdit dans le stockage Hermes.')
            for path in directory.rglob('*'):
                if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
                    raise ValueError('Lien interdit dans le stockage Hermes.')
                if not path.is_file() or path.name.endswith(('-wal', '-shm')): continue
                if path.suffix in ('.db', '.sqlite3'):
                    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)) as db:
                        pages = db.execute('PRAGMA page_count').fetchone()[0] - db.execute('PRAGMA freelist_count').fetchone()[0]
                        total += pages * db.execute('PRAGMA page_size').fetchone()[0]
                else: total += path.stat().st_size
        if reservations:
            with self.lock:
                total += self.reservations.get(owner, 0) if owner else sum(self.reservations.values())
        return total

    def reserve(self, owner, incoming):
        # The canonical lock serializes reservations across owners. Never hold
        # the reservation lock while opening the canonical database.
        with self.workspace.db() as db:
            available = self.workspace.policy(db, owner)['storage_mb'] * 1024 * 1024 - self.workspace.usage(db, owner)
            from workspace import GLOBAL_BYTES
            available = min(available, GLOBAL_BYTES - self.workspace.usage(db))
            amount = min(MAX_TURN_BYTES, max(4096, (available - incoming) // 2)) + incoming
            self.workspace.quota(db, owner, amount)
            with self.lock: self.reservations[owner] = amount
        return amount

    def check(self, owner):
        """Native writes consume the reserved headroom; stop before another call."""
        with self.workspace.db() as db, self.lock:
            from workspace import GLOBAL_BYTES
            own = self.workspace.usage(db, owner) - self.reservations.get(owner, 0)
            total = self.workspace.usage(db) - sum(self.reservations.values())
            if own > self.workspace.policy(db, owner)['storage_mb'] * 1024 * 1024 or total > GLOBAL_BYTES:
                raise ValueError('Limite de stockage de l’assistant atteinte. Exportez puis libérez de la place.')

    def release(self, owner):
        with self.lock: self.reservations.pop(owner, None)

    def compact(self):
        """Compact only the integration journal, while Kiara has no admitted run."""
        paths = [self.root/name for name in ('fred-integration.db','runs_idempotency.db')]
        paths.extend((self.root/'profiles').glob('fred-*/*.db'))
        for path in paths:
            if not path.is_file(): continue
            if (path.is_symlink() or path.parent.is_symlink() or not path.resolve().is_relative_to(self.root.resolve())
                    or (hasattr(path.parent,'is_junction') and path.parent.is_junction())):raise ValueError('Lien interdit dans le stockage Hermes.')
            with closing(sqlite3.connect(path, timeout=5)) as db:
                if path.name=='runs_idempotency.db' and db.execute("SELECT 1 FROM sqlite_master WHERE name='run_idempotency'").fetchone():
                    with db:db.execute("DELETE FROM run_idempotency WHERE updated_at<? AND retention_until<? AND json_extract(status_json,'$.status') IN ('completed','failed','cancelled','interrupted')", (time.time()-86400,time.time()))
                pages = db.execute('PRAGMA page_count').fetchone()[0]
                free = db.execute('PRAGMA freelist_count').fetchone()[0]
                if free > 32 and free > pages // 4: db.execute('VACUUM')
