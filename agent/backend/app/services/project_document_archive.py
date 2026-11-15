"""Typed document forms closure with immutable historical captures.

All operations are on bounded row dictionaries, with no DB or filesystem I/O.
Immutable snapshot text is retained verbatim; only current identifiers and flat
bindings are remapped. Common search preferences never travel in this section.
"""
from copy import deepcopy
from datetime import datetime
import hashlib
import json

from fastapi import HTTPException

from app.services.deliverable_manifest import freeze
from backend.app.services.document_paths import _relative
from backend.app.services.document_template_catalogue import DOCUMENT_IDS, catalogue

PROJECT_TABLES = frozenset({'project_document_drafts', 'project_document_draft_versions'})
MAX_ROWS = 100000
MAX_SNAPSHOT_BYTES = 1024 * 1024
MAX_EMBEDDED_BYTES = 16 * 1024 * 1024
HEAD_KEYS = frozenset({'id', 'project_id', 'document_id', 'revision', 'link_id', 'relative_path', 'overrides', 'updated_at'})
VERSION_KEYS = frozenset({'id', 'project_id', 'draft_id', 'document_id', 'revision', 'snapshot', 'sha256', 'bindings',
                          'actor_id', 'created_at'})
SNAPSHOT_KEYS = frozenset({'format', 'version', 'project_id', 'draft_id', 'document_id', 'revision', 'actor_id',
                           'choice', 'restored_from'})


def native_view(tables):
    """Older typed validators must never silently accept document rows."""
    return {name: rows for name, rows in tables.items() if name not in PROJECT_TABLES}


def remap_row(raw, table_name, mapping):
    row = deepcopy(raw)
    keys = ('id', 'project_id', 'link_id') if table_name == 'project_document_drafts' else ('id', 'project_id', 'draft_id')
    for key in keys:
        if row[key] is not None:
            row[key] = mapping[row[key]]
    if table_name == 'project_document_draft_versions':
        row['bindings'] = {key: mapping[value] if value is not None else None for key, value in row['bindings'].items()}
    return row


def invalid(message):
    raise HTTPException(400, 'Archive de formulaires documentaires : ' + message)


def identity(value, *, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str) or not 1 <= len(value) <= 36 or any(ord(char) < 32 for char in value):
        raise ValueError('identifiant invalide')


def revision(value):
    if type(value) is not int or not 1 <= value <= MAX_ROWS:
        raise ValueError('révision invalide')


def path(value):
    if not isinstance(value, str) or _relative(value) != value:
        raise ValueError('chemin relatif non canonique')


def overrides(value):
    editable = {key for key, field in catalogue()['fields'].items() if field['edit_scope'] is not None}
    if not isinstance(value, dict) or len(value) > 19 or not set(value).issubset(editable):
        raise ValueError('corrections interdites')
    for item in value.values():
        if (not isinstance(item, str) or len(item) > 10000 or any(ord(char) < 32 and char not in '\t\n\r' for char in item)
                or any(0xD800 <= ord(char) <= 0xDFFF or ord(char) in {0xFFFE, 0xFFFF} for char in item)):
            raise ValueError('correction textuelle invalide')


def timestamp(value):
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError('horodatage invalide')
    datetime.fromisoformat(value)


def snapshot(row):
    payload = row['snapshot']
    if (not isinstance(payload, str) or len(payload.encode('utf-8')) > MAX_SNAPSHOT_BYTES
            or hashlib.sha256(payload.encode('utf-8')).hexdigest() != row['sha256']):
        raise ValueError('taille ou empreinte de version invalide')
    value = json.loads(payload)
    if (not isinstance(value, dict) or set(value) != SNAPSHOT_KEYS
            or value['format'] != 'agent-project-document-draft' or type(value['version']) is not int
            or value['version'] != 1 or freeze(value)[0] != payload):
        raise ValueError('capture non canonique')
    identity(value['project_id'])
    identity(value['draft_id'])
    identity(value['restored_from'], nullable=True)
    if value['document_id'] != row['document_id'] or value['revision'] != row['revision'] or type(value['revision']) is not int:
        raise ValueError('capture d’une autre révision ou trame')
    if value['actor_id'] != row['actor_id']:
        raise ValueError('auteur différent de la capture')
    choice = value['choice']
    if not isinstance(choice, dict) or set(choice) != {'link_id', 'relative_path', 'overrides'}:
        raise ValueError('choix capturé invalide')
    identity(choice['link_id'], nullable=True)
    path(choice['relative_path'])
    overrides(choice['overrides'])
    if choice['link_id'] is None and choice['relative_path']:
        raise ValueError('chemin sans lien capturé')
    return value


def validate(tables, section):
    """Require a closed per-project ledger; return missing link identities."""
    try:
        if (not isinstance(tables, dict) or not PROJECT_TABLES.issubset(tables)
                or any(name.startswith('project_document_') and name not in PROJECT_TABLES for name in tables)):
            raise ValueError('tables projet distinctes et complètes requises ; préférences communes interdites')
        if (not isinstance(section, dict) or set(section) != {'format', 'version', 'unresolved_link_ids'}
                or section['format'] != 'agent-project-document-forms' or type(section['version']) is not int
                or section['version'] != 1):
            raise ValueError('section documentaire typée requise')
        projects = tables.get('projects')
        if not isinstance(projects, list) or len(projects) != 1 or not isinstance(projects[0], dict):
            raise ValueError('un seul projet requis')
        pid = projects[0].get('id')
        identity(pid)
        heads, versions = tables['project_document_drafts'], tables['project_document_draft_versions']
        if (not isinstance(heads, list) or not 1 <= len(heads) <= len(DOCUMENT_IDS) or not isinstance(versions, list)
                or not 1 <= len(versions) <= MAX_ROWS):
            raise ValueError('formulaires et historique bornés requis')
        if embedded_bytes(tables) > MAX_EMBEDDED_BYTES:
            raise ValueError('historique documentaire trop volumineux')
        links = tables.get('network_links', [])
        if not isinstance(links, list) or len(links) > MAX_ROWS or any(
                not isinstance(link, dict) or link.get('project_id') != pid for link in links):
            raise ValueError('liens sortant du projet')
        link_ids = {link['id'] for link in links}
        for key in link_ids:
            identity(key)
        identities, documents, current, observed = {pid, *link_ids}, set(), {}, set()
        for head in heads:
            if not isinstance(head, dict) or set(head) != HEAD_KEYS:
                raise ValueError('colonnes de formulaire invalides')
            identity(head['id'])
            identity(head['link_id'], nullable=True)
            revision(head['revision'])
            timestamp(head['updated_at'])
            path(head['relative_path'])
            overrides(head['overrides'])
            if (head['project_id'] != pid or head['document_id'] not in DOCUMENT_IDS
                    or head['document_id'] in documents or head['id'] in identities
                    or head['link_id'] is None and head['relative_path']):
                raise ValueError('identité ou choix du formulaire incohérent')
            documents.add(head['document_id'])
            identities.add(head['id'])
            current[head['id']] = head
            if head['link_id']:
                observed.add(head['link_id'])
        ledgers = {key: {} for key in current}
        captured_bindings = {}
        for row in versions:
            if not isinstance(row, dict) or set(row) != VERSION_KEYS:
                raise ValueError('colonnes d’historique invalides')
            identity(row['id'])
            revision(row['revision'])
            timestamp(row['created_at'])
            if (row['id'] in identities or row['project_id'] != pid or row['draft_id'] not in current
                    or row['document_id'] != current[row['draft_id']]['document_id']
                    or row['revision'] in ledgers[row['draft_id']]):
                raise ValueError('identité, parent ou révision de version incohérent')
            if not isinstance(row['actor_id'], str) or not 1 <= len(row['actor_id']) <= 120:
                raise ValueError('auteur de version invalide')
            identities.add(row['id'])
            value = snapshot(row)
            binding = row['bindings']
            if (not isinstance(binding, dict) or set(binding) != {'project_id', 'draft_id', 'link_id'}
                    or binding['project_id'] != pid or binding['draft_id'] != row['draft_id']):
                raise ValueError('correspondances de version étrangères ou imbriquées')
            identity(binding['link_id'], nullable=True)
            if (binding['link_id'] is None) != (value['choice']['link_id'] is None):
                raise ValueError('lien capturé et correspondance incohérents')
            if binding['link_id']:
                observed.add(binding['link_id'])
                original = value['project_id'], value['draft_id'], value['choice']['link_id']
                previous = captured_bindings.setdefault(original, binding['link_id'])
                if previous != binding['link_id']:
                    raise ValueError('correspondance capturée ambiguë')
            ledgers[row['draft_id']][row['revision']] = (row, value)
        unresolved = observed - link_ids
        if unresolved & identities:
            raise ValueError('lien manquant confondu avec un autre type d’identité')
        declared = section['unresolved_link_ids']
        if (not isinstance(declared, list) or len(declared) > MAX_ROWS or declared != sorted(unresolved)):
            raise ValueError('liste des liens manquants différente du journal')
        for key, ledger in ledgers.items():
            head = current[key]
            if set(ledger) != set(range(1, head['revision'] + 1)):
                raise ValueError('journal de révisions incomplet ou excédentaire')
            row, value = ledger[head['revision']]
            if (row['bindings']['link_id'] != head['link_id'] or value['choice']['relative_path'] != head['relative_path']
                    or value['choice']['overrides'] != head['overrides']):
                raise ValueError('formulaire différent de sa dernière capture')
        return {'unresolved_link_ids': set(unresolved), 'document_ids': documents}
    except HTTPException as exc:
        if exc.status_code == 400:
            raise
        invalid(str(exc.detail))
    except (ValueError, TypeError, KeyError, UnicodeError) as exc:
        invalid(str(exc))


def embedded_bytes(tables):
    total = 0
    for name in PROJECT_TABLES:
        rows = tables.get(name, [])
        if not isinstance(rows, list) or len(rows) > MAX_ROWS:
            raise ValueError('liste documentaire invalide')
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('ligne documentaire invalide')
            payload = row.get('snapshot')
            if payload is not None and (not isinstance(payload, str) or len(payload.encode('utf-8')) > MAX_SNAPSHOT_BYTES):
                raise ValueError('capture documentaire trop volumineuse')
            total += len(json.dumps(row, ensure_ascii=False, allow_nan=False).encode('utf-8'))
            if total > MAX_EMBEDDED_BYTES:
                return total
    return total


def section_for(tables):
    links = {link['id'] for link in tables.get('network_links', [])}
    seen = {head['link_id'] for head in tables['project_document_drafts'] if head['link_id']}
    seen.update(row['bindings']['link_id'] for row in tables['project_document_draft_versions'] if row['bindings']['link_id'])
    section = {'format': 'agent-project-document-forms', 'version': 1, 'unresolved_link_ids': sorted(seen - links)}
    validate(tables, section)
    return section


def remap(tables, section, mapping):
    context = validate(tables, section)
    required = {tables['projects'][0]['id'], *context['unresolved_link_ids']}
    required.update(row['id'] for name in PROJECT_TABLES for row in tables[name])
    required.update(link['id'] for link in tables.get('network_links', []))
    if not required.issubset(mapping) or len({mapping[key] for key in required}) != len(required):
        invalid('correspondances de restauration incomplètes ou ambiguës')
    for key in required:
        try:
            identity(mapping[key])
        except ValueError as exc:
            invalid(str(exc))
    result = {name: [remap_row(row, name, mapping) for row in tables[name]] for name in PROJECT_TABLES}
    new_section = {**section, 'unresolved_link_ids': sorted(mapping[key] for key in context['unresolved_link_ids'])}
    return result, new_section
