"""Prepare an independent OOXML copy in memory after a fresh preview.

Only mapped targets and affected calculation metadata change. VBA code,
bookmarks, namespaces and unrelated XML bytes are retained. Never writes files.
"""
import hashlib
from io import BytesIO
import re
from xml.parsers import expat
from xml.sax.saxutils import escape
import zipfile

from .document_package_preview import CT, P, R, MAX_ENTRY_BYTES, MAX_SOURCE_BYTES, MAX_TOTAL_BYTES, S, W, _Package, _coordinates, _xml, preview_package


def _tag_end(data, start):
    quote = None
    for index in range(start, len(data)):
        char = data[index]
        if quote:
            if char == quote:
                quote = None
        elif char in (34, 39):
            quote = char
        elif char == 62:
            return index + 1
    raise ValueError('Balise XML incomplète')


def _spans(data):
    """Expat byte offsets allow edits without reserializing namespace declarations."""
    parser = expat.ParserCreate(namespace_separator='}')
    spans, stack = [], []

    def start(name, attrs):
        offset = parser.CurrentByteIndex
        end = _tag_end(data, offset)
        opening = data[offset:end]
        qname = re.match(rb'<([^\s/>]+)', opening)[1].decode('ascii')
        item = {'name': name, 'attrs': attrs, 'start': offset, 'open_end': end, 'qname': qname,
                'parent': stack[-1] if stack else None, 'self_closing': opening.rstrip().endswith(b'/>')}
        spans.append(item)
        stack.append(len(spans) - 1)

    def end(name):
        item = spans[stack.pop()]
        item['close_start'] = item['open_end'] if item['self_closing'] else parser.CurrentByteIndex
        item['end'] = item['open_end'] if item['self_closing'] else _tag_end(data, parser.CurrentByteIndex)

    parser.StartElementHandler, parser.EndElementHandler = start, end
    parser.Parse(data, True)
    return spans


def _patch(data, edits):
    ordered = sorted(edits, key=lambda item: (item[0], item[1]))
    previous = 0
    for start, end, replacement in ordered:
        if start < previous or not 0 <= start <= end <= len(data):
            raise ValueError('Modifications de cibles XML qui se chevauchent')
        previous = end
        if not isinstance(replacement, bytes):
            raise ValueError('Modification XML invalide')
    for start, end, replacement in reversed(ordered):
        data = data[:start] + replacement + data[end:]
    if len(data) > MAX_ENTRY_BYTES:
        raise ValueError('Partie Office préparée trop volumineuse')
    _xml(data)
    return data


def _prefix(qname):
    return qname.rsplit(':', 1)[0] + ':' if ':' in qname else ''


def _inline(value, prefix):
    text = escape(value).replace('\r', '&#13;').encode('utf-8')
    return (f'<{prefix}is><{prefix}t xml:space="preserve">'.encode('ascii') + text
            + f'</{prefix}t></{prefix}is>'.encode('ascii'))


def _new_cell(target, value, prefix):
    return (f'<{prefix}c r="{target}" t="inlineStr">'.encode('ascii') + _inline(value, prefix)
            + f'</{prefix}c>'.encode('ascii'))


def _column(target):
    value = 0
    for char in re.match(r'[A-Z]+', target)[0]:
        value = value * 26 + ord(char) - 64
    return value


def _address(column, row):
    letters = ''
    while column:
        column, digit = divmod(column - 1, 26)
        letters = chr(65 + digit) + letters
    return letters + str(row)


def _expand(data, item, insertions):
    """Insert children of a self-closing element while preserving its attributes."""
    opening = data[item['start']:item['open_end']]
    return re.sub(rb'/\s*>$', b'>', opening) + insertions + f'</{item["qname"]}>'.encode('ascii')


def _spreadsheet(data, report):
    spans = _spans(data)
    sheet_data = [item for item in spans if item['name'] == S + '}sheetData']
    if len(sheet_data) != 1:
        raise ValueError('Zone de données Excel absente ou ambiguë')
    section = sheet_data[0]
    section_id = spans.index(section)
    rows = [item for item in spans if item['name'] == S + '}row' and item['parent'] == section_id]
    row_ids = {index for index, item in enumerate(spans) if item['name'] == S + '}row' and item['parent'] == section_id}
    numbers = [int(item['attrs']['r']) for item in rows]
    if numbers != sorted(set(numbers)):
        raise ValueError('Lignes Excel désordonnées ou répétées')
    cells = {item['attrs']['r']: (index, item) for index, item in enumerate(spans)
             if item['name'] == S + '}c' and item['parent'] in row_ids}
    prefix = _prefix(section['qname'])
    edits, new_by_row = [], {}
    dimensions = [item for item in spans if item['name'] == S + '}dimension']
    if len(dimensions) > 1:
        raise ValueError('Dimensions Excel ambiguës')
    if dimensions:
        dimension = dimensions[0]
        ends = dimension['attrs'].get('ref', '').split(':')
        if len(ends) not in {1, 2}:
            raise ValueError('Dimensions Excel invalides')
        coordinates = [_coordinates(address) for address in ends]
        coordinates.extend(_coordinates(target['target']) for target in report['targets'])
        minimum = _address(min(item[0] for item in coordinates), min(item[1] for item in coordinates))
        maximum = _address(max(item[0] for item in coordinates), max(item[1] for item in coordinates))
        reference = minimum if minimum == maximum else minimum + ':' + maximum
        if reference != dimension['attrs'].get('ref'):
            opening = data[dimension['start']:dimension['open_end']]
            opening = re.sub(rb'(\sref\s*=\s*)([\x27\"])[^\x27\"]*\2',
                             lambda match: match[1] + match[2] + reference.encode('ascii') + match[2], opening)
            edits.append((dimension['start'], dimension['open_end'], opening))
    for target in report['targets']:
        address, value = target['target'], target['proposed_value']
        existing = cells.get(address)
        if not existing:
            row_number = int(re.search(r'[0-9]+$', address)[0])
            new_by_row.setdefault(row_number, []).append((address, value))
            continue
        index, item = existing
        opening = data[item['start']:item['open_end']]
        opening = re.sub(rb'/\s*>$', b'>', opening)
        if re.search(rb'\st\s*=', opening):
            opening = re.sub(rb'\st\s*=\s*(?:"[^"]*"|\x27[^\x27]*\x27)', b' t="inlineStr"', opening)
        else:
            opening = opening[:-1] + b' t="inlineStr">'
        children = [child for child in spans if child['parent'] == index
                    and child['name'] in {S + '}v', S + '}is', S + '}f'}]
        inner = data[item['open_end']:item['close_start']]
        for child in reversed(children):
            inner = inner[:child['start'] - item['open_end']] + inner[child['end'] - item['open_end']:]
        filled = opening + _inline(value, _prefix(item['qname'])) + inner + f'</{item["qname"]}>'.encode('ascii')
        edits.append((item['start'], item['end'], filled))
    insertion_groups = {}
    for number, entries in sorted(new_by_row.items()):
        entries.sort(key=lambda item: _column(item[0]))
        row = next((item for item in rows if int(item['attrs']['r']) == number), None)
        if row:
            row_id = spans.index(row)
            row_cells = [item for item in spans if item['parent'] == row_id and item['name'] == S + '}c']
            columns = [_column(item['attrs']['r']) for item in row_cells]
            if columns != sorted(set(columns)):
                raise ValueError('Cellules Excel désordonnées ou répétées')
            child_prefix = _prefix(row['qname'])
            if row['self_closing']:
                filled = b''.join(_new_cell(address, value, child_prefix) for address, value in entries)
                edits.append((row['start'], row['end'], _expand(data, row, filled)))
            else:
                trailing = next((item['start'] for item in spans if item['parent'] == row_id
                                 and item['name'] != S + '}c'), row['close_start'])
                for address, value in entries:
                    offset = next((item['start'] for item in row_cells if _column(item['attrs']['r']) > _column(address)),
                                  trailing)
                    insertion_groups.setdefault(offset, []).append(_new_cell(address, value, child_prefix))
        else:
            new = f'<{prefix}row r="{number}">'.encode('ascii')
            new += b''.join(_new_cell(address, value, prefix) for address, value in entries)
            new += f'</{prefix}row>'.encode('ascii')
            offset = next((item['start'] for item in rows if int(item['attrs']['r']) > number), section['close_start'])
            insertion_groups.setdefault(offset, []).append(new)
    if section['self_closing'] and insertion_groups:
        content = b''.join(part for parts in insertion_groups.values() for part in parts)
        edits.append((section['start'], section['end'], _expand(data, section, content)))
    else:
        edits.extend((offset, offset, b''.join(parts)) for offset, parts in insertion_groups.items())
    return _patch(data, edits)


def _word(data, report):
    spans = _spans(data)
    starts = [item for item in spans if item['name'] == W + '}bookmarkStart']
    ends = {item['attrs'][W + '}id']: item for item in spans if item['name'] == W + '}bookmarkEnd'}
    values = {target['target']: target['proposed_value'] for target in report['targets'] if target['available']}
    edits = []
    for start in starts:
        name = start['attrs'][W + '}name']
        if name not in values:
            continue
        end = ends[start['attrs'][W + '}id']]
        texts = [item for item in spans if item['name'] == W + '}t'
                 and start['end'] <= item['start'] < item['end'] <= end['start']]
        value = escape(values[name]).replace('\r', '&#13;').encode('utf-8')
        if texts:
            for index, item in enumerate(texts):
                content = value if index == 0 else b''
                opening = data[item['start']:item['open_end']]
                # Preserve spaces independently of the original placeholder.
                opening = re.sub(rb'/\s*>$', b'>', opening)
                opening = re.sub(rb'\sxml:space\s*=\s*(?:"[^"]*"|\x27[^\x27]*\x27)', b'', opening)
                opening = opening[:-1] + b' xml:space="preserve">'
                replacement = opening + content + f'</{item["qname"]}>'.encode('ascii')
                edits.append((item['start'], item['end'], replacement))
        else:
            prefix = _prefix(start['qname'])
            replacement = (f'<{prefix}r><{prefix}t xml:space="preserve">'.encode('ascii') + value
                           + f'</{prefix}t></{prefix}r>'.encode('ascii'))
            edits.append((start['end'], start['end'], replacement))
    return _patch(data, edits)


def _invalidate_calc_chain(package):
    """Drop Excel's optional cached formula order when mapped formulas become text."""
    rel_part, types_part = 'xl/_rels/workbook.xml.rels', '[Content_Types].xml'
    rel_data = package.read(rel_part)
    matches = [node for node in _spans(rel_data) if node['name'] == P + '}Relationship'
               and node['attrs'].get('Type') == R + '/calcChain']
    if not matches:
        return {}
    if len(matches) != 1:
        raise ValueError('Chaîne de calcul Excel ambiguë')
    relation = matches[0]
    name = relation['attrs'].get('Target', '')
    part = name.lstrip('/') if name.startswith('/') else 'xl/' + name
    if (relation['attrs'].get('TargetMode') == 'External' or part not in package.names
            or not part.startswith('xl/') or not part.endswith('.xml')
            or '..' in part.split('/') or '\\' in part or part in {'xl/workbook.xml', rel_part}
            or package.xml(part).tag != f'{{{S}}}calcChain'):
        raise ValueError('Chaîne de calcul Excel invalide')
    types_data = package.read(types_part)
    types = [node for node in _spans(types_data) if node['name'] == CT + '}Override'
             and node['attrs'].get('PartName') == '/' + part]
    if (len(types) != 1 or types[0]['attrs'].get('ContentType')
            != 'application/vnd.openxmlformats-officedocument.spreadsheetml.calcChain+xml'):
        raise ValueError('Type de chaîne de calcul Excel invalide')
    return {rel_part: _patch(rel_data, [(relation['start'], relation['end'], b'')]),
            types_part: _patch(types_data, [(types[0]['start'], types[0]['end'], b'')]),
            part: None}


def prepare_package(source, document_id, values, *, expected_sha256):
    """Return new bytes, never overwrite input; expected hash binds to the preview."""
    if not isinstance(expected_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise ValueError('Empreinte de l’aperçu requise')
    report = preview_package(source, document_id, values)
    if report['source_sha256'] != expected_sha256:
        raise ValueError('La trame a changé depuis l’aperçu')
    if not report['can_prepare']:
        raise ValueError('Corriger les champs et cibles bloquants avant préparation')
    package = _Package(source)
    try:
        old = package.read(report['part'])
        filled = (_spreadsheet if report['format'] in {'XLSX', 'XLSM'} else _word)(old, report)
        changes = {report['part']: filled} if filled != old else {}
        if any(target.get('replaces_placeholder') for target in report['targets']):
            changes.update(_invalidate_calc_chain(package))
        output = BytesIO()
        total = 0
        with zipfile.ZipFile(output, 'w') as target:
            target.comment = package.archive.comment
            for entry in package.archive.infolist():
                payload = changes[entry.filename] if entry.filename in changes else package.read(entry.filename)
                if payload is None:
                    continue
                total += len(payload)
                if total > MAX_TOTAL_BYTES:
                    raise ValueError('Copie Office préparée trop volumineuse')
                target.writestr(entry, payload)
        result = output.getvalue()
        if len(result) > MAX_SOURCE_BYTES:
            raise ValueError('Copie Office préparée de 50 Mio maximum requise')
        # Verify the resulting package through the same read-only interpretation.
        verified = preview_package(result, document_id, values)
        if not verified['can_prepare'] or any(item['available'] and item['existing_value'] != item['proposed_value']
                                             for item in verified['targets']):
            raise ValueError('Vérification des cibles préparées échouée')
        return result, {**report, 'output_sha256': hashlib.sha256(result).hexdigest(),
                        'output_size_bytes': len(result), 'changed_parts': list(changes),
                        'read_only': False, 'prepared_in_memory': True}
    finally:
        package.archive.close()
