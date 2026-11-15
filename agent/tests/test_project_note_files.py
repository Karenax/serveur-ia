"""Actual attachment files on fictional stores, integrity and transaction recovery."""
from io import BytesIO
from pathlib import Path

from PIL import Image
import pytest
from sqlalchemy import select

from backend.app.project_note_models import NoteAttachment
from backend.app.services import project_note_files as files
from backend.app.services.project_operator import Operator, operator_context
from tests import test_project_notes_core as core

store = core.store


@pytest.fixture
def attachments(store, tmp_path, monkeypatch):
    core.install(store)
    first, _ = core.created(store)
    monkeypatch.setattr(files, 'APP_DIR', tmp_path)
    return store, first['note']['id'], tmp_path


def upload(attachments, *, data=b'Compte rendu', filename='compte rendu.txt', command_id=None):
    store, note_id, _ = attachments
    _, factory, ids, _ = store
    with factory() as db:
        result = files.upload(db, ids[0], note_id, command_id=command_id or core.command(),
                              filename=filename, stream=BytesIO(data))
        db.commit()
        return result


def test_actual_copy_committed_retry_and_verified_read(attachments):
    store, note_id, root = attachments
    _, factory, ids, _ = store
    command_id = core.command()
    first = upload(attachments, command_id=command_id)
    blobs = list(root.glob('note-files/*/blob'))
    assert len(blobs) == 1 and blobs[0].read_bytes() == b'Compte rendu'
    replay = upload(attachments, command_id=command_id)
    assert replay['replayed'] and replay['attachment'] == first['attachment']
    assert list(root.glob('note-files/*/blob')) == blobs
    with factory() as db:
        data, metadata = files.download(db, ids[0], note_id, first['attachment']['id'])
        assert data == b'Compte rendu' and metadata['filename'] == 'compte rendu.txt'
        assert files.listing(db, ids[0], note_id)['items'] == [metadata]
        assert not db.dirty and not db.new
    core.error(409, lambda: upload(attachments, command_id=command_id, data=b'Changed'))
    with operator_context(Operator('another-editor', 'editor')):
        core.error(409, lambda: upload(attachments, command_id=command_id))
    assert len(list(root.glob('note-files/*/blob'))) == 1


def test_rollback_retains_orphan_and_retry_creates_one_committed_attachment(attachments):
    store, note_id, root = attachments
    _, factory, ids, _ = store
    command_id = core.command()
    with factory() as db:
        result = files.upload(db, ids[0], note_id, command_id=command_id, filename='note.txt', stream=BytesIO(b'Keep'))
        db.rollback()
        assert db.get(NoteAttachment, result['attachment']['id']) is None
    assert len(list(root.glob('note-files/*/blob'))) == 1
    upload(attachments, command_id=command_id, filename='note.txt', data=b'Keep')
    assert len(list(root.glob('note-files/*/blob'))) == 2
    with factory() as db:
        assert len(db.scalars(select(NoteAttachment)).all()) == 1


@pytest.mark.parametrize('filename', ['../note.txt', 'CON.txt', 'mail:secret', 'note.txt ', 'x\\y.txt'])
def test_filename_refused_before_any_output(attachments, filename):
    core.error(422, lambda: upload(attachments, filename=filename))
    assert not (attachments[2] / 'note-files').exists()


def test_foreign_note_and_reader_refused_before_input_read_or_file_probe(attachments, monkeypatch):
    store, note_id, _ = attachments
    _, factory, ids, _ = store
    class NeverRead:
        def read(self, *_):
            pytest.fail('No attachment content read before authorization')
    monkeypatch.setattr(Path, 'resolve', lambda *_: pytest.fail('No file probe before authorization'))
    with factory() as db:
        core.error(404, lambda: files.upload(db, ids[1], note_id, command_id=core.command(),
                    filename='note.txt', stream=NeverRead()))
        with operator_context(Operator('reader', 'reader')):
            core.error(403, lambda: files.upload(db, ids[0], note_id, command_id=core.command(),
                        filename='note.txt', stream=NeverRead()))
        core.error(404, lambda: files.download(db, ids[1], note_id, core.command()))


def test_empty_oversized_and_quota_refused_without_new_blob(attachments):
    core.error(422, lambda: upload(attachments, data=b''))
    core.error(413, lambda: upload(attachments, data=b'x' * (files.MAX_BYTES + 1)))
    assert not (attachments[2] / 'note-files').exists()
    for index in range(20):
        upload(attachments, data=str(index).encode())
    core.error(413, lambda: upload(attachments))
    assert len(list(attachments[2].glob('note-files/*/blob'))) == 20


def test_corrupt_and_missing_blobs_refuse_read_and_ack_without_overwrite(attachments):
    store, note_id, root = attachments
    _, factory, ids, _ = store
    command_id = core.command()
    item = upload(attachments, command_id=command_id)['attachment']
    blob = next(root.glob('note-files/*/blob'))
    blob.write_bytes(b'Corruption')
    with factory() as db:
        core.error(409, lambda: files.download(db, ids[0], note_id, item['id']))
    core.error(409, lambda: upload(attachments, command_id=command_id))
    assert blob.read_bytes() == b'Corruption'
    # Simulate a missing file by pointing the immutable record at a fresh root.
    files_root = files.APP_DIR
    files.APP_DIR = root / 'unavailable'
    try:
        with factory() as db:
            core.error(409, lambda: files.download(db, ids[0], note_id, item['id']))
    finally:
        files.APP_DIR = files_root


def test_decoded_static_images_only_and_office_stays_download(attachments):
    store, note_id, _ = attachments
    _, factory, ids, _ = store
    image_bytes = BytesIO()
    Image.new('RGB', (8, 8), 'red').save(image_bytes, format='PNG')
    image = upload(attachments, filename='photo.png', data=image_bytes.getvalue())['attachment']
    core.error(422, lambda: upload(attachments, filename='false.png', data=b'<svg onload="alert(1)"/>'))
    core.error(422, lambda: upload(attachments, filename='wrong.jpg', data=image_bytes.getvalue()))
    office = upload(attachments, filename='external.docx', data=b'Office download only')['attachment']
    svg = upload(attachments, filename='download.svg', data=b'<svg/>')['attachment']
    assert svg['content_type'] == 'application/octet-stream'
    with factory() as db:
        assert files.download(db, ids[0], note_id, image['id'], inline=True)[0] == image_bytes.getvalue()
        core.error(422, lambda: files.download(db, ids[0], note_id, office['id'], inline=True))
        core.error(422, lambda: files.download(db, ids[0], note_id, svg['id'], inline=True))


def test_failed_file_copy_records_no_attachment_and_preserves_originals(attachments, monkeypatch):
    store, _, root = attachments
    _, factory, _, _ = store
    original = upload(attachments)['attachment']
    blobs = {path: path.read_bytes() for path in root.glob('note-files/*/blob')}
    monkeypatch.setattr(files.os, 'fsync', lambda *_: (_ for _ in ()).throw(OSError('disk unavailable')))
    core.error(409, lambda: upload(attachments))
    with factory() as db:
        assert [row.id for row in db.scalars(select(NoteAttachment))] == [original['id']]
    assert all(path.read_bytes() == data for path, data in blobs.items())
