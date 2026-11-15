"""Durable file-preparation evidence, independent of the v6 SQL transaction.

Interrupted preparations are retained, never cleaned up automatically. SQL
project/link existence determines the commit outcome; the append-only log
identifies planned files for recovery. No claim of SQL/files atomicity.
"""
import hashlib
import json
import logging
import os
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select

logger = logging.getLogger(__name__)


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new(path, content):
    with path.open('xb') as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


class PreparedFiles:
    def __init__(self, root, project_id, brain_project_id, destinations, *, brain_reused=False, exclusive_paths=()):
        self.directory = Path(root) / 'backups' / 'archive-imports' / project_id
        self.destinations = destinations
        self.exclusive_paths = {Path(path) for path in exclusive_paths}
        self.directory.mkdir(parents=True, exist_ok=False)
        manifest = {'format': 'agent-v6-file-preparation', 'version': 1,
                    'project_id': project_id, 'brain_project_id': brain_project_id, 'brain_reused':brain_reused,
                    'files': [{'path': str(path.resolve()), 'sha256': hashlib.sha256(content).hexdigest(),
                               'size_bytes': len(content), 'existed_before': path.exists()}
                              for path, content in destinations]}
        _write_new(self.directory / 'manifest.json', json.dumps(manifest, ensure_ascii=False).encode('utf-8'))
        self.record('prepared')

    def record(self, event, **details):
        with (self.directory / 'events.ndjson').open('ab') as handle:
            handle.write((json.dumps({'event': event, **details}, ensure_ascii=False) + '\n').encode('utf-8'))
            handle.flush()
            os.fsync(handle.fileno())

    def prepare(self):
        for path, content in self.destinations:
            digest = hashlib.sha256(content).hexdigest()
            # New note storage UUIDs never adopt an interrupted import's bytes,
            # even when the digest matches. Preserve both preparations.
            if path in self.exclusive_paths:
                if any(parent.is_symlink() or parent.is_junction() for parent in path.parents):
                    raise HTTPException(409, 'Destination de note redirigée')
                path.parent.parent.mkdir(parents=True, exist_ok=True)
                path.parent.mkdir(exist_ok=False)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
            try:
                _write_new(path, content)
            except FileExistsError:
                if path in self.exclusive_paths or path.is_symlink() or not path.is_file() or _digest(path) != digest:
                    raise HTTPException(409, 'Pièce déjà présente avec un contenu différent') from None
            if path.is_symlink() or _digest(path) != digest:
                raise HTTPException(409, 'Pièce préparée différente de l’archive')
            self.record('file_ready', path=str(path.resolve()), sha256=digest)
        self.record('files_ready')

    def outcome(self, event):
        # A post-commit log failure must not suggest retrying a successful import.
        # The prepared manifest and SQL state remain sufficient to inspect.
        try:
            self.record(event)
        except OSError:
            logger.exception('Journal de préparation archive indisponible : %s', self.directory)


def inspect_preparation(db, directory, brain):
    """Read-only reconciliation; no cleanup or replay of stored file paths."""
    from ..models import BrainLink, Project
    from app.models import Project as BrainProject
    manifest = json.loads((Path(directory) / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('format') != 'agent-v6-file-preparation' or manifest.get('version') != 1:
        raise ValueError('Journal de préparation non reconnu')
    project = db.get(Project, manifest['project_id'])
    link = db.scalar(select(BrainLink).where(BrainLink.project_id == manifest['project_id']))
    expected = manifest['brain_project_id']
    brain_exists = expected is not None and brain.get(BrainProject, expected) is not None
    committed = project is not None and (link is None if expected is None else link is not None and link.brain_project_id == expected and brain_exists)
    not_committed = project is None and link is None and (expected is None or brain_exists==manifest['brain_reused'])
    return {'project_id': manifest['project_id'], 'sql_state': 'committed' if committed else 'not_committed' if not_committed else 'inconsistent',
            'files': manifest['files']}
