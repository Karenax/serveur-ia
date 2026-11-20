"""Complete selected-source inventories, explicit fallback and historical actors."""
from copy import deepcopy
import hashlib
import json
from uuid import uuid4

import pytest

from backend.app.project_note_schemas import NOTE_ATTACHMENT_BUDGET, NoteContent, content_text
from backend.app.services.project_note_source_preview import preview_source

KEY = '20261007T101112123456Z'


def encoded(value):
    return json.dumps(value, ensure_ascii=False).encode('utf-8')


def content(value):
    return encoded({'type': 'doc', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': value}]}]})


def sources():
    return {'manifest.json': encoded({'type': 'xpilot_tiptap_note', 'title': 'Réunion', 'version': 2,
            'created_by': 'Original creator', 'updated_by': 'Original editor', 'updated_at': '2026-10-07T11:00:00Z'}),
            'content.json': content('Actuel'), 'content.txt': b'Actuel', 'content.html': b'<p>Actuel</p>',
            f'versions/{KEY}/content.json': content('Ancien'), f'versions/{KEY}/content.txt': b'Ancien',
            f'versions/{KEY}/content.html': b'<p>Ancien</p>', 'attachments/preuve.txt': b'Original attachment'}


def test_complete_original_byte_inventory_order_and_no_forged_historical_actor():
    files = sources()
    before = deepcopy(files)
    planned = str(uuid4())
    result = preview_source(files, planned_note_id=planned)
    assert result == preview_source(dict(reversed(list(files.items()))), planned_note_id=planned)
    assert files == before and result['can_apply'] and result['originals_must_be_copied']
    assert [row['source_key'] for row in result['versions']] == [KEY, 'current']
    assert result['versions'][0]['source_actor'] is None
    assert result['versions'][1]['source_actor'] == 'Original editor'
    assert len(result['files']) == len(files) and result['total_bytes'] == sum(map(len, files.values()))
    for row in result['files']:
        assert row['sha256'] == hashlib.sha256(files[row['relative_path']]).hexdigest()
        assert row['size_bytes'] == len(files[row['relative_path']])
    assert content_text(NoteContent.model_validate(result['versions'][0]['content'])) == 'Ancien'
    assert 'actor_id' not in result and 'role' not in result


def test_decision_digest_changes_with_bytes_selection_mode_and_target_note():
    files = sources()
    planned = str(uuid4())
    initial = preview_source(files, planned_note_id=planned)
    changed = preview_source({**files, 'attachments/preuve.txt': b'Changed'}, planned_note_id=planned)
    assert initial['source_sha256'] != changed['source_sha256']
    assert initial['preview_sha256'] != changed['preview_sha256']
    another = preview_source(files, planned_note_id=str(uuid4()))
    plain = preview_source(files, planned_note_id=planned, mode='plain')
    assert another['source_sha256'] == plain['source_sha256'] == initial['source_sha256']
    assert len({another['preview_sha256'], plain['preview_sha256'], initial['preview_sha256']}) == 3


def test_unsupported_old_version_blocks_whole_import_and_plain_is_explicit():
    files = sources()
    files[f'versions/{KEY}/content.json'] = encoded({'type': 'doc', 'content': [{'type': 'unknown'}]})
    files[f'versions/{KEY}/content.html'] = b'<unknown>Ancien</unknown>'
    planned = str(uuid4())
    result = preview_source(files, planned_note_id=planned)
    assert not result['can_apply'] and result['versions'][0]['content'] is None
    fallback = preview_source(files, planned_note_id=planned, mode='plain')
    assert fallback['can_apply'] and fallback['conversion_mode'] == 'plain'
    assert fallback['versions'][0]['styles_preserved'] is False
    assert len(fallback['files']) == len(files)  # Originals retained despite derived fallback.


def test_missing_json_does_not_execute_html_or_silently_choose_plain():
    files = sources()
    del files['content.json']
    files['content.html'] = b'<script>dangerous()</script><p>Original</p>'
    planned = str(uuid4())
    result = preview_source(files, planned_note_id=planned)
    assert not result['can_apply']
    fallback = preview_source(files, planned_note_id=planned, mode='plain')
    assert fallback['can_apply']
    assert fallback['versions'][-1]['content']['blocks'][0]['runs'][0]['text'] == 'Actuel'
    assert any(row['relative_path'] == 'content.html' for row in fallback['files'])


def test_actual_xpilot_html_save_uses_current_html_instead_of_stale_generated_json():
    files = sources()
    files['content.json'] = content('Ancien JSON non mis à jour')
    planned = str(uuid4())
    result = preview_source(files, planned_note_id=planned)
    assert result['can_apply']
    assert result['versions'][-1]['conversion_mode'] == 'html'
    assert result['versions'][-1]['source_json_kept_as_original']
    assert content_text(NoteContent.model_validate(result['versions'][-1]['content'])) == 'Actuel'
    fallback = preview_source(files, planned_note_id=planned, mode='plain')
    assert fallback['can_apply']
    assert content_text(NoteContent.model_validate(fallback['versions'][-1]['content'])) == 'Actuel'
    assert len(fallback['files']) == len(files)


def test_embedded_html_image_preview_is_json_safe_and_bound_to_preserved_source():
    from tests.test_project_note_html import raster_uri
    uri, data = raster_uri()
    files = sources()
    files['content.html'] = f'<p>Actuel<img src="{uri}" alt="preuve.png"></p>'.encode()
    result = preview_source(files, planned_note_id=str(uuid4()))
    assert result['can_apply'] and len(result['embedded_images']) == 1
    assert result['embedded_images'][0]['sha256'] == hashlib.sha256(data).hexdigest()
    assert result['versions'][-1]['content']['blocks'][1]['attachment_id'] == result['embedded_images'][0]['id']
    json.dumps(result)  # Binary bytes are internal acquisition results, never a JSON response.


@pytest.mark.parametrize('path', ['../secret.txt', 'attachments/../../secret.txt', 'V:/secret',
                                  '/absolute', 'attachments\\secret.txt', 'attachments/CON.txt',
                                  'versions/invalid/content.json', 'somebodyelse/manifest.json'])
def test_foreign_or_unsafe_selected_paths_refused(path):
    with pytest.raises(ValueError):
        preview_source({**sources(), path: b'Secret'}, planned_note_id=str(uuid4()))


def test_case_collision_and_incomplete_history_refused_before_conversion():
    with pytest.raises(ValueError, match='casse'):
        preview_source({**sources(), 'attachments/PREUVE.TXT': b'Other'}, planned_note_id=str(uuid4()))
    files = sources()
    files['manifest.json'] = encoded({'type': 'xpilot_tiptap_note', 'title': 'Gap', 'version': 4})
    with pytest.raises(ValueError, match='incomplet'):
        preview_source(files, planned_note_id=str(uuid4()))


def test_office_external_never_edited_or_parsed_and_kept_outside_attachment_quota():
    data = b'Original external Office bytes' + b'x' * (6 * 1024 * 1024)
    result = preview_source({'compte rendu.docx': data}, planned_note_id=str(uuid4()))
    assert result['kind'] == 'external_office' and result['read_only'] and not result['editable']
    assert result['versions'] == [] and result['can_apply']
    assert result['files'][0]['sha256'] == hashlib.sha256(data).hexdigest()


def test_attachments_empty_oversized_and_complete_import_limits():
    planned = str(uuid4())
    with pytest.raises(ValueError, match='Pièces source'):
        preview_source({**sources(), 'attachments/empty.txt': b''}, planned_note_id=planned)
    with pytest.raises(ValueError, match='Pièces source'):
        preview_source({**sources(), 'attachments/large.txt': b'x' * (NOTE_ATTACHMENT_BUDGET + 1)}, planned_note_id=planned)
    accepted = preview_source({**sources(), 'attachments/large.txt': b'x' * (6 * 1024 * 1024)}, planned_note_id=planned)
    assert any(file['relative_path'] == 'attachments/large.txt' and file['size_bytes'] == 6 * 1024 * 1024
               for file in accepted['files'])
    with pytest.raises(ValueError, match='50 Mio'):
        preview_source({'large.doc': b'x' * (50 * 1024 * 1024 + 1)}, planned_note_id=planned)
    with pytest.raises(ValueError, match='200 fichiers'):
        preview_source({f'attachments/{index}.txt': b'x' for index in range(201)}, planned_note_id=planned)


def test_invalid_or_duplicate_manifest_and_boolean_revision_refused():
    for source in (b'null', b'{"type":"xpilot_tiptap_note","type":"forged"}',
                   encoded({'type': 'xpilot_tiptap_note', 'title': 'Bad', 'version': True})):
        with pytest.raises(ValueError):
            preview_source({**sources(), 'manifest.json': source}, planned_note_id=str(uuid4()))


def test_preview_has_no_file_or_network_operations(monkeypatch):
    from pathlib import Path
    files = sources()
    monkeypatch.setattr(Path, 'open', lambda *_: pytest.fail('No IO in source preview'))
    assert preview_source(files, planned_note_id=str(uuid4()))['can_apply']


@pytest.mark.parametrize('name,data', [('ancienne.html', b'<p><b>Historique</b></p>'),
                                      ('notes.txt', b'Texte brut'), ('notes.md', b'# Texte Markdown literal')])
def test_legacy_files_have_own_preview_and_preserve_originals(name, data):
    result = preview_source({name: data}, planned_note_id=str(uuid4()))
    assert result['kind'] == 'legacy_text_note' and result['can_apply']
    assert result['versions'][0]['source_actor'] is None
    assert result['files'][0]['sha256'] == hashlib.sha256(data).hexdigest()
    assert result['originals_must_be_copied']
    if name.endswith('.html'):
        assert result['versions'][0]['content']['blocks'][0]['runs'][0]['marks'] == ['bold']
    else:
        assert content_text(NoteContent.model_validate(result['versions'][0]['content'])) == data.decode()


def test_html_without_text_companion_can_use_explicit_plain_fallback():
    planned = str(uuid4())
    result = preview_source({'ancienne.html': b'<unknown>Original</unknown><script>active()</script>'},
                            planned_note_id=planned)
    assert not result['can_apply']
    fallback = preview_source({'ancienne.html': b'<unknown>Original</unknown><script>active()</script>'},
                              planned_note_id=planned, mode='plain')
    assert fallback['can_apply']
    assert content_text(NoteContent.model_validate(fallback['versions'][0]['content'])) == 'Original'


def test_image_quota_counts_all_distinct_historical_assets_before_apply():
    from PIL import Image
    from io import BytesIO
    import base64
    images = []
    for index in range(21):
        stream = BytesIO()
        Image.new('RGB', (2, 2), (index, 0, 0)).save(stream, format='PNG')
        images.append('<img src="data:image/png;base64,' + base64.b64encode(stream.getvalue()).decode() + '">')
    result = preview_source({'ancienne.html': (''.join(images)).encode()}, planned_note_id=str(uuid4()))
    assert not result['can_apply'] and result['issues']
    assert len(result['embedded_images']) == 21  # Report all; never truncate to satisfy quota.
    assert result['files'][0]['size_bytes'] == len((''.join(images)).encode())
