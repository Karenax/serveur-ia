"""Pure typed note graph contract, independent of runtime storage or acquisition.

No ORM, database, configuration, file or network calls. Captured identifiers are
descriptive; current bindings carry portable relationships independently.
"""
from copy import deepcopy
from datetime import datetime
import json
from uuid import UUID, uuid4

from app.services.deliverable_manifest import freeze
from backend.app.project_note_import_schemas import NoteImportCapture
from backend.app.project_note_schemas import (NOTE_ATTACHMENT_BUDGET, NoteContent, NoteCreate, NoteDelete,
                                               NoteSave, NoteRestore, ImageBlock, content_text)

PROJECT_TABLES = frozenset({'project_notes', 'project_note_versions', 'project_note_attachments', 'project_note_imports'})
MAX_ROWS = 100000
MAX_SNAPSHOT_BYTES = 2_500_000
MAX_EMBEDDED_BYTES = 100 * 1024 * 1024
KEYS = {
    'project_notes': {'id', 'project_id', 'title', 'plain_text', 'revision', 'current_version_id', 'created_at', 'updated_at'},
    'project_note_versions': {'id', 'project_id', 'note_id', 'revision', 'snapshot', 'sha256', 'command_id',
        'command_sha256', 'actor_id', 'attachment_bindings', 'restored_version_id', 'execution_blocked', 'created_at'},
    'project_note_attachments': {'id', 'project_id', 'note_id', 'storage_id', 'filename', 'content_type', 'size_bytes',
        'sha256', 'command_id', 'actor_id', 'created_at'},
    'project_note_imports': {'id', 'project_id', 'note_id', 'command_id', 'command_sha256', 'source_kind', 'snapshot',
        'snapshot_sha256', 'storage_id', 'sha256', 'size_bytes', 'actor_id', 'version_bindings',
        'attachment_bindings', 'execution_blocked', 'created_at'},
}
SNAPSHOT_KEYS = {'format', 'version', 'project_id', 'note_id', 'title', 'content', 'plain_text', 'attachment_ids',
                 'revision', 'actor_id', 'command_id', 'operation', 'restored_from'}


def native_view(tables):
    return {name: rows for name, rows in tables.items() if name not in PROJECT_TABLES}


def identity(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError('Identifiant de note non canonique')
    return value


def digest(value):
    if not isinstance(value, str) or len(value) != 64 or any(char not in '0123456789abcdef' for char in value):
        raise ValueError('Empreinte de note incompatible')


def integer(value, maximum=MAX_ROWS):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError('Révision ou taille entière bornée requise')


def actor(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 120:
        raise ValueError('Opérateur capturé incompatible')


def timestamp(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 60:
        raise ValueError('Date de note requise')
    datetime.fromisoformat(value)


def bindings(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys) or len(set(value.values())) != len(value):
        raise ValueError('Liaisons de note incomplètes ou ambiguës')
    for key, target in value.items():
        identity(key)
        identity(target)


def command_digest(project_id, note_id, operation, payload, operator):
    return freeze({'project_id': project_id, 'note_id': note_id, 'operation': operation,
                   'payload': payload.model_dump(mode='json'), 'actor_id': operator})[1]


def _json_snapshot(row, field, sha):
    raw = row[field]
    if not isinstance(raw, str) or len(raw.encode('utf-8')) > MAX_SNAPSHOT_BYTES:
        raise ValueError('Capture de note trop volumineuse')
    value = json.loads(raw)
    if freeze(value) != (raw, row[sha]):
        raise ValueError('Capture et empreinte de note divergentes')
    return value


def version_value(row):
    value = _json_snapshot(row, 'snapshot', 'sha256')
    if (not isinstance(value, dict) or set(value) != SNAPSHOT_KEYS or value['format'] != 'agent-project-note'
            or type(value['version']) is not int or value['version'] != 1
            or type(value['revision']) is not int or value['revision'] != row['revision']
            or value['actor_id'] != row['actor_id'] or value['command_id'] != row['command_id']):
        raise ValueError('Version de note différente de sa capture')
    content = NoteContent.model_validate(value['content'])
    checked = NoteSave(command_id=value['command_id'], expected_revision=value['revision'],
        title=value['title'], content=content, attachment_ids=value['attachment_ids'])
    if (checked.title != value['title'] or checked.attachment_ids != value['attachment_ids']
            or content.model_dump(mode='json') != value['content'] or content_text(content) != value['plain_text']
            or not isinstance(value['project_id'], str) or not 1 <= len(value['project_id']) <= 36):
        raise ValueError('Contenu de note non canonique')
    identity(value['note_id'])
    bindings(row['attachment_bindings'], value['attachment_ids'])
    if not row['execution_blocked'] and (value['project_id'], value['note_id']) != (row['project_id'], row['note_id']):
        raise ValueError('Identités courantes différentes d’une commande active')
    images = {block.attachment_id for block in content.blocks if isinstance(block, ImageBlock)}
    if not images <= set(value['attachment_ids']):
        raise ValueError('Image absente des pièces de la version')
    operation = value['operation']
    if operation not in {'create', 'save', 'restore', 'delete'} or (operation == 'create') != (value['revision'] == 1):
        raise ValueError('Opération de version incompatible')
    if operation == 'create':
        payload = NoteCreate(command_id=value['command_id'], title=value['title'], content=content)
        target = None
    elif operation == 'save':
        payload = NoteSave(command_id=value['command_id'], title=value['title'], content=content,
                           expected_revision=value['revision'] - 1, attachment_ids=value['attachment_ids'])
        target = value['note_id']
    elif operation == 'delete':
        payload = NoteDelete(command_id=value['command_id'], expected_revision=value['revision'] - 1)
        target = value['note_id']
    else:
        identity(value['restored_from'])
        identity(row['restored_version_id'])
        payload = NoteRestore(command_id=value['command_id'], expected_revision=value['revision'] - 1,
                              version_id=value['restored_from'])
        target = value['note_id']
        if not row['execution_blocked'] and value['restored_from'] != row['restored_version_id']:
            raise ValueError('Liaison de restauration active différente de sa capture')
    if operation != 'restore' and (value['restored_from'] is not None or row['restored_version_id'] is not None):
        raise ValueError('Liaison de restauration inattendue')
    if command_digest(value['project_id'], target, operation, payload, value['actor_id']) != row['command_sha256']:
        raise ValueError('Commande de note différente de sa capture')
    return value


def bound_value(row, value):
    content = deepcopy(value['content'])
    for block in content['blocks']:
        if block['type'] == 'image':
            block['attachment_id'] = row['attachment_bindings'][block['attachment_id']]
    return content, [row['attachment_bindings'][key] for key in value['attachment_ids']]


def import_value(row):
    value = _json_snapshot(row, 'snapshot', 'snapshot_sha256')
    capture = NoteImportCapture.model_validate(value)
    if (capture.model_dump(mode='json') != value
            or (capture.id, capture.actor_id, capture.command_id, capture.source_kind, capture.bundle_sha256,
                capture.bundle_size_bytes) != (row['id'] if not row['execution_blocked'] else capture.id,
                    row['actor_id'], row['command_id'], row['source_kind'], row['sha256'], row['size_bytes'])
            or command_digest(capture.project_id, capture.note_id, 'import', capture.command, capture.actor_id) != row['command_sha256']
            or (not row['execution_blocked'] and (capture.project_id, capture.note_id) != (row['project_id'], row['note_id']))):
        raise ValueError('Capture source incompatible')
    bindings(row['version_bindings'], [item.note_version_id for item in capture.versions])
    bindings(row['attachment_bindings'], [item.id for item in capture.attachments])
    return capture


def validate(tables, section):
    if (not isinstance(section, dict) or set(section) != {'format', 'version'}
            or section['format'] != 'agent-project-notes' or type(section['version']) is not int or section['version'] != 1):
        raise ValueError('Section typée de notes requise')
    if not isinstance(tables, dict) or not PROJECT_TABLES <= tables.keys():
        raise ValueError('Toutes les tables de notes sont requises')
    projects = tables.get('projects')
    if (not isinstance(projects, list) or len(projects) != 1 or not isinstance(projects[0], dict)
            or not isinstance(projects[0].get('id'), str) or not 1 <= len(projects[0]['id']) <= 36):
        raise ValueError('Un seul projet identifié requis')
    pid = projects[0]['id']
    ledger, all_ids, total = {}, set(), 0
    for name in sorted(PROJECT_TABLES):
        rows = tables[name]
        if not isinstance(rows, list) or len(rows) > MAX_ROWS:
            raise ValueError('Table de notes bornée requise')
        ledger[name] = {}
        for row in rows:
            if not isinstance(row, dict) or set(row) != KEYS[name] or row['project_id'] != pid:
                raise ValueError('Colonnes ou portée des notes incompatibles')
            identity(row['id'])
            if row['id'] in all_ids:
                raise ValueError('Identifiant ambigu entre objets de notes')
            all_ids.add(row['id'])
            for field in ('note_id', 'storage_id', 'current_version_id', 'command_id'):
                if field in row:
                    identity(row[field])
            if 'actor_id' in row:
                actor(row['actor_id'])
            for field in ('sha256', 'command_sha256', 'snapshot_sha256'):
                if field in row:
                    digest(row[field])
            if 'execution_blocked' in row and type(row['execution_blocked']) is not bool:
                raise ValueError('Gel de commande booléen requis')
            timestamp(row['created_at'])
            if 'updated_at' in row:
                timestamp(row['updated_at'])
            if 'revision' in row:
                integer(row['revision'])
            if 'snapshot' in row:
                if not isinstance(row['snapshot'], str):
                    raise ValueError('Capture textuelle requise')
                total += len(row['snapshot'].encode('utf-8'))
            ledger[name][row['id']] = row
    if total > MAX_EMBEDDED_BYTES:
        raise ValueError('Historique de notes trop volumineux')
    native_ids = {row['id'] for rows in native_view(tables).values() if isinstance(rows, list)
                  for row in rows if isinstance(row, dict) and 'id' in row}
    if all_ids & native_ids:
        raise ValueError('Identifiant de note ambigu avec un objet natif')
    heads, versions, assets, imports = (ledger[name] for name in ('project_notes', 'project_note_versions', 'project_note_attachments', 'project_note_imports'))
    if not heads:
        raise ValueError('Au moins une note requise dans la section typée')
    seen_storage, seen_commands, quotas = set(), set(), {}
    for row in assets.values():
        if row['note_id'] not in heads or row['storage_id'] in seen_storage:
            raise ValueError('Pièce jointe orpheline ou stockage ambigu')
        seen_storage.add(row['storage_id'])
        integer(row['size_bytes'], NOTE_ATTACHMENT_BUDGET)
        if (not isinstance(row['filename'], str) or not 1 <= len(row['filename']) <= 255
                or any(ord(char) < 32 or char in '/\\' for char in row['filename'])
                or not isinstance(row['content_type'], str) or not 1 <= len(row['content_type']) <= 120):
            raise ValueError('Métadonnées de pièce incompatibles')
        key = row['note_id'], row['command_id']
        if key in seen_commands:
            raise ValueError('Commande de pièce dupliquée')
        seen_commands.add(key)
        count, size = quotas.get(row['note_id'], (0, 0))
        quotas[row['note_id']] = count + 1, size + row['size_bytes']
    if any(count > 20 or size > 25 * 1024 * 1024 for count, size in quotas.values()):
        raise ValueError('Quotas de pièces dépassés')
    values, by_note, commands = {}, {}, set()
    for row in sorted(versions.values(), key=lambda row: row['revision']):
        if row['note_id'] not in heads or row['command_id'] in commands:
            raise ValueError('Version orpheline ou commande dupliquée')
        commands.add(row['command_id'])
        value = version_value(row)
        values[row['id']] = value
        sequence = by_note.setdefault(row['note_id'], [])
        if row['revision'] != len(sequence) + 1:
            raise ValueError('Séquence des versions incomplète')
        if sequence and values[sequence[-1]['id']]['operation'] == 'delete':
            raise ValueError('Une note supprimée ne peut pas recevoir de nouvelle version')
        sequence.append(row)
        bound_content, bound_assets = bound_value(row, value)
        for key in bound_assets:
            if key not in assets or assets[key]['note_id'] != row['note_id']:
                raise ValueError('Liaison de pièce absente de cette note')
        for block in bound_content['blocks']:
            if block['type'] == 'image' and assets[block['attachment_id']]['content_type'] not in {'image/png', 'image/jpeg', 'image/webp'}:
                raise ValueError('Image sans pièce décodable')
        if row['restored_version_id'] is not None:
            prior = versions.get(row['restored_version_id'])
            if (not prior or prior['note_id'] != row['note_id'] or prior['revision'] >= row['revision']
                    or prior['id'] not in values or values[prior['id']]['title'] != value['title']
                    or bound_value(prior, values[prior['id']]) != (bound_content, bound_assets)):
                raise ValueError('Version restaurée absente, étrangère ou différente')
    for head in heads.values():
        sequence = by_note.get(head['id'], [])
        if (not sequence or head['current_version_id'] != sequence[-1]['id'] or head['revision'] != len(sequence)
                or head['title'] != values[sequence[-1]['id']]['title'] or head['plain_text'] != values[sequence[-1]['id']]['plain_text']):
            raise ValueError('Tête de note différente de son historique')
    seen_imports, seen_storage, captures = set(), set(), {}
    for row in imports.values():
        if (row['note_id'] not in heads or row['note_id'] in seen_imports
                or row['storage_id'] in seen_storage or row['command_id'] in commands):
            raise ValueError('Reçu source absent ou ambigu')
        seen_imports.add(row['note_id'])
        seen_storage.add(row['storage_id'])
        commands.add(row['command_id'])
        integer(row['size_bytes'], 52 * 1024 * 1024)
        capture = import_value(row)
        captures[row['id']] = capture
        for revision, source in enumerate(capture.versions, start=1):
            target = versions.get(row['version_bindings'][source.note_version_id])
            if (not target or target['note_id'] != row['note_id'] or target['revision'] != revision or not target['execution_blocked']
                    or target['attachment_bindings'] != row['attachment_bindings']):
                raise ValueError('Version source sans liaison exacte')
            value = values[target['id']]
            if ((value['project_id'], value['note_id'], value['actor_id']) != (capture.project_id, capture.note_id, capture.actor_id)
                    or freeze(value['content'])[1] != source.content_sha256
                    or value['attachment_ids'] != [item.id for item in capture.attachments]):
                raise ValueError('Capture source différente de sa version')
        for source in capture.attachments:
            target = assets.get(row['attachment_bindings'][source.id])
            if (not target or target['note_id'] != row['note_id'] or any(target[key] != getattr(source, key)
                    for key in ('filename', 'content_type', 'size_bytes', 'sha256'))):
                raise ValueError('Pièce source absente ou différente')
        head = heads[row['note_id']]
        if row['source_kind'] == 'external_office' and not (head['revision'] == 1 or (
                head['revision'] == 2 and values[head['current_version_id']]['operation'] == 'delete')):
            raise ValueError('Document Office externe modifié')
    return {'heads': heads, 'versions': versions, 'assets': assets, 'imports': imports, 'values': values, 'captures': captures}


def section_for(tables):
    section = {'format': 'agent-project-notes', 'version': 1}
    validate(tables, section)
    return section


def remap_rows(tables, mapping):
    """Keep snapshot text/hash/operator/command verbatim; remap only current graph."""
    section_for(tables)
    result = {}
    for name in PROJECT_TABLES:
        result[name] = []
        for original in tables[name]:
            row = deepcopy(original)
            for key in ('id', 'project_id', 'note_id', 'current_version_id', 'restored_version_id'):
                if key in row and row[key] is not None:
                    row[key] = mapping[row[key]]
            if 'storage_id' in row:
                row['storage_id'] = str(uuid4())
            for key in ('attachment_bindings', 'version_bindings'):
                if key in row:
                    row[key] = {source: mapping[target] for source, target in row[key].items()}
            if 'execution_blocked' in row:
                row['execution_blocked'] = True
            result[name].append(row)
    return result
