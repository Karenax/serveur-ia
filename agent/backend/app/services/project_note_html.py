"""XPilot's saved HTML to closed Agent blocks, without rendering or any IO.

Unknown markup/style blocks conversion. Embedded static raster images become
verified bytes with deterministic scoped IDs; no external resource is fetched.
"""
from app.operational_limits import DOCUMENT_IMPORT_BYTES
import base64
from dataclasses import dataclass, field
import hashlib
from html.parser import HTMLParser
from io import BytesIO
import json
import re
from uuid import UUID, uuid5
import warnings

from PIL import Image, UnidentifiedImageError

from ..project_note_schemas import NOTE_ATTACHMENT_BUDGET
from .project_note_conversion import convert_tiptap

MAX_HTML_BYTES = DOCUMENT_IMPORT_BYTES
MAX_IMAGE_BYTES = NOTE_ATTACHMENT_BUDGET
MAX_IMAGE_PIXELS = 16_000_000
VOID = {'br', 'img', 'input'}
LISTS = {'ul', 'ol'}
BLOCKS = {'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table', *LISTS}
MARKS = {'b': 'bold', 'strong': 'bold', 'i': 'italic', 'em': 'italic', 'u': 'underline',
         's': 'strike', 'strike': 'strike', 'del': 'strike', 'code': 'code'}


@dataclass
class Element:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element('root')
        self.stack = [self.root]
        self.nodes = 0

    def count(self):
        self.nodes += 1
        if self.nodes > 20_000 or len(self.stack) > 32:
            raise ValueError('HTML trop complexe')

    def handle_starttag(self, tag, attrs):
        self.count()
        if len(dict(attrs)) != len(attrs) or any(name.startswith('on') for name, _ in attrs):
            raise ValueError('Attributs HTML ambigus ou exécutables')
        element = Element(tag, dict(attrs))
        self.stack[-1].children.append(element)
        if tag not in VOID:
            self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if len(self.stack) <= 1 or self.stack[-1].tag != tag:
            raise ValueError('HTML non équilibré')
        self.stack.pop()

    def handle_data(self, value):
        self.count()
        self.stack[-1].children.append(value)

    def handle_decl(self, decl):
        raise ValueError('Fragment HTML de note requis')


class HtmlConversion:
    def __init__(self, planned_note_id, image_bindings):
        self.namespace = UUID(planned_note_id)
        self.bindings = image_bindings
        self.assets = {}
        self.issues = []

    def issue(self, message):
        if len(self.issues) < 100:
            self.issues.append({'path': 'html', 'message': message})

    def attrs(self, element, allowed):
        if set(element.attrs) - allowed:
            self.issue(f'Attributs non représentables sur {element.tag[:40]}')
        return element.attrs

    def style(self, raw):
        result = {}
        if not isinstance(raw, str):
            self.issue('Style CSS textuel requis')
            return result
        for part in raw.split(';'):
            if not part.strip():
                continue
            key, separator, value = part.partition(':')
            key = key.strip().lower()
            if not separator or key in result:
                self.issue('Style CSS ambigu')
                continue
            result[key] = value.strip().lower()
        return result

    def color(self, value):
        if not isinstance(value, str):
            self.issue('Couleur textuelle requise')
            return '#000000'
        value = value.lower()
        if re.fullmatch('#[0-9a-f]{6}', value):
            return value
        if re.fullmatch('#[0-9a-f]{3}', value):
            return '#' + ''.join(char * 2 for char in value[1:])
        match = re.fullmatch(r'rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)', value)
        if match and all(int(item) <= 255 for item in match.groups()):
            return '#' + ''.join(f'{int(item):02x}' for item in match.groups())
        self.issue('Couleur CSS non représentable')
        return '#000000'

    def image(self, element):
        attrs = self.attrs(element, {'src', 'alt', 'title'})
        source = attrs.get('src')
        if not isinstance(source, str):
            self.issue('Source d’image requise')
            return None
        if source in self.bindings:
            return {'type': 'image', 'attrs': {'src': source, 'alt': attrs.get('alt'), 'title': attrs.get('title')}}
        match = re.fullmatch(r'data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=]+)', source)
        if not match or len(match[2]) > ((MAX_IMAGE_BYTES + 2) // 3) * 4:
            self.issue('Image externe, active ou trop volumineuse : choisir une copie raster explicite')
            return None
        try:
            data = base64.b64decode(match[2], validate=True)
            if not 0 < len(data) <= MAX_IMAGE_BYTES:
                raise ValueError('Image bornée requise')
            expected = {'image/png': 'PNG', 'image/jpeg': 'JPEG', 'image/webp': 'WEBP'}[match[1]]
            sha = hashlib.sha256(data).hexdigest()
            key = 'embedded-image:' + sha
            attachment_id = str(uuid5(self.namespace, key))
            cached = self.assets.get(attachment_id)
            if cached is not None:
                if cached['content_type'] != match[1]:
                    raise ValueError('Type déclaré différent de la même image')
                self.bindings[key] = attachment_id
                return {'type': 'image', 'attrs': {'src': key, 'alt': attrs.get('alt'), 'title': attrs.get('title')}}
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(BytesIO(data)) as image:
                    if (image.format != expected or image.width * image.height > MAX_IMAGE_PIXELS
                            or getattr(image, 'n_frames', 1) != 1):
                        raise ValueError('Raster statique borné requis')
                    image.verify()
                with Image.open(BytesIO(data)) as image:
                    image.load()
            extension = {'PNG': 'png', 'JPEG': 'jpg', 'WEBP': 'webp'}[expected]
            self.assets[attachment_id] = {'id': attachment_id, 'filename': f'image-{sha[:12]}.{extension}',
                'content_type': match[1], 'sha256': sha, 'size_bytes': len(data), 'data': data}
            self.bindings[key] = attachment_id
            return {'type': 'image', 'attrs': {'src': key, 'alt': attrs.get('alt'), 'title': attrs.get('title')}}
        except (ValueError, OSError, SyntaxError, UnidentifiedImageError, Image.DecompressionBombWarning,
                Image.DecompressionBombError) as exc:
            self.issue('Image intégrée non décodable : ' + type(exc).__name__)
            return None

    def inline(self, children, inherited=None):
        marks = {} if inherited is None else inherited
        result = []
        for child in children:
            if isinstance(child, str):
                # Split long browser text nodes without changing their text.
                result.extend({'type': 'text', 'text': child[index:index + 5000], 'marks': list(marks.values())}
                              for index in range(0, len(child), 5000))
                continue
            if child.tag == 'br':
                self.attrs(child, set())
                result.append({'type': 'hardBreak'})
            elif child.tag == 'img':
                image = self.image(child)
                if image:
                    result.append(image)
            elif child.tag in {*MARKS, 'span', 'font', 'a', 'label'}:
                next_marks = dict(marks)
                allowed = {'style'}
                if child.tag == 'font':
                    allowed |= {'color'}
                if child.tag == 'a':
                    allowed |= {'href', 'target', 'rel'}
                self.attrs(child, allowed)
                if child.tag in MARKS:
                    next_marks[MARKS[child.tag]] = {'type': MARKS[child.tag]}
                if child.tag == 'a':
                    next_marks['link'] = {'type': 'link', 'attrs': {'href': child.attrs.get('href')}}
                if 'color' in child.attrs:
                    next_marks['textStyle'] = {'type': 'textStyle', 'attrs': {'color': self.color(child.attrs['color'])}}
                styles = self.style(child.attrs['style']) if 'style' in child.attrs else {}
                for key, value in styles.items():
                    if key == 'color':
                        next_marks['textStyle'] = {'type': 'textStyle', 'attrs': {'color': self.color(value)}}
                    elif key == 'font-weight' and value in {'bold', '700'}:
                        next_marks['bold'] = {'type': 'bold'}
                    elif key == 'font-style' and value == 'italic':
                        next_marks['italic'] = {'type': 'italic'}
                    elif key in {'text-decoration', 'text-decoration-line'} and value in {'underline', 'line-through'}:
                        style = 'underline' if value == 'underline' else 'strike'
                        next_marks[style] = {'type': style}
                    else:
                        self.issue('Style en ligne non représentable : ' + key[:40])
                result.extend(self.inline(child.children, next_marks))
            else:
                self.issue('Élément en ligne non représentable : ' + child.tag[:40])
        return result

    def paragraph(self, element):
        attrs = self.attrs(element, {'style', 'align'})
        styles = self.style(attrs['style']) if 'style' in attrs else {}
        if set(styles) - {'text-align'}:
            self.issue('Style de paragraphe non représentable')
        align = styles.get('text-align', attrs.get('align', 'left'))
        kind = 'heading' if re.fullmatch('h[1-6]', element.tag) else 'paragraph'
        values, current = [], []
        def flush():
            values.append({'type': kind, 'attrs': {'level': int(element.tag[1])} if kind == 'heading' else {'textAlign': align},
                           'content': list(current)})
            current.clear()
        for node in self.inline(element.children):
            if node['type'] == 'image':
                if current:
                    flush()
                values.append(node)
            else:
                current.append(node)
        if current or not values:
            flush()
        return values

    def listing(self, element):
        attrs = self.attrs(element, {'class', 'start'})
        checklist = attrs.get('class') == 'note-task-list'
        if attrs.get('class') and not checklist:
            self.issue('Classe de liste non représentable')
        kind = 'taskList' if checklist else 'orderedList' if element.tag == 'ol' else 'bulletList'
        items = []
        for child in element.children:
            if isinstance(child, str) and not child.strip():
                continue
            if isinstance(child, str) or child.tag != 'li':
                self.issue('Item de liste HTML requis')
                continue
            self.attrs(child, set())
            checked, children = False, []
            for value in child.children:
                if isinstance(value, Element) and value.tag == 'input':
                    self.attrs(value, {'type', 'checked', 'aria-label'})
                    if not checklist or value.attrs.get('type') != 'checkbox':
                        self.issue('Case HTML réservée aux listes à cocher')
                    checked = 'checked' in value.attrs
                else:
                    children.append(value)
            item = {'type': 'taskItem' if checklist else 'listItem', 'content': self.blocks(children)}
            if checklist:
                item['attrs'] = {'checked': checked}
            items.append(item)
        value = {'type': kind, 'content': items}
        if kind == 'orderedList' and 'start' in attrs:
            try:
                value['attrs'] = {'start': int(attrs['start'])}
            except (TypeError, ValueError):
                self.issue('Départ de numérotation entier requis')
        return value

    def table(self, element):
        self.attrs(element, set())
        rows = []
        def collect(children):
            for child in children:
                if isinstance(child, str) and not child.strip():
                    continue
                if isinstance(child, str):
                    self.issue('Texte hors cellule non représentable')
                elif child.tag in {'thead', 'tbody', 'tfoot'}:
                    self.attrs(child, set())
                    collect(child.children)
                elif child.tag == 'tr':
                    self.attrs(child, set())
                    cells = []
                    for cell in child.children:
                        if isinstance(cell, str) and not cell.strip():
                            continue
                        if isinstance(cell, str) or cell.tag not in {'td', 'th'}:
                            self.issue('Cellule HTML requise')
                            continue
                        attrs = self.attrs(cell, {'colspan', 'rowspan'})
                        try:
                            attrs = {key: int(value) for key, value in attrs.items()}
                        except (TypeError, ValueError):
                            self.issue('Dimensions de cellule entières requises')
                            attrs = {}
                        cells.append({'type': 'tableHeader' if cell.tag == 'th' else 'tableCell',
                                      'attrs': attrs, 'content': self.blocks(cell.children)})
                    rows.append({'type': 'tableRow', 'content': cells})
                else:
                    self.issue('Élément de tableau non représentable : ' + child.tag[:40])
        collect(element.children)
        return {'type': 'table', 'content': rows}

    def blocks(self, children):
        result, pending = [], []
        def flush():
            if pending and not all(isinstance(item, str) and not item.strip() for item in pending):
                result.extend(self.paragraph(Element('p', children=list(pending))))
            pending.clear()
        for child in children:
            if isinstance(child, str) or child.tag not in BLOCKS:
                pending.append(child)
                continue
            flush()
            if child.tag in LISTS:
                result.append(self.listing(child))
            elif child.tag == 'table':
                result.append(self.table(child))
            elif child.tag == 'div' and any(isinstance(item, Element) and item.tag in BLOCKS for item in child.children):
                self.attrs(child, set())
                result.extend(self.blocks(child.children))
            else:
                result.extend(self.paragraph(child))
        flush()
        return result


def convert_html(source, *, planned_note_id, image_bindings=None):
    conversion = HtmlConversion(planned_note_id, dict(image_bindings or {}))
    try:
        if not isinstance(source, bytes) or len(source) > MAX_HTML_BYTES:
            raise ValueError('Source HTML bornée requise')
        parser = Tree()
        parser.feed(source.decode('utf-8-sig'))
        parser.close()
        if len(parser.stack) != 1:
            raise ValueError('HTML non fermé')
        document = {'type': 'doc', 'content': conversion.blocks(parser.root.children)}
        # Images have their own managed IDs after decoding, including dataURI.
        converted = convert_tiptap(json.dumps(document, ensure_ascii=False).encode('utf-8'),
                                   image_bindings=conversion.bindings)
        issues = conversion.issues + converted['issues']
        return {'content': converted['content'] if not issues else None,
                'issues': issues[:100], 'can_import_rich': not issues and converted['can_import_rich'],
                'embedded_assets': conversion.assets}
    except (ValueError, TypeError, RecursionError, UnicodeDecodeError) as exc:
        conversion.issue('HTML incompatible : ' + type(exc).__name__)
        return {'content': None, 'issues': conversion.issues, 'can_import_rich': False, 'embedded_assets': {}}


def html_plain_text(source):
    """Explicit fallback only; preserves source separately and executes nothing."""
    if not isinstance(source, bytes) or len(source) > MAX_HTML_BYTES:
        raise ValueError('Source HTML bornée requise')
    parser = Tree()
    parser.feed(source.decode('utf-8-sig'))
    parser.close()
    if len(parser.stack) != 1:
        raise ValueError('HTML non fermé')
    chunks = []
    def visit(children):
        for child in children:
            if isinstance(child, str):
                chunks.append(child)
            elif child.tag in {'script', 'style', 'iframe', 'object', 'embed', 'head', 'img', 'input'}:
                continue
            elif child.tag == 'br':
                chunks.append('\n')
            else:
                if child.tag in BLOCKS | {'li', 'tr'}:
                    chunks.append('\n')
                visit(child.children)
                if child.tag in BLOCKS | {'li', 'tr'}:
                    chunks.append('\n')
                elif child.tag in {'td', 'th'}:
                    chunks.append('\t')
    visit(parser.root.children)
    return ''.join(chunks).strip()
