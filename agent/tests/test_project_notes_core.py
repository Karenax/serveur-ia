"""Real SQLite note history, lost responses, concurrent authors and isolation."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
import sqlite3
from threading import Barrier
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateTable

from app.db_support import backup_sqlite, configure_sqlite
from backend.app.db import Base
from backend.app.models import Project
from backend.app.project_note_models import NOTE_TABLES, NoteVersion, ProjectNote, NoteAttachment
from backend.app.personal_note_models import PersonalNote, PersonalNoteImage
from backend.app.project_note_schemas import NoteContent, NoteCreate, NoteSave, NoteRestore, content_text
from backend.app.services import project_notes as notes
from backend.app.services.project_note_schema import install_note_schema, validate_note_schema, note_triggers
from backend.app.services.project_note_schema_rules import SEQUENCE_TRIGGER, legacy_attachment_sql, legacy_sequence_sql
from backend.app.services.project_operator import Operator, operator_context


def command():
    return str(uuid4())


def rich():
    return NoteContent.model_validate({'blocks': [
        {'type': 'heading', 'level': 2, 'runs': [{'text': 'Réunion', 'marks': ['bold']}]},
        {'type': 'paragraph', 'runs': [{'text': 'Résultat 50%_ : ', 'color': '#112233'},
            {'text': 'documentation', 'href': 'https://example.org/docs'}]},
        {'type': 'list', 'kind': 'checklist', 'items': [{'runs': [{'text': 'Vérifier'}], 'checked': True}]},
        {'type': 'table', 'rows': [[[{'text': 'Lot'}], [{'text': 'Date'}]], [[{'text': 'BE'}], [{'text': 'Demain'}]]]},
    ]})


@pytest.fixture
def store(tmp_path):
    path = tmp_path / 'notes.db'
    engine = create_engine('sqlite:///' + path.as_posix(), connect_args={'check_same_thread': False})
    configure_sqlite(engine)
    Base.metadata.create_all(engine, tables=[Project.__table__])
    factory = sessionmaker(bind=engine)
    with factory() as db:
        first = Project(code='FIRST', title='Premier', hourly_rate=98, margin_pct=8, tdao_prix_vente=123)
        other = Project(code='SECOND', title='Autre')
        db.add_all([first, other])
        db.commit()
        ids = first.id, other.id
    yield engine, factory, ids, path
    engine.dispose()


def install(store):
    engine, _, _, path = store
    return install_note_schema(engine, backup=lambda: backup_sqlite(path, path.with_suffix('.before.db')))


def created(store, *, title='Première note'):
    _, factory, ids, _ = store
    payload = NoteCreate(command_id=command(), title=title, content=rich())
    with factory() as db:
        result = notes.create_note(db, ids[0], payload)
        db.commit()
    return result, payload


def error(code, callback):
    with pytest.raises(HTTPException) as caught:
        callback()
    assert caught.value.status_code == code


def test_dormant_read_neither_installs_nor_seeds(store, monkeypatch):
    engine, factory, ids, _ = store
    monkeypatch.setattr('pathlib.Path.read_bytes', lambda *args: pytest.fail('No file access'))
    with factory() as db:
        assert notes.list_notes(db, ids[0]) == {'available': False, 'items': [], 'total': 0, 'limit': 30, 'offset': 0}
        error(409, lambda: notes.create_note(db, ids[0], NoteCreate(command_id=command(), title='Vide')))
    assert not set(inspect(engine).get_table_names()) & {table.name for table in NOTE_TABLES}


def test_backup_before_ddl_exact_old_cells_second_install_neutral(store):
    engine, _, _, path = store
    calls = []
    def backup():
        assert not set(inspect(engine).get_table_names()) & {table.name for table in NOTE_TABLES}
        backup_sqlite(path, path.with_suffix('.before.db'))
        calls.append(True)
    plan = install_note_schema(engine, backup=backup)
    assert len(plan['created_tables']) == 4 and len(plan['created_triggers']) == 12 and calls == [True]
    assert install_note_schema(engine, backup=lambda: pytest.fail('Repeat backup')) == {'created_tables': [], 'created_triggers': []}
    with sqlite3.connect(path.with_suffix('.before.db')) as before, sqlite3.connect(path) as after:
        assert before.execute('SELECT * FROM projects').fetchall() == after.execute('SELECT * FROM projects').fetchall()
        assert after.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not after.execute('PRAGMA foreign_key_check').fetchall()


def test_attachment_upgrade_preserves_old_rows_and_accepts_more_than_five_mib(store, tmp_path, monkeypatch):
    import io
    from backend.app.services import project_note_files

    engine, factory, ids, path = store
    monkeypatch.setattr(project_note_files, 'APP_DIR', tmp_path)
    with engine.begin() as db:
        for table in (*NOTE_TABLES, PersonalNote.__table__, PersonalNoteImage.__table__):
            db.exec_driver_sql(legacy_attachment_sql(str(CreateTable(table).compile(dialect=engine.dialect))))
            for index in table.indexes:
                index.create(db)
        for name, trigger in note_triggers().items():
            db.exec_driver_sql(legacy_sequence_sql(trigger) if name == SEQUENCE_TRIGGER else trigger)
    response, _ = created(store)
    note = response['note']
    with factory() as db:
        old = project_note_files.upload(db, ids[0], note['id'], command_id=command(), filename='ancien.txt', stream=io.BytesIO(b'original'))
        db.commit()
    captures = []
    def backup():
        captures.append(True)
        backup_sqlite(path, path.with_suffix('.before.db'))
    plan = install_note_schema(engine, backup=backup)
    assert set(plan['upgrades']) == {'project_note_attachments', 'personal_note_images', SEQUENCE_TRIGGER}
    assert captures == [True]
    assert not validate_note_schema(engine).get('upgrades')
    with factory() as db:
        size = 6 * 1024 * 1024
        result = project_note_files.upload(db, ids[0], note['id'], command_id=command(), filename='grand.txt', stream=io.BytesIO(b'x' * size))
        assert result['attachment']['size_bytes'] == size
        retained = project_note_files.download(db, ids[0], note['id'], old['attachment']['id'])
        assert retained[0] == b'original'
        db.commit()
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()


def test_backup_failure_and_incompatible_schema_precede_any_ddl(store):
    engine, _, _, _ = store
    def failure():
        raise OSError('disk full')
    with pytest.raises(OSError):
        install_note_schema(engine, backup=failure)
    assert 'project_notes' not in inspect(engine).get_table_names()
    with engine.begin() as db:
        db.exec_driver_sql('CREATE TABLE project_notes (id TEXT PRIMARY KEY)')
    with pytest.raises(ValueError, match='incompatible'):
        install_note_schema(engine, backup=lambda: pytest.fail('Preflight first'))


def test_rich_content_plain_text_search_is_literal_paginated_and_neutral(store):
    _, factory, ids, _ = store
    install(store)
    result, _ = created(store)
    with factory() as db:
        assert notes.read_note(db, ids[0], result['note']['id'])['content'] == rich().model_dump(mode='json')
        assert content_text(rich()) == 'Réunion\nRésultat 50%_ : documentation\n[x] Vérifier\nLot\tDate\nBE\tDemain'
        assert notes.list_notes(db, ids[0], query='reunion')['total'] == 1
        assert notes.list_notes(db, ids[0], query='50%_')['total'] == 1
        assert notes.list_notes(db, ids[0], query='%_other')['total'] == 0
        assert notes.list_notes(db, ids[0], limit=1, offset=1)['items'] == []
        assert notes.list_notes(db, ids[1])['total'] == 0
        assert not db.new and not db.dirty
        error(422, lambda: notes.list_notes(db, ids[0], limit=True))


def test_create_and_save_retries_ack_same_command_without_new_version(store):
    _, factory, ids, _ = store
    install(store)
    first, payload = created(store)
    key = first['note']['id']
    with factory() as db:
        replay = notes.create_note(db, ids[0], payload)
        assert replay['replayed'] and replay['note']['id'] == key and replay['command_revision'] == 1
        saved = NoteSave(command_id=command(), expected_revision=1, title='Autre', content=NoteContent())
        second = notes.save_note(db, ids[0], key, saved)
        db.commit()
    with factory() as db:
        assert notes.save_note(db, ids[0], key, saved)['command_version_id'] == second['command_version_id']
        old_ack = notes.create_note(db, ids[0], payload)
        assert old_ack['command_revision'] == 1 and old_ack['note']['revision'] == 2
        assert notes.history(db, ids[0], key)['total'] == 2
        with operator_context(Operator('another-author', 'owner')):
            error(409, lambda: notes.save_note(db, ids[0], key, saved))
        changed = saved.model_copy(update={'title': 'New payload'})
        error(409, lambda: notes.save_note(db, ids[0], key, changed))


def test_restore_appends_version_with_actor_without_changing_raw_history(store):
    _, factory, ids, _ = store
    install(store)
    first, _ = created(store)
    key = first['note']['id']
    with factory() as db:
        raw = db.get(NoteVersion, first['command_version_id']).snapshot
        notes.save_note(db, ids[0], key, NoteSave(command_id=command(), expected_revision=1, title='Révisée', content=NoteContent()))
        db.commit()
    payload = NoteRestore(command_id=command(), expected_revision=2, version_id=first['command_version_id'])
    with factory() as db, operator_context(Operator('technical-author', 'editor')):
        restored = notes.restore_note(db, ids[0], key, payload)
        db.commit()
        assert restored['note']['revision'] == 3 and restored['note']['content'] == rich().model_dump(mode='json')
        assert restored['note']['actor_id'] == 'technical-author'
        assert db.get(NoteVersion, first['command_version_id']).snapshot == raw
        assert notes.restore_note(db, ids[0], key, payload)['replayed']


def test_two_real_connections_cannot_overwrite_same_revision(store):
    _, factory, ids, _ = store
    install(store)
    first, _ = created(store)
    barrier = Barrier(2)
    def write(title):
        with factory() as db:
            barrier.wait(timeout=5)
            try:
                notes.save_note(db, ids[0], first['note']['id'], NoteSave(command_id=command(), expected_revision=1, title=title))
                db.commit()
                return 'saved'
            except HTTPException as exc:
                db.rollback()
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(write, ['Auteur A', 'Auteur B']), key=str) == [409, 'saved']
    with factory() as db:
        assert notes.read_note(db, ids[0], first['note']['id'])['revision'] == 2
        assert notes.history(db, ids[0], first['note']['id'])['total'] == 2


def test_reader_scope_and_foreign_note_cannot_write_or_reveal_history(store):
    _, factory, ids, _ = store
    install(store)
    first, payload = created(store)
    with factory() as db:
        with operator_context(Operator('reader', 'reader')):
            assert notes.list_notes(db, ids[0])['total'] == 1
            error(403, lambda: notes.create_note(db, ids[0], payload))
        error(404, lambda: notes.read_note(db, ids[1], first['note']['id']))
        error(404, lambda: notes.history(db, ids[1], first['note']['id']))
        with operator_context(Operator('scoped', 'editor', frozenset({ids[1]}))):
            error(404, lambda: notes.list_notes(db, ids[0]))


@pytest.mark.parametrize('statement', [
    "UPDATE project_note_versions SET actor_id='forged'",
    'DELETE FROM project_note_versions', 'DELETE FROM project_notes',
    "UPDATE project_notes SET title='orphaned'", 'UPDATE project_notes SET revision=revision+1',
])
def test_sql_history_and_head_protections_are_actual(store, statement):
    engine, _, _, _ = store
    install(store)
    created(store)
    with pytest.raises(IntegrityError), engine.begin() as db:
        db.exec_driver_sql(statement)


def test_missing_or_hostile_trigger_with_data_is_refused(store):
    engine, _, _, _ = store
    install(store)
    created(store)
    trigger = next(iter(note_triggers()))
    with engine.begin() as db:
        db.exec_driver_sql('DROP TRIGGER ' + trigger)
    with pytest.raises(ValueError, match='partiel avec données'):
        validate_note_schema(engine)
    with engine.begin() as db:
        db.exec_driver_sql(f"CREATE TRIGGER {trigger} BEFORE UPDATE ON project_note_versions BEGIN SELECT 1; END")
    with pytest.raises(ValueError, match='Protection'):
        validate_note_schema(engine)


@pytest.mark.parametrize('change', [
    {'actor_id': 'forged'}, {'content_html': '<img src=x onerror=alert(1)>'},
    {'content': {'blocks': [{'type': 'html', 'html': '<script/>'}]}},
    {'content': {'blocks': [{'type': 'paragraph', 'runs': [{'text': 'x', 'href': 'javascript:alert(1)'}]}]}},
    {'content': {'blocks': [{'type': 'paragraph', 'runs': [{'text': 'x', 'href': 'data:text/html,x'}]}]}},
    {'content': {'blocks': [{'type': 'paragraph', 'runs': [{'text': 'x', 'href': 'https://user:pass@example.org/'}]}]}},
    {'content': {'blocks': [{'type': 'table', 'rows': [[[]], [[], []]]}]}},
    {'content': {'blocks': [{'type': 'image', 'attachment_id': command(), 'src': 'https://example.org/track'}]}},
    {'title': '  '}, {'title': 'nul\0'},
])
def test_closed_content_rejects_html_identity_unsafe_urls_and_invalid_tables(change):
    value = {'command_id': command(), 'title': 'Valide', **deepcopy(change)}
    with pytest.raises(ValidationError):
        NoteCreate.model_validate(value)


def test_images_and_attachments_must_belong_to_this_note(store):
    _, factory, ids, _ = store
    install(store)
    first, _ = created(store)
    second, _ = created(store, title='Other note')
    attachment_id = command()
    with factory() as db:
        db.add(NoteAttachment(id=attachment_id, project_id=ids[0], note_id=second['note']['id'], storage_id=command(),
            filename='image.png', content_type='image/png', size_bytes=123, sha256='a'*64, command_id=command(), actor_id='local'))
        db.commit()
        payload = NoteSave(command_id=command(), expected_revision=1, title='Image', attachment_ids=[attachment_id],
            content=NoteContent.model_validate({'blocks': [{'type': 'image', 'attachment_id': attachment_id}]}))
        error(422, lambda: notes.save_note(db, ids[0], first['note']['id'], payload))
        db.rollback()
        assert notes.read_note(db, ids[0], first['note']['id'])['revision'] == 1
        assert db.scalar(select(ProjectNote).where(ProjectNote.id == second['note']['id'])).revision == 1


def test_legacy_project_rows_refuse_notes_instead_of_dropping_history(store):
    from backend.app.services.project_archive import _rows
    _, factory, ids, _ = store
    install(store)
    created(store)
    with factory() as db:
        error(409, lambda: _rows(db, Base.metadata, ids[0]))


def test_unqualified_whole_backup_and_restore_refuse_before_output_creation(store, tmp_path):
    from app.services.backup import create_backup, restore_backup
    engine, _, _, path = store
    install(store)
    created(store)
    # A populated but unprotected note schema must still be refused even now
    # that complete notes have a qualified global transport.
    with engine.begin() as db:
        db.exec_driver_sql('DROP TRIGGER trg_project_note_versions_sequence')
    erp = tmp_path / 'erp'
    erp.mkdir()
    backup_sqlite(path, erp / 'minipilot.db')
    brain = tmp_path / 'brain.db'
    with sqlite3.connect(brain) as db:
        db.execute('CREATE TABLE marker(id INTEGER PRIMARY KEY)')
        db.execute('INSERT INTO marker VALUES (1)')
    output = tmp_path / 'backup-refused'
    with pytest.raises(ValueError, match='Notes'):
        create_backup(output, brain, erp, tmp_path / 'storage')
    assert not output.exists()
    archive = tmp_path / 'fictitious-archive'
    for name, original in [('erp/minipilot.db', erp / 'minipilot.db'), ('brain/project_brain.db', brain)]:
        destination = archive / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        backup_sqlite(original, destination)
    files = {name: hashlib.sha256((archive / name).read_bytes()).hexdigest()
             for name in ('erp/minipilot.db', 'brain/project_brain.db')}
    (archive / 'backup.json').write_text(json.dumps({'format': 'agent-offline-backup', 'version': 1, 'files': files}), encoding='utf-8')
    restored = tmp_path / 'restore-refused'
    with pytest.raises(ValueError, match='Notes'):
        restore_backup(archive, restored)
    assert not restored.exists()


def test_real_runtime_installs_protected_notes_without_seeding(tmp_path, monkeypatch):
    from backend.app import db as runtime
    path = tmp_path / 'fresh-runtime.db'
    engine = create_engine('sqlite:///' + path.as_posix())
    configure_sqlite(engine)
    monkeypatch.setattr(runtime, 'engine', engine)
    monkeypatch.setattr(runtime, 'DB_PATH', path)
    monkeypatch.setattr(runtime, 'APP_DIR', path.parent)
    runtime.init_db()
    assert {table.name for table in NOTE_TABLES} <= set(inspect(engine).get_table_names())
    assert validate_note_schema(engine) == {'created_tables': [], 'created_triggers': []}
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT max(version) FROM schema_migrations WHERE domain='erp'").fetchone()[0] == 11
        assert all(db.execute(f'SELECT count(*) FROM {table.name}').fetchone()[0] == 0 for table in NOTE_TABLES)
    engine.dispose()


def test_sqlite_recovery_preserves_history_and_can_only_freeze_old_commands(store, tmp_path):
    engine, _, ids, path = store
    install(store)
    first, payload = created(store)
    restored = tmp_path / 'independent-recovery.db'
    backup_sqlite(path, restored)
    with sqlite3.connect(path) as original, sqlite3.connect(restored) as copy:
        for table in ('projects', *(item.name for item in NOTE_TABLES)):
            assert original.execute(f'SELECT * FROM {table} ORDER BY id').fetchall() == copy.execute(f'SELECT * FROM {table} ORDER BY id').fetchall()
    copied_engine = create_engine('sqlite:///' + restored.as_posix())
    configure_sqlite(copied_engine)
    factory = sessionmaker(bind=copied_engine)
    with copied_engine.begin() as db:
        db.exec_driver_sql('UPDATE project_note_versions SET execution_blocked=1 WHERE execution_blocked=0')
    with factory() as db:
        preserved = notes.read_note(db, ids[0], first['note']['id'])
        assert preserved['content'] == first['note']['content'] and preserved['sha256'] == first['note']['sha256']
        error(409, lambda: notes.create_note(db, ids[0], payload))
        db.rollback()
        result = notes.restore_note(db, ids[0], first['note']['id'], NoteRestore(command_id=command(),
            expected_revision=1, version_id=first['command_version_id']))
        db.commit()
        assert result['note']['revision'] == 2 and result['note']['content'] == first['note']['content']
    with pytest.raises(IntegrityError), copied_engine.begin() as db:
        db.exec_driver_sql('UPDATE project_note_versions SET execution_blocked=0 WHERE execution_blocked=1')
    with engine.connect() as db:
        assert db.exec_driver_sql('SELECT execution_blocked FROM project_note_versions').scalar() == 0
    copied_engine.dispose()
