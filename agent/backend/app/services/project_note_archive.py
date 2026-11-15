"""Pure note graph and binary closure, for project and global transports.

The caller decodes bounded envelopes and supplies frozen bytes. Validation does
not open paths, import runtime databases, extract ZIPs or acquire source files.
Every managed attachment (including historical/unused ones) and original source
bundle is mandatory. Source conversions are recomputed from retained bytes.
"""
import hashlib

from app.services.deliverable_manifest import freeze
from . import project_note_history as history
from .project_note_binary import content_type
from .project_note_source_bundle import verify_bundle
from .project_note_source_content import validate_source_capture

PROJECT_TABLES = history.PROJECT_TABLES
AREAS = {'note-file': 'project_note_attachments', 'note-original': 'project_note_imports'}
MAX_BINARY_BYTES = 150 * 1024**2
ENVELOPE_KEYS = {'owner', 'area', 'name', 'sha256', 'data'}


def storage_name(area, row):
    if area not in AREAS:
        raise ValueError('Zone de note inconnue')
    return row['storage_id'] + ('/blob' if area == 'note-file' else '/blob.zip')


def validate_files(tables, section, decoded):
    """Validate tuples (envelope, bytes, digest) produced by a bounded decoder."""
    ledger = history.validate(tables, section)
    expected = {(area, row['id']): row for area, table in AREAS.items() for row in tables[table]}
    if not isinstance(decoded, list) or len(decoded) > 100000:
        raise ValueError('Liste bornée de fichiers requise')
    received, total = {}, 0
    for item in decoded:
        if not isinstance(item, tuple) or len(item) != 3 or not isinstance(item[0], dict):
            raise ValueError('Fichier décodé incompatible')
        entry, data, digest = item
        area = entry.get('area')
        if not isinstance(area, str):
            raise ValueError('Zone textuelle requise')
        if area not in AREAS:
            if area.startswith('note-'):
                raise ValueError('Zone de note inconnue')
            continue  # Other domain validators own their files.
        owner = entry.get('owner')
        if not isinstance(owner, str):
            raise ValueError('Propriétaire de note textuel requis')
        key = area, owner
        row = expected.get(key)
        if row is None or key in received or set(entry) != ENVELOPE_KEYS:
            raise ValueError('Fichier de note inconnu, dupliqué ou ambigu')
        if (entry['name'] != storage_name(area, row) or not isinstance(data, bytes)
                or len(data) != row['size_bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']
                or entry['sha256'] != row['sha256'] or digest != row['sha256']):
            raise ValueError('Octets ou liaison de fichier de note différents')
        total += len(data)
        if total > MAX_BINARY_BYTES:
            raise ValueError('Fichiers de notes trop volumineux')
        if area == 'note-file' and content_type(row['filename'], data) != row['content_type']:
            raise ValueError('Type de pièce de note différent des octets')
        received[key] = data
    if set(received) != set(expected):
        raise ValueError('Pièce historique ou original source absent')
    for row in ledger['imports'].values():
        capture = ledger['captures'][row['id']]
        sources = verify_bundle(received['note-original', row['id']], capture.files)
        preview = validate_source_capture(capture, sources)
        for source in capture.versions:
            value = ledger['values'][row['version_bindings'][source.note_version_id]]
            if value['title'] != preview['title']:
                raise ValueError('Titre de version importée différent de sa source')
            # Graph validation already binds the converted content/hash and
            # source actor; binary recomputation above closes those captures.
            if freeze(value['content'])[1] != source.content_sha256:
                raise ValueError('Contenu source différent de sa version liée')
        for source in capture.attachments:
            current = row['attachment_bindings'][source.id]
            data = received['note-file', current]
            if hashlib.sha256(data).hexdigest() != source.sha256:
                raise ValueError('Pièce source différente de la copie gérée')
    return ledger


native_view = history.native_view
section_for = history.section_for
remap_rows = history.remap_rows
