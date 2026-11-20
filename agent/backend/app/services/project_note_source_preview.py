"""Pure preview of explicitly selected XPilot note files, never a directory scan.

Returns a complete byte manifest and independent conversions. The original
bytes remain caller-owned: an eventual import must copy all of them unchanged.
Source actors/timestamps are descriptions, never authenticated identities.
"""
from app.operational_limits import DOCUMENT_IMPORT_BYTES
from datetime import datetime
import hashlib
import json
from pathlib import PurePosixPath
import re
from uuid import UUID, uuid5

from backend.app.project_note_schemas import NOTE_ATTACHMENT_BUDGET, NoteContent, content_text
from .project_note_conversion import convert_tiptap, _unique
from .project_note_html import convert_html, html_plain_text

MAX_IMPORT_BYTES = DOCUMENT_IMPORT_BYTES
MAX_IMPORT_FILES = 200
MAX_IMPORT_VERSIONS = 50
MAX_TEXT_BYTES = 2_000_000
CONTENT_FILES = {'content.json', 'content.txt', 'content.html'}
OFFICE = {'.rtf', '.doc', '.docx', '.xls', '.xlsx'}
LEGACY_TEXT = {'.html', '.htm', '.txt', '.md'}


def _filename(value):
    if (not isinstance(value, str) or not value or len(value) > 255 or value in {'.', '..'}
            or value != value.rstrip(' .') or any(ord(char) < 32 or char in '/\\:<>"|?*' for char in value)
            or value.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
                                               *(f'LPT{i}' for i in range(1, 10))}):
        raise ValueError('Nom de fichier source simple et portable requis')


def _path(value):
    if not isinstance(value, str) or len(value) > 1024:
        raise ValueError('Chemin source borné requis')
    parts = value.split('/')
    for part in parts:
        _filename(part)
    if len(parts) == 1 and value in CONTENT_FILES | {'manifest.json'}:
        return 'content'
    if len(parts) == 2 and parts[0] == 'attachments':
        return 'attachment'
    if len(parts) == 3 and parts[0] == 'versions' and parts[2] in CONTENT_FILES:
        if not re.fullmatch(r'\d{8}T\d{12}Z', parts[1]):
            raise ValueError('Clé de version XPilot non reconnue')
        datetime.strptime(parts[1], '%Y%m%dT%H%M%S%fZ')
        return 'version'
    raise ValueError('Fichier hors du contenu, versions ou pièces de la note sélectionnée')


def _checked_files(files, *, external=False, legacy=False):
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_IMPORT_FILES:
        raise ValueError('Sélection explicite de 1 à 200 fichiers requise')
    if any(not isinstance(name, str) for name in files):
        raise ValueError('Noms source textuels requis')
    seen, total, result = set(), 0, []
    attachments, attachment_bytes = 0, 0
    for name in sorted(files):
        if external or legacy:
            _filename(name)
            kind = 'legacy_text' if legacy else 'external'
        else:
            kind = _path(name)
        if name.casefold() in seen:
            raise ValueError('Noms de fichiers source ambigus par la casse')
        seen.add(name.casefold())
        value = files[name]
        if not isinstance(value, bytes):
            raise ValueError('Octets source requis')
        total += len(value)
        if total > MAX_IMPORT_BYTES:
            raise ValueError('Import limité à 50 Mio, sans omission de fichier')
        if kind in {'content', 'version'} and not name.endswith('content.html') and len(value) > MAX_TEXT_BYTES:
            raise ValueError('Contenu ou manifeste limité à 2 Mo par fichier')
        if kind == 'legacy_text' and PurePosixPath(name).suffix.casefold() not in {'.html', '.htm'} and len(value) > MAX_TEXT_BYTES:
            raise ValueError('Texte source limité à 2 Mo')
        if kind == 'external' and not value:
            raise ValueError('Document externe non vide requis')
        if kind == 'attachment':
            attachments += 1
            attachment_bytes += len(value)
            if not 0 < len(value) <= NOTE_ATTACHMENT_BUDGET or attachments > 20 or attachment_bytes > NOTE_ATTACHMENT_BUDGET:
                raise ValueError('Pièces source limitées à 20 fichiers et 25 Mio au total')
        result.append({'relative_path': name, 'kind': kind, 'size_bytes': len(value),
                       'sha256': hashlib.sha256(value).hexdigest()})
    return result, total


def _plain(source):
    if not isinstance(source, bytes) or len(source) > MAX_TEXT_BYTES:
        raise ValueError('Texte source borné requis')
    text = source.decode('utf-8-sig')
    runs = [{'text': text[index:index + 5000]} for index in range(0, len(text), 5000)]
    return NoteContent.model_validate({'blocks': [{'type': 'paragraph', 'runs': runs}]}).model_dump(mode='json')


def _version(files, prefix, *, image_bindings, mode, title, planned_note_id):
    json_source = files.get(prefix + 'content.json')
    plain_source = files.get(prefix + 'content.txt')
    if mode == 'plain':
        if plain_source is None:
            html_source = files.get(prefix + 'content.html')
            if html_source is not None:
                try:
                    plain_source = html_plain_text(html_source).encode('utf-8')
                except (ValueError, UnicodeDecodeError, RecursionError):
                    plain_source = None
            if plain_source is None:
                return {'content': None, 'can_import_rich': False,
                        'issues': [{'path': prefix, 'message': 'Aucun texte convertible disponible pour le repli explicite'}]}
        try:
            return {'content': _plain(plain_source), 'can_import_rich': True, 'issues': [],
                    'conversion_mode': 'explicit_plain', 'styles_preserved': False}
        except (ValueError, UnicodeDecodeError):
            return {'content': None, 'can_import_rich': False,
                    'issues': [{'path': prefix, 'message': 'Texte source non représentable sans perte'}]}
    html_source = files.get(prefix + 'content.html')
    if html_source is not None:
        # XPilot's real editor persists HTML/text and may leave JSON stale.
        converted = convert_html(html_source, planned_note_id=planned_note_id, image_bindings=image_bindings)
        return {key: converted[key] for key in ('content', 'can_import_rich', 'issues')} | {
            'conversion_mode': 'html', 'source_json_kept_as_original': json_source is not None,
            'embedded_images': [{key: item[key] for key in ('id', 'filename', 'content_type', 'size_bytes', 'sha256')}
                                for _, item in sorted(converted['embedded_assets'].items())]}
    if json_source is None:
        return {'content': None, 'can_import_rich': False,
                'issues': [{'path': prefix, 'message': 'Pas de JSON riche : choisir explicitement le texte disponible'}]}
    converted = convert_tiptap(json_source, image_bindings=image_bindings)
    if converted['can_import_rich'] and plain_source is not None:
        try:
            content = NoteContent.model_validate(converted['content'])
            # XPilot's generated fallback JSON adds the title as heading1,
            # while its editable HTML/text do not necessarily contain it.
            blocks = content.blocks
            if (blocks and blocks[0].type == 'heading' and blocks[0].level == 1
                    and ''.join(run.text for run in blocks[0].runs).strip() == title):
                content = NoteContent(blocks=blocks[1:])
            def normalized(value):
                return value.replace('\u00a0', ' ').strip()
            if normalized(content_text(content)) != normalized(plain_source.decode('utf-8-sig')):
                return {'content': None, 'can_import_rich': False, 'conversion_mode': 'rich',
                        'issues': [{'path': prefix, 'message': 'JSON et texte source divergent : convertir le HTML effectif ou choisir le texte explicitement'}]}
        except (ValueError, UnicodeDecodeError):
            return {'content': None, 'can_import_rich': False, 'conversion_mode': 'rich',
                    'issues': [{'path': prefix, 'message': 'Comparaison du texte source impossible sans perte'}]}
    return {**converted, 'conversion_mode': 'rich'}


def preview_source(files, *, planned_note_id, mode='rich'):
    """planned_note_id is allocated by the caller; it grants no access rights."""
    if (not isinstance(planned_note_id, str) or str(UUID(planned_note_id)) != planned_note_id
            or not isinstance(mode, str) or mode not in {'rich', 'plain'}):
        raise ValueError('Identité de préparation et mode explicites requis')
    if isinstance(files, dict) and len(files) == 1:
        name = next(iter(files))
        if isinstance(name, str) and PurePosixPath(name).suffix.casefold() in OFFICE:
            inventory, total = _checked_files(files, external=True)
            return _seal({'format': 'agent-note-source-preview', 'version': 1, 'kind': 'external_office',
                    'title': name, 'read_only': True, 'editable': False, 'total_bytes': total,
                    'files': inventory, 'source_sha256': _digest(inventory), 'versions': [],
                    'can_apply': True, 'planned_note_id': planned_note_id})
        if isinstance(name, str) and PurePosixPath(name).suffix.casefold() in LEGACY_TEXT:
            inventory, total = _checked_files(files, legacy=True)
            is_html = PurePosixPath(name).suffix.casefold() in {'.html', '.htm'}
            if is_html:
                converted = _version({'content.html': files[name]}, '', image_bindings={}, mode=mode,
                                     title=PurePosixPath(name).stem, planned_note_id=planned_note_id)
            else:
                converted = {'content': _plain(files[name]), 'can_import_rich': True,
                             'issues': [], 'conversion_mode': 'source_plain'}
            embedded, issues = _asset_quota(inventory, [converted])
            return _seal({'format': 'agent-note-source-preview', 'version': 1, 'kind': 'legacy_text_note',
                    'title': PurePosixPath(name).stem, 'read_only': True, 'editable': True,
                    'total_bytes': total, 'files': inventory, 'source_sha256': _digest(inventory),
                    'versions': [{'source_key': 'current', 'source_actor': None, **converted}],
                    'source_metadata': {}, 'planned_note_id': planned_note_id, 'conversion_mode': mode,
                    'can_apply': not issues and converted['can_import_rich'], 'originals_must_be_copied': True,
                    'embedded_images': embedded, 'issues': issues})
    inventory, total = _checked_files(files)
    if 'manifest.json' not in files or not (CONTENT_FILES & files.keys()):
        raise ValueError('Manifeste et contenu courant de la note sélectionnée requis')
    manifest = json.loads(files['manifest.json'].decode('utf-8-sig'), object_pairs_hook=_unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('JSON non fini')))
    if (not isinstance(manifest, dict) or manifest.get('type') != 'xpilot_tiptap_note'
            or not isinstance(manifest.get('title'), str) or not manifest['title'].strip()
            or len(manifest['title']) > 255 or any(ord(char) < 32 for char in manifest['title'])
            or type(manifest.get('version')) is not int or manifest['version'] < 1):
        raise ValueError('Manifeste de note XPilot incompatible')
    keys = sorted({name.split('/')[1] for name in files if name.startswith('versions/')})
    if len(keys) > MAX_IMPORT_VERSIONS or manifest['version'] != len(keys) + 1:
        raise ValueError('Historique source incomplet ou dépassant 50 versions : aucun import partiel implicite')
    for field in ('created_by', 'updated_by', 'created_at', 'updated_at'):
        if field in manifest and (not isinstance(manifest[field], str) or len(manifest[field]) > 500):
            raise ValueError('Métadonnées descriptives source incompatibles')
    bindings = {name: str(uuid5(UUID(planned_note_id), name)) for name in files if name.startswith('attachments/')}
    versions = []
    for key in keys:
        # XPilot backs up no actor/manifest per historical version. Never infer it.
        versions.append({'source_key': key, 'source_actor': None,
                         **_version(files, f'versions/{key}/', image_bindings=bindings, mode=mode, title=manifest['title'].strip(), planned_note_id=planned_note_id)})
    versions.append({'source_key': 'current', 'source_actor': manifest.get('updated_by'),
                     **_version(files, '', image_bindings=bindings, mode=mode, title=manifest['title'].strip(), planned_note_id=planned_note_id)})
    embedded, issues = _asset_quota(inventory, versions)
    return _seal({'format': 'agent-note-source-preview', 'version': 1, 'kind': 'xpilot_note',
            'title': manifest['title'].strip(), 'read_only': True, 'editable': True,
            'source_metadata': {key: manifest[key] for key in ('created_by', 'updated_by', 'created_at', 'updated_at') if key in manifest},
            'source_sha256': _digest(inventory), 'total_bytes': total, 'files': inventory,
            'versions': versions, 'can_apply': not issues and all(row['can_import_rich'] for row in versions),
            'embedded_images': embedded, 'issues': issues,
            'planned_note_id': planned_note_id, 'image_bindings': bindings,
            'originals_must_be_copied': True, 'conversion_mode': mode})


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
                                      allow_nan=False).encode('utf-8')).hexdigest()


def _seal(value):
    return {**value, 'preview_sha256': _digest(value)}


def _asset_quota(inventory, versions):
    embedded = {item['id']: item for version in versions for item in version.get('embedded_images', [])}
    attachments = [item for item in inventory if item['kind'] == 'attachment']
    issues = []
    if (len(attachments) + len(embedded) > 20
            or sum(item['size_bytes'] for item in attachments) + sum(item['size_bytes'] for item in embedded.values()) > NOTE_ATTACHMENT_BUDGET):
        issues.append({'path': 'images', 'message': 'Images historiques et pièces dépassant 20 éléments/25 Mio : aucun import partiel implicite'})
    return list(embedded.values()), issues
