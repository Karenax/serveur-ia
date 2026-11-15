"""Milestone readiness from explicit associations and current human visa evidence."""
from fastapi import HTTPException
from sqlalchemy import and_, inspect, or_

from ..models import Deliverable
from ..project_deliverable_models import (
    DELIVERABLE_TABLES, DeliverableChecklistItem, DeliverableFileVersion, DeliverableMilestone,
    DeliverablePlan, DeliverableVersionMetadata,
)
from ..project_identity_models import ProjectPerson
from . import project_deliverables as commands
from .planning_revision import revision
from .project_identity import _project


def milestone_gates(db, project_id, milestone_id):
    _project(db, project_id)
    commands._milestone(db, project_id, milestone_id)
    present = set(inspect(db.connection()).get_table_names())
    required = {table.name for table in DELIVERABLE_TABLES}
    if not present.intersection(required):
        # An isolated pre-L3 domain remains usable; real startup explicitly
        # installs L3 before exposing the new HTTP routes.
        return {'milestone_id': milestone_id, 'revision': revision(db, project_id), 'checks': [],
                'blocking_checks': [], 'can_validate': True}
    if not required <= present:
        raise HTTPException(409, 'Schéma de livrables incomplet : vérifier la migration L3')
    check = DeliverableChecklistItem
    links = db.query(DeliverableMilestone.deliverable_id).filter_by(project_id=project_id, milestone_id=milestone_id, active=True)
    query = db.query(check, Deliverable).join(Deliverable, Deliverable.id == check.deliverable_id).join(
        DeliverablePlan, DeliverablePlan.deliverable_id == Deliverable.id).filter(
        check.project_id == project_id, Deliverable.project_id == project_id, DeliverablePlan.project_id == project_id,
        DeliverablePlan.active.is_(True), check.active.is_(True), check.is_gate.is_(True),
        or_(check.milestone_id == milestone_id, and_(check.milestone_id.is_(None), check.deliverable_id.in_(links))))
    rows = query.order_by(Deliverable.title, check.position, check.id).all()
    if rows:
        from .project_deliverable_archive_store import require_schema
        require_schema(db)
    latest, file_errors = {}, {}
    values = []
    for item, owner in rows:
        if owner.id not in latest:
            latest[owner.id] = commands._latest(db, owner)
            if latest[owner.id]:
                try:
                    commands._verify_file(db, latest[owner.id])
                except HTTPException as exc:
                    file_errors[owner.id] = str(exc.detail)
        version = latest[owner.id]
        reason = None
        if version is None:
            reason = 'Publier une version avant le visa humain'
        elif owner.id in file_errors:
            reason = file_errors[owner.id]
        elif (not item.completed or item.completed_version_id != version.id or not item.proof.strip()
              or not item.completed_by or not item.completed_at):
            reason = 'Visa humain requis pour la dernière version'
        values.append({'id': item.id, 'label': item.label, 'deliverable_id': owner.id, 'deliverable_title': owner.title,
                       'version_id': version.id if version else None, 'ready': reason is None, 'reason': reason})
    return {'milestone_id': milestone_id, 'revision': revision(db, project_id), 'checks': values,
            'blocking_checks': [value for value in values if not value['ready']],
            'can_validate': all(value['ready'] for value in values)}


def require_milestone_gates(db, project_id, milestone_id):
    result = milestone_gates(db, project_id, milestone_id)
    if result['blocking_checks']:
        raise HTTPException(409, {'message': 'Visas de livrables requis avant validation du jalon',
                                  'blocking_checks': result['blocking_checks']})


def milestone_gate_page(db, project_id, milestone_id, *, include_ready=False, offset=0, limit=50):
    """Paged descriptive read; readiness still evaluates every mandatory check.

    Keep the command guard and original unpaged contract unchanged. Person and
    publication descriptions are loaded only for the requested page, with no
    direct paths, private contacts, events, or domain writes.
    """
    if not 0 <= offset <= 1000000 or not 1 <= limit <= 200:
        raise HTTPException(422, 'Pagination invalide')
    result = milestone_gates(db, project_id, milestone_id)
    selected = result['checks'] if include_ready else result['blocking_checks']
    values = selected[offset:offset + limit]
    plans, versions, references, people = {}, {}, {}, {}
    if values:
        owner_ids = {value['deliverable_id'] for value in values}
        version_ids = {value['version_id'] for value in values if value['version_id']}
        plans = {row.deliverable_id: row for row in db.query(DeliverablePlan).filter(
            DeliverablePlan.project_id == project_id, DeliverablePlan.deliverable_id.in_(owner_ids))}
        versions = {row.id: row for row in db.query(DeliverableFileVersion).filter(
            DeliverableFileVersion.project_id == project_id, DeliverableFileVersion.deliverable_id.in_(owner_ids),
            DeliverableFileVersion.id.in_(version_ids))}
        references = {row.version_id: row.reference for row in db.query(DeliverableVersionMetadata).filter(
            DeliverableVersionMetadata.project_id == project_id, DeliverableVersionMetadata.version_id.in_(version_ids))}
        person_ids = {identity for plan in plans.values() for identity in (plan.responsible_id, plan.verifier_id) if identity}
        people = {row.id: ' '.join(part for part in (row.first_name, row.last_name) if part).strip() or row.trigram or 'Personne'
                  for row in db.query(ProjectPerson).filter(ProjectPerson.id.in_(person_ids))}
    items = []
    for value in values:
        plan = plans.get(value['deliverable_id'])
        version = versions.get(value['version_id'])
        items.append({**value,
            'version': {'id': version.id, 'number': version.number, 'filename': version.filename,
                        'reference': references.get(version.id, '')} if version else None,
            'responsible_id': plan.responsible_id if plan else None,
            'responsible_name': people.get(plan.responsible_id) if plan else None,
            'verifier_id': plan.verifier_id if plan else None,
            'verifier_name': people.get(plan.verifier_id) if plan else None})
    return {'milestone_id': milestone_id, 'revision': result['revision'], 'can_validate': result['can_validate'],
            'checks_total': len(result['checks']), 'blocking_total': len(result['blocking_checks']),
            'items': items, 'total': len(selected), 'offset': offset, 'limit': limit}
