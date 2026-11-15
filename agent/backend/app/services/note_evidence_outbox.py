"""Atomic note events and explicit, backup-first outbox installation."""
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from sqlalchemy import inspect, select
from sqlalchemy.schema import CreateTable

from ..note_evidence_models import NoteEvidenceOutbox
from ..project_note_models import NoteVersion, ProjectNote
from .document_schema_rules import _sql
from .project_planning_migration import read_connection


def validate_outbox_schema(engine):
    with read_connection(engine) as db:
        table = NoteEvidenceOutbox.__table__
        if table.name not in inspect(db).get_table_names():
            return False
        actual = db.exec_driver_sql("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table.name,)).scalar()
        if _sql(actual) != _sql(str(CreateTable(table).compile(dialect=engine.dialect))):
            raise ValueError('Schéma outbox Notes incompatible')
        return True


def install_outbox_schema(engine, *, backup):
    if validate_outbox_schema(engine):
        return False
    backup()
    with engine.begin() as db:
        NoteEvidenceOutbox.__table__.create(db)
    return True


def enqueue_note_version(db, version_id):
    # Standalone historical Notes fixtures/installations remain usable. No DDL
    # or remote side effects are permitted in a note-save command.
    if not inspect(db.connection()).has_table('note_evidence_outbox'):
        return None
    version = db.get(NoteVersion, version_id)
    event_id = str(uuid5(NAMESPACE_URL, 'agent:note-evidence:' + version_id))
    previous = db.get(NoteEvidenceOutbox, event_id)
    if previous:
        return previous
    row = NoteEvidenceOutbox(id=event_id, project_id=version.project_id, note_id=version.note_id,
        version_id=version.id, revision=version.revision, digest=version.sha256)
    db.add(row)
    return row


def backfill(db, *, limit=100, after_id=''):
    """Explicit resumable backfill of current versions; preserves all note data."""
    if type(limit) is not int or not 1 <= limit <= 500 or not isinstance(after_id, str) or len(after_id) > 36:
        raise HTTPException(422, 'Lot de migration ou curseur invalide')
    if not inspect(db.connection()).has_table('note_evidence_outbox'):
        raise HTTPException(409, 'Installer la projection Notes protégée avant migration')
    heads = list(db.scalars(select(ProjectNote).where(ProjectNote.id > after_id)
                           .order_by(ProjectNote.id).limit(limit)))
    for head in heads:
        enqueue_note_version(db, head.current_version_id)
    return {'visited': len(heads), 'after_id': heads[-1].id if heads else after_id,
            'has_more': len(heads) == limit}
