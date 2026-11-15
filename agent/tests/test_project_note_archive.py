"""Actual managed blobs and retained sources must close the portable graph."""
import base64
from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image
import pytest

from app.services.deliverable_manifest import freeze
from backend.app.project_note_schemas import NoteCreate
from backend.app.services import project_note_archive as archive, project_note_history as history
from backend.app.services import project_note_imports as imports
from backend.app.services import project_note_files as managed
from backend.app.services.project_note_binary import content_type
from tests import test_project_notes_core as core
from tests.test_project_note_history import tables
from tests.test_project_note_imports import command
from tests.test_project_note_source_preview import sources

store = core.store


def envelopes(tables, root):
    result = []
    for area, table in archive.AREAS.items():
        for row in tables[table]:
            name = archive.storage_name(area, row)
            folder = 'note-files' if area == 'note-file' else 'note-originals'
            data = (root / folder / name).read_bytes()
            entry = {'owner': row['id'], 'area': area, 'name': name, 'sha256': row['sha256'],
                     'data': base64.b64encode(data).decode('ascii')}
            result.append((entry, data, hashlib.sha256(data).hexdigest()))
    return result


@pytest.fixture
def imported(store, tmp_path, monkeypatch):
    core.install(store)
    root = tmp_path / 'archive-note-store'
    root.mkdir()
    monkeypatch.setattr(managed, 'APP_DIR', root)
    files = sources()
    with store[1]() as db:
        imports.import_selected(db, store[2][0], command(files), acquire=lambda _: files)
        db.commit()
    value = tables(store)
    return value, envelopes(value, root)


def checked(value, files):
    return archive.validate_files(value, archive.section_for(value), files)


def test_all_originals_and_managed_pieces_are_verified_without_runtime_io(imported, monkeypatch):
    value, files = imported
    before = deepcopy((value, files))
    monkeypatch.setattr(Path, 'open', lambda *args, **kwargs: pytest.fail('No path IO in transport validation'))
    monkeypatch.setattr(Path, 'resolve', lambda *args, **kwargs: pytest.fail('No runtime paths'))
    ledger = checked(value, files)
    assert len(ledger['versions']) == 2 and len(ledger['assets']) == 1
    assert before == (value, files)


@pytest.mark.parametrize('change', ['missing_piece', 'missing_original', 'extra_owner', 'duplicate',
    'wrong_name', 'wrong_digest', 'changed_bytes', 'wrong_size', 'extra_field', 'wrong_mime', 'unknown_area'])
def test_binary_closure_refuses_partial_or_modified_archive(imported, change):
    value, files = deepcopy(imported)
    piece = next(item for item in files if item[0]['area'] == 'note-file')
    original = next(item for item in files if item[0]['area'] == 'note-original')
    if change == 'missing_piece':
        files.remove(piece)
    elif change == 'missing_original':
        files.remove(original)
    elif change == 'extra_owner':
        piece[0]['owner'] = core.command()
    elif change == 'duplicate':
        files.append(piece)
    elif change == 'wrong_name':
        piece[0]['name'] = '../blob'
    elif change == 'wrong_digest':
        piece[0]['sha256'] = 'a' * 64
    elif change == 'changed_bytes':
        files[files.index(piece)] = (piece[0], b'Changed attachment!', piece[2])
    elif change == 'wrong_size':
        value['project_note_attachments'][0]['size_bytes'] += 1
    elif change == 'extra_field':
        piece[0]['server_path'] = 'C:/other-file'
    elif change == 'wrong_mime':
        value['project_note_attachments'][0]['content_type'] = 'image/png'
    else:
        piece[0]['area'] = 'note-other'
    with pytest.raises(ValueError):
        checked(value, files)


def test_original_container_with_good_outer_hash_still_requires_its_internal_inventory(imported):
    value, files = deepcopy(imported)
    index = next(i for i, item in enumerate(files) if item[0]['area'] == 'note-original')
    entry, _, _ = files[index]
    data = b'Not a ZIP container'
    sha = hashlib.sha256(data).hexdigest()
    row = value['project_note_imports'][0]
    capture = json.loads(row['snapshot'])
    capture.update(bundle_sha256=sha, bundle_size_bytes=len(data))
    row.update(sha256=sha, size_bytes=len(data))
    row['snapshot'], row['snapshot_sha256'] = freeze(capture)
    entry.update(sha256=sha, data=base64.b64encode(data).decode('ascii'))
    files[index] = entry, data, sha
    with pytest.raises(ValueError, match='Conteneur'):
        checked(value, files)


def test_import_title_cannot_be_reinterpreted_even_with_recomputed_version_hashes(imported):
    value, files = deepcopy(imported)
    for row in value['project_note_versions']:
        snapshot = json.loads(row['snapshot'])
        snapshot['title'] = 'Forged source title'
        row['snapshot'], row['sha256'] = freeze(snapshot)
        content = snapshot['content']
        if snapshot['operation'] == 'create':
            payload = NoteCreate(command_id=row['command_id'], title=snapshot['title'], content=content)
            note_id = None
        else:
            from backend.app.project_note_schemas import NoteSave
            payload = NoteSave(command_id=row['command_id'], title=snapshot['title'], content=content,
                               expected_revision=row['revision'] - 1, attachment_ids=snapshot['attachment_ids'])
            note_id = row['note_id']
        row['command_sha256'] = history.command_digest(snapshot['project_id'], note_id,
            snapshot['operation'], payload, snapshot['actor_id'])
    value['project_notes'][0]['title'] = 'Forged source title'
    with pytest.raises(ValueError, match='Titre'):
        checked(value, files)


def test_rebound_portable_ids_validate_immutable_original_bytes(imported):
    value, files = deepcopy(imported)
    mapping = {value['projects'][0]['id']: core.command()}
    mapping.update({row['id']: core.command() for name in history.PROJECT_TABLES for row in value[name]})
    moved = archive.remap_rows(value, mapping)
    target = {'projects': [{'id': mapping[value['projects'][0]['id']]}], **moved}
    for entry, data, sha in files:
        entry['owner'] = mapping[entry['owner']]
        row = next(row for row in moved[archive.AREAS[entry['area']]] if row['id'] == entry['owner'])
        entry['name'] = archive.storage_name(entry['area'], row)
    assert len(checked(target, files)['imports']) == 1


def test_fresh_note_keeps_unreferenced_attachment_in_archive(store, tmp_path, monkeypatch):
    core.install(store)
    root = tmp_path / 'native-attachments'
    root.mkdir()
    monkeypatch.setattr(managed, 'APP_DIR', root)
    created, _ = core.created(store)
    with store[1]() as db:
        managed.upload(db, store[2][0], created['note']['id'], command_id=core.command(),
            filename='Unlinked.txt', stream=BytesIO(b'Preserve even before save'))
        db.commit()
    value = tables(store)
    files = envelopes(value, root)
    assert len(checked(value, files)['assets']) == 1
    with pytest.raises(ValueError, match='absent'):
        checked(value, [])


def test_shared_binary_type_uses_actual_image_bytes_and_static_frame_limits():
    output = BytesIO()
    Image.new('RGB', (4, 4), 'red').save(output, format='PNG')
    assert content_type('photo.png', output.getvalue()) == 'image/png'
    with pytest.raises(ValueError):
        content_type('photo.jpg', output.getvalue())
    with pytest.raises(ValueError):
        content_type('photo.png', b'<svg/>')
    assert content_type('macro.xlsm', b'Opaque source') == 'application/octet-stream'


def test_native_piece_cannot_claim_jpeg_with_valid_png_hash(store, tmp_path, monkeypatch):
    core.install(store)
    root = tmp_path / 'native-image'
    root.mkdir()
    monkeypatch.setattr(managed, 'APP_DIR', root)
    created, _ = core.created(store)
    output = BytesIO()
    Image.new('RGB', (4, 4), 'blue').save(output, format='PNG')
    with store[1]() as db:
        managed.upload(db, store[2][0], created['note']['id'], command_id=core.command(),
            filename='photo.png', stream=BytesIO(output.getvalue()))
        db.commit()
    value = tables(store)
    files = envelopes(value, root)
    value['project_note_attachments'][0].update(filename='photo.jpg', content_type='image/jpeg')
    with pytest.raises(ValueError, match='Image'):
        checked(value, files)


def test_contract_import_is_independent_of_runtime_and_sqlalchemy(tmp_path):
    import subprocess
    import sys
    code = '''
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == 'sqlalchemy' or name.startswith('sqlalchemy.') or name in {
        'app.db', 'app.config', 'backend.app.db', 'backend.app.models'}:
        raise RuntimeError('Runtime import: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from backend.app.services.project_note_archive import validate_files
'''
    result = subprocess.run([sys.executable, '-c', code], cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
