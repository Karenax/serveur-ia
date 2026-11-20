"""Immutable source bundle preparation and verification, without extraction.

Original note/Office bytes are independent of the ordinary attachment quota.
This staged contract is for the future import row/global backup, not runtime.
"""
import hashlib
from io import BytesIO
import zipfile

from ..project_note_schemas import NOTE_ATTACHMENT_BUDGET
from .project_note_source_preview import preview_source, MAX_IMPORT_BYTES, MAX_IMPORT_FILES, _path, _filename, OFFICE, LEGACY_TEXT
from pathlib import PurePosixPath

MAX_BUNDLE_BYTES = 52 * 1024 * 1024


def prepare_bundle(files, *, planned_note_id, expected_preview_sha256, mode='rich'):
    preview = preview_source(files, planned_note_id=planned_note_id, mode=mode)
    if preview['preview_sha256'] != expected_preview_sha256:
        raise ValueError('Sources ou décision modifiées depuis l’aperçu')
    if not preview['can_apply']:
        raise ValueError('Import bloqué par les éléments non représentables de l’aperçu')
    output = BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as bundle:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100600 << 16
            bundle.writestr(info, files[name])
    data = output.getvalue()
    if len(data) > MAX_BUNDLE_BYTES:
        raise ValueError('Conteneur source trop volumineux')
    # Verify before any later caller may copy/register the bundle.
    verify_bundle(data, preview['files'])
    return data, {'format': 'agent-note-originals', 'version': 1,
                  'size_bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                  'source_sha256': preview['source_sha256'], 'preview_sha256': preview['preview_sha256'],
                  'files': preview['files'], 'source_kind': preview['kind'],
                  'source_metadata': preview.get('source_metadata', {}),
                  'conversion_mode': preview.get('conversion_mode'),
                  'source_versions': [{'source_key': row['source_key'], 'source_actor': row['source_actor']}
                                      for row in preview['versions']],
                  'original_bytes_exact': True}


def _inventory(value):
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_IMPORT_FILES:
        raise ValueError('Inventaire source borné requis')
    lookup, total, attachments, attachment_bytes = {}, 0, 0, 0
    for row in value:
        if (not isinstance(row, dict) or set(row) != {'relative_path', 'kind', 'size_bytes', 'sha256'}
                or not isinstance(row['relative_path'], str) or type(row['size_bytes']) is not int
                or not 0 <= row['size_bytes'] <= MAX_IMPORT_BYTES
                or not isinstance(row['sha256'], str) or len(row['sha256']) != 64
                or any(char not in '0123456789abcdef' for char in row['sha256'])):
            raise ValueError('Inventaire source incompatible')
        name = row['relative_path']
        if row['kind'] == 'external':
            _filename(name)
            if len(value) != 1 or PurePosixPath(name).suffix.casefold() not in OFFICE or not row['size_bytes']:
                raise ValueError('Un seul document Office externe est requis')
        elif row['kind'] == 'legacy_text':
            _filename(name)
            extension = PurePosixPath(name).suffix.casefold()
            if len(value) != 1 or extension not in LEGACY_TEXT:
                raise ValueError('Une seule note texte historique est requise')
            if extension not in {'.html', '.htm'} and row['size_bytes'] > 2_000_000:
                raise ValueError('Texte historique dépassant 2 Mo')
        elif row['kind'] != _path(name):
            raise ValueError('Type de fichier source incompatible')
        if row['kind'] in {'content', 'version'} and not name.endswith('content.html') and row['size_bytes'] > 2_000_000:
            raise ValueError('Contenu source dépassant 2 Mo')
        if row['kind'] == 'attachment':
            attachments += 1
            attachment_bytes += row['size_bytes']
            if (not 0 < row['size_bytes'] <= NOTE_ATTACHMENT_BUDGET or attachments > 20
                    or attachment_bytes > NOTE_ATTACHMENT_BUDGET):
                raise ValueError('Inventaire de pièces dépassant les limites des notes')
        if name.casefold() in {key.casefold() for key in lookup}:
            raise ValueError('Fichiers source dupliqués ou ambigus')
        total += row['size_bytes']
        if total > MAX_IMPORT_BYTES:
            raise ValueError('Inventaire dépassant 50 Mio')
        lookup[name] = row
    return lookup


def verify_bundle(data, inventory):
    """Return exact source bytes only after validating the whole bundle."""
    expected = _inventory(inventory)
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_BUNDLE_BYTES:
        raise ValueError('Conteneur source borné requis')
    try:
        with zipfile.ZipFile(BytesIO(data)) as bundle:
            items = bundle.infolist()
            if (len(items) != len(expected) or len({item.filename for item in items}) != len(items)
                    or {item.filename for item in items} != set(expected)):
                raise ValueError('Conteneur source incomplet ou contenant des fichiers supplémentaires')
            files = {}
            for item in items:
                row = expected[item.filename]
                if (item.is_dir() or item.flag_bits & 1 or item.compress_type != zipfile.ZIP_STORED
                        or item.file_size != row['size_bytes'] or item.compress_size != row['size_bytes']):
                    raise ValueError('Entrée source incohérente, chiffrée ou comprimée')
                content = bundle.read(item)
                if len(content) != row['size_bytes'] or hashlib.sha256(content).hexdigest() != row['sha256']:
                    raise ValueError('Octets source différents de l’inventaire original')
                files[item.filename] = content
            return files
    except (zipfile.BadZipFile, RuntimeError, OSError, NotImplementedError) as exc:
        raise ValueError('Conteneur source illisible') from exc
