"""Guarded document startup through ERP10; never touches user stores."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import sessionmaker

from app.db_support import configure_sqlite, record_schema
from backend.app import db as runtime
from backend.app.models import NetworkLink, Project
from backend.app.project_document_models import DOCUMENT_FORM_TABLES, ProjectDocumentDraft
from backend.app.project_document_job_models import DOCUMENT_JOB_TABLES, DocumentJob
from backend.app.project_note_models import NOTE_TABLES
from backend.app.services.migration_guard import capture_baseline, compare_baseline
from backend.app.services.project_document_migration import validate_document_schema
from backend.app.services.document_job_schema import validate_job_schema
from backend.app.services.document_job_worker import DocumentCoordinator
from backend.app.services.project_operator import Operator

DOCUMENT_TABLES = (*DOCUMENT_FORM_TABLES, *DOCUMENT_JOB_TABLES)


def bind(monkeypatch, engine, path):
    monkeypatch.setattr(runtime, 'engine', engine)
    monkeypatch.setattr(runtime, 'DB_PATH', path)
    monkeypatch.setattr(runtime, 'APP_DIR', path.parent)


@pytest.fixture
def old_store(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "erp.db"}', connect_args={'check_same_thread': False})
    configure_sqlite(engine)
    from backend.app.services.project_identity_migration import install_identity_schema
    from backend.app.services.project_planning_migration import install_planning_schema
    from backend.app.services.project_deliverable_migration import install_deliverable_schema
    from backend.app.services.project_review_migration import install_review_schema
    runtime.Base.metadata.create_all(engine, tables=[table for table in runtime.Base.metadata.sorted_tables
                                                    if table not in (*DOCUMENT_TABLES, *NOTE_TABLES)
                                                    and table.name != 'note_evidence_outbox'])
    for install in (install_identity_schema, install_planning_schema, install_deliverable_schema, install_review_schema):
        install(engine, backup=lambda: None)
    record_schema(engine, 'erp', 8)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(Project(id='legacy-project', code='AIRB26LTH0205-A', title='LED conservée',
                       hourly_rate=89, margin_pct=7, tdao_prix_vente=1243, remaining_hours=42))
        db.flush()
        db.add(NetworkLink(id='legacy-link', project_id='legacy-project', code='projet',
                           libelle='Dossier conservé', chemin='V:/Affaire originale'))
        db.commit()
    path = tmp_path / 'erp.db'
    bind(monkeypatch, engine, path)
    yield engine, factory, path
    engine.dispose()


def ready(engine):
    assert validate_document_schema(engine) == {'created_tables': [], 'created_triggers': []}
    assert validate_job_schema(engine) == {'created_tables': [], 'created_triggers': []}
    with engine.connect() as db:
        assert db.exec_driver_sql("SELECT max(version) FROM schema_migrations WHERE domain='erp'").scalar_one() == 11
        assert not db.exec_driver_sql('PRAGMA foreign_key_check').all()
        assert all(db.exec_driver_sql(f'SELECT count(*) FROM {table.name}').scalar_one() == 0
                   for table in DOCUMENT_TABLES)


def test_upgrade_backs_up_once_preserves_every_cell_and_second_start_is_neutral(old_store, monkeypatch):
    engine, _, path = old_store
    before = capture_baseline(path)
    actual_backup = runtime._backup
    calls = []
    def backup():
        assert not {table.name for table in DOCUMENT_TABLES} & set(inspect(engine).get_table_names())
        assert capture_baseline(path) == before
        actual_backup()
        calls.append(True)
    monkeypatch.setattr(runtime, '_backup', backup)
    runtime.init_db()
    assert calls == [True]
    ready(engine)
    copies = list((path.parent / 'backups').glob('*.db'))
    assert len(copies) == 1 and capture_baseline(copies[0]) == before
    assert compare_baseline(before, capture_baseline(path))['preserved']
    after = capture_baseline(path)
    monkeypatch.setattr(runtime, '_backup', lambda: pytest.fail('second backup'))
    runtime.init_db()
    assert capture_baseline(path) == after


def test_fresh_start_installs_protections_without_seeding_or_repeated_backup(tmp_path, monkeypatch):
    path = tmp_path / 'fresh.db'
    engine = create_engine(f'sqlite:///{path}')
    configure_sqlite(engine)
    bind(monkeypatch, engine, path)
    try:
        runtime.init_db()
        ready(engine)
        before = capture_baseline(path)
        monkeypatch.setattr(runtime, '_backup', lambda: pytest.fail('second backup'))
        runtime.init_db()
        assert capture_baseline(path) == before
    finally:
        engine.dispose()


def test_failed_backup_leaves_the_whole_v8_store_unchanged(old_store, monkeypatch):
    engine, _, path = old_store
    before = capture_baseline(path)
    def fail():
        raise OSError('backup disk unavailable')
    monkeypatch.setattr(runtime, '_backup', fail)
    with pytest.raises(OSError, match='backup disk'):
        runtime.init_db()
    assert capture_baseline(path) == before
    assert not {table.name for table in DOCUMENT_TABLES} & set(inspect(engine).get_table_names())


@pytest.mark.parametrize('table', ['project_document_drafts', 'project_document_jobs'])
def test_incompatible_group_is_rejected_before_any_ddl_or_backup(old_store, monkeypatch, table):
    engine, _, path = old_store
    with engine.begin() as db:
        db.exec_driver_sql(f'CREATE TABLE {table} (id TEXT PRIMARY KEY)')
    before = capture_baseline(path)
    monkeypatch.setattr(runtime, '_backup', lambda: pytest.fail('preflight before backup'))
    with pytest.raises(ValueError, match='incompatible'):
        runtime.init_db()
    assert capture_baseline(path) == before


@pytest.mark.parametrize('group', ['form', 'job'])
def test_populated_partial_group_is_never_completed_implicitly(old_store, monkeypatch, group):
    engine, factory, path = old_store
    model = ProjectDocumentDraft if group == 'form' else DocumentJob
    model.__table__.create(engine)
    with factory() as db:
        if group == 'form':
            db.add(ProjectDocumentDraft(project_id='legacy-project', document_id='ce_request', revision=1))
        else:
            db.add(DocumentJob(project_id='legacy-project', command_id='existing', actor_id='historical',
                               total=1, snapshot='{}', sha256='0'*64))
        db.commit()
    before = capture_baseline(path)
    monkeypatch.setattr(runtime, '_backup', lambda: pytest.fail('partial data must be rejected first'))
    with pytest.raises(ValueError, match='partiel'):
        runtime.init_db()
    assert capture_baseline(path) == before


@pytest.mark.parametrize('group', ['form', 'job'])
def test_wrong_history_trigger_is_rejected_before_other_group_ddl(old_store, monkeypatch, group):
    engine, _, path = old_store
    from backend.app.services.document_schema_rules import immutable_triggers
    from backend.app.services.document_job_schema_rules import protections
    tables, triggers = (DOCUMENT_FORM_TABLES, immutable_triggers()) if group == 'form' else (DOCUMENT_JOB_TABLES, protections())
    runtime.Base.metadata.create_all(engine, tables=list(tables))
    name, sql = next(iter(triggers.items()))
    prefix = sql[:sql.upper().index('BEGIN')]
    with engine.begin() as db:
        db.exec_driver_sql(prefix + 'BEGIN SELECT 1; END')
    before = capture_baseline(path)
    monkeypatch.setattr(runtime, '_backup', lambda: pytest.fail('wrong trigger before backup'))
    with pytest.raises(ValueError, match='Protection'):
        runtime.init_db()
    assert capture_baseline(path) == before
    with engine.connect() as db:
        assert name in {entry[0] for entry in db.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='trigger'")}


def test_real_http_document_reads_after_startup_do_not_seed_or_modify_data(old_store):
    engine, factory, path = old_store
    runtime.init_db()
    before = capture_baseline(path)
    from app.main import app
    from backend.app.db import get_db
    def dependency():
        with factory() as db:
            yield db
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = dependency
    try:
        client = TestClient(app, base_url='http://127.0.0.1:8001')
        for route in ('/documents', '/documents/forms/ce_request'):
            response = client.get('/api/v1/projects/legacy-project' + route)
            assert response.status_code == 200, response.text
        assert capture_baseline(path) == before
        with factory() as db:
            assert db.scalar(select(ProjectDocumentDraft)) is None
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_started_idle_worker_is_leased_and_reader_worker_stays_read_only(old_store):
    engine, factory, path = old_store
    runtime.init_db()
    before = capture_baseline(path)
    worker = DocumentCoordinator(factory, storage_root=path.parent/'managed', operator=Operator('startup-owner', 'owner'))
    reader = DocumentCoordinator(factory, storage_root=path.parent/'managed', operator=Operator('startup-reader', 'reader'))
    try:
        assert reader.start(enabled=True)['state'] == 'read_only'
        state = worker.start(enabled=True)
        assert state['running'] and state['can_submit']
        assert capture_baseline(path) == before
        assert not (path.parent/'managed').exists()
    finally:
        assert worker.stop()
