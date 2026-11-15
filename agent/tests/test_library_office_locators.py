"""Word extraction retains the document part without inventing printed pages."""
from zipfile import ZipFile

from app.services.library_extraction import extract


def test_docx_text_and_struck_reservation_have_an_actual_document_part(tmp_path):
    original = tmp_path/'notice.docx'
    xml = '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
    <w:p><w:r><w:t>Alimentation : 230 V. Ne pas valider.</w:t></w:r></w:p>
    <w:p><w:r><w:rPr><w:strike/></w:rPr><w:t>Ancienne puissance 2250 W</w:t></w:r></w:p>
    <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Puissance actuelle 1250 W</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
    </w:body></w:document>'''
    with ZipFile(original, 'w') as archive:
        archive.writestr('word/document.xml', xml)
    before = original.read_bytes()
    passages = extract(original, 'notice.docx')
    assert len(passages) == 1 and passages[0]['status'] == 'extracted'
    assert '230 V. Ne pas valider.' in passages[0]['text']
    assert '[BARRE] Ancienne puissance 2250 W' in passages[0]['text']
    assert 'Puissance actuelle 1250 W' in passages[0]['text']
    assert passages[0]['locator']['document_part'] == 1
    assert passages[0]['locator']['printed_page'] is None and 'physical_page' not in passages[0]['locator']
    assert original.read_bytes() == before
