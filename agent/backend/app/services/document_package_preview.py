"""Bounded, read-only OOXML inspection of the eight project document templates.

Accepts already acquired bytes, never a path. No Office process, relationship
fetch, macro execution, extraction, database mutation or source modification.
"""
from app.operational_limits import DOCUMENT_IMPORT_BYTES
from collections import Counter, defaultdict
import hashlib
from io import BytesIO
from pathlib import PurePosixPath
import re
import stat
import zipfile
import zlib
from xml.etree import ElementTree as ET
from xml.parsers import expat

from .document_template_catalogue import FIELD_KEYS, document_spec

MAX_SOURCE_BYTES = DOCUMENT_IMPORT_BYTES
MAX_ENTRIES = 2048
MAX_ENTRY_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_RATIO = 200
MAX_XML_NODES = 200_000
MAX_XML_DEPTH = 128
S = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
MC = 'http://schemas.openxmlformats.org/markup-compatibility/2006'

# XPilot fills these identification cells directly. Allow only the formulas
# observed on the supported forms, never a user-defined or financial formula.
_TDAO_INPUTS = {'E6': 'C81', 'E8': 'C8', 'E10': 'C9', 'K6': 'C74',
                'K8': 'C52', 'K10': 'C54', 'E15': 'C61'}


def _template_formula(document_id, address, formula):
    if formula is None or formula.attrib:
        return False
    if document_id == 'tdao' and address in _TDAO_INPUTS:
        source = "'Extract SAGE'!" + _TDAO_INPUTS[address]
        hint = "A remplir obligatoirement depuis extract sage ou directement dans la cellule" if address == 'E8' else ''
        return formula.text == f'IF({source}="","{hint}",{source})'
    return (document_id == 'tdsp' and address == 'L22'
            and formula.text == 'IF(K22="Oui","Précisez la référence","-")')

CONTENT_TYPES = {
    'DOCX': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml',
    'DOCM': 'application/vnd.ms-word.document.macroEnabled.main+xml',
    'XLSX': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml',
    'XLSM': 'application/vnd.ms-excel.sheet.macroEnabled.main+xml',
}


def _xml(data):
    """Reject DTD/entities and excessive structure before building a small tree."""
    try:
        text = data.decode('utf-8-sig')
        declaration = re.match(r'<\?xml\s+.*?\?>', text, flags=re.DOTALL)
        encoding = re.search(r'encoding\s*=\s*[\x27\"]([^\x27\"]+)', declaration[0], re.IGNORECASE) if declaration else None
        if encoding and encoding[1].casefold() not in {'utf-8', 'utf8'}:
            raise ValueError('Déclaration XML UTF-8 requise')
        parser = expat.ParserCreate()
        depth = nodes = 0

        def reject(*args):
            raise ValueError('DTD et entités XML interdits dans une trame')

        def start(*args):
            nonlocal depth, nodes
            depth += 1
            nodes += 1
            if depth > MAX_XML_DEPTH or nodes > MAX_XML_NODES:
                raise ValueError('Structure XML trop volumineuse')

        def end(*args):
            nonlocal depth
            depth -= 1

        parser.StartDoctypeDeclHandler = reject
        parser.EntityDeclHandler = reject
        parser.ExternalEntityRefHandler = reject
        parser.StartElementHandler, parser.EndElementHandler = start, end
        parser.Parse(text, True)
        return ET.fromstring(text)
    except (UnicodeError, expat.ExpatError, ET.ParseError) as exc:
        raise ValueError('XML Office UTF-8 invalide') from exc


class _Package:
    def __init__(self, source):
        if not isinstance(source, bytes) or not source or len(source) > MAX_SOURCE_BYTES:
            raise ValueError('Document Office de 50 Mio maximum requis')
        try:
            self.archive = zipfile.ZipFile(BytesIO(source))
        except zipfile.BadZipFile as exc:
            raise ValueError('Archive Office invalide') from exc
        self.names, self.macro_parts = set(), []
        try:
            entries = self.archive.infolist()
            if len(entries) > MAX_ENTRIES:
                raise ValueError('Trop de fichiers dans la trame Office')
            total, aliases = 0, set()
            for entry in entries:
                name = entry.filename
                alias = name.casefold()
                if (entry.orig_filename != name or not name or '\\' in name or ':' in name or '\x00' in name or name.startswith('/')
                        or '..' in name.split('/') or any(ord(char) < 32 for char in name)
                        or alias in aliases or PurePosixPath(name).as_posix() != name.rstrip('/')):
                    raise ValueError('Chemin interne Office ambigu ou interdit')
                aliases.add(alias)
                self.names.add(name)
                mode = (entry.external_attr >> 16) & 0xFFFF
                if (stat.S_ISLNK(mode) or entry.flag_bits & 1
                        or entry.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}):
                    raise ValueError('Entrée Office chiffrée ou non prise en charge')
                total += entry.file_size
                if (entry.file_size > MAX_ENTRY_BYTES or total > MAX_TOTAL_BYTES
                        or entry.file_size > 1024 * 1024
                        and entry.file_size > max(1, entry.compress_size) * MAX_RATIO):
                    raise ValueError('Archive Office trop volumineuse ou trop compressée')
            # Verify every CRC, including opaque VBA parts, within declared bounds.
            for entry in entries:
                data = self.read(entry.filename)
                if entry.filename.casefold().endswith('/vbaproject.bin'):
                    self.macro_parts.append({'part': entry.filename, 'size_bytes': len(data),
                                             'sha256': hashlib.sha256(data).hexdigest()})
        except Exception:
            self.archive.close()
            raise

    def read(self, name):
        if name not in self.names:
            raise ValueError('Partie Office requise absente : ' + name)
        try:
            with self.archive.open(name) as stream:
                data = stream.read(MAX_ENTRY_BYTES + 1)
            if len(data) > MAX_ENTRY_BYTES:
                raise ValueError('Partie Office trop volumineuse')
            return data
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError, zlib.error) as exc:
            raise ValueError('Partie Office illisible : ' + name) from exc

    def xml(self, name):
        return _xml(self.read(name))


def _values(values):
    if not isinstance(values, dict) or not set(values).issubset(FIELD_KEYS):
        raise ValueError('Champs de remplissage non financiers requis')
    result = {}
    for field, value in values.items():
        if value is None:
            result[field] = ''
        elif (not isinstance(value, str) or len(value) > 10_000
                or any(ord(char) < 32 and char not in '\t\r\n' for char in value)
                or any(0xD800 <= ord(char) <= 0xDFFF or ord(char) in {0xFFFE, 0xFFFF} for char in value)):
            raise ValueError('Valeur documentaire textuelle invalide')
        else:
            result[field] = value
    return result


def _sheet(package, spec):
    workbook = package.xml('xl/workbook.xml')
    sheets = workbook.findall(f'{{{S}}}sheets/{{{S}}}sheet')
    if not sheets:
        raise ValueError('Aucune feuille dans la trame Excel')
    expected = spec['sheet_name']
    if (not expected and spec['id'] == 'manufacturing_specification'
            and any(sheet.get('name') in {"Mode d'emploi", 'Cahier des Charges'} for sheet in sheets)):
        expected = 'Cahier des Charges'
    candidates = [sheet for sheet in sheets if sheet.get('name') == expected] if expected else sheets[:1]
    if len(candidates) != 1:
        raise ValueError('Feuille attendue absente ou ambiguë : ' + str(expected))
    sheet = candidates[0]
    relation_id = sheet.get(f'{{{R}}}id')
    relations = package.xml('xl/_rels/workbook.xml.rels')
    matches = [item for item in relations.findall(f'{{{P}}}Relationship') if item.get('Id') == relation_id]
    if not relation_id or len(matches) != 1:
        raise ValueError('Relation de feuille absente ou ambiguë')
    relation = matches[0]
    target = relation.get('Target', '')
    if (relation.get('TargetMode') == 'External' or not relation.get('Type', '').endswith('/worksheet')
            or not target or '\\' in target or ':' in target or '?' in target or '#' in target
            or '..' in target.split('/') or target.startswith('//')):
        raise ValueError('Relation de feuille interne requise')
    part = target.lstrip('/') if target.startswith('/') else 'xl/' + target
    if not part.startswith('xl/worksheets/') or not part.endswith('.xml'):
        raise ValueError('Partie de feuille Office invalide')
    return part, sheet.get('name'), package.xml(part)


def _cell_text(cell, shared):
    kind = cell.get('t', 'n')
    value = cell.findtext(f'{{{S}}}v') or ''
    if kind == 's':
        try:
            index = int(value)
        except ValueError as exc:
            raise ValueError('Index de chaîne Excel invalide') from exc
        if not 0 <= index < len(shared):
            raise ValueError('Chaîne Excel absente')
        return shared[index]
    if kind == 'inlineStr':
        return ''.join(item.text or '' for item in cell.findall(f'.//{{{S}}}t'))
    return value


def _coordinates(address):
    match = re.fullmatch(r'([A-Z]{1,3})([1-9][0-9]{0,6})', address)
    if not match:
        raise ValueError('Coordonnée de feuille invalide')
    column = 0
    for char in match[1]:
        column = column * 26 + ord(char) - 64
    row = int(match[2])
    if column > 16384 or row > 1048576:
        raise ValueError('Coordonnée hors de la feuille')
    return column, row


def _unlocked_styles(package):
    if 'xl/styles.xml' not in package.names:
        return set()
    styles = package.xml('xl/styles.xml')
    return {str(index) for index, style in enumerate(styles.findall(f'{{{S}}}cellXfs/{{{S}}}xf'))
            if style.get('applyProtection') in {'1', 'true'}
            and (protection := style.find(f'{{{S}}}protection')) is not None
            and protection.get('locked') in {'0', 'false'}}


def _spreadsheet(package, spec, values):
    part, name, xml = _sheet(package, spec)
    if xml.tag != f'{{{S}}}worksheet':
        raise ValueError('Partie de feuille Excel invalide')
    shared = []
    if 'xl/sharedStrings.xml' in package.names:
        shared = [''.join(node.text or '' for node in item.iter(f'{{{S}}}t'))
                  for item in package.xml('xl/sharedStrings.xml').findall(f'{{{S}}}si')]
    cells = defaultdict(list)
    for row in xml.findall(f'{{{S}}}sheetData/{{{S}}}row'):
        for cell in row.findall(f'{{{S}}}c'):
            address = cell.get('r', '')
            _, row_number = _coordinates(address)
            if str(row_number) != row.get('r'):
                raise ValueError('Cellule Excel située dans une autre ligne')
            cells[address].append(cell)
    merged = []
    for item in xml.findall(f'{{{S}}}mergeCells/{{{S}}}mergeCell'):
        endpoints = (item.get('ref') or '').split(':')
        if len(endpoints) != 2:
            raise ValueError('Plage de cellules fusionnées invalide')
        start, end = map(_coordinates, endpoints)
        if start[0] > end[0] or start[1] > end[1]:
            raise ValueError('Plage de cellules fusionnées inversée')
        merged.append((start, end))
    protection = xml.find(f'{{{S}}}sheetProtection')
    protected = protection is not None and protection.get('sheet') not in {None, '0', 'false'}
    unlocked_styles = _unlocked_styles(package) if protected else set()
    reports, blockers = [], []
    for target, field in spec['cells']:
        matches = cells[target]
        if len(matches) > 1:
            raise ValueError('Cellule cible répétée : ' + target)
        cell = matches[0] if matches else None
        formula = cell.find(f'{{{S}}}f') if cell is not None else None
        placeholder = _template_formula(spec['id'], target, formula)
        locked = protected and (cell is None or cell.get('s', '0') not in unlocked_styles)
        coordinate = _coordinates(target)
        non_anchor = any(start[0] <= coordinate[0] <= end[0] and start[1] <= coordinate[1] <= end[1]
                         and coordinate != start for start, end in merged)
        reasons = [code for condition, code in ((formula is not None and not placeholder, 'formula'),
                                                 (non_anchor, 'merged_non_anchor'),
                                                 (locked, 'sheet_protected')) if condition]
        if locked:
            blockers.append('sheet_protected')
        reports.append({'kind': 'cell', 'target': target, 'field': field, 'present': cell is not None,
                        'available': not reasons, 'existing_value': _cell_text(cell, shared) if cell is not None else '',
                        'proposed_value': values.get(field, ''), 'blockers': reasons,
                        'replaces_placeholder': placeholder})
    return part, name, reports, blockers


def _alternate_branch(node, parents):
    while node in parents:
        if node.tag in {f'{{{MC}}}Choice', f'{{{MC}}}Fallback'}:
            parent = parents[node]
            return node if parent.tag == f'{{{MC}}}AlternateContent' else None
        node = parents[node]
    return None


def _parallel_bookmarks(entries, parents):
    branches = [item['branch'] for item in entries]
    return (len(entries) > 1 and None not in branches and len(set(branches)) == len(entries)
            and len({parents[branch] for branch in branches}) == 1)


def _word(package, spec, values):
    part = 'word/document.xml'
    xml = package.xml(part)
    if xml.tag != f'{{{W}}}document':
        raise ValueError('Partie de document Word invalide')
    opened, found, used_ids = {}, defaultdict(list), set()
    position = 0
    parents = {child: parent for parent in xml.iter() for child in parent}
    for node in xml.iter():
        position += 1
        if node.tag == f'{{{W}}}bookmarkStart':
            identifier, name = node.get(f'{{{W}}}id'), node.get(f'{{{W}}}name')
            if not identifier or not name or identifier in used_ids:
                raise ValueError('Début de signet Word ambigu')
            used_ids.add(identifier)
            if len(used_ids) > 4096 or len(opened) >= 128:
                raise ValueError('Trop de signets Word ou de signets simultanés')
            opened[identifier] = {'name': name, 'start': position, 'text': [], 'complex': False,
                                  'parent': parents.get(node), 'has_text': False,
                                  'branch': _alternate_branch(node, parents)}
        elif node.tag == f'{{{W}}}t':
            for bookmark in opened.values():
                bookmark['text'].append(node.text or '')
                bookmark['has_text'] = True
        elif node.tag in {f'{{{W}}}fldChar', f'{{{W}}}instrText', f'{{{W}}}fldSimple'}:
            for bookmark in opened.values():
                bookmark['complex'] = True
        elif node.tag == f'{{{W}}}bookmarkEnd':
            identifier = node.get(f'{{{W}}}id')
            bookmark = opened.pop(identifier, None)
            if bookmark is None:
                raise ValueError('Fin de signet Word sans début')
            if bookmark['branch'] is not _alternate_branch(node, parents):
                raise ValueError('Signet Word réparti entre deux variantes')
            found[bookmark['name']].append({**bookmark, 'end': position})
    if opened:
        raise ValueError('Signet Word non terminé')
    selected = [(target, entry) for target, _ in spec['bookmarks']
                if len(entries := found[target]) == 1 or _parallel_bookmarks(entries, parents)
                for entry in entries]
    overlap = set()
    for index, (left_target, left) in enumerate(selected):
        for right_target, right in selected[index + 1:]:
            if left['start'] < right['end'] and right['start'] < left['end']:
                overlap.update((left_target, right_target))
    reports = []
    for target, field in spec['bookmarks']:
        entries = found[target]
        reasons = [code for condition, code in ((not entries, 'bookmark_missing'),
                    (len(entries) > 1 and not _parallel_bookmarks(entries, parents), 'bookmark_ambiguous'),
                    (target in overlap, 'bookmark_overlap'),
                    (any(item['complex'] for item in entries), 'bookmark_field'),
                    (any(not item['has_text'] and (item['parent'] is None or item['parent'].tag != f'{{{W}}}p')
                         for item in entries), 'bookmark_structure')) if condition]
        reports.append({'kind': 'bookmark', 'target': target, 'field': field, 'present': bool(entries),
                        'available': not reasons,
                        'existing_value': ' / '.join(dict.fromkeys(''.join(item['text']) for item in entries)),
                        'proposed_value': values.get(field, ''), 'blockers': reasons})
    blockers = []
    if 'word/settings.xml' in package.names:
        settings = package.xml('word/settings.xml')
        if settings.find(f'{{{W}}}documentProtection') is not None:
            blockers.append('document_protected')
    return part, None, reports, blockers


def preview_package(source, document_id, values):
    """Inspect acquired bytes and report targets; this function never fills them."""
    spec, values = document_spec(document_id), _values(values)
    package = _Package(source)
    try:
        spreadsheet = spec['format'] in {'XLSX', 'XLSM'}
        main = '/xl/workbook.xml' if spreadsheet else '/word/document.xml'
        types = package.xml('[Content_Types].xml')
        matches = [node.get('ContentType') for node in types.findall(f'{{{CT}}}Override') if node.get('PartName') == main]
        if matches != [CONTENT_TYPES[spec['format']]]:
            raise ValueError('Format Office différent de la trame sélectionnée')
        if spec['format'] in {'DOCX', 'XLSX'} and package.macro_parts:
            raise ValueError('Macros incompatibles avec le format de la trame')
        part, sheet, targets, blockers = (_spreadsheet if spreadsheet else _word)(package, spec, values)
        if any(name.casefold().startswith('_xmlsignatures/') for name in package.names):
            blockers.append('signed_package')
        mapped = {target['field'] for target in targets}
        missing_fields = sorted(field for field in mapped if not values.get(field, '').strip())
        # XPilot includes equivalent bookmark names: one available alias suffices.
        missing_targets = sorted(field for field in mapped if not any(
            target['available'] for target in targets if target['field'] == field))
        blockers.extend('target_unavailable:' + field for field in missing_targets)
        return {'document_id': document_id, 'format': spec['format'], 'source_sha256': hashlib.sha256(source).hexdigest(),
                'size_bytes': len(source), 'part': part, 'sheet': sheet, 'targets': targets,
                'missing_fields': missing_fields, 'missing_targets': missing_targets,
                'blockers': sorted(set(blockers)), 'can_prepare': not blockers and not missing_fields,
                'macro_parts': package.macro_parts, 'read_only': True,
                'unmapped_fields': sorted(set(spec['fields']) - mapped),
                'target_counts': dict(Counter(item['kind'] for item in targets))}
    finally:
        package.archive.close()
