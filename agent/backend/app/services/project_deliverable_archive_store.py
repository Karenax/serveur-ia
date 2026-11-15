"""Read-only SQL closure and conflict reconciliation for the v5 transport.

No startup registration, schema installation, file writes or commits. The caller
validates the domain contract and holds the import transaction's write lock.
"""
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import or_, select

from . import project_deliverable_archive as contract
from .project_deliverable_migration import install_deliverable_schema


def require_schema(db):
    def refuse():
        raise HTTPException(409, 'Activer la migration des livrables avant l’archive v5')
    try:
        install_deliverable_schema(db.get_bind(), backup=refuse)
    except ValueError as exc:
        raise HTTPException(409, 'Schéma des livrables incomplet ou incompatible') from exc


def _serial(row):
    return {key: value.isoformat() if isinstance(value, datetime) else value for key, value in row.items()}


def _select(db, table, condition):
    return [_serial(row) for row in db.execute(select(table).where(condition).order_by(table.c.id)).mappings()]


def export_references(db, metadata, tables):
    """Export only used heads, all their frozen versions and related compositions.

    Historical compositions are kept, including types removed from the current
    selection. Audit entities never justify unrelated global dependencies.
    """
    require_schema(db)
    used = contract.project_dependencies(tables)
    versions = metadata.tables['project_deliverable_type_versions']
    heads = metadata.tables['project_deliverable_types']
    links = metadata.tables['project_deliverable_typology_types']
    audits = metadata.tables['project_reference_changes']
    selected_versions = _select(db, versions, versions.c.id.in_(used['type_versions']))
    if {row['id'] for row in selected_versions} != used['type_versions']:
        raise HTTPException(409, 'Version de type historique absente : export refusé')
    types = used['types'] | {row['type_id'] for row in selected_versions}
    selected_links = _select(db, links, links.c.typology_id.in_(used['typologies']))
    types.update(row['type_id'] for row in selected_links)
    typology_audits = _select(db, audits, (audits.c.entity_kind == 'reference') & audits.c.entity_id.in_(used['typologies']))
    for event in typology_audits:
        for field in ('previous', 'value'):
            selection = event[field].get('deliverable_selection')
            if selection is not None:
                types.update(selection['type_ids'])
    selected_heads = _select(db, heads, heads.c.id.in_(types))
    if {row['id'] for row in selected_heads} != types:
        raise HTTPException(409, 'Type de livrable historique absent : export refusé')
    all_versions = _select(db, versions, versions.c.type_id.in_(types))
    return {'project_deliverable_types': selected_heads,
            'project_deliverable_type_versions': sorted(all_versions, key=lambda row: (row['type_id'], row['number'])),
            'project_deliverable_typology_types': selected_links,
            'project_reference_changes': typology_audits + _select(db, audits,
                (audits.c.entity_kind == 'deliverable_type') & audits.c.entity_id.in_(types))}


def _conflict(name, raw):
    raise HTTPException(409, {'message': 'Référentiel de livrables différent : aucune donnée existante modifiée',
                              'table': name, 'archive_id': raw['id']})


def _date(value):
    stamp = datetime.fromisoformat(value) if isinstance(value, str) else value
    return (stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)).isoformat()


def _candidates(db, table, raw, condition):
    found = {row['id']: dict(row) for row in db.execute(select(table).where(
        or_(table.c.id == raw['id'], condition))).mappings()}
    if len(found) > 1:
        _conflict(table.name, raw)
    return next(iter(found.values()), None)


def reconcile_references(db, metadata, section, mapping, *, typology_ids):
    """Prepare raw missing rows and ID reuse atomically, with no SQL mutation.

    Existing heads retain their revision. Importing an absent immutable version
    into an existing type or changing its typology composition requires a separate
    explicit catalogue operation, so this reconciliation refuses both cases.
    """
    require_schema(db)
    working = dict(mapping)
    pending = {name: [] for name in contract.REFERENCE_TABLES}
    new_types = set()
    heads = metadata.tables['project_deliverable_types']
    versions = metadata.tables['project_deliverable_type_versions']
    links = metadata.tables['project_deliverable_typology_types']
    audits = metadata.tables['project_reference_changes']
    with db.no_autoflush:
        for raw in section[heads.name]:
            existing = _candidates(db, heads, raw, heads.c.code == raw['code'])
            if existing:
                if any(existing[key] != raw[key] for key in ('code', 'label', 'active')) or existing['revision'] < raw['revision']:
                    _conflict(heads.name, raw)
                working[raw['id']] = existing['id']
            else:
                new_types.add(raw['id'])
                pending[heads.name].append(raw)
        for raw in section[versions.name]:
            existing = _candidates(db, versions, raw,
                (versions.c.type_id == working[raw['type_id']]) & (versions.c.number == raw['number']))
            if existing:
                expected = {key: working[raw[key]] if key == 'type_id' else raw[key]
                    for key in ('type_id', 'number', 'definition', 'sha256', 'actor_id')}
                if any(existing[key] != value for key, value in expected.items()) or _date(existing['created_at']) != _date(raw['created_at']):
                    _conflict(versions.name, raw)
                working[raw['id']] = existing['id']
            elif raw['type_id'] not in new_types:
                _conflict(versions.name, raw)
            else:
                pending[versions.name].append(raw)
        incoming = {}
        for raw in section[links.name]:
            incoming.setdefault(working[raw['typology_id']], {})[working[raw['type_id']]] = raw['active']
        # Empty incoming composition matters too: do not silently reuse a typology
        # configured differently in the destination.
        typologies = {working[identity] for identity in typology_ids} | set(incoming)
        for typology in typologies:
            actual = {row['type_id']: row['active'] for row in db.execute(select(links).where(links.c.typology_id == typology)).mappings()}
            if actual != incoming.get(typology, {}) and db.execute(select(metadata.tables['project_references'].c.id).where(
                    metadata.tables['project_references'].c.id == typology)).first():
                _conflict(links.name, {'id': typology})
        for raw in section[links.name]:
            existing = _candidates(db, links, raw,
                (links.c.typology_id == working[raw['typology_id']]) & (links.c.type_id == working[raw['type_id']]))
            if existing:
                if any(existing[key] != working[raw[key]] for key in ('typology_id', 'type_id')) or existing['active'] != raw['active']:
                    _conflict(links.name, raw)
                working[raw['id']] = existing['id']
            else:
                pending[links.name].append(raw)
        for raw in section[audits.name]:
            existing = _candidates(db, audits, raw, (audits.c.entity_kind == raw['entity_kind']) & (
                audits.c.entity_id == working[raw['entity_id']]) & (audits.c.revision == raw['revision']))
            if existing:
                wanted = contract.remap_row(raw, audits, working)
                if any(existing[key] != wanted[key] for key in ('entity_kind', 'entity_id', 'revision', 'actor_id', 'previous', 'value')) or (
                        _date(existing['created_at']) != _date(raw['created_at'])):
                    _conflict(audits.name, raw)
                working[raw['id']] = existing['id']
            else:
                pending[audits.name].append(raw)
    mapping.update(working)
    return pending
