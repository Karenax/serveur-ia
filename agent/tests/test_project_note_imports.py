"""Actual import/copy/rollback/retry, immutable source semantics and isolation."""
from copy import deepcopy
import base64
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException
from PIL import Image
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.project_note_models import ProjectNote, NoteVersion, NoteAttachment, NoteSourceImport
from backend.app.project_note_import_schemas import NoteImportCommand
from backend.app.project_note_schemas import NoteContent, NoteCreate, NoteSave, NoteRestore
from backend.app.services import project_notes as notes, project_note_imports as imports
from backend.app.services import project_note_files as files, project_note_import_files as storage
from backend.app.services.project_note_source_preview import preview_source
from backend.app.services.project_note_source_bundle import verify_bundle
from backend.app.services.project_operator import Operator, operator_context
from tests import test_project_notes_core as core
from tests.test_project_note_source_preview import sources, KEY

store = core.store


@pytest.fixture
def ready(store, tmp_path, monkeypatch):
    core.install(store)
    root = tmp_path / 'managed'
    root.mkdir()
    monkeypatch.setattr(files, 'APP_DIR', root)
    return store, root


def command(source_files):
    note_id = core.command()
    preview = preview_source(source_files, planned_note_id=note_id)
    return NoteImportCommand(command_id=core.command(), planned_note_id=note_id,
                             expected_preview_sha256=preview['preview_sha256'])


def apply(ready, source_files=None, payload=None):
    source_files = sources() if source_files is None else source_files
    payload = payload or command(source_files)
    store, _ = ready
    with store[1]() as db:
        result = imports.import_selected(db, store[2][0], payload, acquire=lambda _: source_files)
        db.commit()
    return result, payload


def test_originals_history_first_real_version_and_lost_response_replay_before_acquisition(ready):
    store, root = ready
    source_files = sources()
    before = deepcopy(source_files)
    first, payload = apply(ready, source_files)
    assert first['note']['revision'] == 2 and first['note']['plain_text'] == 'Actuel'
    assert first['source_metadata']['updated_by'] == 'Original editor'
    assert [item['source_actor'] for item in first['source_versions']] == [None, 'Original editor']
    paths = {path: path.read_bytes() for path in root.rglob('*') if path.is_file()}
    with store[1]() as db:
        replay = imports.import_selected(db, store[2][0], payload, acquire=lambda _: pytest.fail('No network retry'))
        db.commit()
        assert replay['replayed'] and replay['import_id'] == first['import_id']
        versions = db.scalars(select(NoteVersion).order_by(NoteVersion.revision)).all()
        assert len(versions) == 2 and all(item.execution_blocked for item in versions)
        assert notes._value(versions[0])['plain_text'] == 'Ancien'
        assert {item.actor_id for item in versions} == {'local'}
        row = db.get(NoteSourceImport, first['import_id'])
        capture = imports._capture(row)
        bundle = storage._path(row.storage_id).read_bytes()
        assert verify_bundle(bundle, capture.files) == before
        for name, expected in before.items():
            data, metadata = imports.original_file(db, store[2][0], first['note']['id'], name)
            assert data == expected and metadata['relative_path'] == name
        assert len(db.scalars(select(ProjectNote)).all()) == 1
    assert source_files == before and paths == {path: path.read_bytes() for path in root.rglob('*') if path.is_file()}


def test_import_command_actor_and_payload_cannot_change_on_retry(ready):
    store, _ = ready
    _, payload = apply(ready)
    changed = payload.model_copy(update={'mode': 'plain'})
    with store[1]() as db:
        core.error(409, lambda: imports.import_selected(db, store[2][0], changed, acquire=lambda _: pytest.fail('No retry read')))
        with operator_context(Operator('other', 'owner')):
            core.error(409, lambda: imports.import_selected(db, store[2][0], payload, acquire=lambda _: pytest.fail('No actor retry read')))


@pytest.mark.parametrize('actor, code', [('reader', 403), ('outside', 404)])
def test_scope_and_permissions_before_source_or_managed_io(ready, actor, code, monkeypatch):
    store, _ = ready
    payload = command(sources())
    operator = Operator('reader', 'reader') if actor == 'reader' else Operator('outside', 'owner', frozenset())
    monkeypatch.setattr(Path, 'open', lambda *args, **kwargs: pytest.fail('Unauthorized file access'))
    with store[1]() as db, operator_context(operator):
        core.error(code, lambda: imports.import_selected(db, store[2][0], payload, acquire=lambda _: pytest.fail('No acquisition')))


def test_sources_changed_after_preview_no_file_or_sql_creation(ready):
    store, root = ready
    source_files = sources()
    payload = command(source_files)
    source_files['content.html'] = b'<p>Changed after preview</p>'
    with store[1]() as db:
        core.error(422, lambda: imports.import_selected(db, store[2][0], payload, acquire=lambda _: source_files))
        db.rollback()
        assert not db.scalars(select(ProjectNote)).all() and not db.scalars(select(NoteAttachment)).all()
    assert not list(root.iterdir())


def test_sql_rollback_retains_copies_retry_does_not_adopt_or_overwrite_orphans(ready):
    store, root = ready
    source_files = sources()
    payload = command(source_files)
    with store[1]() as db:
        imports.import_selected(db, store[2][0], payload, acquire=lambda _: source_files)
        db.rollback()
        assert db.scalar(select(ProjectNote.id)) is None
    orphans = {path: path.read_bytes() for path in root.rglob('*') if path.is_file()}
    assert len(orphans) == 2
    first, _ = apply(ready, source_files, payload)
    assert first['note']['revision'] == 2
    assert len([path for path in root.rglob('*') if path.is_file()]) == 4
    assert all(path.read_bytes() == data for path, data in orphans.items())


def test_copy_failure_retains_original_but_creates_no_note(ready, monkeypatch):
    store, root = ready
    source_files = sources()
    payload = command(source_files)
    def failure(*args):
        raise HTTPException(409, 'Disk full')
    monkeypatch.setattr(storage, 'write_attachment', failure)
    with store[1]() as db:
        core.error(409, lambda: imports.import_selected(db, store[2][0], payload, acquire=lambda _: source_files))
        db.rollback()
        for model in (ProjectNote, NoteVersion, NoteAttachment, NoteSourceImport):
            assert db.scalar(select(model.id)) is None
    assert len(list(root.rglob('blob.zip'))) == 1


@pytest.mark.parametrize('target', ['original', 'attachment'])
def test_missing_or_tampered_managed_copy_blocks_replay_without_reacquiring(ready, target):
    store, root = ready
    _, payload = apply(ready)
    path = next(root.rglob('blob.zip' if target == 'original' else 'blob'))
    path.write_bytes(b'Tampered')
    with store[1]() as db:
        core.error(409, lambda: imports.import_selected(db, store[2][0], payload, acquire=lambda _: pytest.fail('No source retry')))
        assert len(db.scalars(select(NoteVersion)).all()) == 2


def test_first_version_with_inline_image_and_checklist_keeps_all_exact_source_bytes(ready):
    store, _ = ready
    stream = BytesIO()
    Image.new('RGB', (2, 2), '#336699').save(stream, format='PNG')
    image_data = stream.getvalue()
    encoded = base64.b64encode(image_data).decode('ascii')
    html = ('<p><s>Décision</s></p><img src="data:image/png;base64,' + encoded + '" alt="plan">'
            '<ul class="note-task-list"><li><input type="checkbox" checked><span>Validé</span></li></ul>').encode('utf-8')
    source_files = {'réunion.html': html}
    result, _ = apply(ready, source_files)
    assert result['note']['revision'] == 1
    blocks = result['note']['content']['blocks']
    assert blocks[0]['runs'][0]['marks'] == ['strike'] and blocks[-1]['items'][0]['checked']
    image_id = next(block['attachment_id'] for block in blocks if block['type'] == 'image')
    with store[1]() as db:
        data, _ = files.download(db, store[2][0], result['note']['id'], image_id, inline=True)
        assert data == image_data
        original, _ = imports.original_file(db, store[2][0], result['note']['id'], 'réunion.html')
        assert original == html and len(db.scalars(select(NoteVersion)).all()) == 1


def test_office_source_is_read_only_at_service_and_sql_and_remains_original_download(ready):
    store, _ = ready
    result, _ = apply(ready, {'Compte-rendu.docx': b'Explicit opaque Office original'})
    note_id = result['note']['id']
    assert result['note']['read_only'] and result['source_kind'] == 'external_office'
    with store[1]() as db:
        core.error(409, lambda: notes.save_note(db, store[2][0], note_id, NoteSave(
            command_id=core.command(), expected_revision=1, title='Overwrite Office')))
        core.error(409, lambda: notes.restore_note(db, store[2][0], note_id, NoteRestore(
            command_id=core.command(), expected_revision=1, version_id=result['note']['version_id'])))
        db.rollback()
        payload = NoteSave(command_id=core.command(), expected_revision=1, title='Bypass', content=NoteContent())
        with pytest.raises(IntegrityError):
            notes._append(db, store[2][0], note_id, title=payload.title, content=payload.content, attachment_ids=[],
                revision=2, command_id=payload.command_id, command_digest=notes._command_digest(store[2][0], note_id, 'save', payload, 'local'),
                actor='local', operation='save', head=notes._head(db, store[2][0], note_id))
        db.rollback()
        data, _ = imports.original_file(db, store[2][0], note_id, 'Compte-rendu.docx')
        assert data == b'Explicit opaque Office original'


def test_explicit_plain_fallback_preserves_unsupported_original_html(ready):
    store, _ = ready
    source_files = {'note.html': b'<article><p>Retained text</p></article>'}
    note_id = core.command()
    preview = preview_source(source_files, planned_note_id=note_id, mode='plain')
    payload = NoteImportCommand(command_id=core.command(), planned_note_id=note_id,
        expected_preview_sha256=preview['preview_sha256'], mode='plain')
    result, _ = apply(ready, source_files, payload)
    assert result['note']['plain_text'] == 'Retained text'
    with store[1]() as db:
        data, _ = imports.original_file(db, store[2][0], note_id, 'note.html')
        assert data == source_files['note.html']


def test_edit_imported_note_keeps_source_versions_and_originals_unchanged(ready):
    store, _ = ready
    first, payload = apply(ready)
    with store[1]() as db:
        notes.save_note(db, store[2][0], first['note']['id'], NoteSave(command_id=core.command(),
            expected_revision=2, title='After import', content=core.rich(), attachment_ids=first['note']['attachment_ids']))
        db.commit()
        replay = imports.import_selected(db, store[2][0], payload, acquire=lambda _: pytest.fail('No acquisition after edit'))
        assert replay['note']['revision'] == 3 and len(replay['source_versions']) == 2
        assert imports.original_file(db, store[2][0], first['note']['id'], 'content.txt')[0] == b'Actuel'
        core.error(409, lambda: notes.create_note(db, store[2][0], NoteCreate(command_id=payload.command_id, title='Collision')))


def test_foreign_project_originals_and_unknown_source_path_refused(ready, monkeypatch):
    store, _ = ready
    first, _ = apply(ready)
    with store[1]() as db:
        core.error(404, lambda: imports.original_file(db, store[2][0], first['note']['id'], '../secret'))
        monkeypatch.setattr(storage, 'read_originals', lambda *args: pytest.fail('No cross-project file read'))
        core.error(404, lambda: imports.original_file(db, store[2][1], first['note']['id'], 'content.txt'))


def test_capture_semantics_checked_against_originals_not_just_declared_sha(ready):
    store, _ = ready
    first, _ = apply(ready)
    with store[1]() as db:
        row = db.get(NoteSourceImport, first['import_id'])
        capture = imports._capture(row)
        _, original = storage.read_originals(row, capture)
        changed = capture.model_copy(deep=True)
        changed.versions[-1].source_actor = 'Forged actor'
        with pytest.raises(ValueError, match='Version convertie'):
            imports.validate_source_capture(changed, original)
        changed = capture.model_copy(deep=True)
        changed.versions[0].content_sha256 = '0' * 64
        with pytest.raises(ValueError, match='Version convertie'):
            imports.validate_source_capture(changed, original)
        assert capture.versions[0].source_key == KEY
