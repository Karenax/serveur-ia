"""Read-only schema/reuse preflight for v6; no installation or canonical edits."""
from copy import deepcopy
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select

from .project_review_migration import validate_review_schema


def raw_path(source, brain):
    """Declared media must travel; legacy remote-only sources stay metadata.

    Imported paths are never opened here. Export resolves them beneath RAW_DIR;
    import uses this solely as a required-file signal.
    """
    metadata = source.get('source_metadata') or {}
    declared = metadata.get('raw_path')
    if declared:
        if not isinstance(declared, str):
            raise HTTPException(400, 'Emplacement source invalide')
        return declared
    uri = source.get('original_uri')
    if (any(row['source_id']==source['id'] for row in (brain or {}).get('meeting_recordings', []))
            and isinstance(uri, str) and Path(uri).is_absolute()):
        return uri
    return None


def require_schema(db):
    try:
        plan = validate_review_schema(db.get_bind())
        if any(plan.values()):
            raise ValueError('Installation explicite des revues requise')
    except ValueError as exc:
        raise HTTPException(409, 'Schéma de revues incomplet ou incompatible ; migrer après sauvegarde') from exc


def cloned_transcriptions(brain):
    recordings = {row['id'] for row in brain.get('meeting_recordings', [])}
    return [row for row in brain.get('source_artifacts', []) if row['kind']=='transcription'
            and isinstance(row.get('content_json'), dict) and row['content_json'].get('recording_id') in recordings]


def validate_reused_transcriptions(session, metadata, brain):
    """Current superseded flags may advance; captured transcript bytes may not."""
    incoming = {row['id']: row for row in cloned_transcriptions(brain)}
    table = metadata.tables['source_artifacts']
    existing = {row['id']: row for row in session.execute(select(table).where(table.c.id.in_(incoming))).mappings()}
    def captured(value):
        content = deepcopy(value['content_json'])
        content.pop('superseded', None)
        return value['source_id'], value['kind'], value['content_text'], content
    if set(incoming)!=set(existing) or any(captured(existing[key])!=captured(row) for key,row in incoming.items()):
        raise HTTPException(409, 'Transcription canonique historique absente ou différente ; restauration refusée')
