"""Typed v5 dispatch and file bindings used by the selective project archive."""
from fastapi import HTTPException
from sqlalchemy import inspect, select

from app.services import deliverable_manifest as manifest
from . import project_deliverable_archive as deliverables


def planning_view(tables):
    events = tables.get('project_planning_changes', [])
    if not isinstance(events, list) or any(not isinstance(row, dict) for row in events):
        raise HTTPException(400, 'Historique de planning invalide')
    return {**tables, 'project_planning_changes': [row for row in events
                                                if row.get('action') not in deliverables.ACTIONS]}


def merge_identity_dependencies(*values):
    references, people = {}, set()
    for value in values:
        if value is None:
            continue
        refs, persons = value
        for identity, kind in refs.items():
            if identity in references and references[identity] != kind:
                raise HTTPException(400, 'Utilisation ambiguë d’un référentiel')
            references[identity] = kind
        people.update(persons)
    return references, people


def needs_deliverables(db, metadata, tables):
    if any(tables.get(name) for name in deliverables.PROJECT_TABLES) or any(
            row.get('action') in deliverables.ACTIONS for row in tables.get('project_planning_changes', [])):
        return True
    typologies = deliverables.project_dependencies(tables)['typologies']
    available = set(inspect(db.get_bind()).get_table_names())
    if not typologies:
        return False
    name = 'project_deliverable_typology_types'
    if name in available:
        table = metadata.tables[name]
        if db.execute(select(table.c.id).where(table.c.typology_id.in_(typologies)).limit(1)).first():
            return True
    name = 'project_reference_changes'
    if name in available:
        table = metadata.tables[name]
        for row in db.execute(select(table.c.previous, table.c.value).where(
                (table.c.entity_kind == 'reference') & table.c.entity_id.in_(typologies))).mappings():
            if any('deliverable_selection' in row[field] for field in ('previous', 'value')):
                return True
    return False


def required_files(tables):
    return {('deliverable', row['id']) for row in tables.get('project_deliverable_file_versions', [])
            if row['source_delivery_id'] is None}


def validate_file_bindings(tables, decoded):
    """Frozen rows bind bytes, independent of an envelope's rehashed file entries."""
    actual = {(entry['area'], entry['owner']): (digest, len(content)) for entry, content, digest in decoded}
    for row in tables.get('delivery_versions', []):
        if actual.get(('delivery', row['id']), (None,))[0] != row['sha256']:
            raise HTTPException(400, 'Empreinte de livraison CDC différente de sa version')
    for row in tables.get('project_deliverable_file_versions', []):
        manifest.check_row(row)
        owner = ('delivery', row['source_delivery_id']) if row['source_delivery_id'] else ('deliverable', row['id'])
        if actual.get(owner) != (row['sha256'], row['size_bytes']):
            raise HTTPException(400, 'Fichier de livrable absent ou différent de sa publication')


def manifest_hashes(tables, mapping):
    return {row['id']: manifest.remap(row['manifest'], row['manifest_sha256'], mapping, version_id=row['id'])[1]
            for row in tables.get('project_deliverable_file_versions', [])}

