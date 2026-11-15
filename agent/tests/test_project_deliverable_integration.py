"""Inherited commands, milestone gates and explicit schema/API integration."""
from copy import deepcopy

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, text

from app.db_support import backup_sqlite, configure_sqlite
from app.security import local_guard
from backend.app.db import Base, get_db
from backend.app.models import Deliverable, Milestone
from backend.app.project_deliverable_models import DELIVERABLE_TABLES, DeliverableEvent, DeliverablePlan
from backend.app.project_deliverable_schemas import ChecklistCreate, ChecklistPatch, DeliverableCreate
from backend.app.project_planning_models import MilestonePlan, PlanningChange
from backend.app.project_planning_schemas import MilestonePlanningPatch
from backend.app.routers import project_deliverables as http, project_planning as planning_http, projects as legacy
from backend.app.services import project_archive as archive, project_deliverables as commands, project_planning as planning
from backend.app.services.deliverable_gates import milestone_gates
from backend.app.services.deliverable_queries import detail
from backend.app.services.migration_guard import capture_baseline, compare_baseline
from backend.app.services.planning_revision import revision
from backend.app.services.project_operator import Operator, operator_context
from backend.app.services.project_planning_migration import install_planning_schema
from tests.test_project_deliverables import create, publish, store as base_store, transaction

store = base_store


@pytest.fixture
def api(store):
    factory, ids, path, *_ = store
    install_planning_schema(factory.kw['bind'], backup=lambda: backup_sqlite(path, path.with_suffix('.l2-backup.db')))
    app = FastAPI()
    app.middleware('http')(local_guard)
    for router in (legacy.router, http.router, http.catalog_router, http.typology_router, planning_http.router):
        app.include_router(router)

    def isolated_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = isolated_db
    return TestClient(app, base_url='http://127.0.0.1:8001'), ids, '/api/v1/projects/' + ids['project']


def test_legacy_create_patch_preserve_shape_and_share_cas_without_inventing_visa(api, store):
    client, ids, root = api
    factory, _, path, *_ = store
    response = client.post(root + '/deliverables', json={'title': 'Livrable historique', 'status': 'done'})
    assert response.status_code == 201, response.text
    owner = response.json()['id']
    assert response.json()['status'] == 'done' and response.json()['revision'] == 1
    view = client.get(f'{root}/deliverable-plan/{owner}').json()
    assert view['legacy_status'] == 'done' and view['document_status'] == 'draft' and not view['checklist']
    before = capture_baseline(path)
    bad = client.patch(f'{root}/deliverables/{owner}', json={'title': 'Périmé', 'expected_revision': 0})
    assert bad.status_code == 409 and capture_baseline(path) == before
    patch = client.patch(f'{root}/deliverables/{owner}', json={'title': 'Renommé', 'status': 'in_progress', 'expected_revision': 1})
    assert patch.status_code == 200 and patch.json()['revision'] == 2
    assert client.patch(f'{root}/deliverables/{owner}', json={'status': 'done'}).json()['revision'] == 3
    with factory() as db:
        assert db.query(PlanningChange).filter_by(project_id=ids['project']).count() == 3
        assert db.query(DeliverableEvent).filter_by(deliverable_id=owner).count() == 3
        assert db.get(DeliverablePlan, owner).document_status == 'draft'


def test_legacy_edit_of_existing_done_is_recorded_without_changing_identity_or_other_cells(api, store):
    client, ids, root = api
    factory, _, path, *_ = store
    before = capture_baseline(path)
    response = client.patch(f"{root}/deliverables/{ids['legacy']}", json={'status': 'todo'})
    assert response.status_code == 200 and response.json()['id'] == ids['legacy']
    with factory() as db:
        assert db.get(Deliverable, ids['legacy']).title == 'Historique conservé'
        assert db.get(DeliverablePlan, ids['legacy']).document_status == 'draft'
        event = db.query(DeliverableEvent).one()
        assert event.previous['legacy_status'] == 'done' and event.value['legacy_status'] == 'todo'
    after = capture_baseline(path)
    # One explicit inherited cell changes; other baseline rows/cells are preserved.
    key = next(iter(before['tables']['deliverables']['rows']))
    before['tables']['deliverables']['rows'][key]['status'] = after['tables']['deliverables']['rows'][key]['status']
    assert compare_baseline(before, after)['preserved']


def test_internal_legacy_commands_enforce_reader_scope_and_stale_revision(api, store):
    _, ids, _ = api
    factory, *_ = store
    for actor in (Operator('reader', 'reader'), Operator('limited', 'editor', frozenset({ids['foreign']}))):
        with operator_context(actor), factory() as db, pytest.raises(HTTPException) as error:
            commands.create_legacy_deliverable(db, ids['project'], title='Interdit')
        assert error.value.status_code in {403, 404}
    with factory() as db, pytest.raises(HTTPException) as error:
        commands.patch_legacy_deliverable(db, ids['project'], ids['legacy'], {'status': 'done'}, expected_revision=99)
    assert error.value.status_code == 409


@pytest.mark.parametrize('endpoint', ['planning', 'legacy', 'internal'])
def test_gate_blocks_validation_before_successor_opening_and_dates_or_revision_change(api, store, endpoint):
    client, ids, root = api
    factory, _, path, *_ = store
    owner, gate = create(store)
    with transaction(factory) as db:
        future = Milestone(project_id=ids['project'], title='CDR')
        db.add(future)
        db.flush()
        db.add_all([MilestonePlan(project_id=ids['project'], milestone_id=ids['milestone'], code='pdr', position=1, workflow_status='open'),
                    MilestonePlan(project_id=ids['project'], milestone_id=future.id, code='cdr', position=2)])
        next_id = future.id
    before = capture_baseline(path)
    payload = {'expected_revision': 2, 'workflow_status': 'validated', 'actual_date': '2026-10-06'}
    if endpoint == 'internal':
        with factory() as db, pytest.raises(HTTPException) as error:
            planning.patch_legacy_milestone(db, ids['project'], ids['milestone'],
                {key: value for key, value in payload.items() if key != 'expected_revision'}, expected_revision=2)
        assert error.value.status_code == 409
    else:
        prefix = '/planning' if endpoint == 'planning' else ''
        response = client.patch(f"{root}{prefix}/milestones/{ids['milestone']}", json=payload)
        assert response.status_code == 409, response.text
        assert response.json()['detail']['blocking_checks'][0]['id'] == gate
    assert capture_baseline(path) == before
    with factory() as db:
        assert db.get(MilestonePlan, next_id).workflow_status == 'pending'
        assert db.get(Milestone, ids['milestone']).actual_date == ''
    ready = client.get(f"{root}/deliverable-plan/milestones/{ids['milestone']}/gates").json()
    assert not ready['can_validate'] and ready['blocking_checks'][0]['deliverable_id'] == owner


def test_actual_date_keeps_its_independent_meaning_and_does_not_validate_workflow(api, store):
    client, ids, root = api
    factory, *_ = store
    create(store)
    response = client.patch(f"{root}/milestones/{ids['milestone']}", json={'expected_revision': 2, 'actual_date': '2026-10-06'})
    assert response.status_code == 200, response.text
    with factory() as db:
        assert db.get(Milestone, ids['milestone']).actual_date == '2026-10-06'
        assert db.get(MilestonePlan, ids['milestone']).workflow_status == 'pending'


def test_visas_apply_to_the_target_milestone_without_future_gate_or_document_status_inference(api, store):
    client, ids, root = api
    factory, *_ = store
    with transaction(factory) as db:
        future = Milestone(project_id=ids['project'], title='CDR')
        db.add(future)
        db.flush()
        next_id = future.id
        db.add_all([MilestonePlan(project_id=ids['project'], milestone_id=ids['milestone'], code='pdr', position=1, workflow_status='open'),
                    MilestonePlan(project_id=ids['project'], milestone_id=next_id, code='cdr', position=2)])
        owner = commands.create_deliverable(db, ids['project'], DeliverableCreate(expected_revision=0, title='Multi étapes',
            verifier_id=ids['person'], milestone_ids=[ids['milestone'], next_id]))['id']
        gate = commands.create_check(db, ids['project'], owner, ChecklistCreate(expected_revision=1, code='pdr_visa', label='PDR',
            is_gate=True, milestone_id=ids['milestone']))['item']['id']
        commands.create_check(db, ids['project'], owner, ChecklistCreate(expected_revision=2, code='cdr_visa', label='CDR',
            is_gate=True, milestone_id=next_id))
    published = publish(store, owner)
    with transaction(factory) as db:
        commands.patch_check(db, ids['project'], owner, gate, ChecklistPatch(expected_revision=published['revision'],
            completed=True, proof='PDR relue sur ces octets'))
        assert detail(db, ids['project'], owner)['document_status'] == 'draft'
        assert milestone_gates(db, ids['project'], ids['milestone'])['can_validate']
        assert not milestone_gates(db, ids['project'], next_id)['can_validate']
        rev = revision(db, ids['project'])
    response = client.patch(f"{root}/planning/milestones/{ids['milestone']}", json={'expected_revision': rev, 'workflow_status': 'validated'})
    assert response.status_code == 200, response.text
    assert response.json()['opened_milestone_id'] == next_id
    with factory() as db:
        assert db.get(MilestonePlan, next_id).workflow_status == 'open'
        assert db.get(Milestone, ids['milestone']).actual_date == ''


def test_old_visa_and_changed_file_cannot_validate_even_an_already_validated_workflow(api, store):
    client, ids, root = api
    factory, _, path, *_ = store
    owner, gate = create(store)
    first = publish(store, owner)
    with transaction(factory) as db:
        commands.patch_check(db, ids['project'], owner, gate, ChecklistPatch(expected_revision=first['revision'], completed=True, proof='Relu'))
        result = planning.patch_milestone(db, ids['project'], ids['milestone'], MilestonePlanningPatch(
            expected_revision=revision(db, ids['project']), workflow_status='validated'))
        assert result['milestone']['workflow_status'] == 'validated'
    second = publish(store, owner, name='new-version.md')
    before = capture_baseline(path)
    response = client.patch(f"{root}/planning/milestones/{ids['milestone']}", json={'expected_revision': second['revision'], 'workflow_status': 'validated'})
    assert response.status_code == 409 and capture_baseline(path) == before
    with transaction(factory) as db:
        commands.patch_check(db, ids['project'], owner, gate, ChecklistPatch(expected_revision=revision(db, ids['project']), completed=True, proof='Nouvelle version relue'))
        rev = revision(db, ids['project'])
    (path.parent / 'new-version.md').write_text('Modification en place', encoding='utf-8')
    assert client.patch(f"{root}/milestones/{ids['milestone']}", json={'expected_revision': rev, 'workflow_status': 'validated'}).status_code == 409


def test_legacy_status_history_survives_selective_transport_and_tampering_refuses(api, store, tmp_path, monkeypatch):
    client, ids, root = api
    factory, *_ = store
    import app.db
    from sqlalchemy.orm import sessionmaker
    brain = create_engine(f'sqlite:///{tmp_path / "brain-empty.db"}')
    monkeypatch.setattr(app.db, 'SessionLocal', sessionmaker(bind=brain))
    owner = client.post(root + '/deliverables', json={'title': 'Historique', 'status': 'done'}).json()['id']
    client.patch(f'{root}/deliverables/{owner}', json={'status': 'in_progress'})
    with factory() as db:
        data = archive.export_archive(db, ids['project'])
    assert data['version'] == 5
    with transaction(factory) as db:
        result = archive.import_archive(db, data, code='LEGACY-ROUNDTRIP')
    with factory() as db:
        imported = db.query(Deliverable).filter_by(project_id=result['id'], title='Historique').one()
        assert imported.status == 'in_progress' and db.get(DeliverablePlan, imported.id).document_status == 'draft'
        events = db.query(DeliverableEvent).filter_by(deliverable_id=imported.id).order_by(DeliverableEvent.revision).all()
        assert events[0].value['legacy_status'] == 'done' and events[1].previous['legacy_status'] == 'done'
    bad = deepcopy(data)
    next(row for row in bad['tables']['deliverables'] if row['id'] == owner)['status'] = 'cancelled'
    before = capture_baseline(store[2])
    with factory() as db, pytest.raises(HTTPException) as error:
        archive.import_archive(db, bad, code='BAD-LEGACY-STATUS')
    assert error.value.status_code == 400 and capture_baseline(store[2]) == before
    brain.dispose()


def test_startup_l3_backup_failure_prevents_ddl_and_preserves_entire_baseline(tmp_path, monkeypatch):
    from backend.app import db as erp
    engine = create_engine(f'sqlite:///{tmp_path / "legacy.db"}')
    configure_sqlite(engine)
    Base.metadata.create_all(engine, tables=[table for table in Base.metadata.sorted_tables if table not in DELIVERABLE_TABLES])
    install_planning_schema(engine, backup=lambda: None)
    monkeypatch.setattr(erp, 'engine', engine)
    before = capture_baseline(tmp_path / 'legacy.db')
    monkeypatch.setattr(erp, '_backup', lambda: (_ for _ in ()).throw(RuntimeError('backup unavailable')))
    with pytest.raises(RuntimeError, match='backup unavailable'):
        erp.init_db()
    assert capture_baseline(tmp_path / 'legacy.db') == before
    with engine.connect() as db:
        assert not db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'project_deliverable_%'")).all()
    engine.dispose()


def test_startup_invalid_dormant_l3_schema_refuses_before_other_ddl_or_backup(tmp_path, monkeypatch):
    from backend.app import db as erp
    engine = create_engine(f'sqlite:///{tmp_path / "partial.db"}')
    with engine.begin() as db:
        db.exec_driver_sql('CREATE TABLE project_deliverable_types (id TEXT PRIMARY KEY, code TEXT)')
    monkeypatch.setattr(erp, 'engine', engine)
    monkeypatch.setattr(erp, '_backup', lambda: pytest.fail('Invalid schema must be rejected before any DDL'))
    before = capture_baseline(tmp_path / 'partial.db')
    with pytest.raises(ValueError, match='Schéma de livrables incompatible'):
        erp.init_db()
    assert capture_baseline(tmp_path / 'partial.db') == before
    engine.dispose()


def test_registered_agent_routes_and_inherited_commands_share_one_revision_and_scope(api, store):
    from app.main import app
    factory, ids, *_ = store

    def isolated_db():
        with factory() as db:
            yield db

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = isolated_db
    try:
        client = TestClient(app, base_url='http://127.0.0.1:8001')
        root = '/api/v1/projects/' + ids['project']
        created = client.post(root + '/deliverables', json={'title': 'Ancien client', 'status': 'done'})
        assert created.status_code == 201, created.text
        owner = created.json()['id']
        assert client.get(f'{root}/deliverable-plan/{owner}').json()['revision'] == 1
        assert client.patch(f'{root}/deliverable-plan/{owner}', json={'expected_revision': 1, 'comment': 'Nouveau client'}).status_code == 200
        assert client.patch(f'{root}/deliverables/{owner}', json={'expected_revision': 1, 'title': 'Périmé'}).status_code == 409
        assert client.get(root + '/planning/state').json()['revision'] == 2
        assert client.get('/api/v1/deliverable-types/standard-definition').status_code == 200
        with operator_context(Operator('limited', 'reader', frozenset({ids['foreign']}))):
            assert client.get(root + '/deliverable-plan').status_code == 404
        with operator_context(Operator('reader', 'reader', frozenset({ids['project']}))):
            assert client.get(root + '/deliverable-plan').status_code == 200
            assert client.post(root + '/deliverables', json={'title': 'Interdit'}).status_code == 403
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
