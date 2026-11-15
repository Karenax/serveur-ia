"""Paged global catalogue, reference CAS, and explicit project selection.

Caller commits/rolls back. No seeding or project writes on read.
"""
import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import func, or_

from app.db_support import utc_iso
from ..models import Deliverable
from ..project_deliverable_models import (
    DeliverableMilestone, DeliverablePlan, DeliverableType, DeliverableTypeVersion, DeliverableTypologyType,
)
from ..project_deliverable_schemas import DeliverableCreate, TypeDefinition
from ..project_identity_models import ProjectProfile, ProjectReference
from . import project_deliverables as deliverables
from .planning_revision import begin_change, record_change, revision
from .project_deliverable_rules import frozen_json
from .project_identity import _lock_entity, _normalized, _person, _project, _reference, _reference_change
from .project_operator import current_operator, require_reference_write


def _page(query, *, offset, limit):
    if not 0 <= offset <= 1000000 or not 1 <= limit <= 200:
        raise HTTPException(422, 'Pagination invalide')
    return query.offset(offset).limit(limit).all(), query.count()


def _head(row):
    return {key: getattr(row, key) for key in ('id', 'code', 'label', 'active', 'revision')}


def _type(db, identity):
    row = db.get(DeliverableType, identity)
    if row is None:
        raise HTTPException(404, 'Type de livrable introuvable')
    return row


def _version(db, identity):
    row = db.get(DeliverableTypeVersion, identity)
    if row is None:
        raise HTTPException(404, 'Version de type introuvable')
    head = _type(db, row.type_id)
    try:
        if hashlib.sha256(row.definition.encode('utf-8')).hexdigest() != row.sha256:
            raise ValueError('hash')
        definition = TypeDefinition.model_validate_json(row.definition)
    except (ValueError, TypeError) as exc:
        raise HTTPException(409, 'Définition de type invalide ou empreinte incohérente') from exc
    return row, head, definition


def list_types(db, *, search='', include_inactive=False, typology_id=None, offset=0, limit=50):
    if len(search) > 200:
        raise HTTPException(422, 'Recherche trop longue')
    query = db.query(DeliverableType)
    latest_order = db.query(DeliverableTypeVersion.type_id, func.max(DeliverableTypeVersion.number).label('number')).group_by(
        DeliverableTypeVersion.type_id).subquery()
    query = query.outerjoin(latest_order, latest_order.c.type_id == DeliverableType.id).outerjoin(
        DeliverableTypeVersion, (DeliverableTypeVersion.type_id == latest_order.c.type_id)
        & (DeliverableTypeVersion.number == latest_order.c.number))
    if not include_inactive:
        query = query.filter(DeliverableType.active.is_(True))
    if typology_id:
        _reference(db, typology_id, 'typology', allow_inactive=True)
        ids = db.query(DeliverableTypologyType.type_id).filter_by(typology_id=typology_id, active=True)
        query = query.filter(DeliverableType.id.in_(ids))
    if search.strip():
        # Per-connection pure function, with no DDL or row writes. SQLite's
        # built-in lower does not fold French accents/case consistently.
        db.connection().connection.driver_connection.create_function('agent_normalize', 1, _normalized, deterministic=True)
        term = _normalized(search.strip()).replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        query = query.filter(or_(func.agent_normalize(DeliverableType.code).like('%' + term + '%', escape='\\'),
                                func.agent_normalize(DeliverableType.label).like('%' + term + '%', escape='\\')))
    rows, total = _page(query.order_by(func.coalesce(func.json_extract(DeliverableTypeVersion.definition, '$.position'), 0),
                                     DeliverableType.code, DeliverableType.id), offset=offset, limit=limit)
    latest = db.query(DeliverableTypeVersion.type_id, func.max(DeliverableTypeVersion.number).label('number')).filter(
        DeliverableTypeVersion.type_id.in_([row.id for row in rows])).group_by(DeliverableTypeVersion.type_id).subquery()
    versions = {row.type_id: {'id': row.id, 'number': row.number, 'sha256': row.sha256,
                             'position': json.loads(row.definition).get('position', 0)} for row in
        db.query(DeliverableTypeVersion).join(latest, (latest.c.type_id == DeliverableTypeVersion.type_id)
            & (latest.c.number == DeliverableTypeVersion.number))}
    actor = current_operator()
    return {'items': [{**_head(row), 'latest_version': versions.get(row.id)} for row in rows],
            'total': total, 'offset': offset, 'limit': limit,
            'can_manage': actor.role == 'owner' and actor.project_ids is None}


def type_detail(db, identity):
    return _head(_type(db, identity))


def condition_typologies(db, *, search='', include_inactive=False, offset=0, limit=50):
    """Expose authoritative condition codes without changing reference events."""
    from .project_identity import list_references
    result = list_references(db, kind='typology', search=search, include_inactive=include_inactive,
                             offset=offset, limit=limit)
    codes = {row.id: row.normalized_code for row in db.query(ProjectReference).filter(
        ProjectReference.id.in_([item['id'] for item in result['items']]))}
    return {**result, 'items': [{**item, 'condition_code': codes[item['id']]} for item in result['items']]}


def versions(db, identity, *, offset=0, limit=50):
    _type(db, identity)
    query = db.query(DeliverableTypeVersion).filter_by(type_id=identity).order_by(DeliverableTypeVersion.number.desc())
    rows, total = _page(query, offset=offset, limit=limit)
    return {'items': [{'id': row.id, 'number': row.number, 'sha256': row.sha256, 'created_at': utc_iso(row.created_at)}
                      for row in rows], 'total': total, 'offset': offset, 'limit': limit}


def version_detail(db, type_id, version_id):
    row, head, definition = _version(db, version_id)
    if head.id != type_id:
        raise HTTPException(404, 'Version absente de ce type')
    return {'id': row.id, 'type_id': head.id, 'number': row.number, 'sha256': row.sha256,
            'definition': definition.model_dump(), 'published_definition': json.loads(row.definition)}


def patch_type(db, identity, payload):
    actor = require_reference_write()
    row = _type(db, identity)
    before = _head(row)
    _lock_entity(db, DeliverableType, row, payload.expected_revision)
    for key, value in payload.model_dump(exclude_unset=True, exclude={'expected_revision'}).items():
        setattr(row, key, value)
    result = _head(row)
    _reference_change(db, actor, 'deliverable_type', row.id, row.revision, before, result)
    db.flush()
    return result


def typology_types(db, typology_id):
    row = _reference(db, typology_id, 'typology', allow_inactive=True)
    links = db.query(DeliverableTypologyType).filter_by(typology_id=typology_id, active=True).order_by(
        DeliverableTypologyType.type_id).all()
    return {'typology_id': row.id, 'code': row.code, 'revision': row.revision,
            'type_ids': [item.type_id for item in links], 'active': row.active}


def patch_typology_types(db, typology_id, payload):
    actor = require_reference_write()
    row = _reference(db, typology_id, 'typology')
    before = typology_types(db, typology_id)
    _lock_entity(db, ProjectReference, row, payload.expected_revision)
    existing = {item.type_id: item for item in db.query(DeliverableTypologyType).filter_by(typology_id=typology_id)}
    for identity in payload.type_ids:
        item = _type(db, identity)
        if not item.active and (identity not in existing or not existing[identity].active):
            raise HTTPException(409, 'Un type archivé ne peut être ajouté à une typologie')
    for identity, link in existing.items():
        link.active = identity in payload.type_ids
    for identity in set(payload.type_ids) - set(existing):
        db.add(DeliverableTypologyType(typology_id=typology_id, type_id=identity))
    db.flush()
    result = typology_types(db, typology_id)
    _reference_change(db, actor, 'reference', row.id, row.revision,
                      {'deliverable_selection': before}, {'deliverable_selection': result})
    db.flush()
    return result


def _preview(db, project_id, payload, *, before_revision=None):
    actor = _project(db, project_id)
    current_revision = revision(db, project_id) if before_revision is None else before_revision
    if current_revision != payload.expected_revision:
        raise HTTPException(409, 'Projet modifié : recharger la sélection')
    profile = db.get(ProjectProfile, project_id)
    typology_id = profile.typology_id if profile else None
    if payload.typology_id and payload.typology_id != typology_id:
        raise HTTPException(409, 'La typologie choisie doit correspondre à la fiche projet')
    typology = _reference(db, typology_id, 'typology', allow_inactive=True) if typology_id else None
    for person_id in (payload.responsible_id, payload.verifier_id):
        if person_id:
            _person(db, person_id)
    selected = [_version(db, identity) for identity in payload.type_version_ids]
    if len({head.id for _, head, _ in selected}) != len(selected):
        raise HTTPException(422, 'Plusieurs versions du même type sont sélectionnées')
    if any(not head.active for _, head, _ in selected):
        raise HTTPException(409, 'Un type archivé ne peut être sélectionné')
    selected_ids = {head.id for _, head, _ in selected}
    if set(payload.existing_mapping) - selected_ids:
        raise HTTPException(422, 'Correspondance de livrable pour un type non sélectionné')
    expected_codes = {item.milestone_code for _, _, definition in selected for item in definition.checklist
                      if item.active and item.milestone_code}
    if (set(payload.milestone_mapping) | set(payload.excluded_milestone_codes)) - expected_codes:
        raise HTTPException(422, 'Code de jalon non présent dans les types sélectionnés')
    for milestone_id in payload.milestone_mapping.values():
        deliverables._milestone(db, project_id, milestone_id)
    existing = []
    by_type = {}
    for row, plan in db.query(Deliverable, DeliverablePlan).outerjoin(DeliverablePlan,
        DeliverablePlan.deliverable_id == Deliverable.id).filter(Deliverable.project_id == project_id):
        if plan and plan.project_id != project_id:
            raise HTTPException(409, 'Rattachement de livrable incohérent')
        existing.append((row, plan))
        if plan and plan.type_version_id:
            type_version, _, _ = _version(db, plan.type_version_id)
            by_type.setdefault(type_version.type_id, []).append((row, plan))
    operations, blockers, warnings = [], [], []
    chosen = set()
    for version, head, definition in sorted(selected, key=lambda item: item[1].id):
        explicit = payload.existing_mapping.get(head.id)
        candidates = by_type.get(head.id, [])
        target = next(((row, plan) for row, plan in existing if row.id == explicit), None) if explicit else None
        if explicit and target is None:
            raise HTTPException(422, 'Livrable choisi absent de ce projet')
        if target and target[1] and target[1].type_version_id and target not in candidates:
            raise HTTPException(422, 'Ce livrable utilise déjà un autre type')
        if not target and len(candidates) > 1:
            blockers.append({'type_id': head.id, 'message': 'Plusieurs livrables de ce type : choisir la cible',
                             'candidate_ids': sorted(row.id for row, _ in candidates)})
            continue
        if not target and candidates:
            target = candidates[0]
        row, plan = target if target else (None, None)
        if row:
            chosen.add(row.id)
        adopting = bool(row and (plan is None or plan.type_version_id is None))
        action = 'create' if not row else 'adopt' if adopting else 'reactivate' if not plan.active else 'keep'
        if plan and action != 'keep' and plan.document_status in {'validated', 'to_verify', 'archived'}:
            blockers.append({'type_id': head.id, 'message': 'Rouvrir le livrable avant de modifier sa sélection',
                             'deliverable_id': row.id})
        if action in {'create', 'adopt'}:
            if adopting:
                blockers.extend({'type_id': head.id, 'deliverable_id': row.id, **conflict}
                    for conflict in deliverables.checklist_conflicts(db, row, definition, payload.milestone_mapping))
            for item in definition.checklist:
                if not item.active or item.milestone_code in payload.excluded_milestone_codes:
                    continue
                if item.typology_codes:
                    if typology is None:
                        blockers.append({'type_id': head.id, 'message': 'Typologie requise pour les contrôles conditionnels'})
                        continue
                    if typology.normalized_code not in item.typology_codes:
                        continue
                if item.milestone_code and item.milestone_code not in payload.milestone_mapping and item.milestone_code not in payload.excluded_milestone_codes:
                    blockers.append({'type_id': head.id, 'code': item.milestone_code,
                                     'message': 'Rattacher ou exclure explicitement ce jalon'})
        if plan and plan.type_version_id and plan.type_version_id != version.id:
            warnings.append({'type_id': head.id, 'deliverable_id': row.id,
                             'message': 'Version projet conservée ; la sélection ne remplace pas sa checklist',
                             'retained_version_id': plan.type_version_id})
        operations.append({'operation': action, 'type_id': head.id, 'version_id': version.id,
                           'deliverable_id': row.id if row else None, 'label': row.title if row else head.label})
    if payload.deactivate_missing:
        for row, plan in sorted(existing, key=lambda pair: pair[0].id):
            if not plan or not plan.active or not plan.type_version_id or row.id in chosen:
                continue
            # Ambiguous selected types must not be deactivated as collateral.
            old, _, _ = _version(db, plan.type_version_id)
            if old.type_id in selected_ids:
                continue
            if plan.document_status in {'validated', 'to_verify'}:
                blockers.append({'deliverable_id': row.id, 'message': 'Rouvrir ou archiver avant désactivation'})
            operations.append({'operation': 'deactivate', 'type_id': old.type_id, 'version_id': plan.type_version_id,
                               'deliverable_id': row.id, 'label': row.title})
    input_values = payload.model_dump(exclude={'expected_preview_sha256'})
    fingerprint = {'project_id': project_id, 'revision': current_revision, 'inputs': input_values,
        'profile': {'revision': profile.revision, 'typology_id': profile.typology_id} if profile else None,
        'typology': {'id': typology.id, 'revision': typology.revision, 'active': typology.active} if typology else None,
        'types': [{**_head(head), 'version_id': version.id, 'sha256': version.sha256} for version, head, _ in selected],
        'operations': operations, 'blockers': blockers, 'warnings': warnings}
    _, sha = frozen_json(fingerprint)
    return {'project_id': project_id, 'revision': current_revision, 'can_edit': actor.role != 'reader',
            'operations': operations, 'blockers': blockers, 'warnings': warnings, 'sha256': sha,
            'changes': sum(item['operation'] != 'keep' for item in operations)}


def preview_selection(db, project_id, payload):
    return _preview(db, project_id, payload)


def apply_selection(db, project_id, payload):
    actor, state = begin_change(db, project_id, payload.expected_revision)
    preview = _preview(db, project_id, payload, before_revision=state.revision - 1)
    if preview['sha256'] != payload.expected_preview_sha256:
        raise HTTPException(409, 'Aperçu périmé : relire avant d’appliquer la sélection')
    if preview['blockers']:
        raise HTTPException(409, {'message': 'Sélection non applicable', 'blockers': preview['blockers']})
    changed = []
    for operation in preview['operations']:
        action = operation['operation']
        if action == 'keep':
            continue
        if action == 'create':
            version, _, definition = _version(db, operation['version_id'])
            codes = {item.milestone_code for item in definition.checklist if item.active and item.milestone_code}
            mapping = {key: value for key, value in payload.milestone_mapping.items() if key in codes}
            created = deliverables._create_locked(db, project_id, DeliverableCreate(expected_revision=state.revision - 1,
                title=operation['label'], type_version_id=version.id, milestone_ids=sorted(set(mapping.values())),
                milestone_mapping=mapping, responsible_id=payload.responsible_id, verifier_id=payload.verifier_id),
                actor, state, planning_event=False)
            changed.append({**operation, 'deliverable_id': created['id']})
            continue
        row, _ = deliverables._item(db, project_id, operation['deliverable_id'])
        plan = deliverables._plan(db, row)
        previous = {'active': plan.active, 'type_version_id': plan.type_version_id,
                    'responsible_id': plan.responsible_id, 'verifier_id': plan.verifier_id}
        if action == 'adopt':
            version, _, definition = _version(db, operation['version_id'])
            codes = {item.milestone_code for item in definition.checklist if item.active and item.milestone_code}
            mapping = {key: value for key, value in payload.milestone_mapping.items() if key in codes}
            plan.type_version_id = version.id
            # Preserve manual responsibilities and all existing checklist/files.
            if plan.responsible_id is None:
                plan.responsible_id = payload.responsible_id
            if plan.verifier_id is None:
                plan.verifier_id = payload.verifier_id
            links = {item.milestone_id for item in db.query(DeliverableMilestone).filter_by(deliverable_id=row.id)}
            for identity in set(mapping.values()) - links:
                db.add(DeliverableMilestone(project_id=project_id, deliverable_id=row.id, milestone_id=identity))
            deliverables._instantiate_checklist(db, row, definition, mapping)
        plan.active = action != 'deactivate'
        deliverables._event(db, actor, state, row, 'deliverable_selection_changed', previous,
            {'active': plan.active, 'type_version_id': plan.type_version_id,
             'responsible_id': plan.responsible_id, 'verifier_id': plan.verifier_id}, planning_event=False)
        changed.append(operation)
    # Exactly one planning event per revision, even for several deliverables.
    record_change(db, actor, state, 'deliverable_selection_applied', {},
                  {'preview_sha256': preview['sha256'], 'operations': changed,
                   'inputs': payload.model_dump(exclude={'expected_preview_sha256'}),
                   'excluded_milestone_codes': payload.excluded_milestone_codes})
    db.flush()
    return {'revision': state.revision, 'changed': changed, 'warnings': preview['warnings']}
