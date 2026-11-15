"""Source-grounded conversion cases: no IO, no silent loss, no executable HTML."""
import json
from uuid import uuid4

import pytest

from backend.app.project_note_schemas import NoteContent, content_text
from backend.app.services.project_note_conversion import convert_tiptap


def text(value, **extra):
    return {'type': 'text', 'text': value, **extra}


def paragraph(*runs, **extra):
    return {'type': 'paragraph', 'content': list(runs), **extra}


def convert(*blocks, **kwargs):
    return convert_tiptap(json.dumps({'type': 'doc', 'content': list(blocks)}, ensure_ascii=False).encode(), **kwargs)


def test_styled_literal_text_links_linebreaks_and_empty_paragraphs():
    result = convert({'type': 'heading', 'attrs': {'level': 2}, 'content': [text('Réunion')]},
        paragraph(text('<script>contenu littéral</script>', marks=[{'type': 'bold'}, {'type': 'italic'}]),
                  {'type': 'hardBreak'}, text('Lien', marks=[{'type': 'link', 'attrs': {
                    'href': 'https://example.org', 'target': '_blank', 'rel': 'noopener noreferrer', 'class': None}}]),
                  text('Couleur', marks=[{'type': 'textStyle', 'attrs': {'color': '#112233'}}]),
                  attrs={'textAlign': 'center'}), paragraph())
    assert result['can_import_rich'] and not result['issues']
    content = NoteContent.model_validate(result['content'])
    assert content.blocks[1].align == 'center'
    assert content.blocks[1].runs[0].text == '<script>contenu littéral</script>'
    assert content.blocks[1].runs[0].marks == ['bold', 'italic']
    assert 'Réunion\n<script>contenu littéral</script>\nLienCouleur\n' == content_text(content)


def test_checklists_and_nested_list_order_kept():
    def item(label, **extra):
        return {'type': 'listItem', 'content': [paragraph(text(label))], **extra}
    result = convert({'type': 'taskList', 'content': [{'type': 'taskItem', 'attrs': {'checked': True},
                      'content': [paragraph(), paragraph(text('Fait'))]}]},
                     {'type': 'bulletList', 'content': [item('Parent', content=[paragraph(text('Parent')),
                       {'type': 'bulletList', 'content': [item('Enfant')]}]), item('Suivant')]})
    assert result['can_import_rich']
    blocks = result['content']['blocks']
    assert blocks[0]['items'][0]['checked'] is True
    assert ''.join(run['text'] for run in blocks[0]['items'][0]['runs']) == '\nFait'
    assert [row['indent'] for row in blocks[1]['items']] == [0, 1, 0]
    assert [row['runs'][0]['text'] for row in blocks[1]['items']] == ['Parent', 'Enfant', 'Suivant']


def cell(label, *, header=False, **attrs):
    return {'type': 'tableHeader' if header else 'tableCell', 'attrs': {'colspan': 1, 'rowspan': 1, 'colwidth': None, **attrs},
            'content': [paragraph(text(label))]}


def test_rectangular_table_header_and_explicit_image_binding():
    attachment = str(uuid4())
    result = convert({'type': 'table', 'content': [
        {'type': 'tableRow', 'content': [cell('Lot', header=True), cell('Date', header=True)]},
        {'type': 'tableRow', 'content': [cell('BE'), cell('Demain')]}]},
        {'type': 'image', 'attrs': {'src': 'attachments/photo.png', 'alt': 'Photo', 'title': None}},
        image_bindings={'attachments/photo.png': attachment})
    assert result['can_import_rich']
    assert result['content']['blocks'][0]['header'] is True
    assert result['content']['blocks'][1] == {'type': 'image', 'attachment_id': attachment, 'caption': 'Photo'}


@pytest.mark.parametrize('href', ['javascript:alert(1)', 'file:///V:/secret', 'https://user:pass@example.org',
                                   'data:text/html,test', 'mailto:a@example.org?subject=x'])
def test_unsafe_links_never_enter_editable_content(href):
    result = convert(paragraph(text('Texte préservé dans les originaux', marks=[{'type': 'link', 'attrs': {'href': href}}])))
    assert not result['can_import_rich'] and result['content'] is None and result['issues']


@pytest.mark.parametrize('block', [
    {'type': 'blockquote', 'content': [paragraph(text('Citation'))]},
    {'type': 'heading', 'attrs': {'level': 4}, 'content': [text('Titre')]},
    paragraph(text('Saisie'), attrs={'textAlign': 'justify'}),
    paragraph(text('Saisie', marks=[{'type': 'highlight'}])),
    paragraph(text('Saisie', marks=[{'type': 'textStyle', 'attrs': {'fontSize': '24px'}}])),
    paragraph(text('Saisie'), text='Champ inattendu'),
    {'type': 'image', 'attrs': {'src': 'https://example.org/remote.png'}},
    {'type': 'orderedList', 'attrs': {'start': 7}, 'content': [{'type': 'listItem', 'content': [paragraph(text('Sept'))]}]},
    {'type': 'table', 'content': [{'type': 'tableRow', 'content': [cell('Fusion', colspan=2)]}]},
    {'type': 'table', 'content': [{'type': 'tableRow', 'content': [cell('A'), cell('B')]},
                                 {'type': 'tableRow', 'content': [cell('C')]}]},
])
def test_nonrepresentable_blocks_reported_without_silent_import(block):
    result = convert(block)
    assert result['content'] is None and not result['can_import_rich']
    assert result['issues'] and len(result['issues']) <= 100


@pytest.mark.parametrize('source', [b'', b'not json', b'{"type":"doc","type":"doc"}', b'NaN', b'null',
                                   b'{"type":"doc","content":"wrong"}', b'\xff'])
def test_malformed_sources_reported(source):
    result = convert_tiptap(source)
    assert not result['can_import_rich'] and result['content'] is None and result['issues']


def test_oversized_deep_and_many_issue_sources_bounded():
    assert not convert_tiptap(b' ' * 2_000_001)['can_import_rich']
    value = {'type': 'listItem', 'content': [paragraph(text('Deep'))]}
    for _ in range(40):
        value = {'type': 'listItem', 'content': [paragraph(text('Deep')), {'type': 'bulletList', 'content': [value]}]}
    result = convert({'type': 'bulletList', 'content': [value]})
    assert not result['can_import_rich']
    result = convert(*[{'type': 'unknown', 'content': []} for _ in range(1000)])
    assert len(result['issues']) == 100 and result['content'] is None


def test_conversion_does_not_probe_paths_open_urls_or_change_source(monkeypatch):
    import pathlib
    source = json.dumps({'type': 'doc', 'content': [paragraph(text('Inchangé'))]}).encode()
    monkeypatch.setattr(pathlib.Path, 'open', lambda *_: pytest.fail('No file IO'))
    first = convert_tiptap(source)
    assert first == convert_tiptap(source) and first['can_import_rich']
    assert json.loads(source)['content'][0]['content'][0]['text'] == 'Inchangé'
