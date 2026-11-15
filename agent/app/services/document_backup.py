"""Read-only document history validation for the portable whole-store backup."""
from pathlib import Path
import hashlib
import json
import sqlite3

from fastapi import HTTPException

from .deliverable_manifest import freeze


def validate_document_history(database: Path):
    if not database.is_file():
        raise ValueError('Base documentaire de sauvegarde absente')
    try:
        from backend.app.services import project_document_archive
        from backend.app.services.document_preferences import _items
        from backend.app.services.document_template_catalogue import catalogue
        from backend.app.services.document_schema_rules import validate_sqlite_schema
        # No ORM/runtime/configuration import, no engine or default directory.
        with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as db:
            if not validate_sqlite_schema(db):
                return  # Absent or empty dormant metadata stays untouched.
            db.row_factory = sqlite3.Row
            heads = list(db.execute('SELECT * FROM project_document_search_states LIMIT 2'))
            if len(heads) > 1 or heads and heads[0]['id'] != 'common':
                raise ValueError('Tête commune documentaire invalide')
            head = heads[0] if heads else None
            catalogue_sha = freeze(catalogue())[1]
            count = 0
            latest_id = None
            for row in db.execute('SELECT * FROM project_document_search_versions ORDER BY revision'):
                count += 1
                payload = row['snapshot']
                if (row['revision'] != count or not isinstance(payload, str) or len(payload.encode('utf-8')) > 1024 * 1024
                        or hashlib.sha256(payload.encode('utf-8')).hexdigest() != row['sha256']):
                    raise ValueError('Journal commun documentaire incomplet ou trop volumineux')
                value = json.loads(payload)
                if (not isinstance(value, dict) or set(value) != {'format', 'version', 'revision', 'actor_id', 'catalogue_sha256', 'items', 'restored_from'}
                        or value['format'] != 'agent-document-search-preferences' or type(value['version']) is not int or value['version'] != 1
                        or type(value['revision']) is not int or value['revision'] != row['revision']
                        or value['actor_id'] != row['actor_id'] or value['catalogue_sha256'] != catalogue_sha
                        or freeze(value)[0] != payload):
                    raise ValueError('Capture de préférences incompatible')
                project_document_archive.identity(row['id'])
                project_document_archive.timestamp(row['created_at'])
                if (not isinstance(row['actor_id'], str) or not 1 <= len(row['actor_id']) <= 120
                        or _items(value['items']) != value['items']):
                    raise ValueError('Préférences ou auteur non canoniques')
                latest_id = row['id']
            if (head is None and count or head is not None and (head['revision'] != count or head['current_version_id'] != latest_id)):
                raise ValueError('Tête de préférences différente de son journal')
            if head:
                project_document_archive.timestamp(head['updated_at'])
            pids = {row[0] for name in project_document_archive.PROJECT_TABLES for row in db.execute(f'SELECT DISTINCT project_id FROM {name}')}
            for pid in pids:
                tables = {}
                for name in ('projects', 'network_links', *project_document_archive.PROJECT_TABLES):
                    column = 'id' if name == 'projects' else 'project_id'
                    rows = [dict(row) for row in db.execute(f'SELECT * FROM {name} WHERE {column}=?', (pid,))]
                    for row in rows:
                        for key in ('overrides', 'bindings'):
                            if key in row:
                                row[key] = json.loads(row[key])
                    tables[name] = rows
                project_document_archive.section_for(tables)
    except (HTTPException, ValueError, TypeError, KeyError, sqlite3.Error) as exc:
        raise ValueError('Historique documentaire de sauvegarde invalide') from exc
