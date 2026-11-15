"""Versioned templates and preview-bound, additive project application.

Callers commit/rollback. Publication never modifies a project. Application
preserves contractual/actual dates, evidence and unrelated manual tasks.
"""
from copy import deepcopy
from datetime import date
import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import func, or_

from ..models import Milestone, Task
from ..project_identity_models import ProjectProfile
from ..project_planning_models import (
    MilestonePlan, PlanningTemplate, PlanningTemplateVersion, ProjectPlanningState, TaskPlan,
)
from . import milestones, project_planning as planning
from .planning_revision import begin_change, record_change, revision
from .project_identity import _flush, _lock_entity, _normalized, _page, _reference, _reference_change
from .project_operator import current_operator, require_reference_write
from .project_planning_rules import (
    TemplateDefinition, WorkCalendar, aggregate_task_rows, capture_snapshot,
    compare_snapshots, legacy_mapping_proposals, preview_template,
)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _catalog(db):
    query = db.query(PlanningTemplate)
    scope = current_operator().project_ids
    if scope is not None:
        types = db.query(ProjectProfile.typology_id).filter(ProjectProfile.project_id.in_(scope))
        linked = db.query(PlanningTemplateVersion.template_id).join(ProjectPlanningState,
            ProjectPlanningState.active_template_version_id == PlanningTemplateVersion.id).filter(
                ProjectPlanningState.project_id.in_(scope))
        used = db.query(TaskPlan.template_id).filter(TaskPlan.project_id.in_(scope))
        query = query.filter(or_(PlanningTemplate.typology_id.is_(None), PlanningTemplate.typology_id.in_(types),
                                 PlanningTemplate.id.in_(linked), PlanningTemplate.id.in_(used)))
    return query


def _template(db, template_id):
    row = _catalog(db).filter(PlanningTemplate.id == template_id).first()
    if row is None:
        raise HTTPException(404, "Modèle introuvable dans la portée autorisée")
    return row


def _describe(row):
    return {key: getattr(row, key) for key in ('id', 'code', 'name', 'typology_id', 'active', 'revision')}


def template_detail(db, template_id):
    row = _template(db, template_id)
    latest = db.query(PlanningTemplateVersion).filter_by(template_id=row.id).order_by(PlanningTemplateVersion.number.desc()).first()
    actor = current_operator()
    return {**_describe(row), 'latest_version': {'id': latest.id, 'number': latest.number, 'sha256': latest.sha256} if latest else None,
            'can_manage': actor.role == 'owner' and actor.project_ids is None}


def list_templates(db, *, search='', include_inactive=False, typology_id=None, offset=0, limit=50):
    query = _catalog(db)
    if not include_inactive:
        query = query.filter(PlanningTemplate.active.is_(True))
    if typology_id:
        query = query.filter(or_(PlanningTemplate.typology_id.is_(None), PlanningTemplate.typology_id == typology_id))
    rows, total = _page(query.order_by(PlanningTemplate.search_text, PlanningTemplate.id),
                        PlanningTemplate.search_text, search, offset, limit)
    latest = db.query(PlanningTemplateVersion.template_id, func.max(PlanningTemplateVersion.number).label('number')).filter(
        PlanningTemplateVersion.template_id.in_([row.id for row in rows])).group_by(PlanningTemplateVersion.template_id).subquery()
    versions = {row.template_id: {'id': row.id, 'number': row.number} for row in
                db.query(PlanningTemplateVersion).join(latest, (latest.c.template_id == PlanningTemplateVersion.template_id)
                    & (latest.c.number == PlanningTemplateVersion.number))}
    actor = current_operator()
    return {'items': [{**_describe(row), 'latest_version': versions.get(row.id)} for row in rows],
            'total': total, 'offset': offset, 'limit': limit,
            'can_manage': actor.role == 'owner' and actor.project_ids is None}


def _publish(db, actor, row, definition):
    definition = TemplateDefinition.model_validate(definition.model_dump())
    value = _json(definition.model_dump())
    number = (db.query(func.max(PlanningTemplateVersion.number)).filter_by(template_id=row.id).scalar() or 0) + 1
    version = PlanningTemplateVersion(template_id=row.id, number=number, definition=value,
                                      sha256=_sha(value), actor_id=actor.id)
    db.add(version)
    _flush(db, "Une version de ce modèle a été publiée simultanément")
    return {'id': version.id, 'template_id': row.id, 'number': number, 'sha256': version.sha256}


def create_template(db, payload):
    actor = require_reference_write()
    _reference(db, payload.typology_id, 'typology')
    row = PlanningTemplate(code=payload.code, normalized_code=_normalized(payload.code), name=payload.name,
                           search_text=_normalized(payload.code + ' ' + payload.name), typology_id=payload.typology_id)
    db.add(row)
    _flush(db, "Ce code de modèle existe déjà, même s'il est archivé")
    version = _publish(db, actor, row, payload.definition)
    result = {**_describe(row), 'version': version}
    _reference_change(db, actor, 'planning_template', row.id, row.revision, {}, result)
    return result


def patch_template(db, template_id, payload):
    actor = require_reference_write()
    row = _template(db, template_id)
    previous = _describe(row)
    _lock_entity(db, PlanningTemplate, row, payload.expected_revision)
    values = payload.model_dump(exclude_unset=True, exclude={'expected_revision'})
    if 'typology_id' in values:
        _reference(db, values['typology_id'], 'typology', allow_inactive=values['typology_id'] == row.typology_id)
    for key, value in values.items():
        setattr(row, key, value)
    row.search_text = _normalized(row.code + ' ' + row.name)
    result = _describe(row)
    _reference_change(db, actor, 'planning_template', row.id, row.revision, previous, result)
    return result


def publish_version(db, template_id, payload):
    actor = require_reference_write()
    row = _template(db, template_id)
    if not row.active:
        raise HTTPException(409, "Réactiver le modèle avant publication")
    _lock_entity(db, PlanningTemplate, row, payload.expected_revision)
    version = _publish(db, actor, row, payload.definition)
    result = {**version, 'revision': row.revision}
    _reference_change(db, actor, 'planning_template', row.id, row.revision, {}, {'published_version': result})
    return result


def versions(db, template_id, *, offset=0, limit=50):
    _template(db, template_id)
    if not 0 <= offset <= 1000000 or not 1 <= limit <= 200:
        raise HTTPException(422, "Pagination invalide")
    from app.db_support import utc_iso
    query = db.query(PlanningTemplateVersion).filter_by(template_id=template_id)
    return {'items': [{'id': row.id, 'number': row.number, 'sha256': row.sha256,
                       'actor_id': row.actor_id, 'created_at': utc_iso(row.created_at)} for row in
                      query.order_by(PlanningTemplateVersion.number.desc()).offset(offset).limit(limit)],
            'total': query.count(), 'offset': offset, 'limit': limit}


def _version(db, version_id, *, for_application=False):
    row = db.get(PlanningTemplateVersion, version_id)
    if row is None:
        raise HTTPException(404, "Version introuvable")
    template = _template(db, row.template_id)
    if for_application and not template.active:
        raise HTTPException(409, "Un modèle archivé ne peut être appliqué")
    try:
        if _sha(row.definition) != row.sha256:
            raise ValueError('hash')
        definition = TemplateDefinition.model_validate_json(row.definition)
    except ValueError as exc:
        raise HTTPException(409, "Version de modèle invalide ou empreinte incohérente") from exc
    return row, template, definition


def read_version(db, template_id, version_id):
    row, _, definition = _version(db, version_id)
    if row.template_id != template_id:
        raise HTTPException(404, "Version introuvable dans ce modèle")
    return {'id': row.id, 'number': row.number, 'sha256': row.sha256, 'definition': definition.model_dump()}


def mapping_proposals(db, project_id):
    planning._project(db, project_id)
    milestone_rows, _ = planning._rows(db, project_id)
    return {'revision': revision(db, project_id), 'items': legacy_mapping_proposals(milestone_rows)}


def _forecast(current, proposed, policy):
    if not proposed or policy == 'preserve' or (current and policy == 'fill_empty'):
        return current
    return proposed


def _build(db, project_id, version_id, payload):
    version, template, definition = _version(db, version_id, for_application=True)
    profile = db.get(ProjectProfile, project_id)
    if template.typology_id is not None and (profile is None or profile.typology_id != template.typology_id):
        raise HTTPException(422, "Ce modèle exige la même typologie que la fiche projet")
    try:
        calendar = WorkCalendar(frozenset(date.fromisoformat(value) for value in payload.excluded_dates))
        start = date.fromisoformat(payload.start_date) if payload.start_date else None
        proposed = preview_template(definition, start, calendar)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    old_milestones, old_tasks = planning._rows(db, project_id)
    milestones_by_id = {row['id']: deepcopy(row) for row in old_milestones}
    codes = {row['code']: row['id'] for row in old_milestones if row['code']}
    incoming = {row['code']: row for row in proposed['milestones']}
    if set(payload.milestone_mapping) - incoming.keys():
        raise HTTPException(422, "Code de correspondance absent du modèle")
    if len(set(payload.milestone_mapping.values())) != len(payload.milestone_mapping):
        raise HTTPException(422, "Un jalon ne peut recevoir plusieurs codes")
    evidence = {'kind': 'template', 'label': template.name, 'template_version_id': version.id,
                'actor': current_operator().id}
    milestone_map = {}
    for code, spec in incoming.items():
        target_id = payload.milestone_mapping.get(code, codes.get(code))
        if target_id:
            if target_id not in milestones_by_id:
                raise HTTPException(422, "Jalon de correspondance absent du projet")
            row = milestones_by_id[target_id]
            if row['code'] not in (None, code) or codes.get(code, target_id) != target_id:
                raise HTTPException(409, "Code de jalon déjà affecté ; corriger explicitement la correspondance")
            row['code'] = code
            if not next(value for value in old_milestones if value['id'] == target_id)['code']:
                row['order'] = spec['order']
            if row['active']:
                value = _forecast(row['forecast_date'], spec['forecast_date'], payload.forecast_policy)
                if value != row['forecast_date']:
                    row['forecast_date'] = value
                    row['date_sources'] = {**row['date_sources'], 'forecast_date': evidence}
                    row['due_date'] = value or row['contractual_date']
        else:
            target_id = 'new-milestone:' + code
            row = {'id': target_id, 'title': spec['title'], 'code': code, 'order': spec['order'],
                   'workflow_status': 'pending', 'comment': '', 'active': True,
                   'contractual_date': '', 'actual_date': '', 'forecast_date': spec['forecast_date'],
                   'due_date': spec['forecast_date'],
                   'date_sources': {'forecast_date': evidence} if spec['forecast_date'] else {}}
            milestones_by_id[target_id] = row
        milestone_map[code] = target_id
    if sum(row['active'] and row['code'] is not None and row['workflow_status'] == 'open'
           for row in milestones_by_id.values()) > 1:
        raise HTTPException(422, "Les correspondances donneraient plusieurs jalons ouverts dans le cycle")
    tasks_by_id = {row['id']: deepcopy(row) for row in old_tasks}
    keyed = {row['template_key']: row['id'] for row in old_tasks if row['template_id'] == template.id}
    task_map = {spec['key']: keyed.get(spec['key'], 'new-task:' + spec['key']) for spec in proposed['tasks']}
    for spec in proposed['tasks']:
        identity = task_map[spec['key']]
        existing = identity in tasks_by_id
        row = tasks_by_id.get(identity, {'id': identity, 'title': spec['title'], 'status': 'todo',
            'due_date': '', 'start_date': '', 'end_date': '', 'planned_hours': 0,
            'priority': 'normal', 'parent_id': None, 'milestone_id': None, 'responsible_id': None,
            'template_id': template.id, 'template_key': spec['key'], 'design': False,
            'manufacturing': False, 'comment': '', 'active': True})
        if not existing or (payload.update_tasks and row['active']):
            row.update({key: spec[key] for key in ('title', 'priority', 'design', 'manufacturing', 'planned_hours')})
            row['parent_id'] = task_map.get(spec['parent_key'])
            row['milestone_id'] = milestone_map.get(spec['milestone_code'])
            for field in ('start_date', 'end_date'):
                row[field] = _forecast(row[field], spec[field], payload.forecast_policy) if existing else spec[field]
            row['due_date'] = row['end_date']
        tasks_by_id[identity] = row
    for row in old_tasks:
        was_parent = any(child['parent_id'] == row['id'] for child in old_tasks)
        becomes_parent = any(child['parent_id'] == row['id'] for child in tasks_by_id.values())
        if not was_parent and becomes_parent and not payload.update_tasks and any(
                row[key] for key in ('planned_hours', 'start_date', 'end_date')):
            raise HTTPException(422, "La nouvelle hiérarchie remplacerait les dates/heures propres d'une tâche ; confirmer la mise à jour des tâches")
    try:
        new_tasks = aggregate_task_rows(project_id, list(tasks_by_id.values()))
        before = capture_snapshot(project_id, old_milestones, old_tasks)
        after = capture_snapshot(project_id, list(milestones_by_id.values()), new_tasks)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    inputs = payload.model_dump(exclude={'expected_preview_sha256'})
    inputs['excluded_dates'] = sorted(inputs['excluded_dates'])
    state = db.get(ProjectPlanningState, project_id)
    previous_calendar = state.excluded_dates if state else []
    previous_version = state.active_template_version_id if state else None
    envelope = {'project_id': project_id, 'version_id': version.id, 'version_sha256': version.sha256,
                'inputs': inputs, 'before_sha256': before.sha256, 'after_sha256': after.sha256,
                'previous_calendar': previous_calendar, 'previous_version_id': previous_version}
    changes = compare_snapshots(before, after)
    changes['calendar'] = {'before': previous_calendar, 'after': inputs['excluded_dates']}
    changes['template_version_id'] = {'before': previous_version, 'after': version.id}
    return {'project_id': project_id, 'revision': payload.expected_revision, 'version_id': version.id,
            'preview_sha256': _sha(_json(envelope)), 'milestone_map': milestone_map, 'task_map': task_map,
            'milestones': list(milestones_by_id.values()), 'tasks': new_tasks,
            'changes': changes, 'inputs': inputs}


def preview_application(db, project_id, version_id, payload):
    planning._project(db, project_id)
    if revision(db, project_id) != payload.expected_revision:
        raise HTTPException(409, "Planning modifié : recharger avant de prévisualiser")
    return _build(db, project_id, version_id, payload)


def apply_template(db, project_id, version_id, payload):
    actor, state = begin_change(db, project_id, payload.expected_revision)
    preview = _build(db, project_id, version_id, payload)
    if preview['preview_sha256'] != payload.expected_preview_sha256:
        raise HTTPException(409, "L'aperçu a changé : vérifier le nouvel aperçu avant application")
    old_milestones, old_tasks = planning._rows(db, project_id)
    mapping = {}
    for value in preview['milestones']:
        if value['id'].startswith('new-milestone:'):
            row = Milestone(project_id=project_id, title=value['title'])
            db.add(row)
            db.flush()
            mapping[value['id']] = row.id
        else:
            row = db.get(Milestone, value['id'])
        plan = db.get(MilestonePlan, row.id)
        if value['code'] is not None:
            if plan is None:
                plan = MilestonePlan(milestone_id=row.id, project_id=project_id)
                db.add(plan)
            plan.code, plan.position = value['code'], value['order']
        # Unchanged historic values do not generate history or alter evidence.
        if (row.forecast_date or '') != value['forecast_date']:
            milestones.apply_dates(db, row, {'forecast_date': value['forecast_date']}, value['date_sources']['forecast_date'])
    for value in preview['tasks']:
        if value['id'].startswith('new-task:'):
            row = Task(project_id=project_id, title=value['title'], status=value['status'], due_date=value['due_date'])
            db.add(row)
            db.flush()
            mapping[value['id']] = row.id
    for value in preview['tasks']:
        row = db.get(Task, mapping.get(value['id'], value['id']))
        # Leave unrelated legacy tasks entirely unmaterialized if unchanged.
        previous = next((old for old in old_tasks if old['id'] == value['id']), None)
        if previous == value:
            continue
        plan = planning._task_plan(db, row)
        for field in ('title', 'status', 'due_date'):
            setattr(row, field, value[field])
        for field in ('responsible_id', 'template_id', 'template_key', 'priority', 'start_date', 'end_date',
                      'planned_hours', 'design', 'manufacturing', 'comment', 'active'):
            setattr(plan, field, value[field])
        plan.parent_task_id = mapping.get(value['parent_id'], value['parent_id'])
        plan.milestone_id = mapping.get(value['milestone_id'], value['milestone_id'])
    state.active_template_version_id = version_id
    state.excluded_dates = sorted(payload.excluded_dates)
    db.flush()
    planning._aggregate(db, project_id)
    current_milestones, current_tasks = planning._rows(db, project_id)
    record_change(db, actor, state, 'template_applied', {'milestones': old_milestones, 'tasks': old_tasks},
                  {'milestones': current_milestones, 'tasks': current_tasks, 'version_id': version_id,
                   'preview_sha256': preview['preview_sha256'], 'inputs': preview['inputs']})
    return {'revision': state.revision, 'version_id': version_id,
            'milestone_map': {key: mapping.get(value, value) for key, value in preview['milestone_map'].items()},
            'task_map': {key: mapping.get(value, value) for key, value in preview['task_map'].items()}}
