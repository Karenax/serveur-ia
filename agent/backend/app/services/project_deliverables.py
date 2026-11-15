"""L3 transactional commands; caller commits/rolls back, no implicit migration.

HTTP acquisition authorizes managed copies before calling publish_file.
Generation, inherited progress status and human documentary visa stay distinct.
"""
import hashlib
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import func, update

from ..models import Deliverable, DeliveryVersion, Milestone
from ..project_deliverable_models import (
    DeliverableChecklistItem, DeliverableEvent, DeliverableFileVersion, DeliverableMilestone,
    DeliverablePlan, DeliverableType, DeliverableTypeVersion, DeliverableVersionMetadata,
)
from ..project_identity_models import ProjectProfile, ProjectReference, now
from .planning_revision import begin_change, record_change, revision
from .project_deliverable_rules import (
    file_digest, frozen_json, progress, validate_transition, validation_blockers,
)
from .project_identity import _flush, _person, _project, _reference_change
from .project_operator import require_reference_write


def _item(db, project_id, deliverable_id):
    _project(db, project_id)
    row = db.query(Deliverable).filter_by(project_id=project_id, id=deliverable_id).first()
    if row is None:
        raise HTTPException(404, 'Livrable introuvable')
    plan = db.get(DeliverablePlan, row.id)
    if plan and plan.project_id != project_id:
        raise HTTPException(409, 'Rattachement de livrable incohérent')
    return row, plan


def _plan(db, row):
    plan = db.get(DeliverablePlan, row.id)
    if plan is None:
        # Historical done remains a legacy status, never a human visa.
        plan = DeliverablePlan(deliverable_id=row.id, project_id=row.project_id)
        db.add(plan)
        db.flush()
    return plan


def _latest(db, row):
    return db.query(DeliverableFileVersion).filter_by(deliverable_id=row.id, project_id=row.project_id).order_by(
        DeliverableFileVersion.number.desc()).first()


def _checks(db, row):
    return db.query(DeliverableChecklistItem).filter_by(deliverable_id=row.id, project_id=row.project_id).order_by(
        DeliverableChecklistItem.position, DeliverableChecklistItem.id).all()


def _check_values(item):
    fields = ('id', 'code', 'scope_key', 'milestone_id', 'label', 'position', 'is_gate', 'transverse', 'contributes',
              'active', 'completed', 'completed_version_id', 'completed_by', 'comment', 'proof')
    return {**{field: getattr(item, field) for field in fields},
            'completed_at': item.completed_at.isoformat() if item.completed_at else None}


def _event(db, actor, state, row, action, previous, value, *, planning_event=True):
    db.add(DeliverableEvent(project_id=row.project_id, deliverable_id=row.id, revision=state.revision,
                           actor_id=actor.id, action=action, previous=previous, value=value))
    if planning_event:
        record_change(db, actor, state, action, {'deliverable_id': row.id, **previous}, {'deliverable_id': row.id, **value})
    db.flush()


def _verifier(db, actor, plan):
    if actor.role == 'owner':
        return
    if not actor.person_id or actor.person_id != plan.verifier_id:
        raise HTTPException(403, 'Visa réservé au vérificateur désigné ou au propriétaire')
    _person(db, actor.person_id)


def _milestone(db, project_id, milestone_id):
    row = db.query(Milestone).filter_by(project_id=project_id, id=milestone_id).first()
    if row is None:
        raise HTTPException(422, 'Jalon absent de ce projet')
    return row


def create_type(db, payload):
    actor = require_reference_write()
    if db.query(DeliverableType).filter_by(code=payload.code).first():
        raise HTTPException(409, 'Code de type de livrable déjà utilisé')
    row = DeliverableType(code=payload.code, label=payload.label)
    db.add(row)
    _flush(db, 'Code de type déjà utilisé')
    definition, sha = frozen_json(payload.definition.model_dump())
    version = DeliverableTypeVersion(type_id=row.id, number=1, definition=definition, sha256=sha, actor_id=actor.id)
    db.add(version)
    db.flush()
    result = {'id': row.id, 'version_id': version.id, 'revision': row.revision, 'sha256': sha}
    _reference_change(db, actor, 'deliverable_type', row.id, row.revision, {},
                      {**result, 'code': row.code, 'label': row.label, 'active': row.active})
    return result


def publish_type(db, type_id, payload):
    actor = require_reference_write()
    changed = db.execute(update(DeliverableType).where(DeliverableType.id == type_id,
        DeliverableType.revision == payload.expected_revision, DeliverableType.active.is_(True)).values(
        revision=DeliverableType.revision + 1).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise HTTPException(409, 'Catalogue modifié ou type indisponible : recharger')
    db.expire_all()
    definition, sha = frozen_json(payload.definition.model_dump())
    number = db.query(func.max(DeliverableTypeVersion.number)).filter_by(type_id=type_id).scalar() + 1
    version = DeliverableTypeVersion(type_id=type_id, number=number, definition=definition, sha256=sha, actor_id=actor.id)
    db.add(version)
    db.flush()
    result = {'id': type_id, 'version_id': version.id, 'revision': db.get(DeliverableType, type_id).revision, 'sha256': sha}
    _reference_change(db, actor, 'deliverable_type', type_id, result['revision'], {}, {'published_version': result})
    return result


def create_deliverable(db, project_id, payload):
    actor, state = begin_change(db, project_id, payload.expected_revision)
    return _create_locked(db, project_id, payload, actor, state)


def _create_locked(db, project_id, payload, actor, state, *, planning_event=True, legacy_status=None):
    for person_id in (payload.responsible_id, payload.verifier_id):
        if person_id:
            _person(db, person_id)
    version = db.get(DeliverableTypeVersion, payload.type_version_id) if payload.type_version_id else None
    if payload.type_version_id and (not version or not db.get(DeliverableType, version.type_id).active):
        raise HTTPException(422, 'Version de type indisponible')
    from ..project_deliverable_schemas import TypeDefinition
    definition = TypeDefinition.model_validate_json(version.definition) if version else TypeDefinition()
    if version and hashlib.sha256(version.definition.encode('utf-8')).hexdigest() != version.sha256:
        raise HTTPException(409, 'Empreinte de type incohérente')
    expected_codes = {item.milestone_code for item in definition.checklist if item.active and item.milestone_code}
    if set(payload.milestone_mapping) - expected_codes:
        raise HTTPException(422, 'Correspondance de checklist inconnue')
    if any(value not in payload.milestone_ids for value in payload.milestone_mapping.values()):
        raise HTTPException(422, 'La correspondance doit désigner un jalon sélectionné')
    for milestone_id in payload.milestone_ids:
        _milestone(db, project_id, milestone_id)
    row = Deliverable(project_id=project_id, title=payload.title, status=legacy_status or 'todo')
    db.add(row)
    db.flush()
    plan = _plan(db, row)
    plan.type_version_id = payload.type_version_id
    plan.responsible_id, plan.verifier_id = payload.responsible_id, payload.verifier_id
    for milestone_id in payload.milestone_ids:
        db.add(DeliverableMilestone(project_id=project_id, deliverable_id=row.id, milestone_id=milestone_id))
    _instantiate_checklist(db, row, definition, payload.milestone_mapping)
    _event(db, actor, state, row, 'deliverable_created', {}, {'title': row.title, 'type_version_id': plan.type_version_id,
        'milestone_ids': payload.milestone_ids, 'milestone_mapping': payload.milestone_mapping,
        'responsible_id': plan.responsible_id, 'verifier_id': plan.verifier_id,
        **({'legacy_status': legacy_status} if legacy_status is not None else {})}, planning_event=planning_event)
    return {'id': row.id, 'revision': state.revision}


def create_legacy_deliverable(db, project_id, *, title, status='todo', expected_revision=None):
    from ..project_deliverable_schemas import DeliverableCreate
    if status not in {'todo', 'in_progress', 'done', 'cancelled'}:
        raise HTTPException(422, 'Statut historique invalide')
    actor, state = begin_change(db, project_id, expected_revision)
    payload = DeliverableCreate(expected_revision=state.revision - 1, title=title)
    result = _create_locked(db, project_id, payload, actor, state, legacy_status=status)
    return {**result, 'title': title, 'status': status}


def patch_legacy_deliverable(db, project_id, deliverable_id, changes, expected_revision=None):
    from ..project_deliverable_schemas import DeliverablePatch
    values = {key: value for key, value in changes.items() if value is not None}
    if set(values) - {'title', 'status'} or values.get('status', 'todo') not in {'todo', 'in_progress', 'done', 'cancelled'}:
        raise HTTPException(422, 'Modification historique invalide')
    # Validate a title before allocating a revision, also for internal callers.
    if 'title' in values:
        DeliverablePatch(expected_revision=0, title=values['title'])
    actor, state = begin_change(db, project_id, expected_revision)
    row, _ = _item(db, project_id, deliverable_id)
    _plan(db, row)
    before = {'title': row.title, **({'legacy_status': row.status} if 'status' in values else {})}
    for field, value in values.items():
        setattr(row, field, value)
    captured = {('legacy_status' if field == 'status' else field): value for field, value in values.items()}
    _event(db, actor, state, row, 'deliverable_metadata_changed', before, captured)
    return {'id': row.id, 'title': row.title, 'status': row.status, 'revision': state.revision}


def _instantiate_checklist(db, row, definition, mapping):
    profile = db.get(ProjectProfile, row.project_id)
    typology = db.get(ProjectReference, profile.typology_id) if profile and profile.typology_id else None
    code = typology.normalized_code if typology else None
    previous_checks = _checks(db, row)
    conflicts = checklist_conflicts(db, row, definition, mapping)
    if conflicts:
        raise HTTPException(409, {'message': 'Un contrôle manuel masque un gate du catalogue', 'blocking_checks': conflicts})
    existing = {(item.code, item.scope_key) for item in previous_checks}
    next_position = max((item.position for item in previous_checks), default=-1) + 1
    for index, item in enumerate(definition.checklist):
        if not item.active or item.milestone_code and item.milestone_code not in mapping:
            continue
        if item.typology_codes:
            if code is None:
                raise HTTPException(409, 'Définir la typologie pour les contrôles conditionnels')
            if code not in item.typology_codes:
                continue
        if (item.code, item.milestone_code) in existing:
            continue
        milestone_id = mapping.get(item.milestone_code)
        db.add(DeliverableChecklistItem(project_id=row.project_id, deliverable_id=row.id, code=item.code,
            scope_key=item.milestone_code, milestone_id=milestone_id, label=item.label, position=next_position + index,
            is_gate=item.is_gate, transverse=item.transverse, contributes=item.contributes))


def checklist_conflicts(db, row, definition, mapping):
    profile = db.get(ProjectProfile, row.project_id)
    typology = db.get(ProjectReference, profile.typology_id) if profile and profile.typology_id else None
    code = typology.normalized_code if typology else None
    existing = {(item.code, item.scope_key): item for item in _checks(db, row)}
    conflicts = []
    for item in definition.checklist:
        if (not item.active or not item.is_gate or item.milestone_code and item.milestone_code not in mapping
                or item.typology_codes and code not in item.typology_codes):
            continue
        previous = existing.get((item.code, item.milestone_code))
        if previous and (not previous.is_gate or not previous.active
                         or previous.milestone_id != mapping.get(item.milestone_code)
                         or previous.transverse != item.transverse or previous.contributes != item.contributes):
            conflicts.append({'code': item.code, 'scope_key': item.milestone_code,
                              'message': 'Choisir un autre code dans le catalogue ou un livrable distinct pour conserver le gate'})
    return conflicts


def read_deliverable(db, project_id, deliverable_id):
    row, plan = _item(db, project_id, deliverable_id)
    items = [_check_values(item) for item in _checks(db, row)]
    latest = _latest(db, row)
    return {'id': row.id, 'title': row.title, 'legacy_status': row.status, 'project_id': project_id,
        'revision': revision(db, project_id), 'document_status': plan.document_status if plan else 'draft',
        'active': plan.active if plan else True, 'comment': plan.comment if plan else '',
        'responsible_id': plan.responsible_id if plan else None, 'verifier_id': plan.verifier_id if plan else None,
        'type_version_id': plan.type_version_id if plan else None, 'latest_version_id': latest.id if latest else None,
        'checklist': items, 'progress': progress(items), 'transverse_progress': progress(items, transverse=True),
        'validation_blockers': validation_blockers(items, latest.id if latest else None),
        'milestone_ids': [link.milestone_id for link in db.query(DeliverableMilestone).filter_by(
            project_id=project_id, deliverable_id=row.id, active=True).order_by(DeliverableMilestone.id)]}


def patch_deliverable(db, project_id, deliverable_id, payload):
    actor, state = begin_change(db, project_id, payload.expected_revision)
    row, _ = _item(db, project_id, deliverable_id)
    plan = _plan(db, row)
    values = payload.model_dump(exclude_unset=True, exclude={'expected_revision'})
    before = {'title': row.title, **{key: getattr(plan, key) for key in values if key != 'title'}}
    for person_id in (values.get('responsible_id'), values.get('verifier_id')):
        if person_id:
            _person(db, person_id)
    if plan.document_status == 'validated' and any(key in values and values[key] != getattr(plan, key)
                                                 for key in ('verifier_id', 'responsible_id')):
        raise HTTPException(409, 'Rouvrir le livrable avant de changer ses responsables')
    for key, value in values.items():
        setattr(row if key == 'title' else plan, key, value)
    _event(db, actor, state, row, 'deliverable_metadata_changed', before, values)
    return read_deliverable(db, project_id, deliverable_id)


def create_check(db, project_id, deliverable_id, payload):
    actor, state = begin_change(db, project_id, payload.expected_revision)
    row, _ = _item(db, project_id, deliverable_id)
    plan = _plan(db, row)
    if plan.document_status in {'validated', 'archived'}:
        raise HTTPException(409, 'Rouvrir le livrable avant de modifier sa checklist')
    if payload.milestone_id:
        _milestone(db, project_id, payload.milestone_id)
        if not db.query(DeliverableMilestone).filter_by(project_id=project_id, deliverable_id=row.id,
                                                       milestone_id=payload.milestone_id, active=True).first():
            raise HTTPException(422, 'Rattacher le jalon au livrable avant sa checklist')
    if db.query(DeliverableChecklistItem).filter_by(deliverable_id=row.id, code=payload.code, scope_key='').first():
        raise HTTPException(409, 'Code de checklist déjà utilisé')
    item = DeliverableChecklistItem(project_id=project_id, deliverable_id=row.id,
        position=len(_checks(db, row)), **payload.model_dump(exclude={'expected_revision'}))
    db.add(item)
    db.flush()
    _event(db, actor, state, row, 'deliverable_check_created', {}, _check_values(item))
    return {'item': _check_values(item), 'revision': state.revision}


def patch_check(db, project_id, deliverable_id, item_id, payload):
    actor, state = begin_change(db, project_id, payload.expected_revision)
    row, _ = _item(db, project_id, deliverable_id)
    plan = _plan(db, row)
    item = db.query(DeliverableChecklistItem).filter_by(project_id=project_id, deliverable_id=row.id, id=item_id).first()
    if not item:
        raise HTTPException(404, 'Point de checklist introuvable')
    if plan.document_status in {'validated', 'archived'}:
        raise HTTPException(409, 'Rouvrir le livrable avant de modifier sa checklist')
    before = _check_values(item)
    values = payload.model_dump(exclude_unset=True, exclude={'expected_revision'})
    if item.is_gate:
        _verifier(db, actor, plan)
        if values.get('active') is False:
            raise HTTPException(409, 'Un gate obligatoire ne peut être désactivé')
    for key, value in values.items():
        setattr(item, key, value)
    if values.get('completed') is True:
        if not item.active:
            raise HTTPException(409, 'Point de checklist inactif')
        latest = _latest(db, row)
        if item.is_gate and (not latest or not item.proof.strip()):
            raise HTTPException(409, 'Un visa requiert une version publiée et une preuve humaine')
        if item.is_gate:
            _verify_file(db, latest)
        item.completed_version_id = latest.id if latest else None
        item.completed_by, item.completed_at = actor.id, now()
    elif (values.get('completed') is False or 'label' in values and values['label'] != before['label']
          or item.is_gate and 'proof' in values and values['proof'] != before['proof']):
        item.completed, item.completed_version_id, item.completed_by, item.completed_at = False, None, None, None
    _event(db, actor, state, row, 'deliverable_check_changed', before, _check_values(item))
    return {'item': _check_values(item), 'revision': state.revision}


def version_file_path(db, version):
    metadata = db.get(DeliverableVersionMetadata, version.id)
    if metadata is None or metadata.project_id != version.project_id:
        raise HTTPException(409, 'Métadonnées de version incomplètes')
    return metadata.storage_path or version.path


def _verify_file(db, version):
    digest = file_digest(version_file_path(db, version))
    if digest != {'sha256': version.sha256, 'size_bytes': version.size_bytes}:
        raise HTTPException(409, 'Fichier modifié : publier une nouvelle version')
    from app.services.deliverable_manifest import check_row
    try:
        check_row({key: getattr(version, key) for key in ('manifest', 'manifest_sha256', 'project_id',
            'deliverable_id', 'number', 'filename', 'sha256', 'size_bytes', 'source_delivery_id', 'generated', 'actor_id')})
    except ValueError as exc:
        raise HTTPException(409, 'Manifeste de version incohérent') from exc
    return digest


def publish_file(db, project_id, deliverable_id, payload, *, path):
    actor, state = begin_change(db, project_id, payload.expected_revision)
    row, _ = _item(db, project_id, deliverable_id)
    plan = _plan(db, row)
    if plan.document_status == 'archived':
        raise HTTPException(409, 'Rouvrir le livrable avant de publier')
    source = db.get(DeliveryVersion, payload.source_delivery_id) if payload.source_delivery_id else None
    if payload.source_delivery_id and (not source or source.project_id != project_id):
        raise HTTPException(422, 'Livraison CDC absente de ce projet')
    if source and db.query(DeliverableFileVersion).filter_by(source_delivery_id=source.id).first():
        raise HTTPException(409, 'Livraison CDC déjà reliée à un livrable')
    path = Path(path).resolve()
    if source and Path(source.path).resolve() != path:
        raise HTTPException(422, 'Le fichier doit être la livraison CDC conservée')
    digest = file_digest(path)
    if source and source.sha256 != digest['sha256']:
        raise HTTPException(409, 'Fichier CDC modifié : rétablir la livraison originale')
    latest = _latest(db, row)
    number = latest.number + 1 if latest else 1
    manifest_value = {'format': 'agent-deliverable-version', 'version': 1, 'project_id': project_id,
        'deliverable_id': row.id, 'number': number, 'filename': path.name, **digest,
        'reference': payload.reference, 'comment': payload.comment,
        'source_delivery_id': payload.source_delivery_id, 'generated': payload.generated or bool(source),
        'type_version_id': plan.type_version_id, 'checklist': [_check_values(item) for item in _checks(db, row)],
        'actor_id': actor.id}
    manifest, sha = frozen_json(manifest_value)
    version = DeliverableFileVersion(project_id=project_id, deliverable_id=row.id, number=number,
        path=str(path), filename=path.name, **digest, manifest=manifest, manifest_sha256=sha,
        generated=manifest_value['generated'], actor_id=actor.id, source_delivery_id=payload.source_delivery_id)
    db.add(version)
    db.flush()
    db.add(DeliverableVersionMetadata(project_id=project_id, version_id=version.id,
                                     reference=payload.reference, comment=payload.comment, storage_path=str(path)))
    previous_status = plan.document_status
    plan.document_status = 'draft'
    # Visa is specific to bytes. Ordinary preparation checks remain completed.
    for item in _checks(db, row):
        if item.is_gate:
            item.completed, item.completed_version_id, item.completed_by, item.completed_at = False, None, None, None
    _event(db, actor, state, row, 'deliverable_version_published', {'document_status': previous_status},
           {'version_id': version.id, 'number': number, 'sha256': version.sha256,
            'manifest_sha256': sha, 'document_status': 'draft', 'source_delivery_id': payload.source_delivery_id})
    return {'version_id': version.id, 'number': number, 'revision': state.revision, 'sha256': version.sha256}


def patch_version_metadata(db, project_id, deliverable_id, version_id, payload):
    actor, state = begin_change(db, project_id, payload.expected_revision)
    row, _ = _item(db, project_id, deliverable_id)
    version = db.query(DeliverableFileVersion).filter_by(project_id=project_id, deliverable_id=row.id, id=version_id).first()
    if not version:
        raise HTTPException(404, 'Version introuvable')
    metadata = db.get(DeliverableVersionMetadata, version_id)
    if metadata is None or metadata.project_id != project_id:
        raise HTTPException(409, 'Métadonnées de version incomplètes')
    values = payload.model_dump(exclude_unset=True, exclude={'expected_revision'})
    before = {key: getattr(metadata, key) for key in values}
    for key, value in values.items():
        setattr(metadata, key, value)
    _event(db, actor, state, row, 'deliverable_version_metadata_changed',
           {'version_id': version_id, **before}, {'version_id': version_id, **values})
    return {'version_id': version_id, 'revision': state.revision}


def transition(db, project_id, deliverable_id, payload):
    actor, state = begin_change(db, project_id, payload.expected_revision)
    row, _ = _item(db, project_id, deliverable_id)
    plan = _plan(db, row)
    latest = _latest(db, row)
    if not latest or latest.id != payload.version_id:
        raise HTTPException(409, 'La commande doit porter sur la dernière version publiée')
    validate_transition(plan.document_status, payload.status)
    if payload.status in {'to_verify', 'validated'}:
        if not plan.active:
            raise HTTPException(409, 'Livrable inactif')
        if not plan.verifier_id:
            raise HTTPException(409, 'Désigner un vérificateur avant la soumission')
        _person(db, plan.verifier_id)
        _verify_file(db, latest)
    if payload.status in {'validated', 'to_revise'} and plan.document_status == 'to_verify':
        _verifier(db, actor, plan)
    if payload.status == 'validated':
        blockers = validation_blockers([_check_values(item) for item in _checks(db, row)], latest.id)
        if blockers:
            raise HTTPException(409, {'message': 'Gates obligatoires non visés', 'blocking_checks': blockers})
        if not payload.comment.strip():
            raise HTTPException(422, 'Commentaire de visa humain requis')
    previous = plan.document_status
    plan.document_status = payload.status
    if payload.status == 'to_revise':
        for item in _checks(db, row):
            if item.is_gate:
                item.completed, item.completed_version_id, item.completed_by, item.completed_at = False, None, None, None
    _event(db, actor, state, row, 'deliverable_status_changed', {'document_status': previous},
           {'document_status': plan.document_status, 'version_id': latest.id, 'comment': payload.comment})
    return {'document_status': plan.document_status, 'revision': state.revision}
