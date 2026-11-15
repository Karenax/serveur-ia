"""Scoped, paged L3 reads; never instantiate plans or rewrite historical data."""
import json

from fastapi import HTTPException
from sqlalchemy import case, func, or_

from app.db_support import utc_iso
from ..models import Deliverable, Milestone
from ..project_deliverable_models import (
    DeliverableChecklistItem, DeliverableEvent, DeliverableFileVersion, DeliverableMilestone,
    DeliverablePlan, DeliverableType, DeliverableTypeVersion, DeliverableVersionMetadata,
)
from . import project_deliverables as commands
from .planning_revision import revision
from .project_identity import _normalized, _project
from .project_operator import current_operator


def _page(query, offset, limit):
    if not 0 <= offset <= 1000000 or not 1 <= limit <= 200:
        raise HTTPException(422, 'Pagination invalide')
    total = query.count()
    return query.offset(offset).limit(limit).all(), total


def _result(items, total, offset, limit, project_id, db):
    return {'items': items, 'total': total, 'offset': offset, 'limit': limit,
            'revision': revision(db, project_id)}


def _search(db, query, search, columns):
    if len(search) > 200:
        raise HTTPException(422, 'Recherche trop longue')
    if search.strip():
        db.connection().connection.driver_connection.create_function('agent_normalize', 1,
            lambda value: _normalized(value or ''), deterministic=True)
        term = _normalized(search.strip()).replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        query = query.filter(or_(*(func.agent_normalize(column).like('%' + term + '%', escape='\\')
                                  for column in columns)))
    return query


def _progress(completed, total):
    return {'completed': completed, 'total': total, 'percentage': round(100 * completed / total) if total else 0,
            'state': 'complete' if total and completed == total else 'pending' if total else 'not_applicable'}


def list_deliverables(db, project_id, *, search='', include_inactive=False, status=None, category=None,
                      milestone_id=None, responsible_id=None, verifier_id=None, offset=0, limit=50):
    actor = _project(db, project_id)
    if status is not None and status not in {'draft', 'to_verify', 'validated', 'to_revise', 'archived'}:
        raise HTTPException(422, 'Statut documentaire invalide')
    if category is not None and category not in {'studies', 'fabrication', 'project_end', 'custom'}:
        raise HTTPException(422, 'Catégorie invalide')
    query = db.query(Deliverable, DeliverablePlan, DeliverableTypeVersion, DeliverableType).outerjoin(
        DeliverablePlan, DeliverablePlan.deliverable_id == Deliverable.id).outerjoin(
        DeliverableTypeVersion, DeliverableTypeVersion.id == DeliverablePlan.type_version_id).outerjoin(
        DeliverableType, DeliverableType.id == DeliverableTypeVersion.type_id).filter(Deliverable.project_id == project_id)
    if not include_inactive:
        query = query.filter(or_(DeliverablePlan.deliverable_id.is_(None), DeliverablePlan.active.is_(True)))
    if status:
        query = query.filter(func.coalesce(DeliverablePlan.document_status, 'draft') == status)
    if category:
        query = query.filter(func.coalesce(func.json_extract(DeliverableTypeVersion.definition, '$.category'), 'custom') == category)
    if milestone_id:
        if not db.query(Milestone).filter_by(project_id=project_id, id=milestone_id).first():
            raise HTTPException(404, 'Jalon introuvable dans ce projet')
        query = query.filter(Deliverable.id.in_(db.query(DeliverableMilestone.deliverable_id).filter_by(
            project_id=project_id, milestone_id=milestone_id, active=True)))
    for value, column in ((responsible_id, DeliverablePlan.responsible_id), (verifier_id, DeliverablePlan.verifier_id)):
        if value:
            query = query.filter(column == value)
    query = _search(db, query, search, (Deliverable.title, DeliverableType.label, DeliverableType.code))
    rows, total = _page(query.order_by(func.coalesce(DeliverablePlan.position, 0),
                                     func.lower(Deliverable.title), Deliverable.id), offset, limit)
    identities = [row.id for row, *_ in rows]
    checks = DeliverableChecklistItem
    counts = {(owner, transverse): _progress(int(done), int(count)) for owner, transverse, done, count in db.query(
        checks.deliverable_id, checks.transverse, func.sum(case((checks.completed.is_(True), 1), else_=0)), func.count())
        .filter(checks.project_id == project_id, checks.deliverable_id.in_(identities), checks.active.is_(True),
                checks.contributes.is_(True)).group_by(checks.deliverable_id, checks.transverse)}
    latest_numbers = db.query(DeliverableFileVersion.deliverable_id, func.max(DeliverableFileVersion.number).label('number')).filter(
        DeliverableFileVersion.project_id == project_id, DeliverableFileVersion.deliverable_id.in_(identities)).group_by(
        DeliverableFileVersion.deliverable_id).subquery()
    latest = {row.deliverable_id: _version_values(row, meta) for row, meta in db.query(
        DeliverableFileVersion, DeliverableVersionMetadata).join(latest_numbers,
        (latest_numbers.c.deliverable_id == DeliverableFileVersion.deliverable_id)
        & (latest_numbers.c.number == DeliverableFileVersion.number)).outerjoin(DeliverableVersionMetadata,
            (DeliverableVersionMetadata.version_id == DeliverableFileVersion.id)
            & (DeliverableVersionMetadata.project_id == project_id))}
    links = {}
    for owner, identity in db.query(DeliverableMilestone.deliverable_id, DeliverableMilestone.milestone_id).filter(
            DeliverableMilestone.project_id == project_id, DeliverableMilestone.deliverable_id.in_(identities),
            DeliverableMilestone.active.is_(True)).order_by(DeliverableMilestone.milestone_id):
        links.setdefault(owner, []).append(identity)
    items = []
    for row, plan, version, head in rows:
        if plan and plan.project_id != project_id:
            raise HTTPException(409, 'Rattachement de livrable incohérent')
        definition = json.loads(version.definition) if version else {}
        items.append({'id': row.id, 'project_id': project_id, 'title': row.title, 'legacy_status': row.status,
            'active': plan.active if plan else True, 'document_status': plan.document_status if plan else 'draft',
            'responsible_id': plan.responsible_id if plan else None, 'verifier_id': plan.verifier_id if plan else None,
            'type_version_id': version.id if version else None, 'category': definition.get('category', 'custom'),
            'type': {'id': head.id, 'code': head.code, 'label': head.label} if head else None,
            'progress': counts.get((row.id, False), _progress(0, 0)),
            'transverse_progress': counts.get((row.id, True), _progress(0, 0)),
            'latest_version': latest.get(row.id), 'milestone_ids': links.get(row.id, [])})
    return {**_result(items, total, offset, limit, project_id, db), 'can_edit': actor.role != 'reader'}


def checklist(db, project_id, deliverable_id, *, search='', include_inactive=False, offset=0, limit=50):
    commands._item(db, project_id, deliverable_id)
    query = db.query(DeliverableChecklistItem).filter_by(project_id=project_id, deliverable_id=deliverable_id)
    if not include_inactive:
        query = query.filter(DeliverableChecklistItem.active.is_(True))
    query = _search(db, query, search, (DeliverableChecklistItem.code, DeliverableChecklistItem.label))
    rows, total = _page(query.order_by(DeliverableChecklistItem.position, DeliverableChecklistItem.id), offset, limit)
    return _result([commands._check_values(row) for row in rows], total, offset, limit, project_id, db)


def _version(db, project_id, deliverable_id, version_id):
    commands._item(db, project_id, deliverable_id)
    row = db.query(DeliverableFileVersion).filter_by(project_id=project_id, deliverable_id=deliverable_id, id=version_id).first()
    if row is None:
        raise HTTPException(404, 'Version introuvable dans ce livrable')
    metadata = db.get(DeliverableVersionMetadata, version_id)
    if metadata is None or metadata.project_id != project_id:
        raise HTTPException(409, 'Métadonnées de version incomplètes')
    return row, metadata


def _version_values(row, metadata):
    return {'id': row.id, 'number': row.number, 'filename': row.filename, 'size_bytes': row.size_bytes,
            'sha256': row.sha256, 'manifest_sha256': row.manifest_sha256, 'generated': row.generated,
            'source_delivery_id': row.source_delivery_id, 'actor_id': row.actor_id, 'created_at': utc_iso(row.created_at),
            'reference': metadata.reference if metadata else None, 'comment': metadata.comment if metadata else None}


def versions(db, project_id, deliverable_id, *, offset=0, limit=50):
    commands._item(db, project_id, deliverable_id)
    query = db.query(DeliverableFileVersion, DeliverableVersionMetadata).outerjoin(
        DeliverableVersionMetadata, (DeliverableVersionMetadata.version_id == DeliverableFileVersion.id)
        & (DeliverableVersionMetadata.project_id == project_id)).filter(
        DeliverableFileVersion.project_id == project_id, DeliverableFileVersion.deliverable_id == deliverable_id)
    rows, total = _page(query.order_by(DeliverableFileVersion.number.desc()), offset, limit)
    return _result([_version_values(row, meta) for row, meta in rows], total, offset, limit, project_id, db)


def version_detail(db, project_id, deliverable_id, version_id):
    from app.services.deliverable_manifest import check_row
    row, meta = _version(db, project_id, deliverable_id, version_id)
    try:
        manifest = check_row({key: getattr(row, key) for key in ('manifest', 'manifest_sha256', 'project_id',
            'deliverable_id', 'number', 'filename', 'sha256', 'size_bytes', 'source_delivery_id', 'generated', 'actor_id')})
    except ValueError as exc:
        raise HTTPException(409, 'Manifeste de version incohérent') from exc
    # Inspecting recorded proof remains possible even when the source file is unavailable.
    return {**_version_values(row, meta), 'manifest': manifest, 'published_manifest': json.loads(row.manifest),
            'revision': revision(db, project_id)}


def history(db, project_id, deliverable_id, *, offset=0, limit=50):
    commands._item(db, project_id, deliverable_id)
    rows, total = _page(db.query(DeliverableEvent).filter_by(project_id=project_id, deliverable_id=deliverable_id)
        .order_by(DeliverableEvent.revision.desc(), DeliverableEvent.id), offset, limit)
    return _result([{'id': row.id, 'revision': row.revision, 'action': row.action, 'actor_id': row.actor_id,
                    'created_at': utc_iso(row.created_at)} for row in rows], total, offset, limit, project_id, db)


def history_detail(db, project_id, deliverable_id, event_id):
    commands._item(db, project_id, deliverable_id)
    row = db.query(DeliverableEvent).filter_by(project_id=project_id, deliverable_id=deliverable_id, id=event_id).first()
    if row is None:
        raise HTTPException(404, 'Événement introuvable dans ce livrable')
    return {'id': row.id, 'revision': row.revision, 'action': row.action, 'actor_id': row.actor_id,
            'created_at': utc_iso(row.created_at), 'previous': row.previous, 'value': row.value}


def detail(db, project_id, deliverable_id):
    value = commands.read_deliverable(db, project_id, deliverable_id)
    actor = current_operator()
    return {**value, 'can_edit': actor.role != 'reader', 'can_verify': actor.role != 'reader' and
            (actor.role == 'owner' or bool(actor.person_id and actor.person_id == value['verifier_id']))}
