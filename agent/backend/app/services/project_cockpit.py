"""Scoped ERP cockpit reads. Complete aggregates, bounded independent layers.

No mirror graph database, no implicit plan creation or migration. Commands stay
in the existing L2/L3 services. A revision fence refuses a mixed planning read.
"""
from datetime import date

from fastapi import HTTPException
from sqlalchemy import case, func, literal, select, union_all
from sqlalchemy.orm import aliased

from ..models import CdcItem, Deliverable, Milestone, MilestoneCandidate, Project, SagePointage, Task, TimeEntry
from ..project_deliverable_models import DeliverableMilestone, DeliverablePlan
from ..project_identity_models import ProjectProfile
from ..project_planning_models import MilestonePlan, ProjectPlanningState, TaskPlan
from .deliverable_queries import _search
from .project_identity import _project
from .project_planning import _milestone, _task
from .work_hours import project_hours, sage_hours


def _revision(db, project_id):
    return db.scalar(select(ProjectPlanningState.revision).where(ProjectPlanningState.project_id == project_id)) or 0


def _finish(db, project_id, expected, value):
    if _revision(db, project_id) != expected:
        raise HTTPException(409, 'Le projet a changé pendant le chargement ; recharger le cockpit')
    return {**value, 'revision': expected}


def _page(offset, limit, search=''):
    if not 0 <= offset <= 1000000 or not 1 <= limit <= 100 or len(search) > 200:
        raise HTTPException(422, 'Pagination ou recherche du cockpit invalide')


def _tasks(db, project_id):
    return db.query(Task, TaskPlan).outerjoin(TaskPlan, TaskPlan.task_id == Task.id).filter(
        Task.project_id == project_id, func.coalesce(TaskPlan.active, True).is_(True))


def _documents(db, project_id):
    return db.query(Deliverable, DeliverablePlan).outerjoin(DeliverablePlan, DeliverablePlan.deliverable_id == Deliverable.id).filter(
        Deliverable.project_id == project_id, func.coalesce(DeliverablePlan.active, True).is_(True))


def _milestones(db, project_id):
    return db.query(Milestone, MilestonePlan).outerjoin(MilestonePlan, MilestonePlan.milestone_id == Milestone.id).filter(
        Milestone.project_id == project_id, func.coalesce(MilestonePlan.active, True).is_(True))


def _assert_relations(db, project_id):
    for model, plan, key in ((Task, TaskPlan, TaskPlan.task_id), (Milestone, MilestonePlan, MilestonePlan.milestone_id),
                             (Deliverable, DeliverablePlan, DeliverablePlan.deliverable_id)):
        if db.query(model.id).join(plan, key == model.id).filter(model.project_id == project_id,
                                                               plan.project_id != project_id).first():
            raise HTTPException(409, 'Relations de cockpit incohérentes : vérifier le rattachement au projet')
    if db.query(TaskPlan.task_id).join(Task, Task.id == TaskPlan.task_id).join(
            Milestone, Milestone.id == TaskPlan.milestone_id).filter(Task.project_id == project_id,
                                                                   Milestone.project_id != project_id).first():
        raise HTTPException(409, 'Une tâche est liée à un jalon étranger')
    parent = aliased(Task)
    if db.query(TaskPlan.task_id).join(Task, Task.id == TaskPlan.task_id).join(
            parent, parent.id == TaskPlan.parent_task_id).filter(Task.project_id == project_id,
                                                               parent.project_id != project_id).first():
        raise HTTPException(409, 'Une tâche est liée à un parent étranger')
    if db.query(DeliverableMilestone.id).join(Deliverable, Deliverable.id == DeliverableMilestone.deliverable_id).join(
            Milestone, Milestone.id == DeliverableMilestone.milestone_id).filter(
            ((Deliverable.project_id == project_id) | (DeliverableMilestone.project_id == project_id)),
            ((Deliverable.project_id != project_id) | (Milestone.project_id != project_id)
             | (DeliverableMilestone.project_id != project_id))).first():
        raise HTTPException(409, 'Un livrable est lié à un jalon étranger')


def _milestone_context(db, project_id, milestone_id, unassigned):
    if milestone_id and unassigned:
        raise HTTPException(422, 'Choisir un jalon ou les éléments sans jalon')
    if milestone_id and not db.query(Milestone.id).filter_by(id=milestone_id, project_id=project_id).first():
        raise HTTPException(404, 'Jalon introuvable dans ce projet')


def _task_counts(db, project_id, today):
    active = func.coalesce(TaskPlan.active, True).is_(True)
    opened = Task.status.notin_(['done', 'cancelled'])
    row = db.query(func.count(Task.id), func.sum(case((Task.status == 'done', 1), else_=0)),
        func.sum(case((active, 1), else_=0)), func.sum(case((active & opened, 1), else_=0)),
        func.sum(case((active & (Task.status == 'blocked'), 1), else_=0)),
        func.sum(case((active & opened & (Task.due_date != '') & (Task.due_date < today), 1), else_=0)))
    values = row.outerjoin(TaskPlan, TaskPlan.task_id == Task.id).filter(Task.project_id == project_id).one()
    return {key: int(value or 0) for key, value in zip(('total', 'done', 'active', 'open', 'blocked', 'overdue'), values)}


def structure(db, project_id, *, search='', show_past=False, offset=0, limit=50):
    _page(offset, limit, search)
    actor = _project(db, project_id)
    start = _revision(db, project_id)
    _assert_relations(db, project_id)
    project = db.get(Project, project_id)
    profile = db.get(ProjectProfile, project_id)
    today = date.today().isoformat()
    tasks = _task_counts(db, project_id, today)
    docs = _documents(db, project_id)
    cdc_hours = db.scalar(select(func.sum(CdcItem.estimated_hours)).where(CdcItem.project_id == project_id,
        CdcItem.knowledge_status.notin_(['rejected', 'superseded']))) or 0
    consumed = db.scalar(select(func.sum(TimeEntry.hours)).where(TimeEntry.project_id == project_id)) or 0
    if project.code.strip():
        consumed += sum(sage_hours(row.payload) for row in db.query(SagePointage).filter(
            func.lower(func.trim(SagePointage.affaire)) == project.code.strip().casefold()))
    milestones = _milestones(db, project_id)
    # Use the same workflow ordering/legacy aliases as L2. Milestones form a
    # small workflow spine; no task/doc bodies are downloaded for the spine.
    all_milestones = sorted((_milestone(row, plan) for row, plan in milestones), key=lambda row: (row['order'], row['id']))
    current = next((row for row in all_milestones if row['workflow_status'] == 'open'), None)
    if current is None:
        current = next((row for row in all_milestones if row['workflow_status'] not in ('validated', 'skipped')
                        and not row['actual_date']), None)
    matching = {row.id for row, _ in _search(db, milestones, search, (Milestone.title, MilestonePlan.code))}
    if search.strip():
        task_ids = _search(db, _tasks(db, project_id), search, (Task.title, TaskPlan.comment)).with_entities(TaskPlan.milestone_id)
        matching.update(row[0] for row in task_ids if row[0])
        document_ids = _search(db, docs, search, (Deliverable.title, DeliverablePlan.comment)).with_entities(Deliverable.id)
        matching.update(row[0] for row in db.query(DeliverableMilestone.milestone_id).filter(
            DeliverableMilestone.project_id == project_id, DeliverableMilestone.active.is_(True),
            DeliverableMilestone.deliverable_id.in_(document_ids)))
    visible = []
    for row in all_milestones:
        row['past'] = row['workflow_status'] in ('validated', 'skipped') or bool(
            row['actual_date'] and row['workflow_status'] != 'open')
        if row['id'] in matching and (show_past or not row['past'] or current and row['id'] == current['id']):
            visible.append(row)
    page = visible[offset:offset + limit]
    identities = [row['id'] for row in page]
    task_counts = dict(_tasks(db, project_id).with_entities(TaskPlan.milestone_id, func.count(Task.id)).filter(
        TaskPlan.milestone_id.in_(identities)).group_by(TaskPlan.milestone_id).all())
    links = DeliverableMilestone
    linked = db.query(links.milestone_id, func.count(func.distinct(links.deliverable_id))).join(
        Deliverable, Deliverable.id == links.deliverable_id).outerjoin(DeliverablePlan, DeliverablePlan.deliverable_id == Deliverable.id).filter(
        links.project_id == project_id, links.active.is_(True), links.milestone_id.in_(identities),
        func.coalesce(DeliverablePlan.active, True).is_(True)).group_by(links.milestone_id)
    doc_counts = dict(linked.all())
    for row in page:
        row['task_count'], row['deliverable_count'] = task_counts.get(row['id'], 0), doc_counts.get(row['id'], 0)
    attached = db.query(links.deliverable_id).filter_by(project_id=project_id, active=True)
    value = {'project': {'id': project.id, 'code': project.code, 'title': project.title, 'status': project.status,
        'client_name': project.client_name, 'start_date': profile.start_date if profile else '',
        'planned_end_date': profile.planned_end_date if profile else ''}, 'can_edit': actor.role != 'reader',
        'current_milestone': current, 'tasks': tasks,
        'progress': round(100 * tasks['done'] / tasks['total']) if tasks['total'] else 0,
        'hours': project_hours(project, cdc_hours, consumed), 'deliverables_total': docs.count(),
        'milestones_total': len(all_milestones), 'items': page, 'total': len(visible), 'offset': offset, 'limit': limit,
        'unassigned_tasks': _tasks(db, project_id).filter(TaskPlan.milestone_id.is_(None)).count(),
        'unassigned_deliverables': docs.filter(~Deliverable.id.in_(attached)).count()}
    return _finish(db, project_id, start, value)


def task_page(db, project_id, *, milestone_id=None, unassigned=False, search='', offset=0, limit=25):
    _page(offset, limit, search)
    _project(db, project_id)
    start = _revision(db, project_id)
    _assert_relations(db, project_id)
    _milestone_context(db, project_id, milestone_id, unassigned)
    query = _search(db, _tasks(db, project_id), search, (Task.title, TaskPlan.comment))
    if milestone_id:
        query = query.filter(TaskPlan.milestone_id == milestone_id)
    elif unassigned:
        query = query.filter(TaskPlan.milestone_id.is_(None))
    total = query.count()
    rows = [_task(row, plan) for row, plan in query.order_by(Task.title, Task.id).offset(offset).limit(limit)]
    parents = {row.id: row.title for row in db.query(Task).filter(Task.project_id == project_id,
        Task.id.in_([row['parent_id'] for row in rows if row['parent_id']]))}
    for row in rows:
        row['parent_title'] = parents.get(row['parent_id'])
    return _finish(db, project_id, start, {'items': rows, 'total': total, 'offset': offset, 'limit': limit})


def document_page(db, project_id, *, milestone_id=None, unassigned=False, search='', offset=0, limit=25):
    _page(offset, limit, search)
    _project(db, project_id)
    start = _revision(db, project_id)
    _assert_relations(db, project_id)
    _milestone_context(db, project_id, milestone_id, unassigned)
    query = _search(db, _documents(db, project_id), search, (Deliverable.title, DeliverablePlan.comment))
    links = db.query(DeliverableMilestone.deliverable_id).filter_by(project_id=project_id, active=True)
    if milestone_id:
        query = query.filter(Deliverable.id.in_(links.filter(DeliverableMilestone.milestone_id == milestone_id)))
    elif unassigned:
        query = query.filter(~Deliverable.id.in_(links))
    total = query.count()
    values = [{'id': row.id, 'title': row.title, 'status': row.status,
               'document_status': plan.document_status if plan else 'draft'}
              for row, plan in query.order_by(Deliverable.title, Deliverable.id).offset(offset).limit(limit)]
    selected = {row['id'] for row in values}
    milestone_ids = {}
    for link in db.query(DeliverableMilestone).filter_by(project_id=project_id, active=True).filter(
            DeliverableMilestone.deliverable_id.in_(selected)).order_by(DeliverableMilestone.milestone_id):
        milestone_ids.setdefault(link.deliverable_id, []).append(link.milestone_id)
    for row in values:
        row['milestone_ids'] = milestone_ids.get(row['id'], [])
    return _finish(db, project_id, start, {'items': values, 'total': total, 'offset': offset, 'limit': limit})


def alerts(db, project_id, *, offset=0, limit=25):
    _page(offset, limit)
    _project(db, project_id)
    start = _revision(db, project_id)
    _assert_relations(db, project_id)
    today = date.today().isoformat()
    active_tasks = func.coalesce(TaskPlan.active, True).is_(True)
    active_milestones = func.coalesce(MilestonePlan.active, True).is_(True)
    active_docs = func.coalesce(DeliverablePlan.active, True).is_(True)
    statements = []

    def entry(kind, entity, model, condition, severity, due, joins=()):
        statement = select(literal(kind).label('kind'), literal(entity).label('entity_kind'), model.id.label('id'),
                           model.title.label('title'), literal(severity).label('severity'), due.label('due_date'))
        for other, on in joins:
            statement = statement.outerjoin(other, on)
        statements.append(statement.where(model.project_id == project_id, condition))

    entry('overdue', 'task', Task, active_tasks & Task.status.notin_(['done', 'cancelled']) & (Task.due_date != '')
          & (Task.due_date < today), 'high', Task.due_date, [(TaskPlan, TaskPlan.task_id == Task.id)])
    entry('blocked', 'task', Task, active_tasks & (Task.status == 'blocked'), 'high', Task.due_date,
          [(TaskPlan, TaskPlan.task_id == Task.id)])
    forecast = func.coalesce(func.nullif(Milestone.forecast_date, ''), Milestone.due_date)
    entry('overdue', 'milestone', Milestone, active_milestones & (Milestone.actual_date == '') & (forecast != '')
          & (forecast < today) & func.coalesce(MilestonePlan.workflow_status, 'pending').notin_(['validated', 'skipped']),
          'high', forecast, [(MilestonePlan, MilestonePlan.milestone_id == Milestone.id)])
    entry('blocked', 'milestone', Milestone, active_milestones & (MilestonePlan.workflow_status == 'blocked'),
          'high', forecast, [(MilestonePlan, MilestonePlan.milestone_id == Milestone.id)])
    entry('document_review', 'deliverable', Deliverable, active_docs & DeliverablePlan.document_status.in_(['to_verify', 'to_revise']),
          'normal', literal(''), [(DeliverablePlan, DeliverablePlan.deliverable_id == Deliverable.id)])
    entry('date_proposal', 'candidate', MilestoneCandidate, MilestoneCandidate.status == 'pending', 'normal', literal(''))
    entry('cdc_review', 'cdc', CdcItem, CdcItem.knowledge_status.notin_(['confirmed', 'rejected', 'superseded']),
          'normal', literal(''))
    entry('open_point', 'cdc', CdcItem, (CdcItem.kind == 'open_point') & CdcItem.knowledge_status.notin_(['rejected', 'superseded']),
          'normal', literal(''))
    combined = union_all(*statements).subquery()
    total = db.scalar(select(func.count()).select_from(combined))
    rows = db.execute(select(combined).order_by(case((combined.c.severity == 'high', 0), else_=1),
         combined.c.due_date, combined.c.entity_kind, combined.c.title, combined.c.id, combined.c.kind).offset(offset).limit(limit)).mappings()
    return _finish(db, project_id, start, {'items': [dict(row) for row in rows], 'total': total,
                                         'offset': offset, 'limit': limit})
