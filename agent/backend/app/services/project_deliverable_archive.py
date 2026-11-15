"""V5 deliverable closure, bounded evidence validation and typed remapping.

This contract is deliberately independent from archive transport/file writes.
The v5 importer/exporter uses this contract before its reconciliation and file
transport. Loading this module never installs a schema.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import re

from fastapi import HTTPException

from app.services import deliverable_manifest as manifest
from ..project_deliverable_models import DELIVERABLE_TABLES
from ..project_deliverable_schemas import SelectionPreview, TypeDefinition
from .project_deliverable_rules import TRANSITIONS

PROJECT_TABLES = frozenset(table.name for table in DELIVERABLE_TABLES if 'project_id' in table.c)
REFERENCE_TABLES = frozenset({'project_deliverable_types', 'project_deliverable_type_versions',
                              'project_deliverable_typology_types', 'project_reference_changes'})
ACTIONS = frozenset({'deliverable_created', 'deliverable_metadata_changed', 'deliverable_check_created',
                    'deliverable_check_changed', 'deliverable_version_published', 'deliverable_version_metadata_changed',
                    'deliverable_status_changed', 'deliverable_selection_changed', 'deliverable_selection_applied'})
STATUS = frozenset(TRANSITIONS)
ROLES = frozenset({'responsible_id', 'verifier_id'})
SCALAR_IDS = {'deliverable_id': 'deliverables', 'type_version_id': 'type_versions',
              'responsible_id': 'people', 'verifier_id': 'people', 'source_delivery_id': 'deliveries',
              'milestone_id': 'milestones', 'completed_version_id': 'files'}
CHECK_FIXED = frozenset({'id', 'code', 'scope_key', 'milestone_id', 'position', 'is_gate', 'transverse', 'contributes'})


def invalid(message):
    raise HTTPException(400, 'Archive de livrables : ' + message)


def _integer(value, *, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('entier invalide')


def _text(value, maximum, *, minimum=0):
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise ValueError('texte invalide')


def _bool(value):
    if type(value) is not bool:
        raise ValueError('indicateur invalide')


def _date(value):
    datetime.fromisoformat(value)


def _hash(value):
    if not isinstance(value, str) or re.fullmatch(r'[a-f0-9]{64}', value) is None:
        raise ValueError('empreinte invalide')


def _values(value, required, optional=()):
    if not isinstance(value, dict) or not set(required).issubset(value) or set(value) - set(required) - set(optional):
        raise ValueError('champs absents ou étrangers')


def _list(value, maximum=100000):
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError('liste invalide')
    return value


def _id_list(value, maximum=100000):
    result = _list(value, maximum)
    for identity in result:
        manifest.identity(identity)
    if len(set(result)) != len(result):
        raise ValueError('identifiant dupliqué')
    return result


def _rows(metadata, section):
    _values(section, REFERENCE_TABLES)
    identities = set()
    for name, values in section.items():
        table = metadata.tables[name]
        for row in _list(values):
            _values(row, table.c.keys())
            manifest.identity(row['id'])
            if row['id'] in identities:
                raise ValueError('identifiant global ambigu')
            identities.add(row['id'])
    return identities


def validate_section(metadata, section):
    try:
        return _rows(metadata, section)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        invalid(str(exc))


def project_dependencies(tables):
    """Only project pointers and compositions of its current/historical typologies.

Global audit rows cannot justify importing unrelated global types/typologies.
Definitions contain literal typology codes, which never become UUID pointers.
"""
    people, versions, types, typologies = set(), set(), set(), set()
    def add(value):
        if not isinstance(value, dict):
            raise ValueError('instantané invalide')
        for key in ROLES:
            if value.get(key) is not None:
                manifest.identity(value[key])
                people.add(value[key])
        if value.get('type_version_id') is not None:
            manifest.identity(value['type_version_id'])
            versions.add(value['type_version_id'])
        if value.get('typology_id') is not None:
            manifest.identity(value['typology_id'])
            typologies.add(value['typology_id'])
    for name in ('project_profiles', 'project_deliverable_plans'):
        for row in tables.get(name, []):
            add(row)
    for row in tables.get('project_identity_changes', []) + tables.get('project_deliverable_events', []):
        add(row['previous'])
        add(row['value'])
    for row in tables.get('project_deliverable_file_versions', []):
        add(manifest.check_row(row))
    for event in tables.get('project_planning_changes', []):
        if event.get('action') not in ACTIONS:
            continue
        for value in (event['previous'], event['value']):
            add(value)
        if event['action'] == 'deliverable_selection_applied':
            inputs = event['value']['inputs']
            SelectionPreview.model_validate(inputs)
            add(inputs)
            versions.update(_id_list(inputs['type_version_ids'], 100))
            types.update(inputs['existing_mapping'])
            for operation in _list(event['value']['operations'], 200):
                manifest.identity(operation['type_id'])
                manifest.identity(operation['version_id'])
                types.add(operation['type_id'])
                versions.add(operation['version_id'])
    if tables.get('project_review_publications'):
        from .project_review_archive import deliverable_type_dependencies
        versions.update(deliverable_type_dependencies(tables))
    return {'people': people, 'type_versions': versions, 'types': types, 'typologies': typologies}


def dependencies(tables, section):
    used = project_dependencies(tables)
    people, versions, types, typologies = (used[key] for key in ('people', 'type_versions', 'types', 'typologies'))
    for link in section['project_deliverable_typology_types']:
        if link['typology_id'] in typologies:
            manifest.identity(link['type_id'])
            types.add(link['type_id'])
    for event in section['project_reference_changes']:
        if event['entity_kind'] == 'reference' and event['entity_id'] in typologies:
            for value in (event['previous'], event['value']):
                if 'deliverable_selection' in value:
                    types.update(_id_list(value['deliverable_selection']['type_ids'], 100))
    heads = {row['id']: row for row in section['project_deliverable_type_versions']}
    for identity in versions:
        if identity not in heads:
            raise ValueError('version de type utilisée absente')
        types.add(heads[identity]['type_id'])
    return {'people': people, 'type_versions': versions, 'types': types, 'typologies': typologies}


def identity_dependencies(tables, section):
    try:
        used = dependencies(tables, section)
        return {identity: 'typology' for identity in used['typologies']}, used['people']
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        invalid(str(exc))


def _pointer(context, kind, value, *, owner=None, required=False):
    manifest.identity(value, optional=not required)
    if value is None:
        return
    if value not in context[kind]:
        raise ValueError('parent absent ou étranger : ' + kind)
    if owner is not None and context[kind][value]['deliverable_id'] != owner:
        raise ValueError('preuve/version appartenant à un autre livrable')


def _check(context, value, owner):
    manifest.check_snapshot(value)
    _pointer(context, 'checks', value['id'], owner=owner, required=True)
    _pointer(context, 'milestones', value['milestone_id'])
    _pointer(context, 'files', value['completed_version_id'], owner=owner)
    current = context['checks'][value['id']]
    if any(value[key] != current[key] for key in CHECK_FIXED):
        raise ValueError('structure de contrôle différente de son historique')
    if value['is_gate'] and not value['active']:
        raise ValueError('gate obligatoire désactivé')


def _check_history(context, owner, events):
    """Replay captured snapshots and the implicit gate resets without writes."""
    known = {}
    status = 'draft'
    for event in events:
        action, value = event['action'], event['value']
        if action in {'deliverable_check_created', 'deliverable_check_changed'}:
            if status in {'validated', 'archived'}:
                raise ValueError('contrôle modifié sans réouverture')
            identity = value['id']
            if action == 'deliverable_check_created':
                if identity in known:
                    raise ValueError('contrôle créé plusieurs fois')
            elif identity in known and not _same_check(event['previous'], known[identity]):
                raise ValueError('état précédent de contrôle incohérent')
            known[identity] = deepcopy(value)
        elif action == 'deliverable_version_published':
            version = context['files'][value['version_id']]
            captured = {row['id']: row for row in manifest.check_row(version)['checklist']}
            if any(identity not in captured or not _same_check(captured[identity], check) for identity, check in known.items()):
                raise ValueError('checklist publiée différente de son historique')
            known.update(deepcopy(captured))
            status = 'draft'
        elif action == 'deliverable_status_changed':
            status = value['document_status']
            if status == 'validated' and any(check['active'] and check['is_gate'] and (
                    not check['completed'] or check['completed_version_id'] != value['version_id'] or not check['proof'].strip())
                    for check in known.values()):
                raise ValueError('visa historique sans ses gates humains')
        if action == 'deliverable_version_published' or action == 'deliverable_status_changed' and status == 'to_revise':
            for check in known.values():
                if check['is_gate']:
                    check.update(completed=False, completed_version_id=None, completed_by=None, completed_at=None)
    for identity, expected in known.items():
        current = {key: context['checks'][identity][key] for key in manifest.CHECK_FIELDS}
        if not _same_check(current, expected):
            raise ValueError('contrôle courant différent de son dernier état historique')


def _same_check(left, right):
    def normalized(value):
        result = deepcopy(value)
        if result['completed_at'] is not None:
            stamp = datetime.fromisoformat(result['completed_at'])
            # SQLite stores UTC DateTime without an offset; JSON may retain it.
            stamp = stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
            result['completed_at'] = stamp.isoformat()
        return result
    return normalized(left) == normalized(right)


def _selection(context, value, revision):
    _values(value, {'preview_sha256', 'operations', 'inputs', 'excluded_milestone_codes'})
    _hash(value['preview_sha256'])
    inputs = SelectionPreview.model_validate(value['inputs'])
    if inputs.expected_revision != revision - 1 or inputs.excluded_milestone_codes != value['excluded_milestone_codes']:
        raise ValueError('choix historiques ou révision incohérents')
    for kind, identities in (('type_versions', inputs.type_version_ids), ('milestones', inputs.milestone_mapping.values()),
                             ('types', inputs.existing_mapping), ('deliverables', inputs.existing_mapping.values())):
        for identity in identities:
            _pointer(context, kind, identity, required=True)
    _pointer(context, 'typologies', inputs.typology_id)
    for key in ROLES:
        _pointer(context, 'people', getattr(inputs, key))
    selected = {context['type_versions'][identity]['type_id'] for identity in inputs.type_version_ids}
    if len(selected) != len(inputs.type_version_ids) or set(inputs.existing_mapping) - selected:
        raise ValueError('types sélectionnés dupliqués ou correspondance non sélectionnée')
    codes = {item.milestone_code for identity in inputs.type_version_ids for item in
             TypeDefinition.model_validate_json(context['type_versions'][identity]['definition']).checklist
             if item.active and item.milestone_code}
    if (set(inputs.milestone_mapping) | set(inputs.excluded_milestone_codes)) - codes:
        raise ValueError('code de jalon historique étranger aux types')
    operations = _list(value['operations'], 200)
    seen = set()
    for operation in operations:
        _values(operation, {'operation', 'type_id', 'version_id', 'deliverable_id', 'label'})
        if operation['operation'] not in {'create', 'adopt', 'reactivate', 'deactivate'}:
            raise ValueError('opération de sélection inconnue')
        for key, kind in (('type_id', 'types'), ('version_id', 'type_versions'), ('deliverable_id', 'deliverables')):
            _pointer(context, kind, operation[key], required=True)
        if context['type_versions'][operation['version_id']]['type_id'] != operation['type_id']:
            raise ValueError('version sélectionnée appartenant à un autre type')
        plan = context['plans'].get(operation['deliverable_id'])
        if not plan or not plan['type_version_id'] or context['type_versions'][plan['type_version_id']]['type_id'] != operation['type_id']:
            raise ValueError('opération sur une fiche non typée ou d’un autre type')
        if operation['operation'] == 'deactivate':
            if not inputs.deactivate_missing or operation['type_id'] in selected:
                raise ValueError('désactivation non explicitement demandée')
        elif operation['type_id'] not in selected:
            raise ValueError('opération sur un type non sélectionné')
        if operation['deliverable_id'] in seen:
            raise ValueError('livrable dupliqué dans la sélection')
        seen.add(operation['deliverable_id'])
        _text(operation['label'], 255, minimum=1)


def validate_event(context, event, *, planning=False):
    """Action dispatch distinguishes file version_id from selection type versions."""
    action = event['action']
    if action not in ACTIONS or action == 'deliverable_selection_applied' and not planning:
        raise ValueError('action de livrable inconnue')
    previous, value = deepcopy(event['previous']), deepcopy(event['value'])
    owner = event.get('deliverable_id')
    if action == 'deliverable_selection_applied':
        _values(previous, set())
        _selection(context, value, event['revision'])
        return
    if planning:
        owner = value.pop('deliverable_id', None)
        if previous.pop('deliverable_id', None) != owner:
            raise ValueError('historique de livrable étranger')
    _pointer(context, 'deliverables', owner, required=True)
    for snapshot in (previous, value):
        if not isinstance(snapshot, dict):
            raise ValueError('instantané de livrable invalide')
        for key, kind in SCALAR_IDS.items():
            if key in snapshot:
                _pointer(context, kind, snapshot[key], owner=owner if kind == 'files' else None)
    if 'legacy_status' in value and value['legacy_status'] not in {'todo', 'in_progress', 'done', 'cancelled'}:
        raise ValueError('statut historique invalide')
    if action == 'deliverable_created':
        _values(previous, set())
        _values(value, {'title', 'type_version_id', 'milestone_ids', 'milestone_mapping', *ROLES}, {'legacy_status'})
        _text(value['title'], 255, minimum=1)
        for identity in _id_list(value['milestone_ids'], 100):
            _pointer(context, 'milestones', identity, required=True)
        if not isinstance(value['milestone_mapping'], dict) or len(value['milestone_mapping']) > 100:
            raise ValueError('correspondance de jalons invalide')
        for code, identity in value['milestone_mapping'].items():
            _text(code, 64, minimum=1)
            if identity not in value['milestone_ids']:
                raise ValueError('jalon de checklist non sélectionné')
    elif action == 'deliverable_metadata_changed':
        if set(previous) != set(value) | {'title'} or set(value) - {'title', 'active', 'comment', 'legacy_status', *ROLES}:
            raise ValueError('métadonnées de livrable invalides')
        for snapshot in (previous, value):
            if 'title' in snapshot:
                _text(snapshot['title'], 255, minimum=1)
            if 'active' in snapshot:
                _bool(snapshot['active'])
            if 'comment' in snapshot:
                _text(snapshot['comment'], 20000)
            if 'legacy_status' in snapshot:
                _text(snapshot['legacy_status'], 32)
    elif action in {'deliverable_check_created', 'deliverable_check_changed'}:
        if action == 'deliverable_check_created':
            _values(previous, set())
        else:
            _check(context, previous, owner)
            if previous['id'] != value['id']:
                raise ValueError('identité de contrôle historique différente')
        _check(context, value, owner)
    elif action == 'deliverable_version_published':
        _values(previous, {'document_status'})
        _values(value, {'version_id', 'number', 'sha256', 'manifest_sha256', 'document_status', 'source_delivery_id'})
        _pointer(context, 'files', value['version_id'], owner=owner, required=True)
        row = context['files'][value['version_id']]
        if any(value[key] != row[key] for key in ('number', 'sha256', 'manifest_sha256', 'source_delivery_id')):
            raise ValueError('publication historique différente de sa version')
        if previous['document_status'] not in STATUS or value['document_status'] != 'draft':
            raise ValueError('publication avec état incohérent')
    elif action == 'deliverable_version_metadata_changed':
        if set(previous) != set(value) or set(value) - {'version_id', 'reference', 'comment'}:
            raise ValueError('métadonnées de version invalides')
        if previous.get('version_id') != value.get('version_id'):
            raise ValueError('version de métadonnées historique différente')
        _pointer(context, 'files', value.get('version_id'), owner=owner, required=True)
        for snapshot in (previous, value):
            if 'reference' in snapshot:
                _text(snapshot['reference'], 120, minimum=1)
            if 'comment' in snapshot:
                _text(snapshot['comment'], 20000)
    elif action == 'deliverable_status_changed':
        _values(previous, {'document_status'})
        _values(value, {'document_status', 'version_id', 'comment'})
        if value['document_status'] not in TRANSITIONS.get(previous['document_status'], set()):
            raise ValueError('transition historique impossible')
        _pointer(context, 'files', value['version_id'], owner=owner, required=True)
        _text(value['comment'], 20000)
        if value['document_status'] == 'validated' and not value['comment'].strip():
            raise ValueError('visa humain sans commentaire')
    elif action == 'deliverable_selection_changed':
        for snapshot in (previous, value):
            _values(snapshot, {'active', 'type_version_id', *ROLES})
            _bool(snapshot['active'])


def _global_event(context, event):
    entity, kind = event['entity_id'], event['entity_kind']
    bucket = 'types' if kind == 'deliverable_type' else 'typologies' if kind == 'reference' else None
    if bucket is None:
        raise ValueError('historique global étranger aux livrables')
    _pointer(context, bucket, entity, required=True)
    if event['revision'] > context[bucket][entity]['revision']:
        raise ValueError('historique global plus récent que sa fiche')
    if not event['value']:
        raise ValueError('historique global sans état résultant')
    for value in (event['previous'], event['value']):
        if not isinstance(value, dict):
            raise ValueError('instantané global invalide')
        if not value:
            continue
        if 'deliverable_selection' in value:
            _values(value, {'deliverable_selection'})
            selection = value['deliverable_selection']
            _values(selection, {'typology_id', 'code', 'revision', 'type_ids', 'active'})
            if kind != 'reference' or selection['typology_id'] != entity:
                raise ValueError('composition étrangère à sa typologie')
            _text(selection['code'], 64, minimum=1)
            if selection['code'] != context['typologies'][entity]['code']:
                raise ValueError('code de composition différent de sa typologie')
            _bool(selection['active'])
            _integer(selection['revision'], minimum=1)
            for identity in _id_list(selection['type_ids'], 100):
                _pointer(context, 'types', identity, required=True)
            continue
        if 'published_version' in value:
            _values(value, {'published_version'})
            value = value['published_version']
            _values(value, {'id', 'version_id', 'revision', 'sha256'})
            if kind != 'deliverable_type':
                raise ValueError('publication de type dans un référentiel de typologie')
        else:
            fields = {'id', 'code', 'label', 'active', 'revision'} | ({'kind'} if kind == 'reference' else set())
            if kind == 'deliverable_type' and 'version_id' in value:
                fields |= {'version_id', 'sha256'}
            _values(value, fields)
        if value.get('id') != entity:
            raise ValueError('champs de fiche globale inconnus ou étrangers')
        if 'code' in value and value['code'] != context[bucket][entity]['code']:
            raise ValueError('code de fiche globale modifié dans l’historique')
        for key, maximum in (('code', 64), ('label', 255)):
            if key in value:
                _text(value[key], maximum, minimum=1)
        if 'active' in value:
            _bool(value['active'])
        if 'revision' in value:
            _integer(value['revision'], minimum=1)
            if value['revision'] > event['revision']:
                raise ValueError('instantané global plus récent que son événement')
        if 'kind' in value and value['kind'] != 'typology':
            raise ValueError('nature de référentiel historique étrangère')
        if 'version_id' in value:
            _pointer(context, 'type_versions', value['version_id'], required=True)
            version = context['type_versions'][value['version_id']]
            if kind != 'deliverable_type' or version['type_id'] != entity or value.get('sha256') != version['sha256']:
                raise ValueError('publication de type étrangère à son historique')


def validate(metadata, tables, section, references, *, planning_references=None):
    """Validate V5 before transport writes. Returns a typed lookup for remapping."""
    try:
        global_ids = _rows(metadata, section)
        from .project_archive import _validate_tables
        _validate_tables(metadata, tables, parents={**references, **(planning_references or {}), **section})
        others = [row['id'] for group in (tables, references, planning_references or {}) for rows in group.values() for row in rows if 'id' in row]
        if len(others) != len(set(others)) or global_ids.intersection(others):
            raise ValueError('identifiant ambigu entre projet et référentiels')
        used = dependencies(tables, section)
        context = {key: {row['id']: row for row in rows} for key, rows in (
            ('deliverables', tables.get('deliverables', [])), ('milestones', tables.get('milestones', [])),
            ('checks', tables.get('project_deliverable_checklist', [])), ('files', tables.get('project_deliverable_file_versions', [])),
            ('deliveries', tables.get('delivery_versions', [])), ('people', references['project_people']),
            ('types', section['project_deliverable_types']), ('type_versions', section['project_deliverable_type_versions']),
            ('typologies', [row for row in references['project_references'] if row['kind'] == 'typology']))}
        if set(context['types']) != used['types'] or not used['people'].issubset(context['people']):
            raise ValueError('type global étranger ou personne utilisée absente')
        if not used['typologies'].issubset(context['typologies']):
            raise ValueError('typologie utilisée absente')
        project_id = tables['projects'][0]['id']
        project_ids = set()
        for name in PROJECT_TABLES:
            for row in _list(tables.get(name, [])):
                _values(row, metadata.tables[name].c.keys())
                if row['project_id'] != project_id:
                    raise ValueError('ligne de livrable appartenant à un autre projet')
                if 'id' in row:
                    manifest.identity(row['id'])
                    if row['id'] in project_ids or row['id'] in global_ids:
                        raise ValueError('identifiant de livrable ambigu')
                    project_ids.add(row['id'])
        codes = set()
        for row in context['types'].values():
            if not isinstance(row['code'], str) or re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', row['code']) is None or row['code'] in codes:
                raise ValueError('code de type non canonique ou dupliqué')
            codes.add(row['code'])
            _text(row['label'], 255, minimum=1)
            _bool(row['active'])
            _integer(row['revision'], minimum=1)
        numbers = {}
        for row in context['type_versions'].values():
            _pointer(context, 'types', row['type_id'], required=True)
            _integer(row['number'], minimum=1)
            _text(row['actor_id'], 120, minimum=1)
            _date(row['created_at'])
            if hashlib.sha256(row['definition'].encode('utf-8')).hexdigest() != row['sha256']:
                raise ValueError('empreinte de définition de type incohérente')
            TypeDefinition.model_validate_json(row['definition'])
            bucket = numbers.setdefault(row['type_id'], set())
            if row['number'] in bucket:
                raise ValueError('numéro de version de type dupliqué')
            bucket.add(row['number'])
        for identity, row in context['types'].items():
            bucket = numbers.get(identity, set())
            if not bucket or max(bucket) != len(bucket) or max(bucket) > row['revision']:
                raise ValueError('catalogue incomplet ou révision incohérente')
        pairs = set()
        for row in section['project_deliverable_typology_types']:
            if row['typology_id'] not in used['typologies']:
                raise ValueError('composition de typologie étrangère au projet')
            _pointer(context, 'types', row['type_id'], required=True)
            _bool(row['active'])
            pair = (row['typology_id'], row['type_id'])
            if pair in pairs:
                raise ValueError('composition dupliquée')
            pairs.add(pair)
        plans = {}
        for row in tables.get('project_deliverable_plans', []):
            _pointer(context, 'deliverables', row['deliverable_id'], required=True)
            if row['deliverable_id'] in plans:
                raise ValueError('plan de livrable dupliqué')
            plans[row['deliverable_id']] = row
            for key, kind in (('type_version_id', 'type_versions'), ('responsible_id', 'people'), ('verifier_id', 'people')):
                _pointer(context, kind, row[key])
            _bool(row['active'])
            _text(row['comment'], 20000)
            _integer(row['position'])
            if row['document_status'] not in STATUS:
                raise ValueError('état de livrable invalide')
        context['plans'] = plans
        links, pairs = {}, set()
        for row in tables.get('project_deliverable_milestones', []):
            if row['deliverable_id'] not in plans:
                raise ValueError('rattachement sans plan de livrable')
            _pointer(context, 'milestones', row['milestone_id'], required=True)
            _bool(row['active'])
            pair = (row['deliverable_id'], row['milestone_id'])
            if pair in pairs:
                raise ValueError('rattachement de jalon dupliqué')
            pairs.add(pair)
            links[pair] = row['active']
        file_numbers, latest, delivery_ids = {}, {}, set()
        for row in context['files'].values():
            if row['deliverable_id'] not in plans:
                raise ValueError('version sans plan de livrable')
            value = manifest.check_row(row)
            _text(row['path'], 32768, minimum=1)
            _date(row['created_at'])
            _pointer(context, 'type_versions', value['type_version_id'])
            _pointer(context, 'deliveries', row['source_delivery_id'])
            if row['source_delivery_id'] and context['deliveries'][row['source_delivery_id']]['sha256'] != row['sha256']:
                raise ValueError('liaison CDC avec une empreinte différente')
            if row['source_delivery_id']:
                if row['source_delivery_id'] in delivery_ids:
                    raise ValueError('livraison CDC reliée plusieurs fois')
                delivery_ids.add(row['source_delivery_id'])
            numbers = file_numbers.setdefault(row['deliverable_id'], set())
            if row['number'] in numbers:
                raise ValueError('numéro de fichier dupliqué')
            numbers.add(row['number'])
            if row['deliverable_id'] not in latest or latest[row['deliverable_id']]['number'] < row['number']:
                latest[row['deliverable_id']] = row
            for check in value['checklist']:
                _check(context, check, row['deliverable_id'])
                if check['completed_version_id'] and context['files'][check['completed_version_id']]['number'] >= row['number']:
                    raise ValueError('visa capturé sur une version future')
        for numbers in file_numbers.values():
            if max(numbers) != len(numbers):
                raise ValueError('historique de fichiers incomplet')
        completion, metadata_ids = set(), set()
        for row in tables.get('project_deliverable_version_metadata', []):
            _pointer(context, 'files', row['version_id'], required=True)
            if row['version_id'] in metadata_ids:
                raise ValueError('métadonnées de version dupliquées')
            metadata_ids.add(row['version_id'])
            _text(row['reference'], 120, minimum=1)
            _text(row['comment'], 20000)
            _text(row['storage_path'], 32768)
        if metadata_ids != set(context['files']):
            raise ValueError('métadonnées de fichier absentes')
        for row in context['checks'].values():
            owner = row['deliverable_id']
            if owner not in plans:
                raise ValueError('checklist sans plan')
            check = {key: row[key] for key in manifest.CHECK_FIELDS}
            _check(context, check, owner)
            pair = (owner, row['code'], row['scope_key'])
            if pair in completion:
                raise ValueError('code/scope de checklist dupliqué')
            completion.add(pair)
            if row['active'] and row['milestone_id'] and not links.get((owner, row['milestone_id'])):
                raise ValueError('checklist active sur un jalon non rattaché')
        for owner, row in plans.items():
            if row['document_status'] == 'validated':
                current = latest.get(owner)
                if not current or not row['verifier_id'] or not row['active']:
                    raise ValueError('livrable validé sans version/vérificateur/activité')
                if any(check['deliverable_id'] == owner and check['active'] and check['is_gate'] and (
                        not check['completed'] or check['completed_version_id'] != current['id'] or not check['proof'].strip())
                       for check in context['checks'].values()):
                    raise ValueError('livrable validé avec un gate non visé')
        states = tables.get('project_planning_states', [])
        needs_state = any(tables.get(name) for name in PROJECT_TABLES) or tables.get('project_planning_changes')
        if len(states) > 1 or needs_state and len(states) != 1:
            raise ValueError('un état de planning partagé est requis')
        state_revision = states[0]['revision'] if states else 0
        _integer(state_revision)
        timeline = {}
        for event in tables.get('project_planning_changes', []):
            _integer(event['revision'], minimum=1)
            _text(event['actor_id'], 120, minimum=1)
            _date(event['created_at'])
            if event['revision'] in timeline or event['revision'] > state_revision:
                raise ValueError('révision partagée dupliquée ou future')
            timeline[event['revision']] = event
        global_revisions = set()
        for event in section['project_reference_changes']:
            _integer(event['revision'], minimum=1)
            _text(event['actor_id'], 120, minimum=1)
            _date(event['created_at'])
            key = (event['entity_kind'], event['entity_id'], event['revision'])
            if key in global_revisions:
                raise ValueError('révision globale d’historique dupliquée')
            global_revisions.add(key)
            _global_event(context, event)
        event_ids, events_by_revision, events_by_owner = set(), {}, {}
        for event in tables.get('project_deliverable_events', []):
            _integer(event['revision'], minimum=1)
            _text(event['actor_id'], 120, minimum=1)
            _date(event['created_at'])
            counterpart = timeline.get(event['revision'])
            if (event['deliverable_id'] not in plans or event['id'] in event_ids or event['revision'] > state_revision or not counterpart
                    or counterpart['actor_id'] != event['actor_id'] or counterpart['action'] not in {event['action'], 'deliverable_selection_applied'}):
                raise ValueError('événement sans révision/acteur partagé ou dupliqué')
            event_ids.add(event['id'])
            events_by_revision.setdefault(event['revision'], []).append(event)
            events_by_owner.setdefault(event['deliverable_id'], []).append(event)
            validate_event(context, event)
        for event in timeline.values():
            if event['action'] in ACTIONS:
                validate_event(context, event, planning=True)
                counterparts = events_by_revision.get(event['revision'], [])
                if event['action'] == 'deliverable_selection_applied':
                    operations = event['value']['operations']
                    if len(counterparts) != len(operations) or {row['deliverable_id'] for row in counterparts} != {
                            row['deliverable_id'] for row in operations}:
                        raise ValueError('sélection sans ses événements détaillés')
                    by_owner = {row['deliverable_id']: row for row in counterparts}
                    for operation in operations:
                        detailed = by_owner[operation['deliverable_id']]
                        expected = 'deliverable_created' if operation['operation'] == 'create' else 'deliverable_selection_changed'
                        if detailed['action'] != expected:
                            raise ValueError('opération différente de son événement détaillé')
                        if expected == 'deliverable_selection_changed':
                            active = operation['operation'] != 'deactivate'
                            if detailed['value']['active'] != active or operation['operation'] == 'adopt' and (
                                    detailed['previous']['type_version_id'] is not None or
                                    detailed['value']['type_version_id'] != operation['version_id']):
                                raise ValueError('adoption/activation différente de sa sélection')
                else:
                    if len(counterparts) != 1 or any(event[field] != {
                            'deliverable_id': counterparts[0]['deliverable_id'], **counterparts[0][field]}
                            for field in ('previous', 'value')):
                        raise ValueError('historique partagé différent de son événement de livrable')
        published = set()
        for owner, plan in plans.items():
            status, current_file, current_number = 'draft', None, 0
            ordered_events = sorted(events_by_owner.get(owner, []), key=lambda row: row['revision'])
            _check_history(context, owner, ordered_events)
            for event in ordered_events:
                if event['action'] in {'deliverable_status_changed', 'deliverable_version_published'}:
                    if event['previous']['document_status'] != status:
                        raise ValueError('chaîne d’états de livrable incohérente')
                    if event['action'] == 'deliverable_version_published':
                        if event['value']['number'] != current_number + 1 or event['value']['version_id'] in published:
                            raise ValueError('publications hors séquence ou dupliquées')
                        current_file, current_number = event['value']['version_id'], event['value']['number']
                        published.add(current_file)
                    elif event['value']['version_id'] != current_file:
                        raise ValueError('transition portant sur une ancienne version')
                    status = event['value']['document_status']
                elif event['action'] == 'deliverable_check_changed' and event['value']['is_gate'] and event['value']['completed']:
                    if event['value']['completed_version_id'] != current_file:
                        raise ValueError('visa historique portant sur une ancienne version')
            if status != plan['document_status']:
                raise ValueError('état courant sans transition historique correspondante')
        if published != set(context['files']):
            raise ValueError('version de fichier sans publication historique')
        # Old event payloads did not record inherited status. Only replay and
        # compare that field from the first explicit legacy capture onward.
        for owner, events in events_by_owner.items():
            recorded = None
            for event in sorted(events, key=lambda value: value['revision']):
                previous, current = event['previous'], event['value']
                if 'legacy_status' in current:
                    if current['legacy_status'] not in {'todo', 'in_progress', 'done', 'cancelled'}:
                        raise ValueError('statut historique invalide')
                    if recorded is not None and previous.get('legacy_status') != recorded:
                        raise ValueError('chaîne de statuts historiques incohérente')
                    recorded = current['legacy_status']
            if recorded is not None and context['deliverables'][owner]['status'] != recorded:
                raise ValueError('statut historique sans son événement correspondant')
        return context
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        invalid(str(exc))


def _remap_values(value, mapping):
    result = deepcopy(value)
    for key in {'id', 'version_id', 'type_id', 'type_version_id', 'deliverable_id', 'project_id', 'typology_id',
                'milestone_id', 'completed_version_id', 'source_delivery_id', *ROLES}:
        if result.get(key) is not None:
            result[key] = mapping[result[key]]
    for key in ('milestone_ids', 'type_ids', 'type_version_ids'):
        if key in result:
            result[key] = [mapping[identity] for identity in result[key]]
    if 'milestone_mapping' in result:
        result['milestone_mapping'] = {code: mapping[identity] for code, identity in result['milestone_mapping'].items()}
    if 'existing_mapping' in result:
        result['existing_mapping'] = {mapping[identity]: mapping[target] for identity, target in result['existing_mapping'].items()}
    for key in ('inputs', 'published_version', 'deliverable_selection'):
        if key in result:
            result[key] = _remap_values(result[key], mapping)
    if 'operations' in result:
        result['operations'] = [_remap_values(operation, mapping) for operation in result['operations']]
    return result


def remap_row(raw, table, mapping, *, manifest_hashes=None):
    """Caller validates the contract first; text, codes, actors and origin stay verbatim."""
    result = deepcopy(raw)
    for column in table.c:
        if column.primary_key or column.foreign_keys:
            if result.get(column.name) is not None:
                result[column.name] = mapping[result[column.name]]
    if table.name == 'project_deliverable_file_versions':
        result['manifest'], result['manifest_sha256'] = manifest.remap(raw['manifest'], raw['manifest_sha256'],
            mapping, version_id=raw['id'])
    elif table.name in {'project_deliverable_events', 'project_reference_changes', 'project_planning_changes'}:
        if table.name == 'project_reference_changes':
            result['entity_id'] = mapping[raw['entity_id']]
        for field in ('previous', 'value'):
            result[field] = _remap_values(raw[field], mapping)
        if raw.get('action') == 'deliverable_version_published' and manifest_hashes is not None:
            result['value']['manifest_sha256'] = manifest_hashes[raw['value']['version_id']]
    return result


def remap_archive(metadata, tables, section, mapping):
    """Prepare all L3 rows and hash-bound events before inserting immutable rows."""
    hashes = {row['id']: manifest.remap(row['manifest'], row['manifest_sha256'], mapping, version_id=row['id'])[1]
              for row in tables.get('project_deliverable_file_versions', [])}
    project = {name: [remap_row(row, metadata.tables[name], mapping, manifest_hashes=hashes) for row in rows]
               for name, rows in tables.items() if name in PROJECT_TABLES}
    globals_ = {name: [remap_row(row, metadata.tables[name], mapping) for row in rows] for name, rows in section.items()}
    events = [remap_row(row, metadata.tables['project_planning_changes'], mapping, manifest_hashes=hashes)
              for row in tables.get('project_planning_changes', []) if row['action'] in ACTIONS]
    return project, globals_, events
