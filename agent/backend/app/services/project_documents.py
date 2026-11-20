"""Scoped interactive document preview/copy, without implicit network publication.

Durable batch jobs and prepared-file receipts are separate upcoming commands.
This copy operation returns bounded bytes and changes no project/file data.
"""
import hashlib
import json
from pathlib import Path
from string import Formatter

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import NetworkLink
from .deliverable_files import _filename
from .document_file_access import acquire_file, configured_policy
from .document_discovery import discover_many
from .document_package_prepare import prepare_package
from .document_package_preview import preview_package
from .document_project_values import project_values
from .document_search_rules import SearchRule
from .document_template_catalogue import catalogue, document_spec
from .project_identity import _project
from .project_operator import current_operator
from .document_forms import effective_preferences


def values_sha256(state):
    frozen = {key: state[key] for key in ('project_id', 'identity_revision', 'planning_revision',
        'values', 'origins', 'warnings', 'oversized_fields')}
    return hashlib.sha256(json.dumps(frozen, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _link_sha256(db, project_id, link_id):
    link = db.query(NetworkLink).filter_by(project_id=project_id, id=link_id).first()
    if link is None:
        raise HTTPException(404, 'Lien documentaire introuvable dans ce projet')
    return hashlib.sha256(json.dumps([link.id, link.project_id, link.chemin], ensure_ascii=False).encode()).hexdigest()


def workspace(db, project_id, *, offset=0, limit=100):
    state = project_values(db, project_id)  # Parent check before configuration/probes.
    preferences = effective_preferences(db, project_id)
    from . import document_jobs
    batch_available = document_jobs._ready(db)
    templates = {row['id']: row for row in catalogue()['documents']}
    effective_templates = [{**templates[row['document_id']], 'label': row['label'], 'search_active': row['active']}
                           for row in preferences['items']]
    if type(offset) is not int or type(limit) is not int or not 0 <= offset <= 1_000_000 or not 1 <= limit <= 200:
        raise HTTPException(422, 'Pagination documentaire invalide')
    query = db.query(NetworkLink).filter_by(project_id=project_id)
    total = query.count()
    links = [{'id': row.id, 'code': row.code, 'label': row.libelle, 'path': row.chemin, 'order': row.ordre}
             for row in query.order_by(NetworkLink.ordre, NetworkLink.id).offset(offset).limit(limit).all()]
    try:
        policy = configured_policy(project_id)
        status = {'status': 'configured' if policy.roots else 'disabled',
                  'detail': '' if policy.roots else 'Racines documentaires à configurer sur le serveur'}
    except HTTPException as exc:
        status = {'status': 'invalid', 'detail': exc.detail}
    return {**state, 'values_sha256': values_sha256(state), 'templates': effective_templates,
            'search_preferences': preferences,
            'links': {'items': links, 'total': total, 'offset': offset, 'limit': limit},
            'file_access': status, 'can_prepare_copy': current_operator().role != 'reader',
            'publication': 'explicit_separate_command', 'batch_available': batch_available}


def discover_folder(db, project_id, link_id):
    preferences = effective_preferences(db, project_id)
    values = project_values(db, project_id)['values']
    rules, output_names, fields = [], {}, {}
    for item in preferences['items']:
        if not item['active']:
            continue
        document_id = item['document_id']
        rules.append(SearchRule(document_id, tuple(item['relative_paths']), tuple(item['filename_patterns']),
                                tuple(item['excluded_tokens']), item['preferred_version']))
        spec = document_spec(document_id)
        fields[document_id] = sorted({field for _, field in (*spec['cells'], *spec['bookmarks'])
                                      if not values[field].strip()})
        keys = [key for _, key, _, _ in Formatter().parse(spec['output_name']) if key]
        output_names[document_id] = None
        if all(values[key].strip() for key in keys):
            try:
                output_names[document_id] = _filename(spec['output_name'].format_map(values))
            except HTTPException:
                pass  # The document preview explains invalid output names.
    if not rules:
        raise HTTPException(409, 'Aucune recherche de trame active dans les réglages documentaires')
    result = discover_many(db, project_id, link_id=link_id, rules=rules, output_names=output_names)
    return {**result, 'items': [{**row, 'missing_fields': fields[row['document_id']]} for row in result['items']]}


def _read(db, project_id, payload, *, prepare=False):
    _project(db, project_id, write=prepare)
    state = project_values(db, project_id, overrides=payload.overrides)
    fingerprint = values_sha256(state)
    if prepare and (fingerprint != payload.expected_values_sha256
                    or state['identity_revision'] != payload.expected_identity_revision
                    or state['planning_revision'] != payload.expected_planning_revision):
        raise HTTPException(409, 'Données métier modifiées depuis l’aperçu : consulter les changements')
    binding = _link_sha256(db, project_id, payload.link_id)
    if prepare and binding != payload.expected_link_sha256:
        raise HTTPException(409, 'Lien du projet modifié depuis l’aperçu : refaire l’aperçu')
    data, source = acquire_file(db, project_id, link_id=payload.link_id, relative_path=payload.relative_path,
                               expected_sha256=payload.expected_source_sha256 if prepare else None)
    spec = document_spec(payload.document_id)
    if Path(source['filename']).suffix.lower() != '.' + spec['format'].lower():
        raise HTTPException(422, 'Extension du fichier incompatible avec la trame')
    try:
        report = preview_package(data, payload.document_id, state['values'])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    filename = None
    name_error = None
    try:
        filename = _filename(spec['output_name'].format_map(state['values']))
    except (HTTPException, ValueError, KeyError) as exc:
        name_error = exc.detail if isinstance(exc, HTTPException) else 'Nom de sortie documentaire invalide'
    if name_error:
        report['blockers'] = sorted(set([*report['blockers'], 'output_filename_invalid']))
        report['can_prepare'] = False
    return data, {**report, 'source': source, 'link_sha256': binding, 'field_values': state, 'values_sha256': fingerprint,
                  'output_filename': filename, 'output_filename_error': name_error,
                  'can_prepare_copy': current_operator().role != 'reader'}


def _fresh_values(db, project_id, overrides, report):
    # A network read can outlive an ORM identity cache/read transaction. A new
    # connection checks changes to client/person rows as well as project rows.
    bind = db.get_bind()
    engine = getattr(bind, 'engine', bind)
    with Session(bind=engine) as fresh:
        fingerprint = values_sha256(project_values(fresh, project_id, overrides=overrides))
        try:
            binding = _link_sha256(fresh, project_id, report['source']['link_id'])
        except HTTPException as exc:
            raise HTTPException(409, 'Lien du projet indisponible pendant préparation : refaire l’aperçu') from exc
        if binding != report['link_sha256']:
            raise HTTPException(409, 'Lien du projet modifié pendant préparation : refaire l’aperçu')
        return fingerprint


def preview(db, project_id, payload):
    _, report = _read(db, project_id, payload)
    if _fresh_values(db, project_id, payload.overrides, report) != report['values_sha256']:
        raise HTTPException(409, 'Données métier modifiées pendant l’aperçu : recharger')
    return report


def prepare_copy(db, project_id, payload):
    data, report = _read(db, project_id, payload, prepare=True)
    if not report['can_prepare']:
        raise HTTPException(422, 'Compléter les champs et corriger les cibles bloquantes avant préparation')
    try:
        copied, prepared = prepare_package(data, payload.document_id, report['field_values']['values'],
                                          expected_sha256=payload.expected_source_sha256)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if _fresh_values(db, project_id, payload.overrides, report) != report['values_sha256']:
        raise HTTPException(409, 'Données métier modifiées pendant préparation : refaire l’aperçu')
    return copied, {**report, 'preparation': prepared, 'network_published': False,
                    'persistent_receipt': False}
