"""Selective v4 planning closure, validation and typed UUID remapping."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import math
import re

from fastapi import HTTPException
from sqlalchemy import select

from ..project_planning_models import PLANNING_TABLES
from .project_identity import _normalized
from .project_planning_rules import (
    MILESTONE_FIELDS, TASK_FIELDS, TemplateDefinition, aggregate_task_rows, capture_snapshot, validate_project_values,
)

PROJECT_TABLES = frozenset(table.name for table in PLANNING_TABLES if 'project_id' in table.c)
REFERENCE_TABLES = frozenset({'project_planning_templates', 'project_planning_template_versions'})
ID_FIELDS = frozenset({'id', 'project_id', 'parent_id', 'milestone_id', 'responsible_id', 'template_id'})
EVIDENCE_ERP = frozenset({'candidate_id', 'meeting_id', 'page_id', 'template_version_id'})
EVIDENCE_BRAIN = frozenset({'artifact_id'})


def invalid(message):
    raise HTTPException(400, message)


def _hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _integer(value, *, minimum=0):
    if type(value) is not int or value < minimum:
        invalid("Entier/révision de planning invalide")


def _id(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 36:
        invalid("Identifiant de planning invalide")
    return value


def _actor(row):
    if not isinstance(row.get('actor_id'), str) or not 1 <= len(row['actor_id']) <= 120:
        invalid("Acteur de planning invalide")


def decode_baseline(row):
    try:
        value = row['payload']
        if not isinstance(value, str) or _hash(value) != row['sha256']:
            invalid("Empreinte de référence de planning incohérente")
        snapshot = json.loads(value)
        if (not isinstance(snapshot, dict) or snapshot.get('format') != 'agent-project-planning'
                or type(snapshot.get('version')) is not int or snapshot['version'] not in (1, 2)
                or snapshot.get('project_id') != row.get('project_id')):
            invalid("Référence de planning étrangère ou format invalide")
        fields = {'format', 'version', 'project_id', 'milestones', 'tasks'}
        if snapshot['version'] == 2:
            fields.add('project')
            validate_project_values(snapshot.get('project'))
        if set(snapshot) != fields:
            invalid("Champs étrangers dans la référence de planning")
        return snapshot
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(400, "Référence de planning invalide") from exc


def _snapshot_rows(value):
    if not isinstance(value, dict):
        invalid("Instantané d'historique de planning invalide")
    for kind, single in (('tasks', 'task'), ('milestones', 'milestone')):
        rows = value.get(kind, [])
        if not isinstance(rows, list) or len(rows) > 100000 or any(not isinstance(row, dict) for row in rows):
            invalid("Liste d'instantané de planning invalide")
        if single in value:
            if not isinstance(value[single], dict):
                invalid("Objet d'instantané de planning invalide")
            rows = [*rows, value[single]]
        yield kind, rows


def _evidence_versions(evidence):
    if not isinstance(evidence, dict):
        invalid("Preuve de date invalide")
    return {_id(evidence['template_version_id'])} if evidence.get('template_version_id') else set()


def dependencies(tables):
    templates, versions, people = set(), set(), set()

    def collect_task(row):
        for key, bucket in (('template_id', templates), ('responsible_id', people)):
            if row.get(key):
                bucket.add(_id(row[key]))

    def collect_milestone(row):
        sources = row.get('date_sources', {})
        if not isinstance(sources, dict):
            invalid("Provenances de dates invalides")
        for evidence in sources.values():
            versions.update(_evidence_versions(evidence))

    for row in tables.get('project_task_plans', []):
        collect_task(row)
    for row in tables.get('milestones', []):
        collect_milestone(row)
    for name in ('milestone_changes', 'milestone_candidates', 'milestone_inputs'):
        for row in tables.get(name, []):
            versions.update(_evidence_versions(row.get('evidence', {})))
    for row in tables.get('project_planning_states', []):
        if row.get('active_template_version_id'):
            versions.add(_id(row['active_template_version_id']))
    snapshots = [decode_baseline(row) for row in tables.get('project_planning_baselines', [])]
    for event in tables.get('project_planning_changes', []):
        snapshots.extend([event.get('previous'), event.get('value')])
        if isinstance(event.get('value'), dict) and event['value'].get('version_id'):
            versions.add(_id(event['value']['version_id']))
    for value in snapshots:
        for kind, rows in _snapshot_rows(value):
            for row in rows:
                (collect_task if kind == 'tasks' else collect_milestone)(row)
    return templates, versions, people


def has_planning(tables):
    if any(tables.get(name) for name in PROJECT_TABLES):
        return True
    templates, versions, people = dependencies(tables)
    return bool(templates or versions or people)


def require_schema(db):
    from .project_planning_migration import install_planning_schema

    def refuse():
        raise HTTPException(409, "Activer la migration de planning avant l'import/export v4")
    try:
        install_planning_schema(db.get_bind(), backup=refuse)
    except ValueError as exc:
        raise HTTPException(409, "Schéma de planning incomplet ou incompatible") from exc


def export_templates(db, metadata, tables):
    require_schema(db)
    template_ids, version_ids, people = dependencies(tables)
    version_table = metadata.tables['project_planning_template_versions']
    template_ids.update(db.execute(select(version_table.c.template_id).where(version_table.c.id.in_(version_ids))).scalars())
    template_table = metadata.tables['project_planning_templates']
    result = {template_table.name: [dict(row) for row in db.execute(select(template_table).where(
        template_table.c.id.in_(template_ids)).order_by(template_table.c.id)).mappings()],
        version_table.name: [dict(row) for row in db.execute(select(version_table).where(
            version_table.c.template_id.in_(template_ids)).order_by(version_table.c.template_id, version_table.c.number)).mappings()]}
    if {row['id'] for row in result[template_table.name]} != template_ids or not version_ids.issubset(
            {row['id'] for row in result[version_table.name]}):
        raise HTTPException(409, "Dépendance historique de modèle absente : export refusé")
    for rows in result.values():
        for row in rows:
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
    return result


def identity_dependencies(tables, section):
    _, _, people = dependencies(tables)
    references = {_id(row['typology_id']): 'typology' for row in section['project_planning_templates'] if row.get('typology_id')}
    return references, people


def validate_section(metadata, section):
    if not isinstance(section, dict) or set(section) != REFERENCE_TABLES:
        invalid("Une archive v4 exige ses modèles et versions utilisés")
    ids = set()
    templates, keys = {}, set()
    for name, rows in section.items():
        if not isinstance(rows, list) or len(rows) > 100000:
            invalid("Liste de modèles d'archive invalide")
        for row in rows:
            if not isinstance(row, dict) or set(row) - set(metadata.tables[name].c.keys()):
                invalid("Colonnes de modèle d'archive invalides")
            identity = _id(row.get('id'))
            if identity in ids:
                invalid("Identifiant de modèle/version dupliqué")
            ids.add(identity)
    for row in section['project_planning_templates']:
        if (not isinstance(row.get('code'), str) or not 1 <= len(row['code']) <= 64
                or not isinstance(row.get('name'), str) or not 1 <= len(row['name']) <= 255
                or row['code'].strip() != row['code'] or row['name'].strip() != row['name']
                or row.get('normalized_code') != _normalized(row['code'])
                or row.get('search_text') != _normalized(row['code'] + ' ' + row['name'])
                or type(row.get('active')) is not bool):
            invalid("Fiche de modèle non canonique")
        _integer(row.get('revision'))
        if row['normalized_code'] in keys:
            invalid("Code de modèle dupliqué")
        keys.add(row['normalized_code'])
        templates[row['id']] = row
    numbers, task_keys = set(), {}
    for row in section['project_planning_template_versions']:
        _integer(row.get('number'), minimum=1)
        _actor(row)
        if row.get('template_id') not in templates or (row['template_id'], row['number']) in numbers:
            invalid("Version dupliquée ou modèle absent")
        numbers.add((row['template_id'], row['number']))
        try:
            datetime.fromisoformat(row['created_at'])
            if not isinstance(row.get('definition'), str) or _hash(row['definition']) != row.get('sha256'):
                invalid("Empreinte de modèle incohérente")
            definition = TemplateDefinition.model_validate_json(row['definition'])
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(400, "Version de modèle invalide") from exc
        task_keys.setdefault(row['template_id'], set()).update(task.key for task in definition.tasks)
    return task_keys


def _validate_task(row, task_ids, milestone_ids, people_ids, task_keys):
    if row.get('id') not in task_ids:
        invalid("Tâche d'instantané absente ou étrangère")
    for field, allowed in (('parent_id', task_ids), ('milestone_id', milestone_ids), ('responsible_id', people_ids)):
        if row.get(field) is not None and row[field] not in allowed:
            invalid("Relation de tâche absente ou étrangère")
    template_id, key = row.get('template_id'), row.get('template_key')
    if (template_id is None) != (key is None) or (template_id is not None and key not in task_keys.get(template_id, set())):
        invalid("Provenance de tâche absente du modèle")
    if 'planned_hours' in row and (type(row['planned_hours']) not in (int, float)
            or not math.isfinite(row['planned_hours']) or not 0 <= row['planned_hours'] <= 1000000):
        invalid("Charge de tâche invalide")
    for field in ('active', 'design', 'manufacturing'):
        if field in row and type(row[field]) is not bool:
            invalid("Indicateur de tâche invalide")
    if row.get('priority', 'normal') not in {'low', 'normal', 'high', 'urgent'}:
        invalid("Priorité de tâche invalide")
    if 'status' in row and row['status'] not in {'todo', 'assigned', 'in_progress', 'blocked', 'done', 'cancelled'}:
        invalid("État de tâche invalide")
    if row.get('status') == 'assigned' and 'responsible_id' in row and not row['responsible_id']:
        invalid("Tâche affectée sans responsable")
    for field, limit in (('title', 255), ('comment', 20000)):
        if field in row and (not isinstance(row[field], str) or len(row[field]) > limit):
            invalid("Texte de tâche invalide")
    for field in ('start_date', 'end_date', 'due_date'):
        if field in row and (not isinstance(row[field], str) or len(row[field]) > 32):
            invalid("Date de tâche invalide")


def _validate_milestone(row, milestone_ids, version_ids):
    if row.get('id') not in milestone_ids:
        invalid("Jalon d'instantané absent ou étranger")
    if row.get('code') is not None and (not isinstance(row['code'], str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', row['code'])):
        invalid("Code de jalon invalide")
    if row.get('workflow_status', 'pending') not in {'pending', 'open', 'validated', 'blocked', 'skipped'}:
        invalid("État de jalon invalide")
    if 'active' in row and type(row['active']) is not bool:
        invalid("Activation de jalon invalide")
    if row.get('order') is not None:
        _integer(row['order'])
    sources = row.get('date_sources', {})
    if not isinstance(sources, dict):
        invalid("Provenances de jalon invalides")
    for value in sources.values():
        if not _evidence_versions(value).issubset(version_ids):
            invalid("Version de preuve absente")


def validate_planning(metadata, tables, section, references):
    task_keys = validate_section(metadata, section)
    project_id = tables['projects'][0]['id']
    states = tables.get('project_planning_states', [])
    if len(states) != 1:
        invalid("Un seul état de planning est requis en v4")
    state = states[0]
    _integer(state.get('revision'))
    calendar = state.get('excluded_dates')
    from pydantic import TypeAdapter
    from ..schemas import IsoDate
    try:
        if not isinstance(calendar, list) or len(calendar) > 3660 or any(not value for value in calendar):
            invalid("Calendrier invalide")
        for value in calendar:
            TypeAdapter(IsoDate).validate_python(value)
        if len(set(calendar)) != len(calendar):
            invalid("Calendrier dupliqué")
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Calendrier invalide") from exc
    template_ids = {row['id'] for row in section['project_planning_templates']}
    version_ids = {row['id'] for row in section['project_planning_template_versions']}
    people_ids = {row['id'] for row in references['project_people']}
    task_ids = {row['id'] for row in tables.get('tasks', [])}
    milestone_ids = {row['id'] for row in tables.get('milestones', [])}
    if state.get('active_template_version_id') is not None and state['active_template_version_id'] not in version_ids:
        invalid("Modèle actif absent")
    required_templates, required_versions, _ = dependencies(tables)
    versions_by_id = {row['id']: row for row in section['project_planning_template_versions']}
    if not required_versions.issubset(version_ids):
        invalid("Version historique absente")
    required_templates.update(versions_by_id[key]['template_id'] for key in required_versions)
    if template_ids != required_templates:
        invalid("Modèle absent ou étranger au projet : catalogue global interdit")
    if any(row.get('typology_id') and row['typology_id'] not in {r['id'] for r in references['project_references']}
           for row in section['project_planning_templates']):
        invalid("Typologie du modèle absente")
    current_tasks = {row['id']: {**row, 'parent_id': None, 'milestone_id': None, 'responsible_id': None,
        'template_id': None, 'template_key': None, 'planned_hours': 0, 'active': True,
        'start_date': '', 'end_date': row.get('due_date') or ''} for row in tables.get('tasks', [])}
    for row in tables.get('project_task_plans', []):
        value = {**current_tasks.get(row['task_id'], {}), **row, 'id': row['task_id'], 'parent_id': row.get('parent_task_id')}
        _validate_task(value, task_ids, milestone_ids, people_ids, task_keys)
        current_tasks[row['task_id']] = value
    try:
        aggregated = aggregate_task_rows(project_id, list(current_tasks.values()))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    for row in aggregated:
        original = current_tasks[row['id']]
        if any(row.get(key) != original.get(key) for key in ('planned_hours', 'start_date', 'end_date')):
            invalid("Agrégat de tâches incohérent")
    current_milestones = {row['id']: {**row, 'code': None, 'order': 0, 'active': True} for row in tables.get('milestones', [])}
    for row in tables.get('project_milestone_plans', []):
        value = {**current_milestones.get(row['milestone_id'], {}), **row, 'id': row['milestone_id'], 'order': row.get('position')}
        _validate_milestone(value, milestone_ids, version_ids)
        if not isinstance(row.get('comment'), str) or len(row['comment']) > 20000:
            invalid("Commentaire de jalon invalide")
        current_milestones[row['milestone_id']] = value
    codes = [row['code'] for row in current_milestones.values() if row['code'] is not None]
    if len(codes) != len(set(codes)) or sum(row['active'] and row['code'] is not None and row.get('workflow_status') == 'open'
                                         for row in current_milestones.values()) > 1:
        invalid("Codes dupliqués ou plusieurs jalons ouverts")
    baselines = {row['id'] for row in tables.get('project_planning_baselines', [])}
    for row in tables.get('project_planning_baselines', []):
        _integer(row.get('planning_revision'))
        _actor(row)
        if row['planning_revision'] > state['revision'] or row.get('kind') not in {'initial', 'contractual', 'review', 'amendment'}:
            invalid("Référence de planning incohérente")
        _validate_snapshots(decode_baseline(row), project_id, task_ids, milestone_ids, people_ids, task_keys, version_ids, complete=True)
    revisions = set()
    baselines_by_id = {row['id']: row for row in tables.get('project_planning_baselines', [])}
    pointers = {key: {row['id'] for row in tables.get(name, [])} for key, name in (
        ('candidate_id', 'milestone_candidates'), ('meeting_id', 'meetings'), ('action_id', 'meeting_actions'))}
    for event in tables.get('project_planning_changes', []):
        _integer(event.get('revision'), minimum=1)
        _actor(event)
        if event['revision'] > state['revision'] or event['revision'] in revisions:
            invalid("Révision d'historique dupliquée ou plus récente que le planning")
        revisions.add(event['revision'])
        if event.get('action') not in {'task_created', 'task_changed', 'milestone_created', 'milestone_changed',
                                     'candidate_accepted', 'meeting_action_converted', 'baseline_created',
                                     'baseline_metadata_changed', 'template_applied', 'project_changed'}:
            invalid("Action d'historique de planning inconnue")
        for field in ('previous', 'value'):
            _validate_snapshots(event[field], project_id, task_ids, milestone_ids, people_ids, task_keys, version_ids)
            for key, allowed in pointers.items():
                if event[field].get(key) is not None and event[field][key] not in allowed:
                    invalid("Objet d'historique absent ou étranger")
            if event[field].get('baseline_id') is not None and event[field]['baseline_id'] not in baselines:
                invalid("Référence d'historique absente")
        if event['value'].get('baseline_id') is not None and event['value']['baseline_id'] not in baselines:
            invalid("Référence d'historique absente")
        if event['action'] == 'baseline_created':
            baseline = baselines_by_id.get(event['value'].get('baseline_id'))
            if not baseline or any(event['value'].get(key) != baseline[key] for key in ('kind', 'sha256')):
                invalid("Empreinte d'historique de référence incohérente")
    metadata = {key: {'baseline_id': key, 'label': row['label'], 'comment': '', 'active': True}
                for key, row in baselines_by_id.items()}
    for event in sorted(tables.get('project_planning_changes', []), key=lambda row: row['revision']):
        if event['action'] != 'baseline_metadata_changed':
            continue
        identity = event['value'].get('baseline_id')
        if identity not in baselines_by_id or event['revision'] <= baselines_by_id[identity]['planning_revision']:
            invalid("Métadonnées antérieures ou étrangères à la référence")
        for field in ('previous', 'value'):
            value = event[field]
            if set(value) != {'baseline_id', 'label', 'comment', 'active'} or value['baseline_id'] != identity:
                invalid("Métadonnées de référence invalides")
            if not isinstance(value['label'], str) or not 1 <= len(value['label'].strip()) <= 255:
                invalid("Nom de référence invalide")
            if not isinstance(value['comment'], str) or len(value['comment']) > 20000 or type(value['active']) is not bool:
                invalid("Commentaire ou état de référence invalide")
        if event['previous'] != metadata[identity]:
            invalid("Chaîne des métadonnées de référence incohérente")
        metadata[identity] = event['value']


def _validate_snapshots(value, project_id, task_ids, milestone_ids, people_ids, task_keys, version_ids, *, complete=False):
    if not isinstance(value, dict):
        invalid("Instantané d'historique de planning invalide")
    if value.get('project_id', project_id) != project_id:
        invalid("Instantané appartenant à un autre projet")
    if 'project' in value:
        try:
            validate_project_values(value['project'])
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    collected = {}
    for kind, rows in _snapshot_rows(value):
        fields = TASK_FIELDS if kind == 'tasks' else MILESTONE_FIELDS
        if complete and any(set(row) - set(fields) for row in rows):
            invalid("Champs étrangers dans l'instantané figé")
        ids = [row.get('id') for row in rows]
        if any(not isinstance(identity, str) for identity in ids) or len(ids) != len(set(ids)):
            invalid("Identifiant d'instantané absent ou dupliqué")
        for row in rows:
            if row.get('project_id', project_id) != project_id:
                invalid("Objet d'instantané étranger au projet")
            if kind == 'tasks':
                _validate_task(row, task_ids, milestone_ids, people_ids, task_keys)
            else:
                _validate_milestone(row, milestone_ids, version_ids)
        collected[kind] = rows
    if complete or 'tasks' in value:
        try:
            aggregate_task_rows(project_id, collected['tasks'])
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    if value.get('version_id') is not None and value['version_id'] not in version_ids:
        invalid("Version d'historique absente")
    inputs = value.get('inputs', {})
    if not isinstance(inputs, dict) or not isinstance(inputs.get('milestone_mapping', {}), dict):
        invalid("Correspondances historiques invalides")
    if any(identity not in milestone_ids for identity in inputs.get('milestone_mapping', {}).values()):
        invalid("Correspondance historique étrangère")
    if complete:
        try:
            capture_snapshot(project_id, collected['milestones'], collected['tasks'], project=value.get('project'))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc


def reconcile_templates(db, metadata, section, mapping):
    require_schema(db)
    pending = {name: [] for name in REFERENCE_TABLES}
    for name in ('project_planning_templates', 'project_planning_template_versions'):
        table = metadata.tables[name]
        for raw in section[name]:
            original = db.execute(select(table).where(table.c.id == raw['id'])).mappings().first()
            if name == 'project_planning_templates':
                business = ('code', 'name', 'typology_id', 'active')
                candidates = db.execute(select(table).where(table.c.normalized_code == raw['normalized_code'])).mappings().all()
            else:
                business = ('template_id', 'number', 'definition', 'sha256', 'actor_id', 'created_at')
                candidates = db.execute(select(table).where(table.c.template_id == mapping[raw['template_id']],
                                                           table.c.number == raw['number'])).mappings().all()
            by_id = {row['id']: row for row in candidates}
            if original:
                by_id[original['id']] = original
            wanted = {key: mapping.get(raw[key], raw[key]) if key in {'typology_id', 'template_id'} else raw[key] for key in business}
            def comparable(row, key):
                value = row[key]
                return value.isoformat() if isinstance(value, datetime) else value
            if len(by_id) > 1 or any(any(comparable(row, key) != value for key, value in wanted.items()) for row in by_id.values()):
                raise HTTPException(409, {'message': 'Modèle/version différent : aucune donnée existante modifiée',
                                          'table': name, 'archive_id': raw['id']})
            if by_id:
                mapping[raw['id']] = next(iter(by_id))
            else:
                pending[name].append(raw)
    return pending


def remap_evidence(value, mapping, brain_mapping):
    result = deepcopy(value)
    for key in EVIDENCE_ERP:
        if isinstance(result.get(key), str):
            result[key] = mapping.get(result[key], result[key])
    for key in EVIDENCE_BRAIN:
        if isinstance(result.get(key), str):
            result[key] = brain_mapping.get(result[key], result[key])
    if isinstance(result.get('source_id'), str):
        target = brain_mapping if result.get('kind') in {'brain', 'attachment'} else mapping
        result['source_id'] = target.get(result['source_id'], result['source_id'])
    return result


def evidence_rows(tables):
    for row in tables.get('milestones', []):
        yield from (row.get('date_sources') or {}).values()
    for name in ('milestone_changes', 'milestone_candidates', 'milestone_inputs'):
        for row in tables.get(name, []):
            yield row.get('evidence') or {}
    snapshots = [decode_baseline(row) for row in tables.get('project_planning_baselines', [])]
    for event in tables.get('project_planning_changes', []):
        snapshots.extend([event['previous'], event['value']])
    for value in snapshots:
        for kind, rows in _snapshot_rows(value):
            if kind == 'milestones':
                for row in rows:
                    yield from (row.get('date_sources') or {}).values()


def validate_evidence(tables, section, brain):
    """Typed proof pointers must resolve inside the exported project closure."""
    erp = {key: {row['id'] for row in tables.get(name, [])} for key, name in (
        ('candidate_id', 'milestone_candidates'), ('meeting_id', 'meetings'), ('page_id', 'cdc_source_pages'))}
    erp['template_version_id'] = {row['id'] for row in section['project_planning_template_versions']}
    source_ids = {row['id'] for row in (brain or {}).get('sources', [])}
    artifacts = {row['id']: row for row in (brain or {}).get('source_artifacts', [])}
    for proof in evidence_rows(tables):
        if not isinstance(proof, dict):
            invalid("Preuve de planning invalide")
        for key, allowed in erp.items():
            if proof.get(key) is not None and proof[key] not in allowed:
                invalid("Preuve de planning absente ou étrangère au projet")
        if proof.get('kind') in {'brain', 'attachment'} and proof.get('source_id') not in source_ids:
            invalid("Source Brain de preuve absente ou étrangère")
        if proof.get('artifact_id') is not None and (proof['artifact_id'] not in artifacts
                or artifacts[proof['artifact_id']]['source_id'] != proof.get('source_id')):
            invalid("Artefact de preuve absent ou associé à une autre source")


def validate_reused_brain(session, metadata, tables, brain):
    """Reusing a canonical Brain must not silently relink a missing/changed proof."""
    sources = {proof['source_id'] for proof in evidence_rows(tables)
               if proof.get('kind') in {'brain', 'attachment'}}
    sources.update(row['source_id'] for row in brain.get('meeting_recordings', []))
    artifacts = {proof['artifact_id'] for proof in evidence_rows(tables) if proof.get('artifact_id')}
    for name, identities, fields in (
        ('sources', sources, ('project_id', 'sha256')),
        ('source_artifacts', artifacts, ('source_id', 'content_text')),
    ):
        archived = {row['id']: row for row in brain.get(name, [])}
        table = metadata.tables[name]
        existing = {row['id']: row for row in session.execute(select(table).where(table.c.id.in_(identities))).mappings()}
        if set(existing) != identities or any(any(existing[key][field] != archived[key][field] for field in fields)
                                              for key in identities):
            raise HTTPException(409, "Source/preuve Brain canonique absente ou différente : restauration refusée")


def remap_snapshot(value, mapping, brain_mapping):
    result = deepcopy(value)
    for key in ('project_id', 'version_id', 'baseline_id', 'candidate_id', 'meeting_id', 'action_id'):
        if isinstance(result.get(key), str):
            result[key] = mapping.get(result[key], result[key])
    for kind, rows in _snapshot_rows(value):
        def one(row):
            item = deepcopy(row)
            for key in ID_FIELDS:
                if isinstance(item.get(key), str):
                    item[key] = mapping.get(item[key], item[key])
            if kind == 'milestones' and 'date_sources' in item:
                item['date_sources'] = {key: remap_evidence(proof, mapping, brain_mapping) for key, proof in item['date_sources'].items()}
            return item
        if kind in value:
            result[kind] = [one(row) for row in value[kind]]
        single = 'task' if kind == 'tasks' else 'milestone'
        if single in value:
            result[single] = one(value[single])
    if isinstance(result.get('inputs'), dict) and 'milestone_mapping' in result['inputs']:
        result['inputs']['milestone_mapping'] = {key: mapping.get(identity, identity)
                                               for key, identity in result['inputs']['milestone_mapping'].items()}
    return result


def remap_row(raw, table, mapping, brain_mapping, fallback):
    result = deepcopy(raw)
    for column in table.c:
        logical_fields = {'meeting_actions': {'task_id'}, 'time_entries': {'task_id'},
                          'cdc_items': {'source_id'}, 'cdc_evidence_anchors': {'source_id', 'source_page_id'}}
        if column.primary_key or column.foreign_keys or column.name in logical_fields.get(table.name, set()):
            value = result.get(column.name)
            if isinstance(value, str):
                result[column.name] = mapping.get(value, value)
    if table.name == 'brain_links':
        result['brain_project_id'] = brain_mapping.get(raw['brain_project_id'], raw['brain_project_id'])
    if table.name == 'project_planning_baselines':
        snapshot = remap_snapshot(decode_baseline(raw), mapping, brain_mapping)
        frozen = capture_snapshot(result['project_id'], snapshot['milestones'], snapshot['tasks'], project=snapshot.get('project'))
        result['payload'], result['sha256'] = frozen.payload, frozen.sha256
    elif table.name == 'project_planning_changes':
        for field in ('previous', 'value'):
            result[field] = remap_snapshot(raw[field], mapping, brain_mapping)
        if raw['action'] == 'baseline_created':
            # Hash is supplied by the importer after all baselines are remapped.
            result['value']['sha256'] = mapping.get('baseline-hash:' + raw['value']['baseline_id'], raw['value']['sha256'])
    elif table.name in {'milestones', 'milestone_changes', 'milestone_candidates', 'milestone_inputs'}:
        if 'date_sources' in raw:
            result['date_sources'] = {key: remap_evidence(value, mapping, brain_mapping) for key, value in raw['date_sources'].items()}
        if 'evidence' in raw:
            result['evidence'] = remap_evidence(raw['evidence'], mapping, brain_mapping)
    elif table.name not in PROJECT_TABLES | REFERENCE_TABLES | {'tasks'}:
        from sqlalchemy import JSON
        for column in table.c:
            if isinstance(column.type, JSON) and column.name in raw:
                result[column.name] = fallback(raw[column.name], mapping)
    return result
