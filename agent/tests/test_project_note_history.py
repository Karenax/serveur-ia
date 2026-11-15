"""Typed note graph closes native/imported history and portable restore references."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

from fastapi import HTTPException
import pytest
from sqlalchemy import DateTime, select, text
from sqlalchemy.exc import IntegrityError

from app.services.deliverable_manifest import freeze
from backend.app.project_note_models import NOTE_TABLES
from backend.app.project_note_schemas import NoteSave, NoteRestore
from backend.app.services import project_notes as notes, project_note_imports as imports, project_note_files as managed
from backend.app.services import project_note_import_files as originals
from backend.app.project_note_models import NoteVersion, NoteAttachment, NoteSourceImport
from backend.app.project_note_import_schemas import NoteImportCommand
from backend.app.project_note_schemas import NoteContent
from tests import test_project_notes_core as core
from tests.test_project_note_source_preview import sources
from tests.test_project_note_imports import command

from backend.app.services import project_note_history as history
store = core.store


def tables(store):
    with store[1]() as db:
        result = {'projects': [{'id': store[2][0]}]}
        for table in NOTE_TABLES:
            result[table.name] = [{key: value.isoformat() if isinstance(value, datetime) else value
                for key, value in row.items()} for row in db.execute(select(table).where(table.c.project_id == store[2][0])).mappings()]
        return result


@pytest.fixture
def native(store):
    core.install(store)
    first, _ = core.created(store)
    with store[1]() as db:
        notes.save_note(db, store[2][0], first['note']['id'], NoteSave(command_id=core.command(),
            expected_revision=1, title='Changement', content=core.rich()))
        notes.restore_note(db, store[2][0], first['note']['id'], NoteRestore(command_id=core.command(),
            expected_revision=2, version_id=first['note']['version_id']))
        db.commit()
    return tables(store)


@pytest.fixture
def imported(store, tmp_path, monkeypatch):
    core.install(store)
    root = tmp_path / 'managed-typed'
    root.mkdir()
    monkeypatch.setattr(managed, 'APP_DIR', root)
    files = sources()
    payload = command(files)
    with store[1]() as db:
        result = imports.import_selected(db, store[2][0], payload, acquire=lambda _: files)
        db.commit()
        notes.save_note(db, store[2][0], result['note']['id'], NoteSave(command_id=core.command(),
            expected_revision=2, title='Nouveau compte rendu', attachment_ids=result['note']['attachment_ids']))
        notes.restore_note(db, store[2][0], result['note']['id'], NoteRestore(command_id=core.command(),
            expected_revision=3, version_id=result['source_versions'][0]['note_version_id']))
        db.commit()
    return tables(store)


def section(value):
    return history.section_for(value)


def test_native_note_complete_graph_and_pure_validation_has_no_db_or_path_calls(native, monkeypatch):
    original = deepcopy(native)
    monkeypatch.setattr(Path, 'open', lambda *args, **kwargs: pytest.fail('No filesystem in graph contract'))
    monkeypatch.setattr(Path, 'resolve', lambda *args, **kwargs: pytest.fail('No path resolution in graph contract'))
    report = history.validate(native, section(native))
    assert len(report['heads']) == 1 and len(report['versions']) == 3
    assert native == original


def test_imported_source_versions_and_original_provenance_are_closed(imported):
    report = history.validate(imported, section(imported))
    assert len(report['versions']) == 4 and len(report['imports']) == 1 and len(report['assets']) == 1
    capture = next(iter(report['captures'].values()))
    assert capture.actor_id == 'local' and capture.versions[0].source_actor is None
    assert capture.versions[-1].source_actor == 'Original editor'


@pytest.mark.parametrize('change', ['head_revision', 'head_version', 'missing_version', 'orphan_version',
    'actor', 'snapshot_hash', 'command_hash', 'duplicate_command', 'extra_field', 'bool_revision',
    'bool_freeze', 'native_id_collision', 'missing_table', 'restore_missing', 'restore_foreign',
    'restore_future', 'restore_different_content'])
def test_graph_refuses_incomplete_or_reinterpreted_history(native, change):
    value = deepcopy(native)
    head = value['project_notes'][0]
    versions = value['project_note_versions']
    versions.sort(key=lambda item: item['revision'])
    if change == 'head_revision':
        head['revision'] = 2
    elif change == 'head_version':
        head['current_version_id'] = versions[0]['id']
    elif change == 'missing_version':
        value['project_note_versions'] = versions[1:]
    elif change == 'orphan_version':
        versions[0]['note_id'] = core.command()
    elif change == 'actor':
        versions[0]['actor_id'] = 'forged'
    elif change == 'snapshot_hash':
        versions[0]['snapshot'] += ' '
    elif change == 'command_hash':
        versions[0]['command_sha256'] = '0' * 64
    elif change == 'duplicate_command':
        versions[1]['command_id'] = versions[0]['command_id']
    elif change == 'extra_field':
        head['foreign_key'] = 'secret'
    elif change == 'bool_revision':
        head['revision'] = True
    elif change == 'bool_freeze':
        versions[0]['execution_blocked'] = 0
    elif change == 'native_id_collision':
        value['projects'][0]['id'] = head['id']
        for name in history.PROJECT_TABLES:
            for row in value[name]:
                row['project_id'] = head['id']
    elif change == 'missing_table':
        del value['project_note_imports']
    elif change == 'restore_missing':
        versions[-1]['restored_version_id'] = None
    elif change == 'restore_foreign':
        versions[-1]['restored_version_id'] = core.command()
    elif change == 'restore_future':
        versions[-1]['restored_version_id'] = versions[-1]['id']
    else:
        versions[-1]['restored_version_id'] = versions[1]['id']
    with pytest.raises((ValueError, TypeError)):
        section(value)


@pytest.mark.parametrize('change', ['missing_asset', 'asset_scope', 'asset_sha', 'missing_source_version',
    'version_binding', 'source_actor', 'source_receipt', 'source_note', 'source_nonce', 'source_piece_metadata'])
def test_source_graph_requires_exact_linked_versions_and_original_assets(imported, change):
    value = deepcopy(imported)
    row = value['project_note_imports'][0]
    capture = json.loads(row['snapshot'])
    if change == 'missing_asset':
        value['project_note_attachments'] = []
    elif change == 'asset_scope':
        value['project_note_attachments'][0]['note_id'] = core.command()
    elif change == 'asset_sha':
        value['project_note_attachments'][0]['sha256'] = 'a' * 64
    elif change == 'missing_source_version':
        value['project_note_versions'] = value['project_note_versions'][1:]
    elif change == 'version_binding':
        first = capture['versions'][0]['note_version_id']
        row['version_bindings'][first] = core.command()
    elif change == 'source_actor':
        row['actor_id'] = 'forged'
    elif change == 'source_receipt':
        row['command_sha256'] = 'a' * 64
    elif change == 'source_note':
        row['note_id'] = core.command()
    elif change == 'source_nonce':
        row['command_id'] = value['project_note_versions'][0]['command_id']
    else:
        capture['attachments'][0]['filename'] = 'different-name.txt'
        row['snapshot'], row['snapshot_sha256'] = freeze(capture)
    with pytest.raises((ValueError, TypeError)):
        section(value)


def test_transport_rebinds_current_graph_retains_all_captures_and_freezes_receipts(imported):
    old = deepcopy(imported)
    mapping = {row['id']: core.command() for rows in imported.values() for row in rows}
    moved = {'projects': [{'id': mapping[imported['projects'][0]['id']]}], **history.remap_rows(imported, mapping)}
    report = history.validate(moved, section(moved))
    assert len(report['versions']) == 4 and len(report['imports']) == 1
    for name in history.PROJECT_TABLES:
        for before, after in zip(old[name], moved[name], strict=True):
            for key in ('snapshot', 'sha256', 'snapshot_sha256', 'command_id', 'command_sha256', 'actor_id', 'created_at'):
                if key in before:
                    assert after[key] == before[key]
            if 'execution_blocked' in after:
                assert after['execution_blocked']
            if 'storage_id' in after:
                assert after['storage_id'] != before['storage_id']
    restore = next(item for item in moved['project_note_versions'] if item['revision'] == 4)
    capture = json.loads(restore['snapshot'])
    assert restore['restored_version_id'] == mapping[capture['restored_from']]
    assert capture['restored_from'] != restore['restored_version_id']
    assert imported == old


def test_second_transport_keeps_first_restore_capture_and_rebinds_current_target_again(native):
    first_mapping = {row['id']: core.command() for rows in native.values() for row in rows}
    first = {'projects': [{'id': first_mapping[native['projects'][0]['id']]}], **history.remap_rows(native, first_mapping)}
    second_mapping = {row['id']: core.command() for rows in first.values() for row in rows}
    second = {'projects': [{'id': second_mapping[first['projects'][0]['id']]}], **history.remap_rows(first, second_mapping)}
    assert len(history.validate(second, section(second))['versions']) == 3
    old_restore = next(item for item in native['project_note_versions'] if item['revision'] == 3)
    new_restore = next(item for item in second['project_note_versions'] if item['revision'] == 3)
    assert new_restore['snapshot'] == old_restore['snapshot']
    assert new_restore['restored_version_id'] == second_mapping[first_mapping[old_restore['restored_version_id']]]


def test_legacy_native_view_cannot_silently_validate_or_consume_note_tables(native):
    assert not history.PROJECT_TABLES & history.native_view(native).keys()
    assert history.native_view(native) == {'projects': native['projects']}
    for declared in ({}, {'format': 'agent-project-notes', 'version': True},
                     {'format': 'agent-project-notes', 'version': 1, 'extra': []}):
        with pytest.raises(ValueError):
            history.validate(native, declared)


def test_office_graph_cannot_gain_editable_future_versions(store, tmp_path, monkeypatch):
    core.install(store)
    root = tmp_path / 'office-typed'
    root.mkdir()
    monkeypatch.setattr(managed, 'APP_DIR', root)
    files = {'Source.docx': b'Opaque preserved original'}
    payload = command(files)
    with store[1]() as db:
        result = imports.import_selected(db, store[2][0], payload, acquire=lambda _: files)
        db.commit()
        with pytest.raises(HTTPException):
            notes.save_note(db, store[2][0], result['note']['id'], NoteSave(command_id=core.command(), expected_revision=1, title='Modified'))
    value = tables(store)
    assert len(history.validate(value, section(value))['versions']) == 1


def test_actual_sqlite_rebound_import_preserves_originals_and_can_restore_with_current_ids(store, tmp_path, monkeypatch):
    core.install(store)
    root = tmp_path / 'rebound-files'
    root.mkdir()
    monkeypatch.setattr(managed, 'APP_DIR', root)
    source_files = sources()
    payload = command(source_files)
    with store[1]() as db:
        first = imports.import_selected(db, store[2][0], payload, acquire=lambda _: source_files)
        notes.restore_note(db, store[2][0], first['note']['id'], NoteRestore(command_id=core.command(),
            expected_revision=2, version_id=first['source_versions'][0]['note_version_id']))
        db.commit()
    original = tables(store)
    mapping = {row['id']: core.command() for rows in original.values() for row in rows}
    mapping[store[2][0]] = store[2][1]
    moved = history.remap_rows(original, mapping)
    by_name = {table.name: table for table in NOTE_TABLES}
    with store[1]() as db:
        for before, after in zip(original['project_note_attachments'], moved['project_note_attachments'], strict=True):
            data, _ = managed.download(db, store[2][0], before['note_id'], before['id'])
            originals.write_attachment(after['storage_id'], data)
        for before, after in zip(original['project_note_imports'], moved['project_note_imports'], strict=True):
            row = db.get(NoteSourceImport, before['id'])
            data, _ = originals.read_originals(row, imports._capture(row))
            originals.write_originals(after['storage_id'], data)
        # First real versions/attachments before the final head; deferred FKs
        # close at commit, and the restore trigger sees its prior version.
        for name in ('project_note_attachments', 'project_note_versions', 'project_notes', 'project_note_imports'):
            rows = sorted(moved[name], key=lambda row: row.get('revision', 0))
            for raw in rows:
                value = deepcopy(raw)
                for column in by_name[name].c:
                    if isinstance(column.type, DateTime) and value.get(column.name):
                        value[column.name] = datetime.fromisoformat(value[column.name])
                db.execute(by_name[name].insert().values(**value))
        db.commit()
        assert not db.execute(text('PRAGMA foreign_key_check')).all()
        note_id = mapping[first['note']['id']]
        read = imports.read_import(db, store[2][1], note_id)
        assert read['note']['revision'] == 3 and read['note']['plain_text'] == 'Ancien'
        assert read['import_id'] != first['import_id']
        assert imports.original_file(db, store[2][1], note_id, 'content.html')[0] == source_files['content.html']
        for raw in original['project_note_versions']:
            current = db.get(NoteVersion, mapping[raw['id']])
            assert (current.snapshot, current.sha256, current.command_id, current.actor_id) == (
                raw['snapshot'], raw['sha256'], raw['command_id'], raw['actor_id'])
        restored = notes.restore_note(db, store[2][1], note_id, NoteRestore(command_id=core.command(),
            expected_revision=3, version_id=mapping[first['source_versions'][-1]['note_version_id']]))
        db.commit()
        assert restored['note']['revision'] == 4 and restored['note']['plain_text'] == 'Actuel'
        current = notes.read_version(db, store[2][1], note_id, restored['command_version_id'])
        assert current['restored_version_id'] == mapping[first['source_versions'][-1]['note_version_id']]
        assert current['value']['restored_from'] == current['restored_version_id']
        core.error(409, lambda: imports.import_selected(db, store[2][1], payload,
            acquire=lambda _: pytest.fail('Historical nonce must never reacquire network')))
        assert len(db.scalars(select(NoteAttachment)).all()) == 2


def test_current_restore_reference_is_immutable_in_sql(store):
    core.install(store)
    first, _ = core.created(store)
    with store[1]() as db:
        result = notes.restore_note(db, store[2][0], first['note']['id'], NoteRestore(command_id=core.command(),
            expected_revision=1, version_id=first['note']['version_id']))
        db.commit()
        row = db.get(NoteVersion, result['command_version_id'])
        assert row.restored_version_id == first['note']['version_id']
        with pytest.raises(IntegrityError):
            db.execute(text('UPDATE project_note_versions SET restored_version_id=NULL WHERE id=:id'), {'id': row.id})
        db.rollback()
        assert db.get(NoteVersion, row.id).restored_version_id == first['note']['version_id']


def test_boolean_content_version_is_rejected_and_closed_import_command_stays_strict():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        NoteContent.model_validate({'version': True, 'blocks': []})
    with pytest.raises(ValidationError):
        NoteImportCommand.model_validate({'command_id': core.command(), 'planned_note_id': core.command(),
            'expected_preview_sha256': 'a' * 64, 'actor_id': 'forged'})
