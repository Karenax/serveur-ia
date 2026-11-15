"""Real Agent registration and guarded L4 startup on fictional stores only."""
from copy import deepcopy
import hashlib

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.db_support import configure_sqlite
from backend.app import db as erp
from backend.app.models import Milestone, Project, Task
from backend.app.project_review_models import REVIEW_TABLES, ProjectReview
from backend.app.services.migration_guard import capture_baseline, compare_baseline
from backend.app.services.project_identity_migration import install_identity_schema
from backend.app.services.project_planning_migration import install_planning_schema
from backend.app.services.project_deliverable_migration import install_deliverable_schema
from backend.app.services.project_review_migration import validate_review_schema
from backend.app.services.project_operator import Operator, operator_context
from tests import test_project_reviews as reviews
from tests import test_project_review_archive as archive_fixtures
from tests.test_project_review_archive_contract import old_schema

store = reviews.store
audio = archive_fixtures.audio
envelope = archive_fixtures.envelope
l3_store = archive_fixtures.l3_store
typed_document = archive_fixtures.typed_document
transport = archive_fixtures.transport


def use_engine(monkeypatch, engine, path):
    monkeypatch.setattr(erp, 'engine', engine)
    monkeypatch.setattr(erp, 'DB_PATH', path)
    monkeypatch.setattr(erp, 'APP_DIR', path.parent)


@pytest.fixture
def legacy(tmp_path, monkeypatch):
    path = tmp_path / 'legacy.db'
    engine = create_engine(f'sqlite:///{path}')
    configure_sqlite(engine)
    erp.Base.metadata.create_all(engine, tables=[table for table in erp.Base.metadata.sorted_tables if table not in REVIEW_TABLES])
    install_identity_schema(engine, backup=lambda: None)
    install_planning_schema(engine, backup=lambda: None)
    install_deliverable_schema(engine, backup=lambda: None)
    with sessionmaker(bind=engine)() as db:
        project = Project(code='START-0205', title='Projet historique fictif', tdao_budget_h=37.5, hourly_rate=93, margin_pct=14)
        db.add(project)
        db.flush()
        db.add_all([Task(project_id=project.id, title='Tâche historique'),
                    Milestone(project_id=project.id, title='Jalon historique', contractual_date='2026-12-01')])
        db.commit()
    use_engine(monkeypatch, engine, path)
    yield engine, path
    engine.dispose()


@pytest.mark.parametrize('fresh', [True, False])
def test_startup_installs_review_guards_backs_up_once_and_second_start_is_neutral(legacy, monkeypatch, tmp_path, fresh):
    engine, path = legacy
    fresh_engine = None
    if fresh:
        path = tmp_path / 'fresh.db'
        fresh_engine = create_engine(f'sqlite:///{path}')
        configure_sqlite(fresh_engine)
        engine = fresh_engine
        use_engine(monkeypatch, engine, path)
    before = None if fresh else capture_baseline(path)
    try:
        erp.init_db()
        assert validate_review_schema(engine) == {'created_tables': [], 'created_triggers': []}
        backups = list((path.parent / 'backups').glob('minipilot-*.db'))
        assert len(backups) == 1
        if before:
            assert capture_baseline(backups[0]) == before
            assert compare_baseline(before, capture_baseline(path))['preserved']
        with engine.connect() as db:
            assert db.execute(text("SELECT max(version) FROM schema_migrations WHERE domain='erp'")).scalar_one() == 11
            assert not db.exec_driver_sql('PRAGMA foreign_key_check').all()
        after = capture_baseline(path)
        monkeypatch.setattr(erp, '_backup', lambda: pytest.fail('Second start must not back up again'))
        erp.init_db()
        assert capture_baseline(path) == after
    finally:
        if fresh_engine:
            fresh_engine.dispose()


def test_startup_l4_backup_failure_preserves_entire_existing_store(legacy, monkeypatch):
    engine, path = legacy
    before = capture_baseline(path)
    monkeypatch.setattr(erp, '_backup', lambda: (_ for _ in ()).throw(RuntimeError('backup unavailable')))
    with pytest.raises(RuntimeError, match='backup unavailable'):
        erp.init_db()
    assert capture_baseline(path) == before
    assert not {table.name for table in REVIEW_TABLES} & set(inspect(engine).get_table_names())


@pytest.mark.parametrize('kind', ['columns', 'trigger', 'populated_partial'])
def test_invalid_dormant_review_group_refuses_before_any_ddl_or_backup(legacy, monkeypatch, kind):
    engine, path = legacy
    if kind == 'columns':
        with engine.begin() as db:
            db.exec_driver_sql('CREATE TABLE project_reviews (id TEXT PRIMARY KEY, content JSON)')
    elif kind == 'trigger':
        erp.Base.metadata.create_all(engine, tables=list(REVIEW_TABLES))
        with engine.begin() as db:
            db.exec_driver_sql("CREATE TRIGGER trg_project_reviews_update_immutable BEFORE UPDATE ON project_reviews BEGIN SELECT 1; END")
    else:
        erp.Base.metadata.create_all(engine, tables=[ProjectReview.__table__])
        with sessionmaker(bind=engine)() as db:
            project = db.query(Project).one()
            db.add(ProjectReview(project_id=project.id, number=1, actor_id='fictitious', content={}, provenance={}))
            db.commit()
    before = capture_baseline(path)
    monkeypatch.setattr(erp, '_backup', lambda: pytest.fail('Invalid L4 must fail before a backup or other DDL'))
    with pytest.raises(ValueError, match='revues'):
        erp.init_db()
    assert capture_baseline(path) == before


def test_startup_upgrades_populated_pre_binding_reviews_without_changing_frozen_data(store, monkeypatch):
    initial = reviews.create(store)
    reviews.publish(store, initial['id'])
    engine, path = old_schema(store)
    use_engine(monkeypatch, engine, path)
    before = capture_baseline(path)
    try:
        erp.init_db()
        backups = list((path.parent / 'backups').glob('minipilot-*.db'))
        assert len(backups) == 1 and capture_baseline(backups[0]) == before
        assert compare_baseline(before, capture_baseline(path))['preserved']
        assert validate_review_schema(engine) == {'created_tables': [], 'created_triggers': []}
    finally:
        engine.dispose()


def isolated_client(monkeypatch, erp_factory, brain_factory=None):
    from app.main import app
    from app.db import get_db as get_brain

    def erp_db():
        with erp_factory() as db:
            yield db

    monkeypatch.setitem(app.dependency_overrides, erp.get_db, erp_db)
    if brain_factory:
        def brain_db():
            with brain_factory() as db:
                yield db
        monkeypatch.setitem(app.dependency_overrides, get_brain, brain_db)
    # No lifespan: the fixture stores are installed; production workers never run.
    return TestClient(app, base_url='http://127.0.0.1:8001')


def test_registered_reviews_cockpit_and_legacy_commands_share_revision_and_permissions(store, monkeypatch):
    client = isolated_client(monkeypatch, store[0])
    root = f"/api/v1/projects/{store[1]['project']}"
    assert client.get('/api/v1/review-types').json()[0]['code'] == 'rlp'
    first = client.post(root + '/reviews', json={'expected_revision': 0, 'content': reviews.content(store[1]).model_dump()})
    assert first.status_code == 201, first.text
    row = first.json()
    url = root + '/reviews/' + row['id']
    assert client.get(root + '/cockpit').json()['revision'] == 1
    assert client.post(root + '/tasks', json={'title': 'Ancien client', 'expected_revision': 1}).status_code == 201
    before = capture_baseline(store[2])
    stale = client.put(url, json={'expected_revision': 1, 'expected_review_revision': row['review_revision'], 'content': row['content']})
    assert stale.status_code == 409 and capture_baseline(store[2]) == before
    current = client.get(url).json()
    saved = client.put(url, json={'expected_revision': current['revision'], 'expected_review_revision': current['review_revision'],
                                 'content': {**current['content'], 'notes': 'Décision conservée'}})
    assert saved.status_code == 200, saved.text
    current = saved.json()
    published = client.post(url + '/publish', json={'expected_revision': current['revision'], 'expected_review_revision': current['review_revision'], 'confirmed': True})
    assert published.status_code == 200, published.text
    pdf = client.get(url + '/pdf')
    assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF-')
    assert hashlib.sha256(pdf.content).hexdigest() == published.json()['publication']['pdf_sha256']
    assert client.get(url + '/publication').json()['bindings'] == {}
    assert client.get(root + '/cockpit/items/tasks').json()['items'][0]['title'] == 'Ancien client'
    assert client.get(root + '/planning/state').json()['revision'] == published.json()['revision']
    with operator_context(Operator('reader', 'reader', frozenset([store[1]['project']]))):
        assert client.get(root + '/cockpit').status_code == 200
        assert not client.get(root + '/cockpit').json()['can_edit']
        assert client.get(url + '/pdf').status_code == 200
        assert client.post(url + '/revision', json={}).status_code == 403
    with operator_context(Operator('foreign', 'reader', frozenset([store[1]['foreign']]))):
        for suffix in ('/cockpit', '/cockpit/items/tasks', '/reviews', '/reviews/' + row['id'] + '/pdf'):
            assert client.get(root + suffix).status_code == 404


def test_registered_selective_import_export_keeps_review_pdf_and_bindings(transport, monkeypatch):
    data, target, brain, erp_path, brain_path, _ = transport
    original = deepcopy(data)
    client = isolated_client(monkeypatch, target, brain)
    imported = client.post('/api/v1/projects/import-json', json={'data': data, 'code': 'HTTP-0205'})
    assert imported.status_code == 201, imported.text
    root = f"/api/v1/projects/{imported.json()['id']}"
    exported = client.get(root + '/export')
    assert exported.status_code == 200 and exported.json()['version'] == 6
    captured = data['tables']['project_review_publications'][0]
    actual = exported.json()['tables']['project_review_publications'][0]
    assert all(actual[key] == captured[key] for key in ('snapshot', 'sha256', 'pdf_base64', 'pdf_sha256'))
    before = capture_baseline(erp_path), capture_baseline(brain_path)
    url = root + '/reviews/' + actual['review_id']
    assert client.get(url + '/publication').json()['bindings']['erp'][original['project']['id']] == imported.json()['id']
    assert client.get(root + '/cockpit').status_code == 200
    assert client.get(url + '/pdf').status_code == 200
    assert (capture_baseline(erp_path), capture_baseline(brain_path)) == before
    assert data == original
