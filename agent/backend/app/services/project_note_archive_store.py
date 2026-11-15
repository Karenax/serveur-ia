"""Live adapter for the pure notes transport; no installation or source acquisition."""
import base64
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import DateTime

from ..project_note_models import NOTE_TABLES
from .project_note_schema import validate_note_schema
from . import project_note_archive as contract


def invalid(exc):
    raise HTTPException(400, 'Archive de notes : ' + str(exc)) from exc


def require_schema(db):
    try:
        plan = validate_note_schema(db.get_bind())
        if plan['created_tables'] or plan['created_triggers']:
            raise ValueError('Installation explicite des notes requise')
    except ValueError as exc:
        raise HTTPException(409, 'Schéma de notes non installé ou incompatible') from exc


def section_for(tables):
    try:
        return contract.section_for(tables)
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        invalid(exc)


def validate(tables, section):
    try:
        return contract.history.validate(tables, section)
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        invalid(exc)


def validate_files(tables, section, decoded):
    try:
        return contract.validate_files(tables, section, decoded)
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        invalid(exc)


def export_files(db, project_id, tables):
    """Freeze verified managed bytes; never touch the original network source."""
    from . import project_note_files as attachments, project_note_import_files as originals
    from .project_note_history import import_value
    from types import SimpleNamespace
    files = []
    for area, table in contract.AREAS.items():
        for row in tables[table]:
            if area == 'note-file':
                data, _ = attachments.download(db, project_id, row['note_id'], row['id'])
            else:
                capture = import_value(row)
                data, _ = originals.read_originals(SimpleNamespace(**row), capture)
            files.append({'owner': row['id'], 'area': area, 'name': contract.storage_name(area, row),
                          'sha256': row['sha256'], 'data': base64.b64encode(data).decode('ascii')})
    validate_files(tables, section_for(tables), [
        (entry, base64.b64decode(entry['data']), entry['sha256']) for entry in files])
    return files


def destination(root, area, row):
    """Fresh generated storage only; matching abandoned bytes are not adopted."""
    if area not in contract.AREAS:
        raise HTTPException(400, 'Zone de note inconnue')
    root = Path(root)
    folder = root / ('note-files' if area == 'note-file' else 'note-originals')
    target = folder / contract.storage_name(area, row)
    if (target.parent.exists() or target.parent.is_symlink() or target.exists() or target.is_symlink()
            or any(path.is_symlink() or path.is_junction() for path in (root, folder, target.parent))
            or not target.resolve().is_relative_to(root.resolve())):
        raise HTTPException(409, 'Destination de note déjà occupée ou redirigée')
    return target


def insert_rows(db, rows):
    """Append versions before the head; snapshots/bindings are already prepared."""
    by_name = {table.name: table for table in NOTE_TABLES}
    for name in ('project_note_attachments', 'project_note_versions', 'project_notes', 'project_note_imports'):
        table = by_name[name]
        values = sorted(rows[name], key=lambda row: (row['note_id'], row['revision'])) if name == 'project_note_versions' else rows[name]
        for source in values:
            row = dict(source)
            for column in table.c:
                if isinstance(column.type, DateTime):
                    row[column.name] = datetime.fromisoformat(row[column.name])
            db.execute(table.insert().values(**row))
