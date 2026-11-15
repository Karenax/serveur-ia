"""Offline note history/binary closure and frozen nonces on new restorations.

No ORM, runtime database import, network/source acquisition, DDL or extraction.
Files are read per note so global backups are not limited to one project ZIP's
size. Abandoned managed files remain in the generic backup and are not adopted.
"""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat

from backend.app.services import project_note_archive as contract
from backend.app.services.project_note_schema_rules import validate_schema
from backend.app.services.project_note_history import MAX_ROWS, MAX_EMBEDDED_BYTES


def _projects(db):
    if not validate_schema(db):
        return
    db.row_factory = sqlite3.Row
    for name in contract.PROJECT_TABLES:
        if db.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0] > MAX_ROWS:
            raise ValueError('Historique global de notes trop volumineux')
    pids = {row[0] for name in contract.PROJECT_TABLES for row in db.execute(f'SELECT DISTINCT project_id FROM {name}')}
    for pid in sorted(pids):
        # Bound SQLite text/JSON before loading rows, including malformed values
        # injected outside the API. Individual captures are checked by the graph.
        size = 0
        for name in contract.PROJECT_TABLES:
            columns = [row[1] for row in db.execute(f'PRAGMA table_info({name})')]
            expression = '+'.join('COALESCE(length(CAST("' + column.replace('"', '""') + '" AS BLOB)),0)' for column in columns)
            size += db.execute(f'SELECT COALESCE(SUM({expression}),0) FROM {name} WHERE project_id=?', (pid,)).fetchone()[0]
        if size > MAX_EMBEDDED_BYTES:
            raise ValueError('Historique de notes trop volumineux')
        tables = {'projects': [dict(row) for row in db.execute('SELECT id FROM projects WHERE id=?', (pid,))]}
        for name in contract.PROJECT_TABLES:
            rows = []
            for value in db.execute(f'SELECT * FROM {name} WHERE project_id=?', (pid,)):
                row = dict(value)
                for key in ('version_bindings', 'attachment_bindings'):
                    if key in row:
                        row[key] = json.loads(row[key])
                if 'execution_blocked' in row:
                    if type(row['execution_blocked']) is not int or row['execution_blocked'] not in {0, 1}:
                        raise ValueError('Gel de notes incompatible')
                    row['execution_blocked'] = bool(row['execution_blocked'])
                rows.append(row)
            tables[name] = rows
        contract.section_for(tables)
        yield tables


def validate_history(database):
    try:
        with sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True) as db:
            db.execute('BEGIN')
            return sum(len(tables['project_notes']) for tables in _projects(db))
    except (sqlite3.Error, ValueError, TypeError, KeyError, OverflowError) as exc:
        raise ValueError('Historique de notes invalide') from exc


def _read(root, area, row):
    root = Path(root)
    folder = root / ('note-files' if area == 'note-file' else 'note-originals')
    path = folder / contract.storage_name(area, row)
    if (any(part.is_symlink() or part.is_junction() for part in (root, folder, path.parent, path))
            or not path.resolve().is_relative_to(root.resolve())):
        raise ValueError('Stockage de note redirigé')
    with path.open('rb') as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size != row['size_bytes']:
            raise ValueError('Fichier de note absent, irrégulier ou de taille différente')
        data = handle.read(row['size_bytes'] + 1)
        after = os.fstat(handle.fileno())
    if ((before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns)
            or len(data) != row['size_bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']):
        raise ValueError('Fichier de note modifié pendant lecture')
    return data


def collect_files(database, erp_home):
    try:
        files = []
        with sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True) as db:
            db.execute('BEGIN')
            for tables in _projects(db):
                for head in tables['project_notes']:
                    single = {'projects': tables['projects'], 'project_notes': [head]}
                    single.update({name: [row for row in tables[name] if row['note_id'] == head['id']]
                                   for name in contract.PROJECT_TABLES - {'project_notes'}})
                    decoded = []
                    for area, table in contract.AREAS.items():
                        for row in single[table]:
                            data = _read(erp_home, area, row)
                            entry = {'area': area, 'owner': row['id'], 'name': contract.storage_name(area, row),
                                     'sha256': row['sha256'], 'data': None}
                            decoded.append((entry, data, row['sha256']))
                            files.append({key: row[key] for key in ('id', 'project_id', 'storage_id', 'sha256', 'size_bytes')}
                                         | {'area': area})
                    contract.validate_files(single, contract.section_for(single), decoded)
        return sorted(files, key=lambda row: (row['area'], row['id']))
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        raise ValueError('Notes ou fichiers gérés invalides') from exc


def validate_files(database, source, manifest):
    expected = collect_files(database, Path(source) / 'erp')
    supplied = manifest.get('note_files', [])
    if not isinstance(supplied, list) or supplied != expected:
        raise ValueError('Inventaire des fichiers de notes incomplet ou différent')
    for row in expected:
        folder = 'note-files' if row['area'] == 'note-file' else 'note-originals'
        path = 'erp/' + folder + '/' + contract.storage_name(row['area'], row)
        if manifest['files'].get(path) != row['sha256']:
            raise ValueError('Fichier de note absent du manifeste')
    return expected


def freeze_restored_commands(database):
    """New offline destination only. Freeze historical nonces, keep all captures."""
    validate_history(database)
    with sqlite3.connect(database) as db:
        if not validate_schema(db):
            return
        db.execute('PRAGMA foreign_keys=ON')
        for name in ('project_note_versions', 'project_note_imports'):
            db.execute(f'UPDATE {name} SET execution_blocked=1 WHERE execution_blocked=0')
    validate_history(database)
