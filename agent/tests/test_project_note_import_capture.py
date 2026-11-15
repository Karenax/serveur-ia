"""Actual immutable provenance rows and deferred graph insertion, no runtime activation."""
import hashlib
import json

import pytest
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.services.deliverable_manifest import freeze
from backend.app.project_note_import_schemas import NoteImportCapture, NoteImportCommand
from backend.app.project_note_models import NoteSourceImport, NoteAttachment, NoteVersion
from backend.app.project_note_schemas import NoteCreate, NoteContent, NoteSave
from backend.app.services import project_notes as notes
from backend.app.services.project_note_source_preview import preview_source
from backend.app.services.project_note_source_bundle import prepare_bundle
from backend.app.services.project_note_imports import command_digest
from tests import test_project_notes_core as core
from tests.test_project_note_source_preview import sources

store = core.store


def captured(store):
    core.install(store)
    _, _, ids, _ = store
    note_id = core.command()
    source_files = sources()
    preview = preview_source(source_files, planned_note_id=note_id)
    with store[1]() as db:
        payload = NoteCreate(command_id=core.command(), title='Réunion',
                            content=NoteContent.model_validate(preview['versions'][0]['content']))
        first = notes._append(db, ids[0], note_id, title=payload.title, content=payload.content,
                       attachment_ids=[], revision=1, command_id=payload.command_id,
                       command_digest=notes._command_digest(ids[0], None, 'create', payload, 'local'),
                       actor='local', operation='create')
        current = notes.save_note(db, ids[0], note_id, NoteSave(command_id=core.command(), expected_revision=1,
                       title='Réunion', content=NoteContent.model_validate(preview['versions'][-1]['content'])))
        db.commit()
    bundle, origin = prepare_bundle(source_files, planned_note_id=note_id, expected_preview_sha256=preview['preview_sha256'])
    command = NoteImportCommand(command_id=core.command(), planned_note_id=note_id,
                               expected_preview_sha256=preview['preview_sha256'])
    capture = NoteImportCapture(id=core.command(), project_id=ids[0], note_id=note_id,
        actor_id='local', command_id=command.command_id, command=command, source_kind='xpilot_note',
        bundle_sha256=origin['sha256'], bundle_size_bytes=len(bundle), source_sha256=preview['source_sha256'],
        source_metadata=preview['source_metadata'], files=preview['files'],
        versions=[{'source_key': preview['versions'][0]['source_key'], 'source_actor': None,
                   'note_version_id': first['command_version_id'], 'content_sha256': freeze(first['note']['content'])[1],
                   'conversion_mode': 'html'},
                  {'source_key': 'current', 'source_actor': 'Original editor', 'note_version_id': current['command_version_id'],
                   'content_sha256': freeze(current['note']['content'])[1], 'conversion_mode': 'html'}],
        attachments=[{'id': core.command(), 'filename': 'preuve.txt', 'content_type': 'text/plain',
                      'size_bytes': len(source_files['attachments/preuve.txt']),
                      'sha256': hashlib.sha256(source_files['attachments/preuve.txt']).hexdigest(),
                      'source_path': 'attachments/preuve.txt'}])
    snapshot, sha = freeze(capture.model_dump(mode='json'))
    with store[1]() as db:
        item = capture.attachments[0]
        db.add(NoteAttachment(id=item.id, project_id=ids[0], note_id=note_id, storage_id=core.command(),
               filename=item.filename, content_type=item.content_type, size_bytes=item.size_bytes,
               sha256=item.sha256, command_id=core.command(), actor_id='local'))
        db.commit()
    return NoteSourceImport(id=capture.id, project_id=ids[0], note_id=note_id,
        actor_id='local', command_id=command.command_id, command_sha256=command_digest(ids[0], command, 'local'),
        source_kind='xpilot_note', snapshot=snapshot, snapshot_sha256=sha, storage_id=core.command(),
        sha256=hashlib.sha256(bundle).hexdigest(), size_bytes=len(bundle),
        version_bindings={item.note_version_id: item.note_version_id for item in capture.versions},
        attachment_bindings={item.id: item.id for item in capture.attachments}), capture


def test_capture_keeps_original_actor_descriptive_not_operator_and_closed_command(store):
    row, capture = captured(store)
    assert capture.actor_id == 'local' and capture.versions[-1].source_actor == 'Original editor'
    assert capture.source_metadata['updated_by'] == 'Original editor'
    for extra in ({'actor_id': 'forged'}, {'role': 'owner'}, {'absolute_path': 'V:/secret'}):
        with pytest.raises(ValidationError):
            NoteImportCommand.model_validate({**capture.command.model_dump(mode='json'), **extra})
    with pytest.raises(ValidationError):
        NoteImportCapture.model_validate({**capture.model_dump(mode='json'), 'version': True})
    assert row.snapshot_sha256 == freeze(capture.model_dump(mode='json'))[1]


@pytest.mark.parametrize('change', ['missing_version', 'missing_attachment', 'invented_author', 'duplicate_attachment'])
def test_capture_requires_complete_original_history_and_attachment_links(store, change):
    _, capture = captured(store)
    value = capture.model_dump(mode='json')
    if change == 'missing_version':
        value['versions'] = value['versions'][-1:]
    elif change == 'missing_attachment':
        value['attachments'] = []
    elif change == 'invented_author':
        value['versions'][0]['source_actor'] = 'Invented author'
    else:
        value['attachments'].append({**value['attachments'][0], 'id': core.command()})
    with pytest.raises(ValidationError):
        NoteImportCapture.model_validate(value)


@pytest.mark.parametrize('sql', ["UPDATE project_note_imports SET actor_id='forged'",
    "UPDATE project_note_imports SET snapshot='{}'", 'DELETE FROM project_note_imports'])
def test_import_receipt_and_original_metadata_cannot_be_changed_or_deleted(store, sql):
    row, _ = captured(store)
    _, factory, _, _ = store
    with factory() as db:
        db.add(row)
        db.commit()
        with pytest.raises(IntegrityError):
            db.execute(text(sql))
            db.commit()
        db.rollback()
        assert db.get(NoteSourceImport, row.id).snapshot == row.snapshot


def test_import_execution_can_only_freeze_without_changing_capture_or_bindings(store):
    row, _ = captured(store)
    _, factory, _, _ = store
    with factory() as db:
        db.add(row)
        db.commit()
        snapshot = row.snapshot
        db.execute(text('UPDATE project_note_imports SET execution_blocked=1 WHERE execution_blocked=0'))
        db.commit()
        with pytest.raises(IntegrityError):
            db.execute(text('UPDATE project_note_imports SET execution_blocked=0'))
        db.rollback()
        assert db.get(NoteSourceImport, row.id).snapshot == snapshot


def test_inconsistent_boolean_version_capture_refused_before_row_insert(store):
    row, _ = captured(store)
    _, factory, _, _ = store
    value = json.loads(row.snapshot)
    value['version'] = True
    row.snapshot, row.snapshot_sha256 = freeze(value)
    with factory() as db, pytest.raises(IntegrityError):
        db.add(row)
        db.commit()
    with factory() as db:
        assert db.scalar(select(NoteSourceImport.id)) is None


def test_deferred_attachment_can_precede_first_real_note_version_without_empty_seed(store):
    core.install(store)
    _, factory, ids, _ = store
    note_id, attachment_id = core.command(), core.command()
    content = NoteContent.model_validate({'blocks': [{'type': 'image', 'attachment_id': attachment_id}]})
    payload = NoteCreate(command_id=core.command(), title='Première capture avec image', content=content)
    with factory() as db:
        db.add(NoteAttachment(id=attachment_id, project_id=ids[0], note_id=note_id, storage_id=core.command(),
               filename='image.png', content_type='image/png', size_bytes=123, sha256='a' * 64,
               command_id=core.command(), actor_id='local'))
        db.flush()
        digest = notes._command_digest(ids[0], None, 'create', payload, 'local')
        result = notes._append(db, ids[0], note_id, title=payload.title, content=content, attachment_ids=[attachment_id],
               revision=1, command_id=payload.command_id, command_digest=digest, actor='local', operation='create')
        db.commit()
        assert result['note']['revision'] == 1 and result['note']['content']['blocks'][0]['attachment_id'] == attachment_id
        assert len(db.scalars(select(NoteVersion)).all()) == 1


def test_orphan_deferred_attachment_still_refused_at_commit(store):
    core.install(store)
    _, factory, ids, _ = store
    with factory() as db, pytest.raises(IntegrityError):
        db.add(NoteAttachment(id=core.command(), project_id=ids[0], note_id=core.command(), storage_id=core.command(),
               filename='image.png', content_type='image/png', size_bytes=123, sha256='a' * 64,
               command_id=core.command(), actor_id='local'))
        db.flush()
        db.commit()
