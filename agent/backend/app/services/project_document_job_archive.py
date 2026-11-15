"""Typed queue closure and remapping. Captures and older journal text stay verbatim."""
from copy import deepcopy
from collections import defaultdict
from datetime import datetime, timezone
import json
from uuid import uuid4

from fastapi import HTTPException

from app.services.deliverable_manifest import freeze
from . import document_job_history as history
from . import document_publication_history as publications
from .project_document_archive import identity

PROJECT_TABLES = history.JOB_TABLES


def native_view(tables):
    return {name: rows for name, rows in tables.items() if name not in PROJECT_TABLES}


def invalid(message):
    raise HTTPException(400, 'Archive de lots documentaires : ' + message)


def validate(tables, section):
    try:
        if (not isinstance(section, dict) or set(section) != {'format', 'version', 'unresolved_link_ids'}
                or section['format'] != 'agent-project-document-jobs' or type(section['version']) is not int
                or section['version'] != 1):
            raise ValueError('section typée requise')
        ledger = history.validate(tables)
        if not ledger['jobs']:
            raise ValueError('au moins un lot requis')
        pid = tables['projects'][0]['id']
        links = tables.get('network_links', [])
        if not isinstance(links, list) or any(row.get('project_id') != pid for row in links):
            raise ValueError('liens étrangers au projet')
        link_ids = {row['id'] for row in links}
        seen = {row['link_id'] for row in ledger['job_items'].values()}
        for job in ledger['jobs'].values():
            seen.update(row['binding']['link_id'] for row in publications.for_job(ledger, job).values())
        missing = seen - link_ids
        declared = section['unresolved_link_ids']
        if not isinstance(declared, list) or declared != sorted(missing):
            raise ValueError('liens disparus absents ou ambigus')
        for key in declared:
            identity(key)
        versions = {row['id']: row for row in tables.get('project_document_draft_versions', [])}
        for row in ledger['job_items'].values():
            if row['draft_version_id'] is not None:
                version = versions.get(row['draft_version_id'])
                if not version or version['project_id'] != pid or version['document_id'] != row['document_id']:
                    raise ValueError('version du formulaire absente ou étrangère')
        native_ids = {row['id'] for rows in native_view(tables).values() for row in rows if 'id' in row}
        queue_ids = {row['id'] for name in PROJECT_TABLES for row in tables[name]}
        if queue_ids & native_ids or missing & (native_ids | queue_ids):
            raise ValueError('identifiant ambigu entre lots, liens et objets natifs')
        return {'unresolved_link_ids': missing}
    except HTTPException as exc:
        invalid(str(exc.detail))
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        invalid(str(exc))


def section_for(tables):
    links = {row['id'] for row in tables.get('network_links', [])}
    seen = {row['link_id'] for row in tables['project_document_job_items']}
    ledger = history.validate(tables)
    for job in ledger['jobs'].values():
        seen.update(row['binding']['link_id'] for row in publications.for_job(ledger, job).values())
    section = {'format': 'agent-project-document-jobs', 'version': 1, 'unresolved_link_ids': sorted(seen - links)}
    validate(tables, section)
    return section


def embedded_bytes(tables):
    return sum(len(json.dumps(row, ensure_ascii=False, allow_nan=False).encode())
               for name in PROJECT_TABLES for row in tables.get(name, []))


def validate_files(tables, decoded):
    artifacts = {row['id']: row for row in tables['project_document_job_artifacts']}
    found = set()
    for entry, content, digest in decoded:
        if entry['area'] != 'document-job':
            continue
        row = artifacts.get(entry['owner'])
        if (row is None or entry['owner'] in found or set(entry) != {'owner', 'area', 'name', 'sha256', 'data'}
                or entry['name'] != row['storage_key'] or digest != row['sha256'] or len(content) != row['size_bytes']):
            invalid('copie absente, altérée ou ambiguë')
        found.add(entry['owner'])
    if found != set(artifacts):
        invalid('inventaire des copies incomplet')


def import_rows(tables, mapping, *, actor):
    """Flat IDs only, explicit import binding record, no automatic IO or retry."""
    ledger = history.validate(tables)
    publication_bindings = {mapping[job['id']]: {
        cid: {key:mapping[value] for key, value in record['binding'].items()}
        for cid, record in publications.for_job(ledger, job).items()} for job in ledger['jobs'].values()}
    references = {'id', 'project_id', 'job_id', 'item_id', 'attempt_id', 'artifact_id',
                  'active_attempt_id', 'last_attempt_id', 'link_id', 'draft_version_id'}
    result = {}
    for name in PROJECT_TABLES:
        result[name] = []
        for original in tables[name]:
            row = deepcopy(original)
            for key in references & set(row):
                if row[key] is not None:
                    row[key] = mapping[row[key]]
            if name == 'project_document_job_artifacts':
                row['storage_key'] = mapping[original['id']]
            result[name].append(row)
    occupied = set(mapping.values())

    def fresh():
        for _ in range(10):
            value = str(uuid4())
            if value not in occupied:
                occupied.add(value)
                return value
        raise HTTPException(409, 'Allocation des identifiants de journal impossible')

    timestamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    items = {row['id']: row for row in result['project_document_job_items']}
    items_by_job = defaultdict(list)
    for item in items.values():
        items_by_job[item['job_id']].append(item)
    attempts = {row['id']: row for row in result['project_document_job_attempts']}
    for job in result['project_document_jobs']:
        own = items_by_job[job['id']]
        if job['active_attempt_id']:
            attempt = attempts[job['active_attempt_id']]
            result['project_document_job_receipts'].append({
                'id': fresh(), 'project_id': job['project_id'], 'job_id': job['id'], 'item_id': attempt['item_id'],
                'attempt_id': attempt['id'], 'artifact_id': None, 'outcome': 'interrupted',
                'error': 'Archive importée : génération historique suspendue', 'created_at': timestamp})
        for item in own:
            if item['status'] in {'queued', 'running'}:
                item['status'] = 'interrupted'
        if job['status'] in {'queued', 'running'}:
            job['status'] = 'interrupted'
        job['execution_blocked'] = True
        job['active_attempt_id'] = None
        job['revision'] += 1
        job['updated_at'] = timestamp
        detail = {'project_id': job['project_id'], 'bindings': {
            item['id']: {'link_id': item['link_id'], 'draft_version_id': item['draft_version_id']} for item in own}}
        if publication_bindings[job['id']]:
            detail['publication_bindings'] = publication_bindings[job['id']]
        result['project_document_job_events'].append({
            'id': fresh(), 'project_id': job['project_id'], 'job_id': job['id'], 'revision': job['revision'],
            'kind': 'archive_imported', 'actor_id': actor, 'created_at': timestamp,
            'detail': freeze(detail)[0]})
    history.validate({'projects': [{'id': mapping[tables['projects'][0]['id']]}], **result})
    return result


def require_schema(db):
    from .document_jobs import _ready
    if not _ready(db):
        raise HTTPException(409, 'Installer explicitement la file documentaire après sauvegarde')
