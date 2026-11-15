"""ERP11 Notes/outbox startup and real routing on fictional SQLite stores."""
import hashlib
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.db_support import record_schema
from backend.app import db as runtime
from backend.app.project_note_models import NOTE_TABLES
from backend.app.note_evidence_models import NoteEvidenceOutbox
from backend.app.project_note_schemas import NoteCreate
from backend.app.services import project_notes as notes, project_note_files as files
from backend.app.services.document_job_schema import install_job_schema
from backend.app.services.migration_guard import capture_baseline, compare_baseline
from backend.app.services.project_document_migration import install_document_schema
from backend.app.services.project_note_schema import install_note_schema, validate_note_schema, note_triggers
from backend.app.services.note_evidence_outbox import validate_outbox_schema
from tests.test_project_document_registration import old_store

__all__ = ['old_store']


@pytest.fixture
def erp9(old_store):
    engine, _, _ = old_store
    install_document_schema(engine, backup=lambda: None)
    install_job_schema(engine, backup=lambda: None)
    record_schema(engine, 'erp', 9)
    assert not {table.name for table in NOTE_TABLES} & set(inspect(engine).get_table_names())
    assert NoteEvidenceOutbox.__tablename__ not in inspect(engine).get_table_names()
    return old_store


def marker(engine):
    with engine.connect() as db:
        return db.exec_driver_sql("SELECT max(version) FROM schema_migrations WHERE domain='erp'").scalar_one()


def test_erp9_upgrade_backup_precedes_every_note_table_and_preserves_all_cells(erp9, monkeypatch):
    engine, _, path = erp9
    before = capture_baseline(path)
    actual = runtime._backup
    calls = []
    def backup():
        assert marker(engine) == 9
        assert not {table.name for table in NOTE_TABLES} & set(inspect(engine).get_table_names())
        assert NoteEvidenceOutbox.__tablename__ not in inspect(engine).get_table_names()
        assert capture_baseline(path) == before
        actual()
        calls.append(True)
    monkeypatch.setattr(runtime, '_backup', backup)
    runtime.init_db()
    assert calls == [True] and marker(engine) == 11
    assert validate_note_schema(engine) == {'created_tables': [], 'created_triggers': []}
    assert validate_outbox_schema(engine)
    copies = list((path.parent / 'backups').glob('minipilot-*.db'))
    assert len(copies) == 1 and capture_baseline(copies[0]) == before
    assert compare_baseline(before, capture_baseline(path))['preserved']
    with engine.connect() as db:
        assert all(db.exec_driver_sql(f'SELECT count(*) FROM {table.name}').scalar_one() == 0 for table in NOTE_TABLES)
        assert not db.exec_driver_sql('PRAGMA foreign_key_check').all()
    after = capture_baseline(path)
    monkeypatch.setattr(runtime, '_backup', lambda: pytest.fail('No repeated backup or write on second start'))
    runtime.init_db()
    assert capture_baseline(path) == after


def test_already_installed_notes_still_require_backup_before_marker_upgrade(erp9, monkeypatch):
    engine, factory, path = erp9
    install_note_schema(engine, backup=lambda: None)
    with factory() as db:
        created = notes.create_note(db, 'legacy-project', NoteCreate(command_id=str(uuid4()), title='Note historique'))
        db.commit()
    before = capture_baseline(path)
    actual = runtime._backup
    calls = []
    def backup():
        assert marker(engine) == 9 and capture_baseline(path) == before
        actual()
        calls.append(True)
    monkeypatch.setattr(runtime, '_backup', backup)
    runtime.init_db()
    assert calls == [True] and compare_baseline(before, capture_baseline(path))['preserved']
    with factory() as db:
        assert notes.read_note(db, 'legacy-project', created['note']['id'])['revision'] == 1


def test_failed_note_upgrade_backup_preserves_the_entire_erp9_database(erp9, monkeypatch):
    engine, _, path = erp9
    before = capture_baseline(path)
    def failure():
        raise OSError('backup disk unavailable')
    monkeypatch.setattr(runtime, '_backup', failure)
    with pytest.raises(OSError, match='backup disk'):
        runtime.init_db()
    assert marker(engine) == 9 and capture_baseline(path) == before


@pytest.mark.parametrize('damage', ['table', 'trigger', 'populated_missing_trigger'])
def test_invalid_note_schema_refused_before_other_ddl_or_backup(erp9, monkeypatch, damage):
    engine, factory, path = erp9
    if damage == 'table':
        with engine.begin() as db:
            db.exec_driver_sql('CREATE TABLE project_notes (id TEXT PRIMARY KEY)')
    else:
        install_note_schema(engine, backup=lambda: None)
        if damage == 'populated_missing_trigger':
            with factory() as db:
                notes.create_note(db, 'legacy-project', NoteCreate(command_id=str(uuid4()), title='Capture conservée'))
                db.commit()
        name = next(iter(note_triggers()))
        with engine.begin() as db:
            db.exec_driver_sql(f'DROP TRIGGER {name}')
            if damage == 'trigger':
                db.exec_driver_sql(f'CREATE TRIGGER {name} BEFORE UPDATE ON project_note_versions BEGIN SELECT 1; END')
    before = capture_baseline(path)
    monkeypatch.setattr(runtime, '_backup', lambda: pytest.fail('Schema rejection must precede backup'))
    with pytest.raises(ValueError, match='incompatible|partiel'):
        runtime.init_db()
    assert marker(engine) == 9 and capture_baseline(path) == before


def test_empty_unprotected_metadata_is_guarded_only_after_backup(erp9, monkeypatch):
    engine, _, path = erp9
    runtime.Base.metadata.create_all(engine, tables=list(NOTE_TABLES))
    before = capture_baseline(path)
    actual = runtime._backup
    calls = []
    def backup():
        assert capture_baseline(path) == before
        actual()
        calls.append(True)
    monkeypatch.setattr(runtime, '_backup', backup)
    runtime.init_db()
    assert calls == [True] and validate_note_schema(engine) == {'created_tables': [], 'created_triggers': []}
    assert compare_baseline(before, capture_baseline(path))['preserved']


@pytest.fixture
def registered(erp9, monkeypatch):
    engine, factory, path = erp9
    runtime.init_db()
    from app.main import app
    from backend.app.db import get_db
    def dependency():
        with factory() as db:
            yield db
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = dependency
    monkeypatch.setattr(files, 'APP_DIR', path.parent)
    monkeypatch.setenv('AGENT_TESTING', '0')
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'owner')
    monkeypatch.setenv('AGENT_OPERATOR_ID', 'registration-owner')
    monkeypatch.delenv('AGENT_OPERATOR_PROJECT_IDS', raising=False)
    client = TestClient(app, base_url='http://127.0.0.1:8001')
    try:
        # Without the lifespan context: retain actual routes/middleware while
        # keeping unrelated background workers stopped. ERP was started above.
        yield client, '/api/v1/projects/legacy-project/notes', erp9
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def authenticate(client):
    client.headers.update({'x-agent-token': client.get('/api/v1/session').json()['token']})


def test_real_registration_reads_are_neutral_and_commands_require_session(registered):
    client, base, (_, _, path) = registered
    before = capture_baseline(path)
    page = client.get(base)
    assert page.status_code == 200 and page.json()['available'] and page.json()['items'] == []
    assert page.json()['operator_id'] == 'registration-owner'
    assert capture_baseline(path) == before
    payload = {'command_id': str(uuid4()), 'title': 'Réunion locale'}
    assert client.post(base, json=payload).status_code == 403
    authenticate(client)
    first = client.post(base, json=payload)
    assert first.status_code == 201, first.text
    assert client.post(base, json=payload).json()['replayed']
    assert client.get(base).json()['total'] == 1


def test_registered_files_import_replay_originals_and_network_routes(registered, monkeypatch):
    client, base, (_, _, path) = registered
    authenticate(client)
    first = client.post(base, json={'command_id':str(uuid4()),'title':'Avec preuve'})
    note_id = first.json()['note']['id']
    attachment = client.post(base+'/'+note_id+'/attachments', data={'command_id':str(uuid4())}, files={'file':('proof.txt',b'Preuve fictive','text/plain')})
    assert attachment.status_code == 201, attachment.text
    asset_id = attachment.json()['attachment']['id']
    assert client.get(base+'/'+note_id+'/attachments/'+asset_id+'/download').content == b'Preuve fictive'
    original = b'<p><strong>Decision LED</strong></p>'
    planned = str(uuid4())
    selection = [('files',('import.html',original,'text/html'))]
    preview = client.post(base+'/imports/preview',data={'planned_note_id':planned,'paths':'["import.html"]'},files=selection)
    assert preview.status_code == 200 and preview.json()['can_apply'], preview.text
    command = {'command_id':str(uuid4()),'planned_note_id':planned,'expected_preview_sha256':preview.json()['preview_sha256'],'mode':'rich','source':{'kind':'upload','link_id':None,'relative_path':''}}
    applied = client.post(base+'/imports',data={'command':json.dumps(command),'paths':'["import.html"]'},files=selection)
    assert applied.status_code == 201, applied.text
    source = client.get(base+'/'+planned+'/source')
    assert source.status_code == 200 and source.json()['source_files'][0]['sha256'] == hashlib.sha256(original).hexdigest()
    assert client.get(base+'/'+planned+'/originals/download',params={'relative_path':'import.html'}).content == original
    replay = client.post(base+'/imports/replay',json=command)
    assert replay.status_code == 200 and replay.json()['replayed']
    assert client.get(base).json()['total'] == 2
    # The network static route must reach its own closed validator, before any
    # source access, rather than the dynamic note-id route.
    monkeypatch.setenv('AGENT_DOCUMENT_ROOTS','[]')
    network = client.post(base+'/imports/network/preview',json={'planned_note_id':'invalid','source':{'kind':'project_link','link_id':'legacy-link','relative_path':'note.html'}})
    assert network.status_code == 422
    assert any(error['loc'][-1]=='planned_note_id' for error in network.json()['detail'])
    unconfigured = client.post(base+'/imports/network/preview',json={'planned_note_id':str(uuid4()),'source':{'kind':'project_link','link_id':'legacy-link','relative_path':'note.html'}})
    assert unconfigured.status_code == 409  # Server roots remain required.
    assert path.parent.joinpath('note-files').exists() and path.parent.joinpath('note-originals').exists()


def test_registered_reader_and_foreign_scope_cannot_mutate_or_reveal(registered, monkeypatch):
    client, base, (_, _, path) = registered
    authenticate(client)
    monkeypatch.setenv('AGENT_OPERATOR_ROLE','reader')
    before = capture_baseline(path)
    assert client.get(base).status_code == 200
    assert client.post(base,json={'command_id':str(uuid4()),'title':'Forbidden'}).status_code == 403
    assert client.post(base+'/imports/replay',json={}).status_code == 403
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS','["other-project"]')
    assert client.get(base).status_code == 404
    assert capture_baseline(path) == before
