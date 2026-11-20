"""Actual immutable bytes: complete original history and poisoned containers."""
from copy import deepcopy
from io import BytesIO
import hashlib
from uuid import uuid4
import zipfile

import pytest

from backend.app.project_note_schemas import NOTE_ATTACHMENT_BUDGET
from backend.app.services.project_note_source_bundle import prepare_bundle, verify_bundle
from backend.app.services.project_note_source_preview import preview_source
from tests.test_project_note_source_preview import sources


def prepare(files=None, *, mode='rich'):
    files = sources() if files is None else files
    planned = str(uuid4())
    preview = preview_source(files, planned_note_id=planned, mode=mode)
    return prepare_bundle(files, planned_note_id=planned, mode=mode, expected_preview_sha256=preview['preview_sha256'])


def zipped(files, *, compression=zipfile.ZIP_STORED):
    output = BytesIO()
    with zipfile.ZipFile(output, 'w', compression=compression) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


def test_originals_preserved_exactly_with_immutable_descriptive_history():
    files = sources()
    before = deepcopy(files)
    data, manifest = prepare(files)
    assert files == before and verify_bundle(data, manifest['files']) == before
    assert manifest['sha256'] == hashlib.sha256(data).hexdigest()
    assert manifest['source_versions'][0]['source_actor'] is None
    assert manifest['source_versions'][1]['source_actor'] == 'Original editor'
    assert manifest['original_bytes_exact']
    assert 'actor_id' not in manifest and 'role' not in manifest


def test_deterministic_bundle_and_changed_preview_refused():
    files = sources()
    planned = str(uuid4())
    preview = preview_source(files, planned_note_id=planned)
    args = {'planned_note_id': planned, 'expected_preview_sha256': preview['preview_sha256']}
    first = prepare_bundle(files, **args)
    assert first == prepare_bundle(dict(reversed(list(files.items()))), **args)
    with pytest.raises(ValueError, match='modifiées'):
        prepare_bundle({**files, 'attachments/preuve.txt': b'Changed'}, **args)
    with pytest.raises(ValueError, match='modifiées'):
        prepare_bundle(files, **{**args, 'mode': 'plain'})


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'different', 'compressed'])
def test_poisoned_bundle_refused_before_returning_any_source(mutation):
    files = sources()
    _, manifest = prepare(files)
    if mutation == 'missing':
        del files['content.html']
    elif mutation == 'extra':
        files['../outside.txt'] = b'Secret'
    elif mutation == 'different':
        files['content.txt'] = b'Altered'
    data = zipped(files, compression=zipfile.ZIP_DEFLATED if mutation == 'compressed' else zipfile.ZIP_STORED)
    with pytest.raises(ValueError):
        verify_bundle(data, manifest['files'])


def test_duplicate_zip_entry_and_bad_original_inventory_refused():
    files = sources()
    data, manifest = prepare(files)
    output = BytesIO(data)
    with zipfile.ZipFile(output, 'a') as archive, pytest.warns(UserWarning, match='Duplicate'):
        archive.writestr('content.txt', b'Actuel')
    with pytest.raises(ValueError, match='incomplet'):
        verify_bundle(output.getvalue(), manifest['files'])
    inventory = deepcopy(manifest['files'])
    inventory[0]['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='Octets source'):
        verify_bundle(data, inventory)
    inventory[0]['relative_path'] = '../outside.txt'
    with pytest.raises(ValueError):
        verify_bundle(data, inventory)


def test_office_original_bytes_preserved_without_conversion_or_execution():
    files = {'external.xls': b'Raw Office original'}
    data, manifest = prepare(files)
    assert verify_bundle(data, manifest['files']) == files
    assert manifest['source_kind'] == 'external_office' and manifest['source_versions'] == []


def test_forged_inventory_cannot_expand_source_limits():
    data, manifest = prepare()
    inventory = deepcopy(manifest['files'])
    next(row for row in inventory if row['relative_path'] == 'content.json')['size_bytes'] = 2_000_001
    with pytest.raises(ValueError, match='2 Mo'):
        verify_bundle(data, inventory)
    inventory = deepcopy(manifest['files'])
    next(row for row in inventory if row['kind'] == 'attachment')['size_bytes'] = NOTE_ATTACHMENT_BUDGET + 1
    with pytest.raises(ValueError, match='limites'):
        verify_bundle(data, inventory)


def test_bundle_verification_does_not_extract_to_any_file(monkeypatch):
    data, manifest = prepare()
    monkeypatch.setattr(zipfile.ZipFile, 'extract', lambda *_: pytest.fail('No extraction'))
    monkeypatch.setattr(zipfile.ZipFile, 'extractall', lambda *_: pytest.fail('No extraction'))
    assert verify_bundle(data, manifest['files']) == sources()


def test_legacy_html_source_kept_as_original_with_derived_rich_content():
    files = {'ancienne.html': b'<p><b>Original</b></p>'}
    data, manifest = prepare(files)
    assert verify_bundle(data, manifest['files']) == files
    assert manifest['source_kind'] == 'legacy_text_note'
