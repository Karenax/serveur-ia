"""L2 additive schema, concurrency, ownership, neutral legacy reads and freezing."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db_support import backup_sqlite, configure_sqlite
from backend.app.db import Base
from backend.app.models import (
    Deliverable, Meeting, MeetingAction, Milestone, MilestoneCandidate, MilestoneChange, Project, Task,
)
from backend.app.project_identity_models import IDENTITY_TABLES, ProjectPerson
from backend.app.project_planning_models import (
    IMMUTABLE_TABLES, MilestonePlan, PlanningBaseline, PlanningChange, PlanningTemplate,
    PlanningTemplateVersion, ProjectPlanningState, TaskPlan,
)
from backend.app.project_planning_schemas import MilestonePlanningPatch, TaskPlanningPatch
from backend.app.services import project_planning as planning
from backend.app.services.migration_guard import capture_baseline, compare_baseline
from backend.app.services.project_operator import Operator, operator_context
from backend.app.services.project_planning_migration import install_planning_schema


@contextmanager
def transaction(factory):
    with factory() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise


@pytest.fixture
def store(tmp_path):
    path = tmp_path / 'planning.db'
    engine = create_engine(f'sqlite:///{path}', connect_args={'check_same_thread': False})
    configure_sqlite(engine)
    Base.metadata.create_all(engine, tables=[Project.__table__, Milestone.__table__, MilestoneChange.__table__, Task.__table__, *IDENTITY_TABLES])
    factory = sessionmaker(bind=engine, autoflush=False)
    with transaction(factory) as db:
        projects = [Project(code=f'PLAN-{index}', title=f'Projet fictif {index}', hourly_rate=97, margin_pct=11) for index in (1, 2)]
        db.add_all(projects)
        db.flush()
        milestones = [Milestone(project_id=row.id, title='FAT', contractual_date='2026-10-02', forecast_date='2026-10-06') for row in projects]
        tasks = [Task(project_id=projects[0].id, title='Groupe'), Task(project_id=projects[0].id, title='Études'),
                 Task(project_id=projects[0].id, title='Contrôle'), Task(project_id=projects[1].id, title='Tâche autre projet')]
        person = ProjectPerson(first_name='Alice', last_name='Recette')
        db.add_all([*milestones, *tasks, person])
        db.flush()
        ids = {'projects': [row.id for row in projects], 'milestones': [row.id for row in milestones],
               'tasks': [row.id for row in tasks], 'person': person.id}
    before = capture_baseline(path)
    backup = tmp_path / 'before-l2.db'
    installed = install_planning_schema(engine, backup=lambda: backup_sqlite(path, backup))
    yield factory, ids, path, before, backup, installed
    engine.dispose()


def patch_task(store, index=1, **values):
    factory, ids, *_ = store
    with transaction(factory) as db:
        return planning.patch_task(db, ids['projects'][0], ids['tasks'][index], TaskPlanningPatch(**values))


def test_legacy_milestone_workflow_order_precedes_pagination_and_honors_explicit_positions(store):
    factory, ids, *_ = store
    project_id = ids['projects'][0]
    with transaction(factory) as db:
        rows = [Milestone(project_id=project_id, title=title) for title in (
            'Validation du CDC', 'Lancement du projet', 'reception-definitive', 'Revue de conception',
            'Fin des études', 'Livraison', 'SAT', 'Contrôle spécifique', 'Autre jalon')]
        db.add_all(rows)
        db.flush()
        explicit = next(row for row in rows if row.title == 'Contrôle spécifique')
        db.add(MilestonePlan(milestone_id=explicit.id, project_id=project_id, position=9))
    expected = ['Lancement du projet', 'Validation du CDC', 'Revue de conception', 'Fin des études',
                'FAT', 'Livraison', 'SAT', 'reception-definitive', 'Contrôle spécifique', 'Autre jalon']
    with factory() as db:
        pages = [planning.planning_items(db, project_id, 'milestones', offset=offset, limit=3)
                 for offset in (0, 3, 6, 9)]
        assert [row['title'] for page in pages for row in page['items']] == expected
        assert all(page['total'] == 10 and page['revision'] == 0 for page in pages)
        filtered = planning.planning_items(db, project_id, 'milestones', search='du', limit=3)
        assert [row['title'] for row in filtered['items']] == ['Lancement du projet', 'Validation du CDC']
        assert db.query(MilestonePlan).filter_by(project_id=project_id).count() == 1
        assert db.get(ProjectPlanningState, project_id) is None


@pytest.fixture
def api(store):
    from app.main import app
    from backend.app.db import get_db
    factory, ids, *_ = store
    Base.metadata.create_all(factory.kw['bind'], tables=[Deliverable.__table__, Meeting.__table__,
                                                       MeetingAction.__table__, MilestoneCandidate.__table__])

    def isolated_db():
        with factory() as db:
            yield db

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = isolated_db
    try:
        yield TestClient(app, base_url='http://127.0.0.1:8001'), ids
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous


def test_install_is_additive_backup_precedes_ddl_and_repeated_install_is_readonly(store):
    factory, ids, path, before, backup, installed = store
    assert len(installed['created_tables']) == 7 and len(installed['created_triggers']) == 6
    assert compare_baseline(before, capture_baseline(path))['preserved']
    assert capture_baseline(backup) == before
    with factory() as db:
        engine = db.get_bind()
        assert install_planning_schema(engine, backup=lambda: pytest.fail('Unexpected backup')) == {'created_tables': [], 'created_triggers': []}
        assert db.get(Project, ids['projects'][0]).hourly_rate == 97
        assert db.get(Project, ids['projects'][0]).margin_pct == 11


def test_project_dates_invalidate_planning_and_baseline_keeps_operational_commitments(store):
    from backend.app.project_identity_schemas import IdentityPatch
    from backend.app.services import project_identity as identity
    factory, ids, *_ = store
    project_id = ids['projects'][0]
    with transaction(factory) as db:
        db.get(Project, project_id).tdao_budget_h = 120
        db.flush()
        identity.patch_identity(db, project_id, IdentityPatch(expected_revision=0,
            start_date='2026-10-01', planned_end_date='2026-12-01'))
        assert planning.planning_info(db, project_id)['revision'] == 1
        baseline = planning.create_baseline(db, project_id, expected_revision=1, kind='contractual', label='Engagements')
        frozen = db.get(PlanningBaseline, baseline['id'])
        payload, sha = frozen.payload, frozen.sha256
        snapshot = json.loads(payload)
        assert snapshot['version'] == 2
        assert snapshot['project'] == {'start_date': '2026-10-01', 'planned_end_date': '2026-12-01', 'budget_hours': 120}
        assert 'hourly_rate' not in payload and 'margin_pct' not in payload
        identity.patch_identity(db, project_id, IdentityPatch(expected_revision=1, description='Texte uniquement'))
        assert planning.planning_info(db, project_id)['revision'] == 2
        identity.patch_identity(db, project_id, IdentityPatch(expected_revision=2, planned_end_date='2026-12-10'))
        assert planning.planning_info(db, project_id)['revision'] == 3
        event = db.query(PlanningChange).filter_by(action='project_changed', revision=3).one()
        assert event.previous['project']['planned_end_date'] == '2026-12-01'
        assert event.value['project']['planned_end_date'] == '2026-12-10'
        diff = planning.compare_baseline(db, project_id, baseline['id'])
        assert diff['project_comparison_available'] is True and diff['project_budget_hours_delta'] == 0
        assert diff['planned_hours_delta'] == 0
        assert diff['changes'] == [{'kind': 'project', 'id': project_id, 'title': 'Projet', 'field': 'planned_end_date',
                                   'severity': 'high', 'before': '2026-12-01', 'after': '2026-12-10'}]
        assert (db.get(PlanningBaseline, baseline['id']).payload, frozen.sha256) == (payload, sha)
    with pytest.raises(HTTPException) as error:
        with transaction(factory) as db:
            planning.create_baseline(db, project_id, expected_revision=2, kind='review', label='Vue périmée')
    assert error.value.status_code == 409


def test_invalid_stored_project_budget_refuses_capture_without_writes(store):
    factory, ids, path, *_ = store
    with transaction(factory) as db:
        db.get(Project, ids['projects'][0]).tdao_budget_h = -5
    before = capture_baseline(path)
    with pytest.raises(HTTPException) as error:
        with transaction(factory) as db:
            planning.create_baseline(db, ids['projects'][0], expected_revision=0, kind='initial', label='Invalide')
    assert error.value.status_code == 409 and capture_baseline(path) == before


def test_paged_task_labels_and_detail_resolve_relations_outside_the_page(api, store):
    client, ids = api
    patch_task(store, expected_revision=0, parent_task_id=ids['tasks'][0], milestone_id=ids['milestones'][0],
               responsible_id=ids['person'], planned_hours=6)
    root = f"/api/v1/projects/{ids['projects'][0]}/planning"
    before = capture_baseline(store[2])
    page = client.get(root + '/items/tasks', params={'search': 'Études', 'limit': 1}).json()
    assert page['total'] == 1 and len(page['items']) == 1
    row = page['items'][0]
    assert row['parent_title'] == 'Groupe' and row['milestone_title'] == 'FAT' and row['responsible_name'] == 'Alice Recette'
    detail = client.get(root + f"/items/tasks/{row['id']}").json()
    assert detail['revision'] == 1 and detail['children_total'] == 0
    assert detail['parent'] == {'id': ids['tasks'][0], 'title': 'Groupe'}
    assert detail['responsible']['id'] == ids['person']
    parent = client.get(root + f"/items/tasks/{ids['tasks'][0]}").json()
    assert parent['children_total'] == 1 and parent['item']['planned_hours'] == 6
    assert client.get(root + f"/items/milestones/{ids['milestones'][0]}").json()['item']['title'] == 'FAT'
    assert capture_baseline(store[2]) == before


def test_planning_item_routes_hide_other_projects_and_remain_readonly_for_reader(api, store, monkeypatch):
    client, ids = api
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', json.dumps([ids['projects'][0]]))
    root = f"/api/v1/projects/{ids['projects'][0]}/planning"
    before = capture_baseline(store[2])
    own = client.get(root + f"/items/tasks/{ids['tasks'][1]}")
    assert own.status_code == 200 and own.json()['can_edit'] is False
    assert client.get(root + f"/items/tasks/{ids['tasks'][3]}").status_code == 404
    assert client.get(root + f"/items/milestones/{ids['milestones'][1]}").status_code == 404
    assert client.get(f"/api/v1/projects/{ids['projects'][1]}/planning/items/tasks/{ids['tasks'][3]}").status_code == 404
    assert capture_baseline(store[2]) == before


def test_baseline_metadata_is_journaled_without_changing_snapshot(api, store):
    client, ids = api
    root = f"/api/v1/projects/{ids['projects'][0]}/planning"
    frozen = client.post(root + '/baselines', json={'expected_revision': 0, 'kind': 'contractual', 'label': 'Contrat initial'}).json()
    with store[0]() as db:
        row = db.get(PlanningBaseline, frozen['id'])
        before = (row.label, row.payload, row.sha256, row.planning_revision, row.actor_id, row.created_at)
    changed = client.patch(root + '/baselines/' + frozen['id'], json={
        'expected_revision': 1, 'label': 'Contrat revu', 'comment': 'Revue du contrat', 'active': False})
    assert changed.status_code == 200, changed.text
    assert client.get(root + '/baselines').json()['total'] == 0
    listed = client.get(root + '/baselines?include_inactive=true').json()
    assert listed['total'] == 1 and listed['items'][0]['comment'] == 'Revue du contrat'
    detail = client.get(root + '/baselines/' + frozen['id']).json()
    assert detail['revision'] == 2 and detail['baseline']['metadata_revision'] == 2
    assert detail['baseline']['capture_label'] == 'Contrat initial'
    assert client.get(root + '/baselines/' + frozen['id'] + '/compare').json()['changes'] == []
    snapshot = capture_baseline(store[2])
    assert client.patch(root + '/baselines/' + frozen['id'], json={'expected_revision': 1, 'active': True}).status_code == 409
    assert capture_baseline(store[2]) == snapshot
    assert client.patch(root + '/baselines/' + frozen['id'], json={'expected_revision': 2, 'active': True}).status_code == 200
    with store[0]() as db:
        row = db.get(PlanningBaseline, frozen['id'])
        assert (row.label, row.payload, row.sha256, row.planning_revision, row.actor_id, row.created_at) == before
        events = db.query(PlanningChange).filter_by(action='baseline_metadata_changed').order_by(PlanningChange.revision).all()
        assert len(events) == 2 and events[1].previous == events[0].value


def test_baseline_metadata_scope_reader_and_bad_inputs_leave_no_mutation(api, store, monkeypatch):
    client, ids = api
    root = f"/api/v1/projects/{ids['projects'][0]}/planning"
    frozen = client.post(root + '/baselines', json={'expected_revision': 0, 'kind': 'initial', 'label': 'Initial'}).json()
    before = capture_baseline(store[2])
    other = f"/api/v1/projects/{ids['projects'][1]}/planning/baselines/{frozen['id']}"
    assert client.get(other).status_code == 404
    assert client.patch(other, json={'expected_revision': 0, 'label': 'Étranger'}).status_code == 404
    for body in ({'label': '   '}, {'comment': None}, {'active': None}, {'sha256': 'a' * 64}, {'payload': '{}'}):
        assert client.patch(root + '/baselines/' + frozen['id'], json={'expected_revision': 1, **body}).status_code == 422
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    assert client.get(root + '/baselines/' + frozen['id']).json()['can_edit'] is False
    assert client.patch(root + '/baselines/' + frozen['id'], json={'expected_revision': 1, 'active': False}).status_code == 403
    assert capture_baseline(store[2]) == before


def test_read_is_neutral_and_does_not_create_metadata_or_infer_workflow(store):
    factory, ids, path, *_ = store
    before = capture_baseline(path)
    with factory() as db:
        out = planning.read_planning(db, ids['projects'][0])
        assert out['revision'] == 0 and out['active_template_version_id'] is None
        assert out['milestones'][0]['code'] is None
        assert out['milestones'][0]['workflow_status'] == 'pending'
        assert not db.query(ProjectPlanningState).count()
        assert not db.query(TaskPlan).count()
    assert capture_baseline(path) == before


def test_legacy_and_new_edits_share_revision_and_do_not_overwrite_a_stale_view(api, store):
    client, ids = api
    root = f"/api/v1/projects/{ids['projects'][0]}"
    task_id = ids['tasks'][1]
    assert client.get(root).json()['planning_revision'] == 0
    old = client.patch(root + f'/tasks/{task_id}', json={'due_date': '2026-10-09'})
    assert old.status_code == 200 and old.json()['revision'] == 1
    stale = client.patch(root + f'/planning/tasks/{task_id}',
                         json={'expected_revision': 0, 'title': 'Écrasement interdit'})
    assert stale.status_code == 409
    fresh = client.patch(root + f'/planning/tasks/{task_id}',
                         json={'expected_revision': 1, 'start_date': '2026-10-05', 'planned_hours': 8})
    assert fresh.status_code == 200 and fresh.json()['revision'] == 2
    assert client.patch(root + f'/tasks/{task_id}', json={'expected_revision': 1, 'title': 'Périmé'}).status_code == 409
    with store[0]() as db:
        assert db.get(Task, task_id).title == 'Études'
        assert db.get(TaskPlan, task_id).end_date == '2026-10-09'
        assert db.query(PlanningChange).filter_by(project_id=ids['projects'][0]).count() == 2


def test_full_task_creation_is_atomic_and_supports_assigned_and_blocked_statuses(api, store):
    client, ids = api
    root = f"/api/v1/projects/{ids['projects'][0]}"
    out = client.post(root + '/planning/tasks', json={
        'expected_revision': 0, 'title': 'Tâche affectée', 'status': 'assigned',
        'parent_task_id': ids['tasks'][0], 'milestone_id': ids['milestones'][0],
        'responsible_id': ids['person'], 'planned_hours': 6, 'start_date': '2026-10-02',
        'end_date': '2026-10-08', 'priority': 'urgent', 'design': True})
    assert out.status_code == 201, out.text
    row = out.json()
    assert row['revision'] == 1 and row['task']['status'] == 'assigned'
    with store[0]() as db:
        assert db.get(TaskPlan, ids['tasks'][0]).planned_hours == 6
        assert db.query(PlanningChange).count() == 1
    blocked = client.patch(root + f"/tasks/{row['task']['id']}", json={'expected_revision': 1, 'status': 'blocked'})
    assert blocked.status_code == 200 and blocked.json()['revision'] == 2
    assert 'blocked' in client.get(root + '/planning/state').json()['task_statuses']


def test_invalid_new_task_relation_or_assignment_leaves_no_task_or_revision(api, store):
    client, ids = api
    before = capture_baseline(store[2])
    root = f"/api/v1/projects/{ids['projects'][0]}/planning/tasks"
    for values in ({'status': 'assigned'}, {'parent_task_id': ids['tasks'][3]}, {'milestone_id': ids['milestones'][1]}):
        out = client.post(root, json={'expected_revision': 0, 'title': 'Commande refusée', **values})
        assert out.status_code == 422
        assert capture_baseline(store[2]) == before


def test_legacy_due_date_cannot_bypass_parent_aggregation_and_failed_command_rolls_back(api, store):
    client, ids = api
    root = f"/api/v1/projects/{ids['projects'][0]}"
    child, parent = ids['tasks'][1], ids['tasks'][0]
    changed = client.patch(root + f'/planning/tasks/{child}', json={
        'expected_revision': 0, 'parent_task_id': parent, 'end_date': '2026-10-07', 'planned_hours': 6})
    assert changed.status_code == 200
    assert client.patch(root + f'/tasks/{parent}', json={'due_date': '2026-12-01'}).status_code == 422
    assert client.get(root + '/planning/state').json()['revision'] == 1
    with store[0]() as db:
        assert db.get(Task, parent).due_date == '2026-10-07'
        assert db.get(TaskPlan, parent).planned_hours == 6


def test_paged_lists_literal_search_archives_and_full_baselines(api):
    client, ids = api
    root = f"/api/v1/projects/{ids['projects'][0]}"
    task = ids['tasks'][1]
    out = client.get(root + '/planning/items/tasks', params={'limit': 1}).json()
    assert out['total'] == 3 and len(out['items']) == 1
    assert client.get(root + '/planning/items/tasks', params={'search': '%'}).json()['total'] == 0
    assert client.get(root + '/planning/items/tasks', params={'limit': 201}).status_code == 422
    assert client.patch(root + f'/planning/tasks/{task}', json={'expected_revision': 0, 'active': False}).status_code == 200
    assert client.get(root + '/planning/items/tasks').json()['total'] == 2
    assert client.get(root + '/planning/items/tasks', params={'include_inactive': True}).json()['total'] == 3
    frozen = client.post(root + '/planning/baselines', json={
        'expected_revision': 1, 'kind': 'initial', 'label': 'Référence complète'}).json()
    detail = client.get(root).json()
    assert detail['planning_revision'] == 2 and len(detail['tasks']) == 3
    assert client.patch(root + f'/tasks/{task}', json={'title': 'Titre modifié'}).status_code == 200
    delta = client.get(root + f"/planning/baselines/{frozen['id']}/compare").json()
    assert any(change['id'] == task and change['field'] == 'title' for change in delta['changes'])
    assert client.get(root + '/planning/baselines').json()['total'] == 1
    history = client.get(root + '/planning/history', params={'limit': 1}).json()
    assert history['total'] == 3 and len(history['items']) == 1 and 'value' not in history['items'][0]
    record = client.get(root + '/planning/history/' + history['items'][0]['id']).json()
    assert 'tasks' in record['value']


def test_scoped_reader_and_editor_cannot_read_or_write_foreign_planning(api, monkeypatch):
    client, ids = api
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', json.dumps([ids['projects'][0]]))
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    root = f"/api/v1/projects/{ids['projects'][0]}/planning"
    assert client.get(root + '/state').json()['can_edit'] is False
    assert client.patch(root + f"/tasks/{ids['tasks'][1]}", json={'expected_revision': 0, 'title': 'Non'}).status_code == 403
    foreign = f"/api/v1/projects/{ids['projects'][1]}/planning"
    for suffix in ('/state', '/items/tasks', '/items/milestones', '/baselines', '/history'):
        assert client.get(foreign + suffix).status_code == 404
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'editor')
    assert client.patch(root + f"/tasks/{ids['tasks'][3]}", json={'expected_revision': 0, 'title': 'Autre'}).status_code == 404
    assert client.get(root + '/state').json()['revision'] == 0


def test_candidate_acceptance_shares_revision_and_trusted_actor_preserving_date_conflicts(api, store, monkeypatch):
    client, ids = api
    factory = store[0]
    project_id, milestone_id = ids['projects'][0], ids['milestones'][0]
    with transaction(factory) as db:
        row = MilestoneCandidate(project_id=project_id, title='FAT', date_type='forecast_date',
                                 value='2026-10-12', quote='FAT prévue le 12/10/2026', evidence={},
                                 fingerprint='revision-test')
        db.add(row)
        db.flush()
        candidate_id = row.id
    monkeypatch.setattr('backend.app.services.milestones.evidence_current', lambda *args: True)
    monkeypatch.setenv('AGENT_OPERATOR_ID', 'pilote-recette')
    root = f'/api/v1/projects/{project_id}'
    legacy = client.patch(root + f'/milestones/{milestone_id}', json={'forecast_date': '2026-10-08'})
    assert legacy.json()['revision'] == 1
    url = root + f'/milestones/candidates/{candidate_id}/decision'
    assert client.post(url, json={'decision': 'accept', 'expected_revision': 0,
                                  'expected_value': '2026-10-08'}).status_code == 409
    assert client.post(url, json={'decision': 'accept', 'expected_revision': 1,
                                  'expected_value': '2026-10-06'}).status_code == 409
    with factory() as db:
        assert db.get(MilestoneCandidate, candidate_id).status == 'pending'
        assert db.get(ProjectPlanningState, project_id).revision == 1
    out = client.post(url, json={'decision': 'accept', 'expected_revision': 1,
                                  'expected_value': '2026-10-08'}).json()
    assert out['revision'] == 2 and out['forecast_date'] == '2026-10-12'
    with factory() as db:
        assert db.get(Milestone, milestone_id).date_sources['forecast_date']['actor'] == 'pilote-recette'
        assert db.query(PlanningChange).filter_by(project_id=project_id, actor_id='pilote-recette').count() == 2


def test_meeting_action_conversion_invalidates_old_planning_and_cannot_duplicate(api):
    client, ids = api
    root = f"/api/v1/projects/{ids['projects'][0]}"
    meeting = client.post(root + '/meetings', json={'title': 'Revue'}).json()
    action = client.post(root + f"/meetings/{meeting['id']}/actions", json={'title': 'Contrôler le dossier'}).json()
    url = root + f"/meetings/{meeting['id']}/actions/{action['id']}/to-task"
    assert client.post(url, params={'expected_revision': 0}).json()['revision'] == 1
    assert client.post(url).status_code == 409
    assert client.get(root + '/planning/state').json()['revision'] == 1
    assert client.post(root + '/tasks', json={'title': 'Préparée avant réunion', 'expected_revision': 0}).status_code == 409


def test_parent_load_limit_rejects_overflow_without_partial_update(store):
    factory, ids, path, *_ = store
    parent = ids['tasks'][0]
    patch_task(store, expected_revision=0, parent_task_id=parent, planned_hours=600000)
    before = capture_baseline(path)
    with pytest.raises(HTTPException) as error:
        patch_task(store, index=2, expected_revision=1, parent_task_id=parent, planned_hours=600000)
    assert error.value.status_code == 422
    assert capture_baseline(path) == before


def test_legacy_and_new_concurrent_commands_on_same_revision_have_one_winner(store):
    factory, ids, *_ = store

    def run(legacy):
        try:
            with transaction(factory) as db:
                if legacy:
                    planning.patch_legacy_task(db, ids['projects'][0], ids['tasks'][1],
                                               {'title': 'Ancien écran'}, expected_revision=0)
                else:
                    planning.patch_task(db, ids['projects'][0], ids['tasks'][1],
                                         TaskPlanningPatch(expected_revision=0, title='Nouvel écran'))
            return 200
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(run, [True, False])) == [200, 409]
    with factory() as db:
        assert db.get(ProjectPlanningState, ids['projects'][0]).revision == 1
        assert db.query(PlanningChange).count() == 1


def test_task_responsible_remains_visible_through_scoped_history_and_baselines(api, store, monkeypatch):
    client, ids = api
    root = f"/api/v1/projects/{ids['projects'][0]}"
    task = ids['tasks'][1]
    assert client.patch(root + f'/planning/tasks/{task}', json={
        'expected_revision': 0, 'responsible_id': ids['person']}).status_code == 200
    assert client.post(root + '/planning/baselines', json={
        'expected_revision': 1, 'kind': 'review', 'label': 'Responsable initial'}).status_code == 201
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', json.dumps([ids['projects'][0]]))
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'editor')
    assert client.patch(root + f'/planning/tasks/{task}', json={'expected_revision': 2, 'comment': 'Toujours visible'}).status_code == 200
    assert client.patch(root + f'/planning/tasks/{task}', json={'expected_revision': 3, 'responsible_id': None}).status_code == 200
    assert [row['id'] for row in client.get('/api/v1/project-people').json()['items']] == [ids['person']]
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', json.dumps([ids['projects'][1]]))
    assert client.get('/api/v1/project-people').json()['total'] == 0


def test_milestone_state_is_independent_of_actual_date_and_actor_is_trusted(store):
    factory, ids, *_ = store
    with operator_context(Operator('test-caf', 'editor')):
        with transaction(factory) as db:
            out = planning.patch_milestone(db, ids['projects'][0], ids['milestones'][0],
                MilestonePlanningPatch(expected_revision=0, code='fat', workflow_status='validated'))
            assert out['revision'] == 1
            assert out['milestone']['actual_date'] == ''
            assert out['milestone']['workflow_status'] == 'validated'
        with factory() as db:
            assert db.query(PlanningChange).one().actor_id == 'test-caf'
    with transaction(factory) as db:
        baseline = planning.create_baseline(db, ids['projects'][0], expected_revision=1, kind='contractual', label='Contrat')
        saved = json.loads(db.get(PlanningBaseline, baseline['id']).payload)
        assert saved['milestones'][0]['workflow_status'] == 'validated'


def test_stale_commands_do_not_overwrite_dates_or_consume_revision(store):
    factory, ids, *_ = store
    with transaction(factory) as db:
        planning.patch_milestone(db, ids['projects'][0], ids['milestones'][0], MilestonePlanningPatch(expected_revision=0, forecast_date='2026-10-07'))
    with pytest.raises(HTTPException) as error:
        with transaction(factory) as db:
            planning.patch_milestone(db, ids['projects'][0], ids['milestones'][0], MilestonePlanningPatch(expected_revision=0, actual_date='2026-10-03'))
    assert error.value.status_code == 409
    with factory() as db:
        out = planning.read_planning(db, ids['projects'][0])
        assert out['revision'] == 1 and out['milestones'][0]['forecast_date'] == '2026-10-07'
        assert out['milestones'][0]['actual_date'] == ''


def test_concurrent_commands_with_same_revision_have_one_winner(store):
    factory, ids, *_ = store
    def command(title):
        try:
            with transaction(factory) as db:
                planning.patch_task(db, ids['projects'][0], ids['tasks'][1], TaskPlanningPatch(expected_revision=0, title=title))
            return 200
        except HTTPException as exc:
            return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(command, ['Version A', 'Version B'])) == [200, 409]
    with factory() as db:
        assert db.get(ProjectPlanningState, ids['projects'][0]).revision == 1


def test_scopes_reader_and_foreign_objects_are_checked_before_writes(store):
    factory, ids, path, *_ = store
    before = capture_baseline(path)
    with operator_context(Operator('reader', 'reader')):
        with pytest.raises(HTTPException) as error:
            patch_task(store, expected_revision=0, title='Interdit')
        assert error.value.status_code == 403
    with operator_context(Operator('scoped', 'editor', frozenset([ids['projects'][1]]))):
        with pytest.raises(HTTPException) as error:
            with factory() as db:
                planning.read_planning(db, ids['projects'][0])
        assert error.value.status_code == 404
    with operator_context(Operator('scoped', 'editor', frozenset([ids['projects'][0]]))):
        with pytest.raises(HTTPException) as error:
            patch_task(store, expected_revision=0, responsible_id=ids['person'])
        assert error.value.status_code == 404
    with pytest.raises(HTTPException) as error:
        patch_task(store, index=3, expected_revision=0, title='Étranger')
    assert error.value.status_code == 404
    assert capture_baseline(path) == before


@pytest.mark.parametrize('field', ['parent_task_id', 'milestone_id'])
def test_foreign_task_relations_rejected_without_state_write(store, field):
    factory, ids, path, *_ = store
    before = capture_baseline(path)
    foreign = ids['tasks'][3] if field == 'parent_task_id' else ids['milestones'][1]
    with pytest.raises(HTTPException) as error:
        patch_task(store, expected_revision=0, **{field: foreign})
    assert error.value.status_code == 422
    assert capture_baseline(path) == before


def test_hierarchy_aggregate_cycle_parent_manual_edit_and_archive_rules(store):
    factory, ids, *_ = store
    parent = ids['tasks'][0]
    patch_task(store, expected_revision=0, parent_task_id=parent, planned_hours=8, start_date='2026-10-02', end_date='2026-10-05')
    patch_task(store, index=2, expected_revision=1, parent_task_id=parent, planned_hours=4, start_date='2026-10-03', end_date='2026-10-06')
    with factory() as db:
        group = db.get(TaskPlan, parent)
        assert (group.planned_hours, group.start_date, group.end_date) == (12, '2026-10-02', '2026-10-06')
    for values in ({'parent_task_id': ids['tasks'][1]}, {'planned_hours': 99}, {'active': False}):
        with pytest.raises(HTTPException) as error:
            patch_task(store, index=0, expected_revision=2, **values)
        assert error.value.status_code == 422
    with transaction(factory) as db:
        baseline = planning.create_baseline(db, ids['projects'][0], expected_revision=2, kind='initial', label='Avant archivage')
    patch_task(store, index=2, expected_revision=3, active=False)
    with factory() as db:
        assert db.get(TaskPlan, parent).planned_hours == 8
        assert db.get(TaskPlan, ids['tasks'][2]).planned_hours == 4
        assert not db.get(TaskPlan, ids['tasks'][2]).active
        assert planning.compare_baseline(db, ids['projects'][0], baseline['id'])['planned_hours_delta'] == -4


def test_existing_parent_values_are_not_silently_replaced_by_first_child(store):
    factory, ids, path, *_ = store
    patch_task(store, index=0, expected_revision=0, planned_hours=40, end_date='2026-11-01')
    before = capture_baseline(path)
    with pytest.raises(HTTPException) as error:
        patch_task(store, expected_revision=1, parent_task_id=ids['tasks'][0])
    assert error.value.status_code == 422
    assert capture_baseline(path) == before


def test_dates_responsible_and_unique_codes_have_explicit_errors(store):
    factory, ids, *_ = store
    patch_task(store, expected_revision=0, start_date='2026-10-05', responsible_id=ids['person'])
    with pytest.raises(HTTPException) as error:
        patch_task(store, expected_revision=1, end_date='2026-10-02')
    assert error.value.status_code == 422
    with transaction(factory) as db:
        extra = Milestone(project_id=ids['projects'][0], title='Livraison')
        db.add(extra)
        db.flush()
        extra_id = extra.id
        planning.patch_milestone(db, ids['projects'][0], ids['milestones'][0], MilestonePlanningPatch(expected_revision=1, code='fat'))
    with pytest.raises(HTTPException) as error:
        with transaction(factory) as db:
            planning.patch_milestone(db, ids['projects'][0], extra_id, MilestonePlanningPatch(expected_revision=2, code='fat'))
    assert error.value.status_code == 409


def test_baseline_survives_later_changes_and_foreign_access_is_refused(store):
    factory, ids, *_ = store
    with transaction(factory) as db:
        baseline = planning.create_baseline(db, ids['projects'][0], expected_revision=0, kind='initial', label='Avant modification')
        saved = db.get(PlanningBaseline, baseline['id']).payload
    with transaction(factory) as db:
        planning.patch_milestone(db, ids['projects'][0], ids['milestones'][0], MilestonePlanningPatch(expected_revision=1, actual_date='2026-10-04'))
    with factory() as db:
        diff = planning.compare_baseline(db, ids['projects'][0], baseline['id'])
        assert any(value['field'] == 'actual_date' for value in diff['changes'])
        assert db.get(PlanningBaseline, baseline['id']).payload == saved
        with pytest.raises(HTTPException) as error:
            planning.compare_baseline(db, ids['projects'][1], baseline['id'])
        assert error.value.status_code == 404


def test_database_protects_published_versions_baselines_and_audit_from_update_delete(store):
    factory, ids, *_ = store
    with transaction(factory) as db:
        template = PlanningTemplate(code='standard', normalized_code='standard', name='Standard')
        db.add(template)
        db.flush()
        db.add(PlanningTemplateVersion(template_id=template.id, number=1, definition='{}', sha256='a' * 64, actor_id='test'))
        planning.create_baseline(db, ids['projects'][0], expected_revision=0, kind='review', label='Revue')
    for table in IMMUTABLE_TABLES:
        for operation in ('UPDATE', 'DELETE'):
            with factory() as db:
                sql = f'UPDATE {table} SET actor_id=actor_id' if operation == 'UPDATE' else f'DELETE FROM {table}'
                with pytest.raises(IntegrityError, match='immutable'):
                    db.execute(text(sql))
                db.rollback()


def test_migration_rejects_incompatible_existing_trigger_before_any_write(store):
    factory, ids, path, *_ = store
    with factory() as db:
        name = 'trg_project_planning_baselines_update_immutable'
        db.execute(text(f'DROP TRIGGER {name}'))
        db.execute(text(f'CREATE TRIGGER {name} BEFORE UPDATE ON project_planning_baselines BEGIN SELECT 1; END'))
        db.commit()
        before = capture_baseline(path)
        with pytest.raises(ValueError, match='Protection'):
            install_planning_schema(db.get_bind(), backup=lambda: pytest.fail('Must validate before backup'))
    assert capture_baseline(path) == before


def test_backup_failure_prevents_schema_and_trigger_creation(tmp_path):
    path = tmp_path / 'existing.db'
    engine = create_engine(f'sqlite:///{path}')
    Base.metadata.create_all(engine, tables=[Project.__table__, Task.__table__, Milestone.__table__, *IDENTITY_TABLES])
    before = capture_baseline(path)
    def failing_backup():
        raise OSError('Backup unavailable')
    with pytest.raises(OSError):
        install_planning_schema(engine, backup=failing_backup)
    assert capture_baseline(path) == before
    engine.dispose()
