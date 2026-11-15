"""Pure staged TipTap conversion. No IO, HTML rendering or implicit fallback.

Unsupported content blocks application and is reported by path. The importer
must retain the source bytes separately and offer an explicit alternative.
Image bindings are supplied by acquisition, never derived from remote URLs.
"""
import json

from pydantic import ValidationError

from backend.app.project_note_schemas import NoteContent, TextRun

MAX_SOURCE_BYTES = 2_000_000
MAX_NODES = 20_000
MAX_DEPTH = 32
MAX_ISSUES = 100


class Conversion:
    def __init__(self, image_bindings):
        self.images = image_bindings
        self.issues = []
        self.nodes = 0

    def issue(self, path, message):
        if len(self.issues) < MAX_ISSUES:
            self.issues.append({'path': path, 'message': message})

    def node(self, value, path, depth=0):
        self.nodes += 1
        if depth > MAX_DEPTH or self.nodes > MAX_NODES:
            raise ValueError('Document trop complexe')
        if not isinstance(value, dict) or not isinstance(value.get('type'), str):
            self.issue(path, 'Nœud structuré typé requis')
            return None
        allowed = {'type', 'attrs', 'content'}
        if value['type'] == 'text':
            allowed = {'type', 'text', 'marks'}
        elif value['type'] == 'image':
            allowed = {'type', 'attrs'}
        elif value['type'] == 'hardBreak':
            allowed = {'type'}
        if set(value) - allowed:
            self.issue(path, 'Champs de nœud non représentables')
        return value

    def children(self, value, path):
        content = value.get('content', [])
        if not isinstance(content, list):
            self.issue(path, 'Liste de contenu requise')
            return []
        return content

    def attrs(self, value, allowed, path):
        attrs = value.get('attrs', {})
        if attrs is None:
            attrs = {}
        if not isinstance(attrs, dict):
            self.issue(path, 'Attributs structurés requis')
            return {}
        if any(key not in allowed and item is not None for key, item in attrs.items()):
            self.issue(path, 'Attributs non représentables')
        return attrs

    def runs(self, values, path, depth):
        result = []
        for index, value in enumerate(values):
            location = f'{path}/{index}'
            value = self.node(value, location, depth)
            if value is None:
                continue
            if value['type'] == 'hardBreak':
                if set(value) - {'type'}:
                    self.issue(location, 'Attributs de saut de ligne non représentables')
                result.append({'text': '\n'})
                continue
            if value['type'] != 'text' or not isinstance(value.get('text'), str):
                self.issue(location, 'Texte ou saut de ligne requis')
                continue
            if set(value) - {'type', 'text', 'marks'}:
                self.issue(location, 'Champs de texte non représentables')
            marks = value.get('marks', [])
            if not isinstance(marks, list):
                self.issue(location, 'Liste de styles requise')
                marks = []
            run = {'text': value['text'], 'marks': []}
            seen = set()
            for mark in marks:
                if not isinstance(mark, dict) or set(mark) - {'type', 'attrs'}:
                    self.issue(location, 'Style structuré non représentable')
                    continue
                kind = mark.get('type')
                if not isinstance(kind, str) or kind in seen:
                    self.issue(location, 'Style invalide ou répété')
                    continue
                seen.add(kind)
                if kind in {'bold', 'italic', 'underline', 'strike', 'code'}:
                    self.attrs(mark, set(), location)
                    run['marks'].append(kind)
                elif kind == 'link':
                    attrs = self.attrs(mark, {'href', 'target', 'rel', 'class'}, location)
                    if attrs.get('class'):
                        self.issue(location, 'Style de lien par classe non représentable')
                    if not isinstance(attrs.get('href'), str):
                        self.issue(location, 'Adresse de lien requise')
                    else:
                        run['href'] = attrs['href']
                elif kind == 'textStyle':
                    attrs = self.attrs(mark, {'color'}, location)
                    if attrs.get('color') is not None:
                        run['color'] = attrs['color']
                else:
                    self.issue(location, f'Style non représentable : {kind[:80]}')
            try:
                result.append(TextRun.model_validate(run).model_dump(mode='json'))
            except ValidationError:
                self.issue(location, 'Texte, lien ou couleur incompatible avec les notes Agent')
        return result

    def paragraphs(self, values, path, depth):
        runs = []
        for index, value in enumerate(values):
            location = f'{path}/{index}'
            value = self.node(value, location, depth)
            if value is None:
                continue
            if value['type'] != 'paragraph':
                self.issue(location, 'Paragraphe requis dans cette cellule ou cet item')
                continue
            attrs = self.attrs(value, {'textAlign'}, location)
            if attrs.get('textAlign') not in {None, 'left'}:
                self.issue(location, 'Alignement interne non représentable')
            if index:
                runs.append({'text': '\n'})
            runs.extend(self.runs(self.children(value, location), location, depth + 1))
        return runs

    def list_items(self, value, path, depth, indent=0):
        if indent > 6:
            self.issue(path, 'Liste imbriquée au-delà de six niveaux')
            return []
        kind = value['type']
        attrs = self.attrs(value, {'start'} if kind == 'orderedList' else set(), path)
        if kind == 'orderedList' and (type(attrs.get('start', 1)) is not int or attrs.get('start', 1) != 1):
            self.issue(path, 'Numérotation commençant après un non représentable')
        result = []
        for index, item in enumerate(self.children(value, path)):
            location = f'{path}/{index}'
            item = self.node(item, location, depth + 1)
            if item is None:
                continue
            if item['type'] != ('taskItem' if kind == 'taskList' else 'listItem'):
                self.issue(location, 'Type d’item incompatible avec la liste')
            attributes = self.attrs(item, {'checked'} if kind == 'taskList' else set(), location)
            checked = attributes.get('checked', False)
            if type(checked) is not bool:
                self.issue(location, 'État de case booléen requis')
                checked = False
            paragraphs, nested = [], []
            nested_started = False
            for child in self.children(item, location):
                if isinstance(child, dict) and child.get('type') == kind:
                    nested.append(child)
                    nested_started = True
                elif nested_started:
                    self.issue(location, 'Contenu après sous-liste non représentable sans changement d’ordre')
                else:
                    paragraphs.append(child)
            result.append({'runs': self.paragraphs(paragraphs, location, depth + 2),
                           'checked': checked, 'indent': indent})
            for index, child in enumerate(nested):
                child = self.node(child, location + '/nested', depth + 2)
                if child:
                    result.extend(self.list_items(child, f'{location}/nested/{index}', depth + 2, indent + 1))
        return result

    def table(self, value, path, depth):
        self.attrs(value, set(), path)
        rows, headers = [], []
        for index, row in enumerate(self.children(value, path)):
            location = f'{path}/{index}'
            row = self.node(row, location, depth + 1)
            if row is None:
                continue
            if row['type'] != 'tableRow':
                self.issue(location, 'Ligne de tableau requise')
            self.attrs(row, set(), location)
            cells, row_headers = [], []
            for position, cell in enumerate(self.children(row, location)):
                cell_path = f'{location}/{position}'
                cell = self.node(cell, cell_path, depth + 2)
                if cell is None:
                    continue
                if cell['type'] not in {'tableCell', 'tableHeader'}:
                    self.issue(cell_path, 'Cellule de tableau requise')
                attrs = self.attrs(cell, {'colspan', 'rowspan', 'colwidth'}, cell_path)
                if any(type(attrs.get(key, 1)) is not int or attrs.get(key, 1) != 1 for key in ('colspan', 'rowspan')):
                    self.issue(cell_path, 'Cellules fusionnées non représentables')
                if attrs.get('colwidth') is not None:
                    self.issue(cell_path, 'Largeur de colonne fixée non représentable')
                row_headers.append(cell['type'] == 'tableHeader')
                cells.append(self.paragraphs(self.children(cell, cell_path), cell_path, depth + 3))
            rows.append(cells)
            headers.append(row_headers)
        header = bool(headers and headers[0] and all(headers[0]))
        if (headers and any(headers[0]) and not header) or any(any(row) for row in headers[1:]):
            self.issue(path, 'En-têtes de tableau non représentables')
        return {'type': 'table', 'header': header, 'rows': rows}

    def blocks(self, values, path='', depth=0):
        blocks = []
        for index, value in enumerate(values):
            location = f'{path}/{index}'
            value = self.node(value, location, depth)
            if value is None:
                continue
            kind = value['type']
            if kind in {'paragraph', 'heading'}:
                attrs = self.attrs(value, {'textAlign'} if kind == 'paragraph' else {'level'}, location)
                block = {'type': kind, 'runs': self.runs(self.children(value, location), location, depth + 1)}
                if kind == 'heading':
                    block['level'] = attrs.get('level', 1)
                else:
                    block['align'] = attrs.get('textAlign') or 'left'
                blocks.append(block)
            elif kind in {'bulletList', 'orderedList', 'taskList'}:
                blocks.append({'type': 'list', 'kind': {'bulletList': 'bullet', 'orderedList': 'ordered',
                                                       'taskList': 'checklist'}[kind],
                               'items': self.list_items(value, location, depth)})
            elif kind == 'table':
                blocks.append(self.table(value, location, depth))
            elif kind == 'image':
                attrs = self.attrs(value, {'src', 'alt', 'title'}, location)
                source = attrs.get('src')
                if not isinstance(source, str) or source not in self.images:
                    self.issue(location, 'Image sans liaison explicite à une pièce sélectionnée')
                    continue
                if attrs.get('title') and attrs.get('alt') and attrs['title'] != attrs['alt']:
                    self.issue(location, 'Titre et texte alternatif distincts non représentables par une seule légende')
                blocks.append({'type': 'image', 'attachment_id': self.images[source],
                               'caption': attrs.get('alt') or attrs.get('title') or ''})
            else:
                self.issue(location, f'Bloc non représentable : {kind[:80]}')
        return blocks


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Champ JSON répété')
        result[key] = value
    return result


def convert_tiptap(source: bytes, *, image_bindings=None):
    converter = Conversion(image_bindings or {})
    try:
        if not isinstance(source, bytes) or not 0 < len(source) <= MAX_SOURCE_BYTES:
            raise ValueError('Source JSON bornée de 2 Mo requise')
        if not isinstance(converter.images, dict) or len(converter.images) > 20:
            raise ValueError('Liaisons d’images explicites bornées requises')
        value = json.loads(source.decode('utf-8-sig'), object_pairs_hook=_unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nombre JSON non fini')))
        value = converter.node(value, '')
        if value is None or value['type'] != 'doc':
            raise ValueError('Document TipTap requis')
        converter.attrs(value, set(), '')
        content = NoteContent.model_validate({'blocks': converter.blocks(converter.children(value, ''))})
        if converter.issues:
            return {'content': None, 'issues': converter.issues, 'can_import_rich': False}
        return {'content': content.model_dump(mode='json'), 'issues': [], 'can_import_rich': True}
    except (ValueError, TypeError, RecursionError, UnicodeDecodeError, ValidationError) as exc:
        converter.issue('', 'Source incompatible ou non représentable : ' + type(exc).__name__)
        return {'content': None, 'issues': converter.issues, 'can_import_rich': False}
