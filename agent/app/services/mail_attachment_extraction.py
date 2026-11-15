"""Bounded text extraction for mail attachments; originals are never executed."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import uuid
from zipfile import ZipFile

from .library_extraction import MAX_TEXT

VERSION = 'mail-attachments-v1'
INTERPRETATION_REVISION = 2
MAX_BYTES = 50 * 1024**2
MAX_ARCHIVE_BYTES = 100 * 1024**2
MAX_ARCHIVE_MEMBERS = 200
TEXT_SUFFIXES = {'.txt', '.md', '.csv', '.ics', '.xml', '.json', '.log'}
IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tif', '.tiff'}
MIME_SUFFIXES = {
    'application/pdf': '.pdf', 'text/plain': '.txt', 'text/calendar': '.ics',
    'application/ics': '.ics', 'text/csv': '.csv', 'text/html': '.html',
    'image/jpeg': '.jpg', 'image/png': '.png', 'image/gif': '.gif',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
    'application/zip': '.zip', 'application/x-zip-compressed': '.zip',
}


def suffix_for(filename, mime):
    return MIME_SUFFIXES.get(mime) or Path(filename).suffix.casefold()


def _receipt_hash(items):
    return hashlib.sha256(json.dumps(items, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def extract_attachment(data, filename, mime, storage):
    """Reuse extraction by byte identity and format, independently of project ownership."""
    suffix = suffix_for(filename, mime)
    revision = ':office-images-v2' if suffix in {'.docx', '.pptx'} else ''
    key = hashlib.sha256((VERSION + suffix + revision).encode() + data).hexdigest()
    directory = Path(storage) / 'mail-attachments' / 'v1'
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / (key + '.json')
    if receipt.is_file():
        saved = json.loads(receipt.read_text(encoding='utf-8'))
        if saved.get('digest') != _receipt_hash(saved['items']):
            raise ValueError('Reçu d’extraction incompatible')
        return saved['items']
    if not data or len(data) > MAX_BYTES:
        return [_state('empty' if not data else 'too_large')]
    from .document_sandbox import extract
    with tempfile.TemporaryDirectory(prefix='attachment-', dir=directory) as temporary:
        path = Path(temporary) / ('attachment' + suffix)
        path.write_bytes(data)
        items = extract(path, path.name, 'mail_attachment')
        _recognize(items, path, directory)
    if sum(len(item['text']) for item in items) > MAX_TEXT:
        raise ValueError('Texte de pièce jointe supérieur à 2 millions de caractères')
    # Transient failures are retried; successful/unsupported interpretations are reusable.
    if not any(item['status'] in {'failed', 'ocr_required'} for item in items):
        temporary = directory / (uuid.uuid4().hex + '.part')
        temporary.write_text(json.dumps({'items': items, 'digest': _receipt_hash(items)},
                                        ensure_ascii=False), encoding='utf-8')
        temporary.replace(receipt)
    return items


def _state(status, **locator):
    return {'text': '', 'kind': 'attachment', 'status': status, 'locator': locator}


def _office_images(path, prefix):
    result = []
    with ZipFile(path) as archive:
        _check_archive(archive)
        for name in archive.namelist():
            if name.startswith(prefix) and Path(name).suffix.casefold() in IMAGE_SUFFIXES:
                result.append(_state('ocr_required', image=True, archive_member=name, archive_chain=[name]))
    return result


def _extract_local(path, filename, *, depth=0, budget=None):
    """Runs inside the existing resource/time limited document subprocess."""
    from .library_extraction import _extract_local as library_extract
    suffix = Path(filename).suffix.casefold()
    if suffix in IMAGE_SUFFIXES:
        return [_state('ocr_required', image=True)]
    if suffix in TEXT_SUFFIXES:
        from backend.app.services.cdc_extraction import _decode_text
        return [{'text': _decode_text(path.read_bytes()), 'kind': 'attachment',
                 'status': 'extracted', 'locator': {}}]
    if suffix == '.pptx':
        from defusedxml import ElementTree
        with ZipFile(path) as archive:
            _check_archive(archive)
            names = [name for name in archive.namelist()
                     if name.startswith('ppt/slides/slide') and name.endswith('.xml')
                     and name[len('ppt/slides/slide'):-4].isdigit()]
            names.sort(key=lambda name: int(name[len('ppt/slides/slide'):-4]))
            result = []
            for name in names:
                root = ElementTree.fromstring(archive.read(name))
                text = '\n'.join(node.text for node in root.iter()
                                 if node.tag == '{http://schemas.openxmlformats.org/drawingml/2006/main}t' and node.text)
                result.append({'text': text, 'kind': 'attachment',
                    'status': 'extracted' if text.strip() else 'empty',
                    'locator': {'slide': int(name[len('ppt/slides/slide'):-4])}})
            return (result or [_state('empty')]) + _office_images(path, 'ppt/media/')
    if suffix == '.zip':
        if depth >= 2:
            return [_state('unsupported', reason='archive_depth')]
        budget = budget if budget is not None else {'bytes': 0, 'members': 0}
        result = []
        with ZipFile(path) as archive, tempfile.TemporaryDirectory(prefix='attachment-zip-') as directory:
            _check_archive(archive)
            for member in archive.infolist():
                if member.is_dir():
                    continue
                budget['bytes'] += member.file_size
                budget['members'] += 1
                if budget['bytes'] > MAX_ARCHIVE_BYTES or budget['members'] > MAX_ARCHIVE_MEMBERS:
                    raise ValueError('Archive de pièces jointes trop volumineuse')
                if member.flag_bits & 1:
                    result.append(_state('encrypted', archive_member=member.filename))
                    continue
                # Never extract member paths; names remain provenance only.
                target = Path(directory) / (uuid.uuid4().hex + Path(member.filename).suffix.casefold())
                target.write_bytes(archive.read(member))
                try:
                    items = _extract_local(target, target.name, depth=depth + 1, budget=budget)
                except Exception as exc:
                    items = [_state('failed', error_type=type(exc).__name__, extraction_error=str(exc)[:300])]
                for item in items:
                    nested = item['locator'].get('archive_member')
                    item['locator']['archive_member'] = member.filename + ('/' + nested if nested else '')
                    item['locator']['archive_chain'] = [member.filename] + item['locator'].get('archive_chain', [])
                    result.append(item)
        return result or [_state('empty')]
    if suffix not in {'.pdf', '.docx', '.xlsx', '.xlsm', '.html', '.htm'}:
        return [_state('unsupported')]
    if suffix in {'.html', '.htm'}:
        from html.parser import HTMLParser
        from backend.app.services.cdc_extraction import _decode_text

        class PlainText(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.hidden, self.parts = 0, []

            def handle_starttag(self, tag, attrs):
                if tag in {'head', 'script', 'style', 'noscript'}:
                    self.hidden += 1

            def handle_endtag(self, tag):
                if tag in {'head', 'script', 'style', 'noscript'}:
                    self.hidden = max(0, self.hidden - 1)

            def handle_data(self, data):
                if not self.hidden and data.strip():
                    self.parts.append(data.strip())

        parser = PlainText()
        parser.feed(_decode_text(path.read_bytes()))
        return [{'text': '\n'.join(parser.parts), 'kind': 'attachment', 'status': 'extracted', 'locator': {}}]
    try:
        items = library_extract(path, filename)
    except Exception:
        if suffix != '.pdf':
            raise
        # Some supplier PDFs use AES restrictions unsupported by this pypdf install.
        # The existing local PDF renderer can read them without adding dependencies.
        from .pdf_render import runtime_python
        from .document_sandbox import extract
        python = runtime_python()
        if not python.is_file():
            raise
        items = extract(path, filename, 'mail_pdfium', python=python)
    if suffix == '.docx':
        for item in items:
            if not item['text'].strip():
                item['status'] = 'empty'
        return items + _office_images(path, 'word/media/')
    if suffix in {'.xlsx', '.xlsm'}:
        # Preserve the sheet/range while avoiding one embedding request per short row.
        sheets = {}
        for item in items:
            name = item['locator']['sheet']
            sheets.setdefault(name, []).append(item)
        return [{'text': '\n'.join(item['text'] for item in rows), 'kind': 'attachment',
                 'status': 'extracted', 'locator': {'sheet': name,
                     'range': rows[0]['locator']['range'].split(':')[0] + ':' + rows[-1]['locator']['range'].split(':')[-1]}}
                for name, rows in sheets.items()]
    return items


def _extract_pdfium(path):
    import pypdfium2 as pdfium
    items = []
    size = 0
    with pdfium.PdfDocument(str(path)) as document:
        if len(document) > 2000:
            raise ValueError('Document limité à 2000 pages')
        for index in range(len(document)):
            page = document[index]
            try:
                textpage = page.get_textpage()
                try:
                    text = textpage.get_text_range()
                finally:
                    textpage.close()
            finally:
                page.close()
            size += len(text)
            if size > MAX_TEXT:
                raise ValueError('Texte extrait supérieur à 2 millions de caractères')
            items.append({'text': text, 'kind': 'document_page',
                'status': 'extracted' if text.strip() else 'ocr_required',
                'locator': {'physical_page': index + 1, 'printed_page': None,
                            'extractor': 'pypdfium2', 'visual_review_required': len(text.strip()) < 30}})
    return items


def _check_archive(archive):
    entries = archive.infolist()
    if (len(entries) > 10000 or sum(item.file_size for item in entries) > MAX_ARCHIVE_BYTES
            or any(item.file_size > MAX_BYTES for item in entries)):
        raise ValueError('Document décompressé trop volumineux')


def _normalize_image(path):
    """Decode untrusted images only inside the limited document subprocess."""
    from PIL import Image, ImageOps
    with Image.open(path) as image:
        normalized = ImageOps.exif_transpose(image).convert('RGB')
    try:
        normalized.thumbnail((9500, 9500))
        output = path.with_name(uuid.uuid4().hex + '.png')
        normalized.save(output)
    finally:
        normalized.close()
    return {'path': str(output)}


def _recognize(items, path, storage):
    pending = [item for item in items if item['status'] == 'ocr_required']
    if not pending:
        return
    from .library_ocr import powershell, profile, recognize_page
    try:
        settings = profile()
    except Exception as exc:
        for item in pending:
            item['locator']['ocr_error'] = type(exc).__name__ + ': ' + str(exc)[:250]
        return
    original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    for item in pending:
        try:
            chain = item['locator'].get('archive_chain')
            if chain:
                data = path.read_bytes()
                for name in chain:
                    with ZipFile(BytesIO(data)) as archive:
                        entry = archive.getinfo(name)
                        if entry.file_size > MAX_BYTES:
                            raise ValueError('Membre trop volumineux pour l’OCR')
                        data = archive.read(entry)
                with tempfile.TemporaryDirectory(prefix='ocr-member-', dir=path.parent) as directory:
                    original = Path(directory) / ('member' + Path(chain[-1]).suffix.casefold())
                    original.write_bytes(data)
                    local = {**item, 'locator': {k: v for k, v in item['locator'].items()
                             if k not in {'archive_chain', 'archive_member'}}}
                    _recognize([local], original, storage)
                    item['text'], item['status'] = local['text'], local['status']
                    item['locator'].update(local['locator'])
                continue
            if item['locator'].get('image'):
                from .document_sandbox import extract
                image_path = Path(extract(path, path.name, 'mail_image')[0]['path'])
                recognized = powershell('-InputImage', str(image_path.resolve()), '-LanguageTag', settings['language'])
            else:
                recognized = recognize_page(path, item['locator']['physical_page'], storage.parent.parent,
                                            original_hash, settings)
            item['text'] = recognized['text']
            item['status'] = 'extracted' if item['text'].strip() else 'empty'
            item['locator']['ocr'] = {'engine': settings['engine'], 'language': settings['language']}
        except Exception as exc:
            item['status'] = 'ocr_required'
            item['locator']['ocr_error'] = type(exc).__name__ + ': ' + str(exc)[:250]
