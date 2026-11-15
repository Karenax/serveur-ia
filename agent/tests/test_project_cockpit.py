"""Complete scoped cockpit reads and existing command parity on fictional stores."""
import json

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from backend.app.db import get_db
from backend.app.models import CdcItem, Deliverable, Milestone, MilestoneCandidate, Project, SagePointage, Task, TimeEntry
from backend.app.project_deliverable_models import DeliverableMilestone, DeliverablePlan
from backend.app.project_planning_models import MilestonePlan, TaskPlan
from backend.app.project_planning_schemas import TaskPlanningCreate, TaskPlanningPatch
from backend.app.routers import project_cockpit as http
from backend.app.routers.portfolio_tools import planning as timeline
from backend.app.routers.projects import portfolio
from backend.app.services import project_cockpit as cockpit, project_planning as commands
from backend.app.services.migration_guard import capture_baseline
from backend.app.services.project_operator import Operator, operator_context
from tests.test_project_reviews import store as review_store, transaction

store = review_store


def seed(store, *, count=6):
    factory, ids, *_ = store
    pid = ids['project']
    with transaction(factory) as db:
        past = Milestone(project_id=pid, title='Réception passée', actual_date='2026-01-01')
        foreign = Milestone(project_id=ids['foreign'], title='Jalon étranger')
        db.add_all([past, foreign])
        db.flush()
        db.add_all([MilestonePlan(milestone_id=ids['milestone'], project_id=pid, position=1, workflow_status='open'),
                    MilestonePlan(milestone_id=past.id, project_id=pid, position=0, workflow_status='validated')])
        tasks = [Task(project_id=pid, title=f'Étude {i:04}', status='done' if i == 0 else 'todo') for i in range(count)]
        tasks.extend([Task(project_id=pid, title='Sans plan'), Task(project_id=ids['foreign'], title='Secret')])
        db.add_all(tasks)
        db.flush()
        db.add_all([TaskPlan(task_id=t.id, project_id=pid, milestone_id=ids['milestone'],
                             parent_task_id=tasks[0].id if i else None, active=i != count - 1)
                    for i, t in enumerate(tasks[:count])])
        db.add_all([DeliverablePlan(deliverable_id=ids['deliverable'], project_id=pid, document_status='to_verify'),
            DeliverableMilestone(project_id=pid, deliverable_id=ids['deliverable'], milestone_id=ids['milestone']),
            DeliverableMilestone(project_id=pid, deliverable_id=ids['deliverable'], milestone_id=past.id)])
        ids.update(past=past.id, foreign_milestone=foreign.id, tasks=[t.id for t in tasks])
    return ids


def test_complete_counts_layers_and_no_read_mutation(store):
    ids = seed(store, count=607)
    before = capture_baseline(store[2])
    with store[0]() as db:
        graph = cockpit.structure(db, ids['project'], limit=1)
        assert graph['tasks'] == {'total': 608, 'done': 1, 'active': 607, 'open': 606, 'blocked': 0, 'overdue': 0}
        assert graph['items'][0]['task_count'] == 606
        assert graph['items'][0]['deliverable_count'] == 1
        assert graph['deliverables_total'] == 1 and graph['milestones_total'] == 2
        assert graph['unassigned_tasks'] == 1 and graph['unassigned_deliverables'] == 0
        first = cockpit.task_page(db, ids['project'], milestone_id=ids['milestone'], limit=100)
        last = cockpit.task_page(db, ids['project'], milestone_id=ids['milestone'], offset=600, limit=100)
        assert first['total'] == last['total'] == 606
        assert len(first['items']) == 100 and len(last['items']) == 6
        assert first['items'][1]['parent_title'] == 'Étude 0000'
        docs = cockpit.document_page(db, ids['project'], milestone_id=ids['milestone'])
        assert docs['total'] == 1 and set(docs['items'][0]['milestone_ids']) == {ids['milestone'], ids['past']}
        assert cockpit.document_page(db, ids['project'], milestone_id=ids['past'])['total'] == 1
        assert cockpit.task_page(db, ids['project'], unassigned=True)['items'][0]['title'] == 'Sans plan'
    assert capture_baseline(store[2]) == before


def test_search_accents_literal_percent_and_related_milestones(store):
    ids = seed(store)
    with transaction(store[0]) as db:
        db.get(Task, ids['tasks'][1]).title = 'Vérifier 50% des écarts'
        db.get(Deliverable, ids['deliverable']).title = 'État réseau'
    with store[0]() as db:
        assert cockpit.task_page(db, ids['project'], search='verifier 50%')['total'] == 1
        assert cockpit.task_page(db, ids['project'], search='%')['total'] == 1
        assert cockpit.structure(db, ids['project'], search='verifier')['total'] == 1
        assert cockpit.structure(db, ids['project'], search='etat', show_past=True)['total'] == 2
        assert cockpit.structure(db, ids['project'], search='absent')['total'] == 0


def test_past_filter_order_and_explicit_current(store):
    ids = seed(store)
    with store[0]() as db:
        view = cockpit.structure(db, ids['project'])
        assert view['current_milestone']['id'] == ids['milestone']
        assert [r['id'] for r in view['items']] == [ids['milestone']]
        full = cockpit.structure(db, ids['project'], show_past=True, limit=1)
        assert full['total'] == 2 and full['items'][0]['id'] == ids['past']
        assert cockpit.structure(db, ids['project'], show_past=True, offset=1, limit=1)['items'][0]['id'] == ids['milestone']


@pytest.mark.parametrize('estimated,reestimated', [(0, None), (24, None), (24, 7)])
def test_hours_and_task_progress_match_portfolio_and_timeline(store, estimated, reestimated):
    ids = seed(store)
    with transaction(store[0]) as db:
        project = db.get(Project, ids['project'])
        project.tdao_budget_h, project.remaining_hours = 30, reestimated
        db.add_all([TimeEntry(project_id=project.id, person='Recette', hours=4),
            SagePointage(batch_id='fictitious', affaire='  l4-0001  ', payload=json.dumps({'Heures': '3,5'})),
            SagePointage(batch_id='fictitious', affaire='L4-0002', payload=json.dumps({'Heures': '100'})),
            CdcItem(project_id=project.id, kind='function', title='Fonction', source_quote='Preuve', estimated_hours=estimated),
            CdcItem(project_id=project.id, kind='function', title='Rejet', source_quote='Preuve', estimated_hours=1000, knowledge_status='rejected')])
    with store[0]() as db:
        view = cockpit.structure(db, ids['project'])
        row = next(r for r in portfolio(db) if r['id'] == ids['project'])
        agenda = timeline(ids['project'], db)
        assert view['hours']['initial_hours'] == row['initial_hours'] == agenda['budget_hours'] == (estimated or 30)
        assert view['hours']['consumed_hours'] == row['consumed_hours'] == agenda['consumed_hours'] == 7.5
        assert view['hours']['raf'] == row['raf'] == agenda['remaining_hours']
        assert view['progress'] == row['avancement']
        assert not {'hourly_rate', 'margin_pct', 'sales'} & set(view['project'])


def test_alerts_complete_independent_paging_and_archived_exclusion(store):
    ids = seed(store)
    with transaction(store[0]) as db:
        db.get(Task, ids['tasks'][1]).status = 'blocked'
        db.get(Task, ids['tasks'][1]).due_date = '2000-01-01'
        db.get(Task, ids['tasks'][5]).status = 'blocked'
        db.add_all([CdcItem(project_id=ids['project'], kind='open_point', title='Question', source_quote='Preuve'),
            MilestoneCandidate(project_id=ids['project'], title='Date proposée', date_type='forecast_date',
                               value='2026-11-01', quote='Preuve', fingerprint='a' * 64)])
    with store[0]() as db:
        first = cockpit.alerts(db, ids['project'], limit=2)
        rest = cockpit.alerts(db, ids['project'], offset=2)
        assert first['total'] == rest['total'] == 6
        assert {r['kind'] for r in first['items']} == {'overdue', 'blocked'}
        assert {r['kind'] for r in rest['items']} == {'document_review', 'date_proposal', 'cdc_review', 'open_point'}


@pytest.mark.parametrize('corruption', ['task_project', 'task_milestone', 'task_parent', 'document_link'])
def test_inconsistent_relations_refused_on_all_branches(store, corruption):
    ids = seed(store)
    with transaction(store[0]) as db:
        plan = db.get(TaskPlan, ids['tasks'][1])
        if corruption == 'task_project':
            plan.project_id = ids['foreign']
        elif corruption == 'task_milestone':
            plan.milestone_id = ids['foreign_milestone']
        elif corruption == 'task_parent':
            plan.parent_task_id = ids['tasks'][-1]
        else:
            link = db.query(DeliverableMilestone).filter_by(milestone_id=ids['milestone']).one()
            link.milestone_id = ids['foreign_milestone']
    with store[0]() as db:
        for fn in (cockpit.structure, cockpit.task_page, cockpit.document_page, cockpit.alerts):
            with pytest.raises(HTTPException) as exc:
                fn(db, ids['project'])
            assert exc.value.status_code == 409


def test_existing_task_commands_refresh_cockpit_and_revision(store):
    ids = seed(store)
    with transaction(store[0]) as db:
        created = commands.create_task(db, ids['project'], TaskPlanningCreate(expected_revision=0,
            title='Créée depuis le jalon', milestone_id=ids['milestone'], planned_hours=3))
    with store[0]() as db:
        view = cockpit.structure(db, ids['project'])
        assert view['revision'] == created['revision'] == 1 and view['items'][0]['task_count'] == 6
        assert cockpit.task_page(db, ids['project'], search='créée')['items'][0]['milestone_id'] == ids['milestone']
    with transaction(store[0]) as db:
        commands.patch_task(db, ids['project'], created['task']['id'], TaskPlanningPatch(expected_revision=1, status='done'))
    with store[0]() as db:
        assert cockpit.structure(db, ids['project'])['tasks']['done'] == 2
        with pytest.raises(HTTPException) as exc:
            commands.patch_task(db, ids['project'], created['task']['id'], TaskPlanningPatch(expected_revision=1, title='Périmée'))
        assert exc.value.status_code == 409


@pytest.mark.parametrize('fn', [cockpit.structure, cockpit.task_page, cockpit.document_page, cockpit.alerts])
def test_revision_fence_refuses_mixed_read(store, monkeypatch, fn):
    ids = seed(store)
    revisions = iter([0, 1])
    monkeypatch.setattr(cockpit, '_revision', lambda *_: next(revisions))
    with store[0]() as db, pytest.raises(HTTPException) as exc:
        fn(db, ids['project'])
    assert exc.value.status_code == 409


def test_http_reader_scope_invalid_pages_and_context(store):
    ids = seed(store)
    app = FastAPI()
    app.include_router(http.router)
    def dependency():
        with store[0]() as db:
            yield db
    app.dependency_overrides[get_db] = dependency
    root = f"/api/v1/projects/{ids['project']}/cockpit"
    before = capture_baseline(store[2])
    with TestClient(app) as client, operator_context(Operator('reader', 'reader', frozenset([ids['project']]))):
        assert not client.get(root).json()['can_edit']
        assert client.get(root + '/items/tasks?limit=1').json()['total'] == 6
        assert client.get(root + '/alerts').status_code == 200
        for suffix in ('?limit=101', '?offset=-1', '?search=' + 'a' * 201, '/items/unknown',
                       f"/items/tasks?milestone_id={ids['milestone']}&unassigned=true"):
            assert client.get(root + suffix).status_code == 422
        assert client.get(root + f"/items/tasks?milestone_id={ids['foreign_milestone']}").status_code == 404
        assert client.get(root.replace(ids['project'], ids['foreign'])).status_code == 404
    assert capture_baseline(store[2]) == before
