"""Transactional L2 commands; caller commits or rolls back."""
from fastapi import HTTPException
from sqlalchemy import case, func, literal, select
from sqlalchemy.orm import aliased

from ..models import Milestone, Project, Task
from ..project_planning_models import (
    MilestonePlan, PlanningBaseline, PlanningChange, ProjectPlanningState, TaskPlan,
)
from . import milestones
from .project_operator import require_project_access
from .project_identity import _person
from .project_planning_rules import PlanningSnapshot, capture_snapshot, compare_snapshots, validate_parent
from .planning_revision import begin_change, record_change, project_values


def _project(db, project_id, *, write=False):
    actor = require_project_access(project_id, write=write)
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "Projet introuvable")
    return actor


def _lock(db, project_id, expected):
    return begin_change(db, project_id, expected)[1]


def _milestone(row, plan):
    if plan and plan.project_id != row.project_id:
        raise HTTPException(409, "Rattachement de jalon incohérent")
    return {**milestones.describe(row), "code": plan.code if plan else None,
            "order": plan.position if plan and plan.position is not None else milestones.order(row)[0],
            "workflow_status": plan.workflow_status if plan else "pending",
            "comment": plan.comment if plan else "", "active": plan.active if plan else True}


def _task(row, plan):
    if plan and plan.project_id != row.project_id:
        raise HTTPException(409, "Rattachement de tâche incohérent")
    return {"id": row.id, "title": row.title, "status": row.status, "due_date": row.due_date or "",
            "parent_id": plan.parent_task_id if plan else None, "milestone_id": plan.milestone_id if plan else None,
            "responsible_id": plan.responsible_id if plan else None,
            "template_id": plan.template_id if plan else None, "template_key": plan.template_key if plan else None,
            "priority": plan.priority if plan else "normal", "start_date": plan.start_date if plan else "",
            "end_date": plan.end_date if plan else row.due_date or "", "planned_hours": plan.planned_hours if plan else 0,
            "design": plan.design if plan else False, "manufacturing": plan.manufacturing if plan else False,
            "comment": plan.comment if plan else "", "active": plan.active if plan else True}


def _milestone_rows(db, project_id):
    milestone_rows = [_milestone(row, plan) for row, plan in db.query(Milestone, MilestonePlan).outerjoin(
        MilestonePlan, MilestonePlan.milestone_id == Milestone.id).filter(Milestone.project_id == project_id)]
    return sorted(milestone_rows, key=lambda value: (value["order"], value["id"]))


def _rows(db, project_id):
    task_rows = [_task(row, plan) for row, plan in db.query(Task, TaskPlan).outerjoin(
        TaskPlan, TaskPlan.task_id == Task.id).filter(Task.project_id == project_id)]
    return _milestone_rows(db, project_id), sorted(task_rows, key=lambda value: value["id"])


def read_planning(db, project_id):
    actor = _project(db, project_id)
    state = db.get(ProjectPlanningState, project_id)
    milestone_rows, task_rows = _rows(db, project_id)
    return {"project_id": project_id, "revision": state.revision if state else 0,
            "active_template_version_id": state.active_template_version_id if state else None,
            "task_statuses": ["todo", "assigned", "in_progress", "blocked", "done", "cancelled"],
            "excluded_dates": state.excluded_dates if state else [], "can_edit": actor.role != "reader",
            "milestones": milestone_rows, "tasks": task_rows}


def planning_info(db, project_id):
    actor = _project(db, project_id)
    state = db.get(ProjectPlanningState, project_id)
    from .project_planning_rules import PROJECT_WORKFLOW
    return {"project_id": project_id, "revision": state.revision if state else 0,
            "can_edit": actor.role != "reader", "excluded_dates": state.excluded_dates if state else [],
            "active_template_version_id": state.active_template_version_id if state else None,
            "task_statuses": ["todo", "assigned", "in_progress", "blocked", "done", "cancelled"],
            "workflow": [{"code": code, "title": title} for code, title in PROJECT_WORKFLOW]}


def planning_items(db, project_id, kind, *, search="", include_inactive=False, offset=0, limit=50):
    _project(db, project_id)
    if kind not in {"tasks", "milestones"}:
        raise HTTPException(422, "Type de planning inconnu")
    if len(search) > 200 or not 0 <= offset <= 1000000 or not 1 <= limit <= 200:
        raise HTTPException(422, "Pagination ou recherche invalide")
    model, plan_model, describe = (Task, TaskPlan, _task) if kind == "tasks" else (Milestone, MilestonePlan, _milestone)
    key = plan_model.task_id if kind == "tasks" else plan_model.milestone_id
    query = db.query(model, plan_model).outerjoin(plan_model, key == model.id).filter(model.project_id == project_id)
    if not include_inactive:
        query = query.filter(func.coalesce(plan_model.active, True).is_(True))
    if search.strip():
        term = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.filter(model.title.ilike("%" + term + "%", escape="\\"))
    total = query.count()
    if kind == 'milestones':
        # Preserve the legacy workflow, including normalized title aliases,
        # before pagination. Explicit L2 positions remain authoritative.
        legacy_positions = {row.id: milestones.order(row)[0] for row in query.with_entities(model.id, model.title)
                            .filter(plan_model.position.is_(None)) if milestones.order(row)[0] != 99}
        legacy_order = case(legacy_positions, value=model.id, else_=99) if legacy_positions else literal(99)
        query = query.order_by(func.coalesce(plan_model.position, legacy_order), model.title, model.id)
    else:
        query = query.order_by(model.title, model.id)
    state = db.get(ProjectPlanningState, project_id)
    values = [describe(row, plan) for row, plan in query.offset(offset).limit(limit)]
    if kind == 'tasks':
        from ..project_identity_models import ProjectPerson
        parent_names = {row.id: row.title for row in db.query(Task).filter(
            Task.project_id == project_id, Task.id.in_({value['parent_id'] for value in values if value['parent_id']}))}
        milestone_names = {row.id: row.title for row in db.query(Milestone).filter(
            Milestone.project_id == project_id, Milestone.id.in_({value['milestone_id'] for value in values if value['milestone_id']}))}
        people_names = {row.id: (row.first_name + ' ' + row.last_name).strip() for row in db.query(ProjectPerson).filter(
            ProjectPerson.id.in_({value['responsible_id'] for value in values if value['responsible_id']}))}
        for value in values:
            value.update(parent_title=parent_names.get(value['parent_id']), milestone_title=milestone_names.get(value['milestone_id']),
                         responsible_name=people_names.get(value['responsible_id']))
    return {"items": values,
            "total": total, "offset": offset, "limit": limit, "revision": state.revision if state else 0}


def planning_item(db, project_id, kind, item_id):
    """Scoped item and relation labels, without downloading the full planning."""
    actor = _project(db, project_id)
    if kind not in {'tasks', 'milestones'}:
        raise HTTPException(422, "Type de planning inconnu")
    from .planning_revision import revision
    expected = revision(db, project_id)
    model, plan_model, key, describe = (Task, TaskPlan, TaskPlan.task_id, _task) if kind == 'tasks' else (
        Milestone, MilestonePlan, MilestonePlan.milestone_id, _milestone)
    found = db.query(model, plan_model).outerjoin(plan_model, key == model.id).filter(
        model.project_id == project_id, model.id == item_id).first()
    if found is None:
        raise HTTPException(404, "Élément de planning introuvable dans ce projet")
    row, plan = found
    result = {'item': describe(row, plan), 'revision': expected, 'can_edit': actor.role != 'reader'}
    if kind == 'tasks':
        from ..project_identity_models import ProjectPerson
        from .project_identity import describe_person
        parent = db.query(Task).filter_by(id=plan.parent_task_id, project_id=project_id).first() if plan and plan.parent_task_id else None
        milestone = db.query(Milestone).filter_by(id=plan.milestone_id, project_id=project_id).first() if plan and plan.milestone_id else None
        person = db.get(ProjectPerson, plan.responsible_id) if plan and plan.responsible_id else None
        if plan and ((plan.parent_task_id and parent is None) or (plan.milestone_id and milestone is None)
                     or (plan.responsible_id and person is None)):
            raise HTTPException(409, "Relation de tâche incohérente : vérifier le rattachement")
        result.update(parent={'id': parent.id, 'title': parent.title} if parent else None,
                      milestone={'id': milestone.id, 'title': milestone.title} if milestone else None,
                      responsible=describe_person(person) if person else None,
                      children_total=db.query(TaskPlan).filter_by(project_id=project_id, parent_task_id=item_id).count())
    return result


def planning_history(db, project_id, *, offset=0, limit=50):
    _project(db, project_id)
    if not 0 <= offset <= 1000000 or not 1 <= limit <= 200:
        raise HTTPException(422, "Pagination invalide")
    from app.db_support import utc_iso
    query = db.query(PlanningChange).filter_by(project_id=project_id)
    return {"items": [{"id": row.id, "revision": row.revision, "actor_id": row.actor_id,
                       "action": row.action, "created_at": utc_iso(row.created_at)} for row in
                      query.order_by(PlanningChange.revision.desc(), PlanningChange.id).offset(offset).limit(limit)],
            "total": query.count(), "offset": offset, "limit": limit}


def planning_history_detail(db, project_id, change_id):
    _project(db, project_id)
    row = db.query(PlanningChange).filter_by(project_id=project_id, id=change_id).first()
    if row is None:
        raise HTTPException(404, "Modification introuvable")
    return {"id": row.id, "revision": row.revision, "previous": row.previous, "value": row.value}


def _baseline_query(db, project_id):
    latest = aliased(PlanningChange)
    last_id = select(latest.id).where(latest.project_id == project_id,
        latest.action == 'baseline_metadata_changed',
        latest.value['baseline_id'].as_string() == PlanningBaseline.id).order_by(
        latest.revision.desc()).limit(1).correlate(PlanningBaseline).scalar_subquery()
    return db.query(PlanningBaseline, PlanningChange).outerjoin(PlanningChange,
        PlanningChange.id == last_id).filter(PlanningBaseline.project_id == project_id)


def _baseline(row, event):
    from app.db_support import utc_iso
    metadata = {'baseline_id': row.id, 'label': row.label, 'comment': '', 'active': True}
    if event:
        metadata.update(event.value)
    return {**metadata, 'id': row.id, 'kind': row.kind, 'capture_label': row.label,
            'revision': row.planning_revision, 'metadata_revision': event.revision if event else row.planning_revision,
            'sha256': row.sha256, 'actor_id': row.actor_id, 'created_at': utc_iso(row.created_at)}


def list_baselines(db, project_id, *, offset=0, limit=50, include_inactive=False):
    _project(db, project_id)
    if not 0 <= offset <= 1000000 or not 1 <= limit <= 200:
        raise HTTPException(422, "Pagination invalide")
    query = _baseline_query(db, project_id)
    if not include_inactive:
        query = query.filter(func.coalesce(PlanningChange.value['active'].as_boolean(), True).is_(True))
    return {"items": [_baseline(row, event) for row, event in query.order_by(
                           PlanningBaseline.planning_revision.desc(), PlanningBaseline.id).offset(offset).limit(limit)],
            "total": query.count(), "offset": offset, "limit": limit}


def baseline_detail(db, project_id, baseline_id):
    actor = _project(db, project_id)
    state = db.get(ProjectPlanningState, project_id)
    revision = state.revision if state else 0
    found = _baseline_query(db, project_id).filter(PlanningBaseline.id == baseline_id).first()
    if found is None:
        raise HTTPException(404, "Référence introuvable")
    return {'baseline': _baseline(*found), 'revision': revision, 'can_edit': actor.role != 'reader'}


def patch_baseline_metadata(db, project_id, baseline_id, payload):
    actor, state = begin_change(db, project_id, payload.expected_revision)
    found = _baseline_query(db, project_id).filter(PlanningBaseline.id == baseline_id).first()
    if found is None:
        raise HTTPException(404, "Référence introuvable")
    row, event = found
    current = _baseline(row, event)
    previous = {key: current[key] for key in ('baseline_id', 'label', 'comment', 'active')}
    changes = payload.model_dump(exclude_unset=True, exclude={'expected_revision'})
    if 'label' in changes:
        changes['label'] = changes['label'].strip()
    value = {**previous, **changes}
    _change(db, actor, state, 'baseline_metadata_changed', previous, value)
    db.flush()  # a subsequent command in this transaction must see this event
    return {'revision': state.revision, 'baseline': {**current, **value, 'metadata_revision': state.revision}}


def _change(db, actor, state, action, previous, value):
    record_change(db, actor, state, action, previous, value)


def patch_milestone(db, project_id, milestone_id, payload):
    return _patch_milestone(db, project_id, milestone_id, payload.expected_revision,
                            payload.model_dump(exclude_unset=True, exclude={"expected_revision"}))


def patch_legacy_milestone(db, project_id, milestone_id, changes, expected_revision=None):
    # Legacy nulls were ignored, and due_date is a forecast alias.
    values = {key: value for key, value in changes.items() if value is not None}
    if "due_date" in values:
        values.setdefault("forecast_date", values.pop("due_date"))
    return _patch_milestone(db, project_id, milestone_id, expected_revision, values)


def _patch_milestone(db, project_id, milestone_id, expected_revision, values):
    actor = _project(db, project_id, write=True)
    state = _lock(db, project_id, expected_revision)
    row = db.query(Milestone).filter_by(project_id=project_id, id=milestone_id).first()
    if row is None:
        raise HTTPException(404, "Jalon introuvable")
    plan = db.get(MilestonePlan, milestone_id)
    previous = _milestone(row, plan)
    previous_milestones = _milestone_rows(db, project_id)
    if values.get('workflow_status') == 'validated':
        from .deliverable_gates import require_milestone_gates
        require_milestone_gates(db, project_id, milestone_id)
    if values.get("code"):
        duplicate = db.query(MilestonePlan).filter(MilestonePlan.project_id == project_id,
            MilestonePlan.code == values["code"], MilestonePlan.milestone_id != milestone_id).first()
        if duplicate:
            raise HTTPException(409, "Ce code est déjà affecté à un autre jalon")
    if plan is None:
        plan = MilestonePlan(milestone_id=milestone_id, project_id=project_id)
        db.add(plan)
        db.flush()
    for field in ("code", "position", "workflow_status", "comment", "active"):
        if field in values:
            setattr(plan, field, values[field])
    milestones.apply_dates(db, row, {key: values[key] for key in ("title", *milestones.DATE_FIELDS) if key in values},
                           {"kind": "manual", "label": "Saisie manuelle", "actor": actor.id})
    db.flush()
    opened = _advance_workflow(db, project_id, milestone_id, previous, values)
    current = _milestone(row, plan)
    _change(db, actor, state, "milestone_changed", {"milestones": previous_milestones},
            {"milestones": _milestone_rows(db, project_id)})
    return {"revision": state.revision, "milestone": current, "opened_milestone_id": opened}


def _advance_workflow(db, project_id, milestone_id, previous, values):
    """Only explicitly coded active steps participate. Never infer actual dates.

    Opening does not validate another step. Validation opens the next pending
    step unless blocked or an existing step is already open. Both changes share
    one revision and one complete milestone history entry.
    """
    rows = [row for row in _milestone_rows(db, project_id) if row['code'] and row['active']]
    target = next((row for row in rows if row['id'] == milestone_id), None)
    if target is None:
        return None
    others_open = any(row['workflow_status'] == 'open' and row['id'] != milestone_id for row in rows)
    if target['workflow_status'] == 'open' and others_open:
        raise HTTPException(409, "Un jalon est déjà ouvert ; le traiter explicitement avant d'en ouvrir un autre")
    if (values.get('workflow_status') != 'validated' or previous['workflow_status'] == 'validated' or others_open):
        return None
    following = rows[rows.index(target) + 1:]
    next_step = next((row for row in following if row['workflow_status'] not in {'validated', 'skipped'}), None)
    if next_step is None or next_step['workflow_status'] != 'pending':
        return None
    db.get(MilestonePlan, next_step['id']).workflow_status = 'open'
    db.flush()
    return next_step['id']


def _task_plan(db, row):
    plan = db.get(TaskPlan, row.id)
    if plan is None:
        plan = TaskPlan(task_id=row.id, project_id=row.project_id, end_date=row.due_date or "")
        db.add(plan)
        db.flush()
    return plan


def _aggregate(db, project_id):
    _, task_rows = _rows(db, project_id)
    by_id = {row["id"]: row for row in task_rows}
    graph = {key: {**row, "project_id": project_id} for key, row in by_id.items()}
    children = {}
    for row in task_rows:
        validate_parent(graph, project_id, row["id"], row["parent_id"])
        if row["parent_id"]:
            children.setdefault(row["parent_id"], []).append(row["id"])
    pending = set(children)
    while pending:
        ready = [key for key in pending if not any(child in pending for child in children[key])]
        if not ready:
            raise HTTPException(422, "Cycle de tâches interdit")
        for key in ready:
            child_rows = [by_id[child] for child in children[key] if by_id[child]["active"]]
            row = db.get(Task, key)
            plan = _task_plan(db, row)
            hours = sum(value["planned_hours"] for value in child_rows)
            if hours > 1000000:
                raise HTTPException(422, "La charge cumulée du groupe dépasse 1 000 000 heures")
            plan.planned_hours = hours
            plan.start_date = min(value["start_date"] for value in child_rows) if child_rows and all(value["start_date"] for value in child_rows) else ""
            plan.end_date = max(value["end_date"] for value in child_rows) if child_rows and all(value["end_date"] for value in child_rows) else ""
            row.due_date = plan.end_date
            by_id[key] = _task(row, plan)
            pending.remove(key)
    db.flush()


def patch_task(db, project_id, task_id, payload):
    return _patch_task(db, project_id, task_id, payload.expected_revision,
                       payload.model_dump(exclude_unset=True, exclude={"expected_revision"}))


def patch_legacy_task(db, project_id, task_id, changes, expected_revision=None):
    values = {key: value for key, value in changes.items() if value is not None}
    if "due_date" in values:
        values["end_date"] = values.pop("due_date")
    return _patch_task(db, project_id, task_id, expected_revision, values)


def create_task(db, project_id, payload):
    actor, state = begin_change(db, project_id, payload.expected_revision)
    row = Task(project_id=project_id, title=payload.title)
    db.add(row)
    db.flush()
    values = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
    return _patch_task(db, project_id, row.id, payload.expected_revision, values,
                       context=(actor, state), created=True)


def _patch_task(db, project_id, task_id, expected_revision, values, *, context=None, created=False):
    if context is None:
        actor = _project(db, project_id, write=True)
        state = _lock(db, project_id, expected_revision)
    else:
        actor, state = context
    row = db.query(Task).filter_by(project_id=project_id, id=task_id).first()
    if row is None:
        raise HTTPException(404, "Tâche introuvable")
    previous_milestones, previous_tasks = _rows(db, project_id)
    previous = next(value for value in previous_tasks if value["id"] == task_id)
    graph = {value["id"]: {**value, "project_id": project_id} for value in previous_tasks}
    parent_id = values.get("parent_task_id", previous["parent_id"])
    try:
        validate_parent(graph, project_id, task_id, parent_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if parent_id:
        if not graph[parent_id]["active"]:
            raise HTTPException(422, "La tâche parente est archivée")
        if not any(value["parent_id"] == parent_id for value in previous_tasks) and any(
                graph[parent_id][key] for key in ("planned_hours", "start_date", "end_date")):
            raise HTTPException(422, "La tâche parente possède des dates ou une charge propres ; choisir un groupe vide")
    children = [value for value in previous_tasks if value["parent_id"] == task_id]
    if children and any(key in values for key in ("planned_hours", "start_date", "end_date")):
        raise HTTPException(422, "Les dates et charges d'une tâche parente proviennent de ses enfants")
    if values.get("active") is False and any(value["active"] for value in children):
        raise HTTPException(422, "Archiver les enfants avant leur tâche parente")
    milestone_id = values.get("milestone_id", previous["milestone_id"])
    if milestone_id and not any(value["id"] == milestone_id for value in previous_milestones):
        raise HTTPException(422, "Jalon absent du projet")
    person_id = values.get("responsible_id", previous["responsible_id"])
    if person_id:
        _person(db, person_id, allow_inactive=person_id == previous["responsible_id"])
    if values.get("status", previous["status"]) == "assigned" and not person_id:
        raise HTTPException(422, "Une tâche affectée doit avoir un responsable")
    start, end = values.get("start_date", previous["start_date"]), values.get("end_date", previous["end_date"])
    if start and end and end < start:
        raise HTTPException(422, "La fin de tâche précède son début")
    plan = _task_plan(db, row)
    for field in ("title", "status"):
        if field in values:
            setattr(row, field, values[field])
    for field, value in values.items():
        if field not in {"title", "status"}:
            setattr(plan, field, value)
    if "end_date" in values:
        row.due_date = plan.end_date
    db.flush()
    _aggregate(db, project_id)
    current_milestones, current_tasks = _rows(db, project_id)
    _change(db, actor, state, "task_created" if created else "task_changed",
            {"tasks": [row for row in previous_tasks if not created or row["id"] != task_id]}, {"tasks": current_tasks})
    return {"revision": state.revision, "task": next(value for value in current_tasks if value["id"] == task_id)}


def create_baseline(db, project_id, *, expected_revision, kind, label):
    actor = _project(db, project_id, write=True)
    if kind not in {"initial", "contractual", "review", "amendment"} or not isinstance(label, str) or not 1 <= len(label.strip()) <= 255:
        raise HTTPException(422, "Type et libellé de référence requis")
    state = _lock(db, project_id, expected_revision)
    milestone_rows, task_rows = _rows(db, project_id)
    try:
        snapshot = capture_snapshot(project_id, milestone_rows, task_rows, project=project_values(db, project_id))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    baseline = PlanningBaseline(project_id=project_id, kind=kind, label=label.strip(),
                                planning_revision=state.revision, payload=snapshot.payload,
                                sha256=snapshot.sha256, actor_id=actor.id)
    db.add(baseline)
    db.flush()
    _change(db, actor, state, "baseline_created", {}, {"baseline_id": baseline.id, "kind": kind, "sha256": baseline.sha256})
    return {"id": baseline.id, "label": baseline.label, "kind": kind, "revision": state.revision, "sha256": baseline.sha256}


def compare_baseline(db, project_id, baseline_id):
    _project(db, project_id)
    state = db.get(ProjectPlanningState, project_id)
    revision = state.revision if state else 0
    baseline = db.query(PlanningBaseline).filter_by(id=baseline_id, project_id=project_id).first()
    if baseline is None:
        raise HTTPException(404, "Référence introuvable")
    milestone_rows, task_rows = _rows(db, project_id)
    try:
        return {**compare_snapshots(PlanningSnapshot(baseline.payload, baseline.sha256),
                                  capture_snapshot(project_id, milestone_rows, task_rows, project=project_values(db, project_id))),
                'revision': revision, 'baseline_revision': baseline.planning_revision}
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
