"""Fictional Office packages: bounded preview and copy, no network/Office writes."""
from copy import deepcopy
import hashlib
from io import BytesIO
import json
import struct
import warnings
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
import zipfile

import pytest

from backend.app.services import document_package_preview as preview
from backend.app.services.document_package_prepare import prepare_package
from backend.app.services.document_template_catalogue import CATALOGUE, DOCUMENT_IDS, catalogue, document_spec, validate_catalogue


def package(parts, *, duplicate=None):
    output = BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.comment = b'Fictional Agent test package'
        for name, content in parts.items():
            item = zipfile.ZipInfo(name, date_time=(2025, 6, 18, 12, 10, 2))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            item.comment = b'entry annotation'
            archive.writestr(item, content)
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                archive.writestr(duplicate, b'duplicate')
    result = output.getvalue()
    # ZipInfo normalizes native backslashes on Windows; exercise raw ZIP names.
    for name in parts:
        if '\\' in name:
            result = result.replace(name.replace('\\', '/').encode(), name.encode())
    return result


def parts_for(document_id, *, sheet_name=None, body=None, prefix='', extra=None):
    spec = document_spec(document_id)
    spreadsheet = spec['format'] in {'XLSX', 'XLSM'}
    main = '/xl/workbook.xml' if spreadsheet else '/word/document.xml'
    parts = {'[Content_Types].xml': f'<Types xmlns="{preview.CT}"><Override PartName="{main}" '
             f'ContentType="{preview.CONTENT_TYPES[spec["format"]]}"/></Types>',
             'docProps/custom.xml': b'<unchanged>client metadata</unchanged>',
             'customXml/opaque.bin': b'\x00\x01Do not interpret, execute or change\xff'}
    if spreadsheet:
        name = sheet_name if sheet_name is not None else spec['sheet_name'] or 'Accueil'
        parts['xl/workbook.xml'] = f'<workbook xmlns="{preview.S}" xmlns:r="{preview.R}"><sheets>' \
            f'<sheet name="{escape(name)}" sheetId="1" r:id="rId1"/></sheets></workbook>'
        parts['xl/_rels/workbook.xml.rels'] = f'<Relationships xmlns="{preview.P}"><Relationship Id="rId1" ' \
            f'Type="{preview.R}/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
        parts['xl/worksheets/sheet1.xml'] = (f'<{prefix}worksheet xmlns="{preview.S}"'
            + (f' xmlns:x="{preview.S}"' if prefix else '')
            + ' xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"'
              ' xmlns:xr="http://schemas.microsoft.com/office/spreadsheetml/2014/revision" mc:Ignorable="xr">'
            + (body if body is not None else f'<{prefix}sheetData/>') + f'</{prefix}worksheet>')
        parts['xl/styles.xml'] = b'<opaque-style>keep exact</opaque-style>'
    else:
        bookmarks = ''.join(f'<w:p><w:bookmarkStart w:id="{index}" w:name="{escape(target)}"/>'
            '<w:r><w:rPr><w:b/></w:rPr><w:t>Old </w:t></w:r><w:r><w:t>value</w:t></w:r>'
            f'<w:bookmarkEnd w:id="{index}"/></w:p>' for index, (target, _) in enumerate(spec['bookmarks']))
        parts['word/document.xml'] = f'<w:document xmlns:w="{preview.W}" xmlns:keep="urn:keep">' \
            '<w:body><!--retain this comment-->' + (body if body is not None else bookmarks) + '</w:body></w:document>'
        parts['word/styles.xml'] = b'<opaque-style>keep exact</opaque-style>'
    if spec['format'] in {'XLSM', 'DOCM'}:
        parts['xl/vbaProject.bin' if spreadsheet else 'word/vbaProject.bin'] = b'Fictional inert VBA payload\x00\xff'
    parts.update(extra or {})
    return parts


def values_for(document_id):
    spec = document_spec(document_id)
    return {field: f' Valeur & <{field}> é € \r\n fin ' for _, field in spec['cells'] + spec['bookmarks']}


def prepare(source, document_id, values=None):
    return prepare_package(source, document_id, values or values_for(document_id),
                           expected_sha256=hashlib.sha256(source).hexdigest())


def test_exact_eight_template_identity_contract_and_cache_isolation():
    value = catalogue()
    assert {item['id'] for item in value['documents']} == DOCUMENT_IDS
    assert sum(len(item['cells']) for item in value['documents']) == 33
    assert sum(len(item['bookmarks']) for item in value['documents']) == 24
    assert not value['financial_calculations']
    assert not {'price', 'margin_pct', 'hourly_rate', 'tdao_prix_vente'} & set(value['fields'])
    assert document_spec('tdao')['cells'][0] == ['E6', 'offer_number']
    assert document_spec('tdsp')['sheet_name'] == "Page d'Accueil"
    value['documents'][1]['cells'][0][0] = 'A1'
    assert document_spec('tdao')['cells'][0][0] == 'E6'
    assert validate_catalogue(json.loads(CATALOGUE.read_text(encoding='utf-8'))) == catalogue()
    with pytest.raises(ValueError):
        document_spec('invented')


@pytest.mark.parametrize('location,value', [
    (('financial_calculations',), True), (('version',), True),
    (('source', 'sha256'), '0'), (('source', 'commit'), []),
    (('fields', 'project_code', 'edit_scope'), []),
    (('documents', 1, 'id'), {}), (('documents', 1, 'format'), []),
    (('documents', 1, 'cells', 0, 0), 'XFE1'),
    (('documents', 1, 'cells', 0, 0), 'A1048577'),
    (('documents', 1, 'cells', 0, 1), []),
    (('documents', 1, 'output_name'), '../elsewhere.xlsm'),
    (('documents', 1, 'output_name'), '{project_code.__class__}.xlsm'),
    (('documents', 1, 'output_name'), '{project_code!r}.xlsm'),
    (('documents', 1, 'output_name'), '{project_code}.xlsx'),
    (('documents', 1, 'fields'), ['hourly_rate']),
    (('documents', 1, 'bookmarks'), [['Wrong', 'project_code']]),
])
def test_invalid_catalogue_refused_without_type_errors(location, value):
    invalid = catalogue()
    cursor = invalid
    for component in location[:-1]:
        cursor = cursor[component]
    cursor[location[-1]] = value
    with pytest.raises(ValueError):
        validate_catalogue(invalid)


@pytest.mark.parametrize('document_id', sorted(DOCUMENT_IDS))
def test_all_eight_formats_preview_and_prepare_keep_opaque_parts(document_id):
    source = package(parts_for(document_id))
    original = source[:]
    values = values_for(document_id)
    report = preview.preview_package(source, document_id, values)
    assert report['read_only'] and report['can_prepare']
    assert report['missing_fields'] == report['missing_targets'] == report['blockers'] == []
    output, prepared = prepare(source, document_id, values)
    assert source == original
    assert prepared['prepared_in_memory'] and prepared['changed_parts'] == [report['part']]
    checked = preview.preview_package(output, document_id, values)
    assert checked['can_prepare']
    assert all(item['existing_value'] == item['proposed_value'] for item in checked['targets'])
    assert checked['macro_parts'] == report['macro_parts']
    with zipfile.ZipFile(BytesIO(source)) as old, zipfile.ZipFile(BytesIO(output)) as new:
        assert old.namelist() == new.namelist()
        assert old.comment == new.comment
        for item in old.infolist():
            other = new.getinfo(item.filename)
            assert (item.date_time, item.comment, item.external_attr, item.compress_type) == (
                other.date_time, other.comment, other.external_attr, other.compress_type)
            if item.filename != report['part']:
                assert old.read(item.filename) == new.read(item.filename)
        changed = new.read(report['part'])
        marker = b'<!--retain this comment-->' if document_id in {'offer_lt_simple', 'ce_request', 'user_manual'} else b'mc:Ignorable="xr"'
        assert marker in changed
    again, _ = prepare(output, document_id, values)
    assert preview.preview_package(again, document_id, values)['targets'] == checked['targets']


def test_excel_styles_unrelated_cells_namespaces_and_order_are_preserved():
    body = '<x:sheetData><x:row r="2"><x:c r="A2" s="4"><x:v>91</x:v></x:c>' \
        '<x:c r="C2" s="8" t="s"><x:v>0</x:v></x:c><x:c r="Z2"><x:f>SUM(A1:A2)</x:f><x:v>99</x:v></x:c>' \
        '</x:row><x:row r="3"/><x:row r="10"><x:c r="A10"><x:v>12</x:v></x:c></x:row></x:sheetData>'
    extra = {'xl/sharedStrings.xml': f'<sst xmlns="{preview.S}"><si><r><t>Shared </t></r>'
             '<r><t>rich</t></r></si></sst>'}
    source = package(parts_for('customer_satisfaction_product', prefix='x:', body=body, extra=extra))
    report = preview.preview_package(source, 'customer_satisfaction_product', values_for('customer_satisfaction_product'))
    assert next(item for item in report['targets'] if item['target'] == 'C2')['existing_value'] == 'Shared rich'
    output, _ = prepare(source, 'customer_satisfaction_product')
    with zipfile.ZipFile(BytesIO(output)) as archive:
        data = archive.read('xl/worksheets/sheet1.xml')
    assert b'<x:c r="A2" s="4"><x:v>91</x:v></x:c>' in data
    assert b'<x:c r="Z2"><x:f>SUM(A1:A2)</x:f><x:v>99</x:v></x:c>' in data
    assert b'<x:c r="C2" s="8" t="inlineStr">' in data
    assert b'xmlns:xr=' in data and b'mc:Ignorable="xr"' in data
    tree = ET.fromstring(data)
    rows = tree.findall(f'{{{preview.S}}}sheetData/{{{preview.S}}}row')
    assert [item.get('r') for item in rows] == ['2', '3', '10']
    assert [item.get('r') for item in rows[0]] == ['A2', 'C2', 'I2', 'P2', 'Z2']


@pytest.mark.parametrize('body,expected', [
    ('<sheetData><row r="2"><c r="C2"><f>SUM(A1:A2)</f><v>4</v></c></row></sheetData>', 'target_unavailable:client_name'),
    ('<sheetData/><sheetProtection sheet="1"/>', 'sheet_protected'),
    ('<sheetData/><mergeCells><mergeCell ref="B2:D2"/></mergeCells>', 'target_unavailable:client_name'),
])
def test_excel_formula_protection_and_non_anchor_are_blocked(body, expected):
    source = package(parts_for('customer_satisfaction_product', body=body))
    report = preview.preview_package(source, 'customer_satisfaction_product', values_for('customer_satisfaction_product'))
    assert expected in report['blockers'] and not report['can_prepare']
    with pytest.raises(ValueError, match='bloquants'):
        prepare(source, 'customer_satisfaction_product')


def test_named_excel_sheet_never_falls_back_to_first_sheet():
    source = package(parts_for('tdao', sheet_name='A different sheet'))
    with pytest.raises(ValueError, match='Feuille attendue'):
        preview.preview_package(source, 'tdao', values_for('tdao'))


@pytest.mark.parametrize('target', ['https://example.invalid/sheet.xml', '../outside.xml', '/elsewhere.xml'])
def test_external_or_escaping_sheet_relationships_are_refused(target):
    parts = parts_for('tdao')
    parts['xl/_rels/workbook.xml.rels'] = str(parts['xl/_rels/workbook.xml.rels']).replace('worksheets/sheet1.xml', target)
    with pytest.raises(ValueError):
        preview.preview_package(package(parts), 'tdao', values_for('tdao'))


def test_alternative_word_bookmark_missing_is_reported_without_erasing_another():
    body = '<w:p><w:bookmarkStart w:id="1" w:name="Affaire"/><w:r><w:t/></w:r><w:bookmarkEnd w:id="1"/></w:p>'
    source = package(parts_for('ce_request', body=body))
    report = preview.preview_package(source, 'ce_request', {'project_code': 'AIRB26LTH0205-A'})
    assert report['can_prepare'] and not report['targets'][1]['present']
    result, _ = prepare(source, 'ce_request', {'project_code': 'AIRB26LTH0205-A'})
    assert preview.preview_package(result, 'ce_request', {'project_code': 'AIRB26LTH0205-A'})['targets'][0]['existing_value'] == 'AIRB26LTH0205-A'


def test_word_fills_parallel_bookmarks_in_both_rendering_branches():
    def bookmark(identifier, text):
        return (f'<w:p><w:bookmarkStart w:id="{identifier}" w:name="Affaire"/>'
                f'<w:r><w:t>{text}</w:t></w:r><w:bookmarkEnd w:id="{identifier}"/></w:p>')
    body = (f'<mc:AlternateContent xmlns:mc="{preview.MC}" xmlns:wps="urn:test:wps">'
            f'<mc:Choice Requires="wps">{bookmark(1, "Choice")}</mc:Choice>'
            f'<mc:Fallback>{bookmark(2, "Fallback")}</mc:Fallback></mc:AlternateContent>')
    result, _ = prepare(package(parts_for('ce_request', body=body)), 'ce_request', {'project_code': 'DEMO'})
    with zipfile.ZipFile(BytesIO(result)) as archive:
        xml = ET.fromstring(archive.read('word/document.xml'))
        assert [node.text for node in xml.iter(f'{{{preview.W}}}t')] == ['DEMO', 'DEMO']


def test_tdao_replaces_only_known_template_formula_and_invalidates_cached_order():
    formula = '''IF('Extract SAGE'!C81="","",'Extract SAGE'!C81)'''
    body = (f'<sheetData><row r="6"><c r="E6" t="str"><f>{formula}</f><v/></c>'
            '<c r="T6"><f>SUM(A6:D6)</f><v>8</v></c></row></sheetData>')
    parts = parts_for('tdao', body=body, extra={'xl/calcChain.xml': f'<calcChain xmlns="{preview.S}"><c r="E6" i="1"/></calcChain>'})
    parts['xl/_rels/workbook.xml.rels'] = parts['xl/_rels/workbook.xml.rels'].replace('</Relationships>',
        f'<Relationship Id="rId2" Type="{preview.R}/calcChain" Target="calcChain.xml"/></Relationships>')
    parts['[Content_Types].xml'] = parts['[Content_Types].xml'].replace('</Types>',
        '<Override PartName="/xl/calcChain.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.calcChain+xml"/></Types>')
    content, _ = prepare(package(parts), 'tdao')
    with zipfile.ZipFile(BytesIO(content)) as archive:
        assert 'xl/calcChain.xml' not in archive.namelist()
        assert b'SUM(A6:D6)' in archive.read('xl/worksheets/sheet1.xml')
        assert b'Extract SAGE' not in archive.read('xl/worksheets/sheet1.xml')
        assert archive.read('xl/vbaProject.bin') == parts['xl/vbaProject.bin']
    parts['xl/worksheets/sheet1.xml'] = parts['xl/worksheets/sheet1.xml'].replace(formula, 'SUM(A1:A6)')
    with pytest.raises(ValueError, match='bloquants'):
        prepare(package(parts), 'tdao')


@pytest.mark.parametrize('body,kind', [
    ('<w:p><w:r><w:t>no bookmark</w:t></w:r></w:p>', 'missing'),
    ('<w:p><w:bookmarkStart w:id="1" w:name="Affaire"/><w:bookmarkStart w:id="2" w:name="Affaire2"/>'
     '<w:r><w:t>nested</w:t></w:r><w:bookmarkEnd w:id="2"/><w:bookmarkEnd w:id="1"/></w:p>', 'overlap'),
    ('<w:p><w:bookmarkStart w:id="1" w:name="Affaire"/><w:bookmarkEnd w:id="1"/>'
     '<w:bookmarkStart w:id="2" w:name="Affaire"/><w:bookmarkEnd w:id="2"/></w:p>', 'ambiguous'),
])
def test_unavailable_or_overlapping_word_targets_block_prepare(body, kind):
    source = package(parts_for('ce_request', body=body))
    report = preview.preview_package(source, 'ce_request', {'project_code': '0205'})
    assert not report['can_prepare']
    assert any('bookmark_' + kind in item['blockers'] for item in report['targets'])
    with pytest.raises(ValueError):
        prepare(source, 'ce_request', {'project_code': '0205'})


@pytest.mark.parametrize('body', [
    '<w:bookmarkEnd w:id="1"/>', '<w:bookmarkStart w:id="1" w:name="Affaire"/>',
    '<w:bookmarkStart w:id="1" w:name="Affaire"/><w:bookmarkStart w:id="1" w:name="Affaire2"/>',
])
def test_unbalanced_word_bookmarks_are_refused(body):
    with pytest.raises(ValueError, match='[Ss]ignet Word'):
        preview.preview_package(package(parts_for('ce_request', body=body)), 'ce_request', {'project_code': '0205'})


def test_missing_values_and_changed_source_never_prepare():
    source = package(parts_for('ce_request'))
    report = preview.preview_package(source, 'ce_request', {})
    assert report['missing_fields'] == ['project_code'] and not report['can_prepare']
    with pytest.raises(ValueError, match='bloquants'):
        prepare_package(source, 'ce_request', {}, expected_sha256=hashlib.sha256(source).hexdigest())
    with pytest.raises(ValueError, match='changé'):
        prepare_package(source, 'ce_request', {'project_code': '0205'}, expected_sha256='0' * 64)


@pytest.mark.parametrize('values', [{'hourly_rate': '1'}, {'project_code': 2}, {'project_code': '\x01'},
                                    {'project_code': '\ud800'}, {'project_code': 'a' * 10001}])
def test_non_text_financial_or_invalid_xml_values_are_refused(values):
    with pytest.raises(ValueError):
        preview.preview_package(package(parts_for('ce_request')), 'ce_request', values)


@pytest.mark.parametrize('unsafe', ['../file.bin', '/file.bin', 'V:/file.bin', 'dir\\file.bin', './file.bin', 'a//file.bin'])
def test_unsafe_zip_paths_are_refused_without_extraction(unsafe):
    with pytest.raises(ValueError, match='Chemin interne'):
        preview.preview_package(package(parts_for('ce_request', extra={unsafe: b'no write'})), 'ce_request', {'project_code': '0205'})


def test_duplicates_crc_and_signed_packages_are_detected():
    parts = parts_for('ce_request')
    with pytest.raises(ValueError, match='ambigu'):
        preview.preview_package(package(parts, duplicate='word/document.xml'), 'ce_request', {'project_code': '0205'})
    with pytest.raises(ValueError, match='ambigu'):
        preview.preview_package(package({**parts, 'WORD/DOCUMENT.XML': b'alias'}), 'ce_request', {'project_code': '0205'})
    source = package({**parts, '_xmlsignatures/sig1.xml': b'opaque signature'})
    assert 'signed_package' in preview.preview_package(source, 'ce_request', {'project_code': '0205'})['blockers']
    with pytest.raises(ValueError, match='bloquants'):
        prepare(source, 'ce_request', {'project_code': '0205'})


def test_declared_format_and_macro_contract_are_enforced():
    parts = parts_for('ce_request', extra={'word/vbaProject.bin': b'Unexpected macro'})
    with pytest.raises(ValueError, match='Macros incompatibles'):
        preview.preview_package(package(parts), 'ce_request', {'project_code': '0205'})
    parts = parts_for('ce_request')
    parts['[Content_Types].xml'] = str(parts['[Content_Types].xml']).replace(preview.CONTENT_TYPES['DOCX'], preview.CONTENT_TYPES['DOCM'])
    with pytest.raises(ValueError, match='Format Office'):
        preview.preview_package(package(parts), 'ce_request', {'project_code': '0205'})


def test_dtd_entities_depth_and_archive_limits(monkeypatch):
    parts = parts_for('ce_request')
    parts['word/document.xml'] = '<!DOCTYPE a [<!ENTITY injected "value">]><a>&injected;</a>'
    with pytest.raises(ValueError, match='DTD'):
        preview.preview_package(package(parts), 'ce_request', {'project_code': '0205'})
    parts['word/document.xml'] = '<a>' * 130 + '</a>' * 130
    with pytest.raises(ValueError, match='Structure XML'):
        preview.preview_package(package(parts), 'ce_request', {'project_code': '0205'})
    monkeypatch.setattr(preview, 'MAX_ENTRIES', 2)
    with pytest.raises(ValueError, match='Trop de fichiers'):
        preview.preview_package(package(parts_for('ce_request')), 'ce_request', {'project_code': '0205'})
    monkeypatch.setattr(preview, 'MAX_ENTRIES', 2048)
    monkeypatch.setattr(preview, 'MAX_ENTRY_BYTES', 12)
    with pytest.raises(ValueError, match='volumineuse'):
        preview.preview_package(package(parts_for('ce_request')), 'ce_request', {'project_code': '0205'})


def test_catalogue_duplicate_targets_cannot_be_published():
    invalid = deepcopy(catalogue())
    invalid['documents'][1]['cells'].append(['E6', 'project_code'])
    with pytest.raises(ValueError, match='répétée'):
        validate_catalogue(invalid)


def test_excel_expands_dimension_and_inserts_before_row_extensions():
    body = '<dimension ref="A1:C2"/><sheetData><row r="2"><c r="C2"><v>19</v></c>' \
           '<extLst><ext uri="urn:keep"/></extLst></row></sheetData>'
    source = package(parts_for('customer_satisfaction_product', body=body))
    output, _ = prepare(source, 'customer_satisfaction_product')
    with zipfile.ZipFile(BytesIO(output)) as archive:
        data = archive.read('xl/worksheets/sheet1.xml')
    tree = ET.fromstring(data)
    assert tree.find(f'{{{preview.S}}}dimension').get('ref') == 'A1:P3'
    row = tree.find(f'{{{preview.S}}}sheetData/{{{preview.S}}}row')
    assert [item.tag.rsplit('}', 1)[1] for item in row] == ['c', 'c', 'c', 'extLst']
    assert b'<extLst><ext uri="urn:keep"/></extLst>' in data


@pytest.mark.parametrize('body,reason', [
    ('<w:p><w:bookmarkStart w:id="1" w:name="Affaire"/><w:fldSimple w:instr="DATE">'
     '<w:r><w:t>Today</w:t></w:r></w:fldSimple><w:bookmarkEnd w:id="1"/></w:p>', 'bookmark_field'),
    ('<w:bookmarkStart w:id="1" w:name="Affaire"/><w:bookmarkEnd w:id="1"/>', 'bookmark_structure'),
])
def test_word_recalculated_fields_and_invalid_empty_run_locations_are_blocked(body, reason):
    source = package(parts_for('ce_request', body=body))
    report = preview.preview_package(source, 'ce_request', {'project_code': '0205'})
    assert reason in report['targets'][0]['blockers']
    with pytest.raises(ValueError):
        prepare(source, 'ce_request', {'project_code': '0205'})


def test_empty_word_bookmark_in_paragraph_can_be_filled_and_protection_blocks():
    body = '<w:p><w:bookmarkStart w:id="1" w:name="Affaire"/><w:bookmarkEnd w:id="1"/></w:p>'
    parts = parts_for('ce_request', body=body)
    result, _ = prepare(package(parts), 'ce_request', {'project_code': '0205'})
    assert preview.preview_package(result, 'ce_request', {'project_code': '0205'})['targets'][0]['existing_value'] == '0205'
    parts['word/settings.xml'] = f'<w:settings xmlns:w="{preview.W}"><w:documentProtection w:enforcement="1"/></w:settings>'
    assert 'document_protected' in preview.preview_package(package(parts), 'ce_request', {'project_code': '0205'})['blockers']


def test_corrupt_crc_is_checked_even_for_unmapped_parts():
    source = bytearray(package(parts_for('ce_request')))
    with zipfile.ZipFile(BytesIO(source)) as archive:
        entry = archive.getinfo('customXml/opaque.bin')
        offset = entry.header_offset
        name_length, extra_length = struct.unpack_from('<HH', source, offset + 26)
        payload_start = offset + 30 + name_length + extra_length
        source[payload_start + entry.compress_size // 2] ^= 16
    with pytest.raises(ValueError, match='illisible'):
        preview.preview_package(bytes(source), 'ce_request', {'project_code': '0205'})


def test_zip_compression_bomb_and_encryption_flags_refused():
    source = package(parts_for('ce_request', extra={'opaque/bomb.bin': b'0' * (2 * 1024 * 1024)}))
    with pytest.raises(ValueError, match='compressée'):
        preview.preview_package(source, 'ce_request', {'project_code': '0205'})
    source = bytearray(package(parts_for('ce_request')))
    for signature, offset in ((b'PK\x03\x04', 6), (b'PK\x01\x02', 8)):
        index = source.find(signature)
        flags = struct.unpack_from('<H', source, index + offset)[0]
        struct.pack_into('<H', source, index + offset, flags | 1)
    with pytest.raises(ValueError, match='chiffrée'):
        preview.preview_package(bytes(source), 'ce_request', {'project_code': '0205'})


def test_missing_parts_xml_encoding_and_small_xml_structure_limits(monkeypatch):
    parts = parts_for('ce_request')
    del parts['word/document.xml']
    with pytest.raises(ValueError, match='requise absente'):
        preview.preview_package(package(parts), 'ce_request', {'project_code': '0205'})
    parts = parts_for('ce_request')
    parts['word/document.xml'] = '<?xml version="1.0" encoding="UTF-16"?>' + parts['word/document.xml']
    with pytest.raises(ValueError, match='Déclaration XML'):
        preview.preview_package(package(parts), 'ce_request', {'project_code': '0205'})
    monkeypatch.setattr(preview, 'MAX_XML_NODES', 4)
    with pytest.raises(ValueError, match='Structure XML'):
        preview.preview_package(package(parts_for('ce_request')), 'ce_request', {'project_code': '0205'})


def test_large_excel_copy_keeps_all_unrelated_rows_and_last_cell():
    body = '<sheetData>' + ''.join(f'<row r="{number}"><c r="A{number}"><v>{number}</v></c></row>'
                                   for number in range(1, 3001)) + '</sheetData>'
    source = package(parts_for('customer_satisfaction_product', body=body))
    result, _ = prepare(source, 'customer_satisfaction_product')
    with zipfile.ZipFile(BytesIO(result)) as archive:
        xml = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
    rows = xml.findall(f'{{{preview.S}}}sheetData/{{{preview.S}}}row')
    assert len(rows) == 3000
    assert rows[-1].find(f'{{{preview.S}}}c').get('r') == 'A3000'
    assert rows[-1].findtext(f'{{{preview.S}}}c/{{{preview.S}}}v') == '3000'
