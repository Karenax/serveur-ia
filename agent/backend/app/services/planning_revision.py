"""One transaction lock for all human, legacy and evidence-based planning writes."""
from fastapi import HTTPException
from sqlalchemy import inspect, update
from sqlalchemy.dialects.sqlite import insert

from ..models import Project
from ..project_planning_models import PlanningChange, ProjectPlanningState
from .project_operator import require_project_access


def revision(db, project_id):
    state = db.get(ProjectPlanningState, project_id)
    return state.revision if state else 0


def begin_change(db, project_id, expected_revision=None):
    """Caller owns rollback. Missing legacy revision still invalidates old views.

    The SQLite INSERT obtains the write lock before the revision predicate is
    evaluated. Never read a revision and then issue an unconditional update.
    """
    actor = require_project_access(project_id, write=True)
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "Projet introuvable")
    db.execute(insert(ProjectPlanningState).values(project_id=project_id, excluded_dates=[])
               .on_conflict_do_nothing(index_elements=["project_id"]))
    command = update(ProjectPlanningState).where(ProjectPlanningState.project_id == project_id)
    if expected_revision is not None:
        command = command.where(ProjectPlanningState.revision == expected_revision)
    changed = db.execute(command.values(revision=ProjectPlanningState.revision + 1)
                         .execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise HTTPException(409, "Planning modifié : recharger avant de réappliquer la commande")
    db.expire_all()
    return actor, db.get(ProjectPlanningState, project_id)


def record_change(db, actor, state, action, previous, value):
    db.add(PlanningChange(project_id=state.project_id, revision=state.revision,
                          actor_id=actor.id, action=action, previous=previous, value=value))


def project_values(db, project_id):
    from ..project_identity_models import ProjectProfile
    row = db.get(Project, project_id)
    profile = db.get(ProjectProfile, project_id)
    return {'start_date': profile.start_date if profile else '',
            'planned_end_date': profile.planned_end_date if profile else '',
            'budget_hours': row.tdao_budget_h}


def record_project_dates(db, project_id, before, after):
    """L1 remains usable without L2; installed L2 shares the same transaction."""
    if all(before[field] == after[field] for field in ('start_date', 'planned_end_date')):
        return
    tables = set(inspect(db.connection()).get_table_names())
    if not {'project_planning_states', 'project_planning_changes'} <= tables:
        return
    # Metadata.create_all may expose dormant tables before L2 activation.
    # Record only once all immutable protections have been installed.
    from .project_planning_migration import immutable_triggers, _sql
    expected = immutable_triggers()
    installed = {name: statement for name, statement in db.connection().exec_driver_sql(
        "SELECT name, sql FROM sqlite_master WHERE type='trigger'")}
    if not set(expected).intersection(installed):
        return
    if any(name not in installed or _sql(installed[name]) != _sql(statement) for name, statement in expected.items()):
        raise HTTPException(409, "Protections du planning incomplètes : vérifier la migration L2")
    from .project_planning_rules import validate_project_values
    current = validate_project_values(project_values(db, project_id))
    previous = {**current, **{field: before[field] for field in ('start_date', 'planned_end_date')}}
    actor, state = begin_change(db, project_id)
    record_change(db, actor, state, 'project_changed', {'project': previous}, {'project': current})
    db.flush()
