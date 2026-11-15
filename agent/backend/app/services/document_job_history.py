"""Bounded, closed queue history validation, without SQL or filesystem effects."""
from app.operational_limits import DOCUMENT_IMPORT_BYTES
import hashlib
import json
from collections import defaultdict
from pathlib import PureWindowsPath
from uuid import UUID

from app.services.deliverable_manifest import freeze
from .document_job_schema_rules import specification
from .project_document_archive import identity, timestamp, overrides
from .document_paths import _relative
from .document_template_catalogue import DOCUMENT_IDS
from ..project_document_job_schemas import DocumentBatchSubmit
from . import document_publication_history as publications

MAX_ROWS = 100000
MAX_CAPTURE_BYTES = 4 * 1024 * 1024
MAX_HISTORY_BYTES = 64 * 1024 * 1024
JOB_TABLES = frozenset(specification()['tables'])
KINDS = {'submitted', 'cancel_requested', 'retry_requested', 'item_started', 'item_succeeded',
         'item_failed', 'item_interrupted', 'worker_interrupted', 'store_restored', 'archive_imported'} | publications.KINDS


def canonical(raw, digest=None):
    if not isinstance(raw, str) or len(raw.encode()) > MAX_CAPTURE_BYTES:
        raise ValueError('Capture documentaire trop volumineuse')
    value = json.loads(raw)
    if not isinstance(value, dict) or freeze(value)[0] != raw:
        raise ValueError('Capture documentaire non canonique')
    if digest is not None and hashlib.sha256(raw.encode()).hexdigest() != digest:
        raise ValueError('Empreinte documentaire incorrecte')
    return value


def _actor(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 120 or any(ord(char) < 32 for char in value):
        raise ValueError('Auteur documentaire invalide')


def _number(value):
    if type(value) is not int or not 1 <= value <= MAX_ROWS:
        raise ValueError('Révision documentaire invalide')


def validate(tables):
    """Validate one project and all six queue tables, retaining raw captures."""
    spec = specification()['tables']
    if not isinstance(tables, dict) or not JOB_TABLES.issubset(tables):
        raise ValueError('Les six tables documentaires sont requises')
    projects = tables.get('projects')
    if not isinstance(projects, list) or len(projects) != 1:
        raise ValueError('Un projet documentaire requis')
    pid = projects[0]['id']
    identity(pid)
    ledger, all_ids, text_bytes = {}, {pid}, 0
    for name in JOB_TABLES:
        rows = tables[name]
        if not isinstance(rows, list) or len(rows) > MAX_ROWS:
            raise ValueError('Historique documentaire non borné')
        indexed = {}
        for row in rows:
            if not isinstance(row, dict) or set(row) != set(spec[name]['columns']) or row['project_id'] != pid:
                raise ValueError('Colonnes ou projet documentaire invalides')
            identity(row['id'])
            if row['id'] in all_ids:
                raise ValueError('Identifiant documentaire ambigu')
            all_ids.add(row['id'])
            indexed[row['id']] = row
            for column in ('created_at', 'updated_at'):
                if column in row:
                    timestamp(row[column])
            if 'actor_id' in row:
                _actor(row['actor_id'])
            for column in ('snapshot', 'detail', 'provenance'):
                if column in row:
                    if not isinstance(row[column], str):
                        raise ValueError('Capture documentaire textuelle requise')
                    text_bytes += len(row[column].encode())
                    if text_bytes > MAX_HISTORY_BYTES:
                        raise ValueError('Historique documentaire trop volumineux')
        ledger[name.removeprefix('project_document_')] = indexed
    jobs, items, attempts = ledger['jobs'], ledger['job_items'], ledger['job_attempts']
    artifacts, receipts, events = ledger['job_artifacts'], ledger['job_receipts'], ledger['job_events']
    if not jobs and any(ledger.values()):
        raise ValueError('Historique sans lot documentaire')
    items_by_job, attempts_by_item, events_by_job = defaultdict(list), defaultdict(list), defaultdict(list)
    for row in items.values():
        items_by_job[row['job_id']].append(row)
    for row in attempts.values():
        _number(row['number'])
        attempts_by_item[row['item_id']].append(row)
    for row in events.values():
        _number(row['revision'])
        events_by_job[row['job_id']].append(row)
    for name, rows in ledger.items():
        for row in rows.values():
            if name != 'jobs' and row['job_id'] not in jobs:
                raise ValueError('Lot documentaire parent absent')
            if name in {'job_attempts', 'job_artifacts', 'job_receipts'}:
                item = items.get(row['item_id'])
                if not item or item['job_id'] != row['job_id']:
                    raise ValueError('Fichier documentaire parent absent')
            if name in {'job_artifacts', 'job_receipts'}:
                attempt = attempts.get(row['attempt_id'])
                if not attempt or (attempt['job_id'], attempt['item_id']) != (row['job_id'], row['item_id']):
                    raise ValueError('Tentative documentaire parent absente')
    by_receipt, by_artifact, storage_keys = {}, {}, set()
    for row in artifacts.values():
        key = row['storage_key']
        if not isinstance(key, str) or str(UUID(key)) != key or key in storage_keys:
            raise ValueError('Stockage documentaire ambigu')
        storage_keys.add(key)
        filename = row['filename']
        if (not isinstance(filename, str) or not 1 <= len(filename) <= 255
                or PureWindowsPath(filename).name != filename or ':' in filename or '/' in filename
                or any(ord(char) < 32 for char in filename)):
            raise ValueError('Nom de copie documentaire invalide')
        if type(row['size_bytes']) is not int or not 1 <= row['size_bytes'] <= DOCUMENT_IMPORT_BYTES:
            raise ValueError('Taille de copie documentaire invalide')
        if not isinstance(row['sha256'], str) or len(row['sha256']) != 64 or set(row['sha256']) - set('0123456789abcdef'):
            raise ValueError('Empreinte de copie documentaire invalide')
        canonical(row['provenance'])
        if row['attempt_id'] in by_artifact:
            raise ValueError('Deux copies pour une tentative')
        by_artifact[row['attempt_id']] = row
    for row in receipts.values():
        if row['attempt_id'] in by_receipt or row['outcome'] not in {'succeeded', 'failed', 'interrupted'}:
            raise ValueError('Reçu documentaire ambigu')
        by_receipt[row['attempt_id']] = row
        if not isinstance(row['error'], str) or len(row['error']) > 1000:
            raise ValueError('Erreur documentaire invalide')
        artifact = by_artifact.get(row['attempt_id'])
        if row['outcome'] == 'succeeded':
            if not artifact or row['artifact_id'] != artifact['id'] or row['error']:
                raise ValueError('Succès documentaire sans copie validée')
        elif row['artifact_id'] is not None or artifact:
            raise ValueError('Copie documentaire sans reçu de succès')
    if set(by_artifact) - set(by_receipt):
        raise ValueError('Copie documentaire orpheline')
    command_ids = set()
    for job in jobs.values():
        _number(job['revision'])
        if job['command_id'] in command_ids:
            raise ValueError('Commande documentaire ambiguë')
        command_ids.add(job['command_id'])
        raw = canonical(job['snapshot'], job['sha256'])
        if DocumentBatchSubmit.model_validate(raw).model_dump() != raw:
            raise ValueError('Commande documentaire non canonique')
        if (set(raw) != {'command_id', 'items'} or raw['command_id'] != job['command_id']
                or type(job['total']) is not int or not 1 <= job['total'] <= 8
                or not isinstance(raw['items'], list) or len(raw['items']) != job['total']
                or type(job['cancel_requested']) not in {bool, int} or job['cancel_requested'] not in (0, 1)
                or type(job['execution_blocked']) not in {bool, int} or job['execution_blocked'] not in (0, 1)
                or job['status'] not in {'queued', 'running', 'completed', 'failed', 'cancelled', 'interrupted'}):
            raise ValueError('Capture du lot documentaire incohérente')
        own = sorted(items_by_job[job['id']], key=lambda i: i['position'])
        imports = [e for e in events_by_job[job['id']] if e['kind'] == 'archive_imported']
        bindings = None
        if imports:
            latest = canonical(max(imports, key=lambda e: e['revision'])['detail'])
            if (not job['execution_blocked'] or set(latest) not in ({'project_id', 'bindings'}, {'project_id', 'bindings', 'publication_bindings'}) or latest['project_id'] != pid
                    or not isinstance(latest['bindings'], dict) or set(latest['bindings']) != {i['id'] for i in own}):
                raise ValueError('Liaisons de lot importé incohérentes')
            bindings = latest['bindings']
        if len(own) != job['total'] or [i['position'] for i in own] != list(range(job['total'])):
            raise ValueError('Position documentaire incohérente')
        if len({i['document_id'] for i in own}) != job['total']:
            raise ValueError('Trame documentaire dupliquée')
        for item, command in zip(own, raw['items'], strict=True):
            if type(item['position']) is not int:
                raise ValueError('Position documentaire entière requise')
            capture = canonical(item['snapshot'], item['sha256'])
            if (set(capture) != {'command', 'preview', 'catalogue_sha256', 'draft_version_id'}
                    or capture['command'] != command or item['document_id'] not in DOCUMENT_IDS
                    or command['document_id'] != item['document_id']
                    or item['status'] not in {'queued', 'running', 'succeeded', 'failed', 'cancelled', 'interrupted'}):
                raise ValueError('Capture du fichier documentaire incohérente')
            expected_binding = {'link_id': item['link_id'], 'draft_version_id': item['draft_version_id']}
            if ((bindings is None and expected_binding != {'link_id': command['link_id'], 'draft_version_id': capture['draft_version_id']})
                    or bindings is not None and bindings[item['id']] != expected_binding):
                raise ValueError('Liaisons courantes différentes de la capture ou de l’import')
            identity(item['link_id'])
            identity(item['draft_version_id'], nullable=True)
            preview = capture['preview']
            if (not isinstance(preview, dict) or preview.get('can_prepare') is not True
                    or preview.get('can_prepare_copy') is not True
                    or any(preview.get(key) != command['expected_' + key] for key in ('source_sha256', 'link_sha256', 'values_sha256'))
                    or preview['field_values']['identity_revision'] != command['expected_identity_revision']
                    or preview['field_values']['planning_revision'] != command['expected_planning_revision']):
                raise ValueError('Aperçu capturé différent de la commande vérifiée')
            overrides(command['overrides'])
            source = preview['source']
            identity(source['project_id'])
            if (source['link_id'] != command['link_id'] or source['relative_path'] != _relative(command['relative_path'])
                    or source['sha256'] != command['expected_source_sha256']
                    or preview['field_values']['project_id'] != source['project_id']
                    or bindings is None and source['project_id'] != pid):
                raise ValueError('Source capturée différente de la commande ou du projet')
            values = {key: preview['field_values'][key] for key in ('project_id', 'identity_revision', 'planning_revision',
                'values', 'origins', 'warnings', 'oversized_fields')}
            if freeze(values)[1] != preview['values_sha256']:
                raise ValueError('Valeurs capturées différentes de leur empreinte')
            own_attempts = sorted(attempts_by_item[item['id']], key=lambda a: a['number'])
            if [a['number'] for a in own_attempts] != list(range(1, len(own_attempts) + 1)):
                raise ValueError('Journal des tentatives incomplet')
            last = own_attempts[-1]['id'] if own_attempts else None
            if item['last_attempt_id'] != last:
                raise ValueError('Dernière tentative incohérente')
            pending = [a['id'] for a in own_attempts if a['id'] not in by_receipt]
            if pending != ([last] if item['status'] == 'running' else []):
                raise ValueError('Tentative documentaire non clôturée')
            if item['status'] in {'succeeded', 'failed'} and (last not in by_receipt or by_receipt[last]['outcome'] != item['status']):
                raise ValueError('État du fichier différent de son reçu')
        active = [i['last_attempt_id'] for i in own if i['status'] == 'running']
        if active != ([job['active_attempt_id']] if job['active_attempt_id'] else []) or active and job['status'] != 'running':
            raise ValueError('Tentative active incohérente')
        states = {i['status'] for i in own}
        if (job['status'] == 'completed' and states != {'succeeded'}
                or job['status'] in {'completed', 'failed', 'cancelled', 'interrupted'} and states & {'queued', 'running'}):
            raise ValueError('Lot clôturé avec des fichiers actifs')
        own_events = sorted(events_by_job[job['id']], key=lambda e: e['revision'])
        if [e['revision'] for e in own_events] != list(range(1, job['revision'] + 1)):
            raise ValueError('Journal des événements incomplet')
        for event in own_events:
            if event['kind'] not in KINDS:
                raise ValueError('Événement documentaire inconnu')
            canonical(event['detail'])
        publications.for_job(ledger, job)
    return ledger
