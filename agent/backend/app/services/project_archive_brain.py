"""Include only source parents used by a project's knowledge, including its inbox."""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select


def library_content_hash(source):
    metadata = source.get('source_metadata')
    if isinstance(metadata, dict) and metadata.get('origin_kind') == 'library_import' and metadata.get('library_item_id'):
        return metadata.get('content_sha256')
    return None


def referenced_sources(brain):
    return {row['source_id'] for name in ('proposals', 'provenance_links', 'memory_projections', 'meeting_recordings')
            for row in brain.get(name, []) if row.get('source_id')}


def validate_detached_sources(brain):
    used = referenced_sources(brain)
    if any(row.get('project_id') is None and row['id'] not in used for row in brain.get('sources', [])):
        raise HTTPException(400, 'Source non classée sans relation au projet : import global interdit')


def include_source_parents(session, metadata, brain):
    project = brain['projects'][0]['id']
    present = {row['id'] for row in brain.get('sources', [])}
    missing = referenced_sources(brain) - present
    table = metadata.tables['sources']
    rows = session.execute(select(table).where(table.c.id.in_(missing))).mappings().all()
    if {row['id'] for row in rows} != missing or any(row['project_id'] not in (None, project) for row in rows):
        raise HTTPException(409, 'Preuve liée à un autre projet ou absente : utiliser la sauvegarde globale')
    def serial(row):
        return {key: value.isoformat() if isinstance(value, datetime) else value for key, value in row.items()}
    brain['sources'].extend(serial(row) for row in rows)
    artifacts = metadata.tables['source_artifacts']
    brain['source_artifacts'] = [serial(row) for row in session.execute(select(artifacts).where(
        artifacts.c.source_id.in_({row['id'] for row in brain['sources']}))).mappings()]
    validate_detached_sources(brain)
    return brain
