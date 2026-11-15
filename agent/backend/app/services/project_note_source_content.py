"""Pure conversion/provenance checks over selected bytes; no runtime imports."""
from pathlib import PurePosixPath
from uuid import UUID, uuid5

from app.services.deliverable_manifest import freeze
from ..project_note_schemas import NoteContent
from .project_note_binary import content_type
from .project_note_html import convert_html
from .project_note_source_preview import preview_source


def _office_content(title):
    return NoteContent.model_validate({'blocks': [{'type': 'paragraph', 'runs': [
        {'text': 'Document Office externe : ' + title}]}]}).model_dump(mode='json')


def _derived(files, preview, mode):
    """Return complete converted versions and validated assets, bytes internal."""
    assets = {}
    for item in preview['files']:
        if item['kind'] == 'attachment':
            name = item['relative_path']
            filename = PurePosixPath(name).name
            data = files[name]
            asset_id = str(uuid5(UUID(preview['planned_note_id']), name))
            assets[asset_id] = {'id': asset_id, 'filename': filename,
                'content_type': content_type(filename, data), 'data': data,
                'size_bytes': len(data), 'sha256': item['sha256'], 'source_path': name}
    if mode == 'rich':
        for item in preview['files']:
            name = item['relative_path']
            if name.endswith('content.html') or (item['kind'] == 'legacy_text' and PurePosixPath(name).suffix.casefold() in {'.html', '.htm'}):
                converted = convert_html(files[name], planned_note_id=preview['planned_note_id'],
                                         image_bindings=preview.get('image_bindings', {}))
                if not converted['can_import_rich']:
                    raise ValueError('Contenu HTML devenu incompatible')
                for asset_id, asset in converted['embedded_assets'].items():
                    assets[asset_id] = {**asset, 'source_path': None}
    expected = {item['id']: item for item in preview.get('embedded_images', [])}
    if {key for key, item in assets.items() if item['source_path'] is None} != set(expected):
        raise ValueError('Inventaire des images intégrées incompatible')
    for key, item in expected.items():
        if any(assets[key][field] != item[field] for field in item):
            raise ValueError('Image différente de l’aperçu')
    versions = preview['versions']
    if preview['kind'] == 'external_office':
        versions = [{'source_key': 'current', 'source_actor': None,
                     'content': _office_content(preview['title']), 'conversion_mode': 'external'}]
    return versions, [assets[key] for key in sorted(assets)]


def _asset_capture(item):
    return {key: item[key] for key in ('id', 'filename', 'content_type', 'size_bytes', 'sha256', 'source_path')}


def validate_source_capture(capture, files):
    """Recompute source semantics for reads and future offline transport validation."""
    preview = preview_source(files, planned_note_id=capture.command.planned_note_id, mode=capture.command.mode)
    if (not preview['can_apply'] or preview['preview_sha256'] != capture.command.expected_preview_sha256
            or preview['source_sha256'] != capture.source_sha256 or preview['files'] != capture.files
            or preview['kind'] != capture.source_kind or preview.get('source_metadata', {}) != capture.source_metadata):
        raise ValueError('Capture différente des originaux et de la décision validée')
    versions, assets = _derived(files, preview, capture.command.mode)
    if len(versions) != len(capture.versions):
        raise ValueError('Historique source incomplet')
    for source, recorded in zip(versions, capture.versions, strict=True):
        if ((source['source_key'], source['source_actor'], source['conversion_mode'], freeze(source['content'])[1]) !=
                (recorded.source_key, recorded.source_actor, recorded.conversion_mode, recorded.content_sha256)):
            raise ValueError('Version convertie différente de la source')
    if [_asset_capture(item) for item in assets] != [item.model_dump(mode='json') for item in capture.attachments]:
        raise ValueError('Pièces converties différentes des originaux')
    return preview


