"""Actual XPilot HTML examples, closed conversion and verified dataURI images."""
import base64
from io import BytesIO
import json
from uuid import uuid4

from PIL import Image
import pytest

from backend.app.project_note_schemas import NoteContent, content_text
from backend.app.services.project_note_html import convert_html, html_plain_text


def convert(html, **kwargs):
    return convert_html(html.encode('utf-8'), planned_note_id=kwargs.pop('planned_note_id', str(uuid4())), **kwargs)


def raster_uri(format='PNG'):
    data = BytesIO()
    Image.new('RGB', (5, 5), 'blue').save(data, format=format)
    mime = {'PNG': 'image/png', 'JPEG': 'image/jpeg'}[format]
    return 'data:' + mime + ';base64,' + base64.b64encode(data.getvalue()).decode(), data.getvalue()


def test_html_styles_current_editor_not_stale_plain_json():
    result = convert('<h2>Réunion</h2><p><b>Fort</b> <i>Italique</i> <u>Souligné</u> <s>Barré</s> '
                     '<span style="color:rgb(17, 34, 51)">Couleur</span><br>'
                     '<a href="https://example.org" target="_blank" rel="noopener">Lien</a></p>')
    assert result['can_import_rich'], result['issues']
    content = NoteContent.model_validate(result['content'])
    assert content.blocks[0].level == 2
    runs = content.blocks[1].runs
    assert next(run for run in runs if run.text == 'Barré').marks == ['strike']
    assert next(run for run in runs if run.text == 'Couleur').color == '#112233'
    assert next(run for run in runs if run.text == 'Lien').href == 'https://example.org'
    assert 'Réunion\nFort Italique Souligné Barré Couleur\nLien' == content_text(content)


def test_real_xpilot_checklist_table_and_empty_browser_paragraphs():
    result = convert('<ul class="note-task-list"><li><input type="checkbox" checked '
                     'aria-label="Marquer cet élément comme terminé"> <span>Fait</span></li>'
                     '<li><input type="checkbox">Encore</li></ul><p><br></p>'
                     '<table><thead><tr><th>Titre</th><th>Date</th></tr></thead><tbody>'
                     '<tr><td><br></td><td>Demain</td></tr></tbody></table>')
    assert result['can_import_rich'], result['issues']
    blocks = result['content']['blocks']
    assert blocks[0]['kind'] == 'checklist'
    assert [item['checked'] for item in blocks[0]['items']] == [True, False]
    assert blocks[2]['header'] is True
    assert blocks[2]['rows'][1][1][0]['text'] == 'Demain'


def test_embedded_images_verified_deduplicated_and_scoped_with_surrounding_text():
    uri, data = raster_uri()
    note_id = str(uuid4())
    html = f'<p>Avant<img src="{uri}" alt="image.png">Après</p><p><img src="{uri}"></p>'
    first = convert(html, planned_note_id=note_id)
    assert first['can_import_rich'], first['issues']
    assert first == convert(html, planned_note_id=note_id)
    assert len(first['embedded_assets']) == 1
    image_id, image = next(iter(first['embedded_assets'].items()))
    assert image['data'] == data and image['content_type'] == 'image/png'
    assert [block['type'] for block in first['content']['blocks']] == ['paragraph', 'image', 'paragraph', 'image']
    assert first['content']['blocks'][1]['attachment_id'] == image_id
    assert first['content']['blocks'][3]['attachment_id'] == image_id
    assert image_id not in convert(html, planned_note_id=str(uuid4()))['embedded_assets']


@pytest.mark.parametrize('html', [
    '<p onclick="run()">Active</p>', '<script>run()</script>', '<style>body{display:none}</style>',
    '<iframe src="https://example.org"></iframe>', '<p><a href="javascript:run()">Lien</a></p>',
    '<img src="https://example.org/remote.png">', '<img src="file:///V:/private.png">',
    '<img src="data:image/svg+xml;base64,PHN2Zy8+">', '<p style="background-image:url(x)">CSS</p>',
    '<table><tr><td colspan="2">Fusion</td></tr></table>', '<p><b>Non fermé</p>',
    '<p title="one" title="two">Ambigu</p>',
])
def test_active_external_unknown_and_lossy_content_refused(html):
    result = convert(html)
    assert not result['can_import_rich'] and result['content'] is None and result['issues']


def test_forged_mime_and_bad_base64_not_accepted_as_managed_images():
    uri, _ = raster_uri('JPEG')
    result = convert(f'<img src="{uri.replace("image/jpeg", "image/png")}">')
    assert not result['can_import_rich'] and not result['embedded_assets']
    result = convert('<img src="data:image/png;base64,====">')
    assert not result['can_import_rich'] and not result['embedded_assets']


def test_explicit_attachment_binding_and_no_io_or_url_fetch(monkeypatch):
    from pathlib import Path
    import urllib.request
    monkeypatch.setattr(Path, 'open', lambda *_: pytest.fail('No file IO'))
    monkeypatch.setattr(urllib.request, 'urlopen', lambda *_: pytest.fail('No URL acquisition'))
    image_id = str(uuid4())
    result = convert('<p><img src="attachments/photo.png" alt="Photo"></p>',
                     image_bindings={'attachments/photo.png': image_id})
    assert result['can_import_rich'] and not result['embedded_assets']
    assert result['content']['blocks'][0]['attachment_id'] == image_id
    json.dumps(result['content'])  # No HTML or binary content in the editable value.


def test_nested_lists_align_and_font_color_preserved():
    result = convert('<div><p style="text-align:center"><font color="#abc">Couleur</font></p>'
                     '<ul><li>Parent<ul><li>Enfant</li></ul></li><li>Suite</li></ul></div>')
    assert result['can_import_rich'], result['issues']
    assert result['content']['blocks'][0]['align'] == 'center'
    assert result['content']['blocks'][0]['runs'][0]['color'] == '#aabbcc'
    assert [item['indent'] for item in result['content']['blocks'][1]['items']] == [0, 1, 0]


def test_oversized_and_deep_html_reports_instead_of_executing():
    result = convert('<div>' * 40 + 'Trop profond' + '</div>' * 40)
    assert not result['can_import_rich']


def test_explicit_plain_fallback_never_includes_active_code_or_image_uri():
    result = html_plain_text(b'<p>Texte <b>visible</b></p><script>run()</script><style>danger</style>'
                             b'<p>Suite<img src="data:image/png;base64,invalid"></p>')
    assert 'visible' in result and 'Suite' in result
    assert 'run()' not in result and 'danger' not in result and 'base64' not in result


def test_repeated_large_raster_is_not_decoded_for_each_html_reference(monkeypatch):
    uri, _ = raster_uri()
    original = Image.open
    calls = []
    def counted(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(Image, 'open', counted)
    result = convert(f'<p><img src="{uri}"><img src="{uri}"><img src="{uri}"></p>')
    assert result['can_import_rich'] and len(result['embedded_assets']) == 1
    assert len(calls) == 2  # Verify plus decode, once for the shared asset.
