"""V5 domain contract on fictional stores; transport activation remains separate."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import DateTime, create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db_support import backup_sqlite, configure_sqlite
from app.services.backup import create_backup, restore_backup
from app.services import deliverable_manifest as manifest
from backend.app.db import Base
from backend.app.models import DeliveryVersion
from backend.app.project_deliverable_models import DeliverablePlan
from backend.app.project_deliverable_schemas import (
    ChecklistPatch, DeliverableCreate, DeliverablePatch, DocumentTransition, FilePublication,
    SelectionApply, SelectionPreview, TypeCreate, TypeDefinition, TypePublish, TypologyTypesPatch,
)
from backend.app.project_identity_schemas import IdentityPatch, PersonCreate, ReferenceCreate
from backend.app.services import deliverable_catalogue as catalogue, project_deliverables as service
from backend.app.services import project_deliverable_archive as contract, project_identity as identity
from backend.app.services import project_identity_archive as identity_archive
from backend.app.services.migration_guard import capture_baseline
from backend.app.services.planning_revision import revision
from backend.app.services.project_deliverable_migration import install_deliverable_schema
from backend.app.services.project_planning_migration import install_planning_schema
from backend.app.services.project_operator import Operator, operator_context
from tests import test_project_deliverables as fixtures
from tests.test_project_deliverables import transaction

store = fixtures.store


def serial(row):
    return {key: value.isoformat() if isinstance(value, datetime) else value for key, value in row.items()}


@pytest.fixture
def envelope(store):
    factory, ids, *_ = store
    project = ids['project']
    with transaction(factory) as db:
        typology = identity.create_reference(db, ReferenceCreate(kind='typology', code='modification', label='Modification'))
        identity.patch_identity(db, project, IdentityPatch(expected_revision=0, typology_id=typology['id']))
        verifier = identity.create_person(db, PersonCreate(first_name='Alice', last_name='Visa', email='visa@example.test'))
        previous = identity.create_person(db, PersonCreate(first_name='Bob', last_name='Historique', email='history@example.test'))
        secret = identity.create_person(db, PersonCreate(first_name='Autre', last_name='Projet', email='secret@example.test'))
        main = service.create_type(db, TypeCreate(code='main', label='Dossier', definition=TypeDefinition(checklist=[
            {'code': 'visa', 'label': 'Visa PDR', 'is_gate': True, 'milestone_code': 'pdr'}])))
        retained = service.create_type(db, TypeCreate(code='retained', label='Manuel typé', definition=TypeDefinition()))
        unused = service.create_type(db, TypeCreate(code='secret', label='Autre projet', definition=TypeDefinition()))
        catalogue.patch_typology_types(db, typology['id'], TypologyTypesPatch(expected_revision=1,
            type_ids=[main['id'], retained['id']]))
        catalogue.patch_typology_types(db, typology['id'], TypologyTypesPatch(expected_revision=2, type_ids=[main['id']]))
        created = service.create_deliverable(db, project, DeliverableCreate(expected_revision=0,
            title=project, type_version_id=main['version_id'], milestone_ids=[ids['milestone']],
            milestone_mapping={'pdr': ids['milestone']}, verifier_id=verifier['id'], responsible_id=previous['id']))
        deliverable = created['id']
        gate = service.read_deliverable(db, project, deliverable)['checklist'][0]['id']
        with operator_context(Operator(project, 'owner')):
            service.patch_deliverable(db, project, deliverable, DeliverablePatch(expected_revision=1, responsible_id=None,
                                                                              comment=main['version_id']))
        service.patch_check(db, project, deliverable, gate, ChecklistPatch(expected_revision=2, label=project))
        v2 = service.publish_type(db, main['id'], TypePublish(expected_revision=1,
            definition=TypeDefinition(checklist=[{'code': 'visa', 'label': 'Visa PDR', 'is_gate': True, 'milestone_code': 'pdr'},
                                               {'code': 'doc', 'label': 'CDR', 'milestone_code': 'cdr'}])))
    first = fixtures.publish(store, deliverable)
    for state in ('to_verify', 'validated', 'to_revise'):
        with transaction(factory) as db:
            if state == 'validated':
                service.patch_check(db, project, deliverable, gate, ChecklistPatch(expected_revision=revision(db, project),
                    completed=True, proof=deliverable, comment=ids['milestone']))
            service.transition(db, project, deliverable, DocumentTransition(expected_revision=revision(db, project),
                status=state, version_id=first['version_id'], comment=project))
    second = fixtures.publish(store, deliverable, name='document-v2.md', content='Version deux')
    with transaction(factory) as db:
        service.patch_check(db, project, deliverable, gate, ChecklistPatch(expected_revision=revision(db, project),
            completed=True, proof=deliverable))
        for state in ('to_verify', 'validated'):
            service.transition(db, project, deliverable, DocumentTransition(expected_revision=revision(db, project),
                status=state, version_id=second['version_id'], comment=first['version_id']))
        path = store[2].parent / 'cdc.md'
        path.write_text('CDC conservé', encoding='utf-8')
        source = DeliveryVersion(project_id=project, version=1, path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        db.add(source)
        db.flush()
        service.publish_file(db, project, ids['legacy'], FilePublication(expected_revision=revision(db, project),
            reference='CDC-001', source_delivery_id=source.id), path=path)
        inputs = SelectionPreview(expected_revision=revision(db, project), type_version_ids=[v2['version_id'], retained['version_id']],
            existing_mapping={retained['id']: ids['legacy']}, typology_id=typology['id'],
            milestone_mapping={'pdr': ids['milestone']}, excluded_milestone_codes=['cdr'], verifier_id=verifier['id'])
        preview = catalogue.preview_selection(db, project, inputs)
        catalogue.apply_selection(db, project, SelectionApply(**inputs.model_dump(), expected_preview_sha256=preview['sha256']))
    tables = {}
    references, section = {}, {}
    used_types = {main['id'], retained['id']}
    with factory() as db:
        for table in Base.metadata.sorted_tables:
            # A v5 envelope contains only its supported domains. Importing
            # dormant metadata must not add document or note placeholders.
            if table.name.startswith(('project_document_', 'project_note')) or table.name == 'project_knowledge_analyses':
                continue
            if table.name == 'projects':
                values = db.execute(select(table).where(table.c.id == project)).mappings()
            elif 'project_id' in table.c:
                values = db.execute(select(table).where(table.c.project_id == project)).mappings()
            else:
                continue
            tables[table.name] = [serial(row) for row in values]
        for name, values in (('project_references', [typology['id']]), ('project_people', [verifier['id'], previous['id']])):
            table = Base.metadata.tables[name]
            references[name] = [serial(row) for row in db.execute(select(table).where(table.c.id.in_(values))).mappings()]
        for name in contract.REFERENCE_TABLES:
            table = Base.metadata.tables[name]
            column = table.c.entity_id if name == 'project_reference_changes' else table.c.type_id if name != 'project_deliverable_types' else table.c.id
            values = used_types | {typology['id']} if name == 'project_reference_changes' else used_types
            section[name] = [serial(row) for row in db.execute(select(table).where(column.in_(values))).mappings()]
    return {'tables': tables, 'section': section, 'references': references,
            'ids': {**ids, 'main': main, 'retained': retained, 'unused': unused, 'secret': secret, 'verifier': verifier,
                    'previous': previous, 'typology': typology, 'deliverable': deliverable, 'gate': gate,
                    'first': first, 'second': second}}


def validate(value):
    return contract.validate(Base.metadata, value['tables'], value['section'], value['references'])


def mapping(value):
    return {row['id']: str(uuid.uuid4()) for group in (value['tables'], value['section'], value['references'])
            for rows in group.values() for row in rows if 'id' in row}


def test_complete_contract_keeps_old_versions_history_inactive_composition_and_excludes_unrelated(envelope, store):
    before = capture_baseline(store[2])
    snapshot = deepcopy(envelope)
    context = validate(envelope)
    used = contract.dependencies(envelope['tables'], envelope['section'])
    assert used['types'] == {envelope['ids']['main']['id'], envelope['ids']['retained']['id']}
    assert used['people'] == {envelope['ids']['verifier']['id'], envelope['ids']['previous']['id']}
    assert envelope['ids']['secret']['id'] not in json.dumps({k: v for k, v in envelope.items() if k != 'ids'})
    assert envelope['ids']['unused']['id'] not in json.dumps({k: v for k, v in envelope.items() if k != 'ids'})
    assert len(context['files']) == 3 and len(context['type_versions']) == 3
    assert any(not row['active'] for row in envelope['section']['project_deliverable_typology_types'])
    assert context['type_versions'][envelope['ids']['main']['version_id']]['number'] == 1
    assert envelope == snapshot and capture_baseline(store[2]) == before


def test_remapping_is_typed_preserves_literal_uuid_text_and_source_publication(envelope):
    validate(envelope)
    original = deepcopy(envelope)
    ids = envelope['ids']
    replacements = mapping(envelope)
    project, globals_, events = contract.remap_archive(Base.metadata, envelope['tables'], envelope['section'], replacements)
    all_project = deepcopy(envelope['tables'])
    for name, rows in all_project.items():
        if name in project:
            continue
        table = Base.metadata.tables[name]
        if name in identity_archive.PROJECT_TABLES:
            all_project[name] = [identity_archive.remap_identity_row(row, table, replacements) for row in rows]
            continue
        for row in rows:
            for column in table.c:
                if (column.primary_key or column.foreign_keys) and row.get(column.name) is not None:
                    row[column.name] = replacements[row[column.name]]
    all_project.update(project)
    all_project['project_planning_changes'] = events  # This fixture only emits L3 planning commands.
    references = {name: [contract.remap_row(row, Base.metadata.tables[name], replacements) for row in rows]
                  for name, rows in envelope['references'].items()}
    contract.validate(Base.metadata, all_project, globals_, references)
    latest = next(row for row in project['project_deliverable_file_versions'] if row['id'] == replacements[ids['second']['version_id']])
    source = next(row for row in envelope['tables']['project_deliverable_file_versions'] if row['id'] == ids['second']['version_id'])
    value = manifest.check_row(latest)
    assert value['version'] == 2 and value['source_publication'] == {
        'version_id': source['id'], 'manifest': source['manifest'], 'manifest_sha256': source['manifest_sha256']}
    assert latest['path'] == source['path'] and latest['sha256'] == source['sha256']
    assert next(row for row in project['project_deliverable_plans'] if row['deliverable_id'] == replacements[ids['deliverable']])['comment'] == ids['main']['version_id']
    assert next(row for row in project['project_deliverable_checklist'] if row['id'] == replacements[ids['gate']])['proof'] == ids['deliverable']
    assert next(row for row in project['project_deliverable_checklist'] if row['id'] == replacements[ids['gate']])['label'] == ids['project']
    assert next(row for row in project['project_deliverable_events'] if row['action'] == 'deliverable_metadata_changed')['actor_id'] == ids['project']
    status = next(row for row in project['project_deliverable_events'] if row['value'].get('version_id') == replacements[ids['second']['version_id']]
                  and row['action'] == 'deliverable_status_changed' and row['value']['document_status'] == 'validated')
    assert status['value']['comment'] == ids['first']['version_id']
    assert globals_['project_deliverable_type_versions'][0]['definition'] == envelope['section']['project_deliverable_type_versions'][0]['definition']
    assert envelope == original


@pytest.mark.parametrize('with_state', [True, False])
def test_typology_composition_survives_without_any_selected_project_deliverable(envelope, with_state):
    value = deepcopy(envelope)
    for name in contract.PROJECT_TABLES:
        value['tables'][name] = []
    value['tables']['project_planning_changes'] = []
    if with_state:
        value['tables']['project_planning_states'][0]['revision'] = 0
    else:
        value['tables']['project_planning_states'] = []
    value['references']['project_people'] = []
    context = validate(value)
    assert len(context['types']) == 2 and len(context['type_versions']) == 3
    assert context['plans'] == {} and context['files'] == {}


def test_code_keys_and_actor_ids_equal_to_uuid_are_never_remapped(envelope):
    ids = mapping(envelope)
    identity = envelope['ids']['project']
    other = envelope['ids']['milestone']
    value = {'actor_id': identity, 'label': identity, 'proof': identity, 'comment': identity,
             'milestone_mapping': {identity: other}, 'existing_mapping': {identity: other}}
    result = contract._remap_values(value, ids)
    assert result['actor_id'] == result['label'] == result['proof'] == result['comment'] == identity
    assert result['milestone_mapping'] == {identity: ids[other]}
    assert result['existing_mapping'] == {ids[identity]: ids[other]}


def test_repeated_remapping_preserves_one_original_v1_leaf(envelope):
    validate(envelope)
    row = envelope['tables']['project_deliverable_file_versions'][0]
    replacements = mapping(envelope)
    first, digest = manifest.remap(row['manifest'], row['manifest_sha256'], replacements, version_id=row['id'])
    original = manifest.decode(first, digest)['source_publication']
    next_ids = {target: str(uuid.uuid4()) for target in replacements.values()}
    for _ in range(20):
        first, digest = manifest.remap(first, digest, next_ids, version_id=str(uuid.uuid4()))
        assert manifest.decode(first, digest)['source_publication'] == original
        next_ids = {target: str(uuid.uuid4()) for target in next_ids.values()}


@pytest.mark.parametrize('case', [
    'missing_type', 'unused_type', 'missing_old_type_version', 'bad_definition_hash', 'huge_version_number',
    'missing_person', 'foreign_project', 'foreign_file_owner', 'missing_metadata', 'duplicate_metadata',
    'foreign_completion', 'inactive_gate', 'lost_human_proof', 'invalid_current_state', 'missing_global_field',
    'bad_shared_event', 'duplicate_revision', 'unknown_action', 'invented_snapshot_field', 'foreign_composition',
    'wrong_cdc_hash', 'missing_published_version_event', 'bad_manifest_hash', 'file_gap', 'old_version_transition',
    'missing_selection_event', 'forged_global_snapshot', 'changed_global_code',
])
def test_incomplete_or_foreign_contract_is_refused_without_writes(envelope, store, case):
    validate(envelope)
    value = deepcopy(envelope)
    tables, section, refs, ids = value['tables'], value['section'], value['references'], value['ids']
    if case == 'missing_type':
        section['project_deliverable_types'].pop()
    elif case == 'unused_type':
        row = deepcopy(section['project_deliverable_types'][0])
        row.update(id=str(uuid.uuid4()), code='unused')
        section['project_deliverable_types'].append(row)
    elif case == 'missing_old_type_version':
        section['project_deliverable_type_versions'] = [row for row in section['project_deliverable_type_versions'] if row['id'] != ids['main']['version_id']]
    elif case in {'bad_definition_hash', 'huge_version_number'}:
        section['project_deliverable_type_versions'][0]['sha256' if case == 'bad_definition_hash' else 'number'] = '0' * 64 if case == 'bad_definition_hash' else 10**30
    elif case == 'missing_person':
        refs['project_people'] = [row for row in refs['project_people'] if row['id'] != ids['previous']['id']]
    elif case == 'foreign_project':
        tables['project_deliverable_plans'][0]['project_id'] = ids['foreign']
    elif case == 'foreign_file_owner':
        tables['project_deliverable_file_versions'][0]['deliverable_id'] = ids['legacy']
    elif case == 'missing_metadata':
        tables['project_deliverable_version_metadata'].pop()
    elif case == 'duplicate_metadata':
        tables['project_deliverable_version_metadata'].append(deepcopy(tables['project_deliverable_version_metadata'][0]))
    elif case in {'foreign_completion', 'inactive_gate', 'lost_human_proof'}:
        gate = tables['project_deliverable_checklist'][0]
        if case == 'foreign_completion':
            gate['completed_version_id'] = next(row['id'] for row in tables['project_deliverable_file_versions'] if row['deliverable_id'] == ids['legacy'])
        elif case == 'inactive_gate':
            gate['active'] = False
        else:
            gate['proof'] = ''
    elif case == 'invalid_current_state':
        next(row for row in tables['project_deliverable_plans'] if row['deliverable_id'] == ids['legacy'])['document_status'] = 'validated'
    elif case == 'missing_global_field':
        del section['project_deliverable_types'][0]['code']
    elif case == 'bad_shared_event':
        tables['project_planning_changes'][0]['value']['title'] = 'Titre divergent'
    elif case == 'duplicate_revision':
        row = deepcopy(tables['project_planning_changes'][0])
        row['id'] = str(uuid.uuid4())
        tables['project_planning_changes'].append(row)
    elif case == 'unknown_action':
        tables['project_deliverable_events'][0]['action'] = 'arbitrary'
    elif case == 'invented_snapshot_field':
        tables['project_deliverable_events'][0]['value']['hourly_rate'] = 50
    elif case == 'foreign_composition':
        section['project_deliverable_typology_types'][0]['typology_id'] = str(uuid.uuid4())
    elif case == 'wrong_cdc_hash':
        tables['delivery_versions'][0]['sha256'] = '0' * 64
    elif case == 'missing_published_version_event':
        tables['project_deliverable_events'] = [row for row in tables['project_deliverable_events'] if row['value'].get('version_id') != ids['second']['version_id']]
    elif case == 'bad_manifest_hash':
        tables['project_deliverable_file_versions'][0]['manifest_sha256'] = '0' * 64
    elif case == 'old_version_transition':
        event = next(row for row in tables['project_deliverable_events'] if row['action'] == 'deliverable_status_changed'
                     and row['value']['version_id'] == ids['second']['version_id'])
        event['value']['version_id'] = ids['first']['version_id']
        next(row for row in tables['project_planning_changes'] if row['revision'] == event['revision'])['value']['version_id'] = ids['first']['version_id']
    elif case == 'missing_selection_event':
        tables['project_deliverable_events'] = [row for row in tables['project_deliverable_events'] if row['action'] != 'deliverable_selection_changed']
    elif case in {'forged_global_snapshot', 'changed_global_code'}:
        event = next(row for row in section['project_reference_changes'] if row['entity_kind'] == 'deliverable_type' and 'code' in row['value'])
        if case == 'forged_global_snapshot':
            event['value'] = {'id': event['entity_id']}
        else:
            event['value']['code'] = 'different'
    else:
        tables['project_deliverable_file_versions'] = [row for row in tables['project_deliverable_file_versions'] if row['id'] != ids['first']['version_id']]
    before = capture_baseline(store[2])
    with pytest.raises(HTTPException) as error:
        validate(value)
    assert error.value.status_code == 400
    assert capture_baseline(store[2]) == before


@pytest.mark.parametrize('case', ['current_proof', 'current_label', 'current_completion_date', 'current_position',
                                  'changed_fixed_flag', 'forged_previous', 'publication_before_reset'])
def test_checklist_history_and_gate_resets_refuse_consistent_but_forged_snapshots(envelope, store, case):
    validate(envelope)
    value = deepcopy(envelope)
    tables, ids = value['tables'], value['ids']
    current = next(row for row in tables['project_deliverable_checklist'] if row['id'] == ids['gate'])
    changes = sorted((row for row in tables['project_deliverable_events'] if row['action'] == 'deliverable_check_changed'),
                     key=lambda row: row['revision'])
    if case.startswith('current_'):
        field = {'current_proof': 'proof', 'current_label': 'label', 'current_completion_date': 'completed_at',
                 'current_position': 'position'}[case]
        current[field] = 99 if field == 'position' else '2026-10-06T12:00:00' if field == 'completed_at' else 'Valeur falsifiée'
    elif case in {'changed_fixed_flag', 'forged_previous'}:
        event = changes[-1]
        field = 'transverse' if case == 'changed_fixed_flag' else 'label'
        event['previous'][field] = True if field == 'transverse' else 'Avant falsifié'
        next(row for row in tables['project_planning_changes'] if row['revision'] == event['revision'])['previous'][field] = event['previous'][field]
    else:
        version = next(row for row in tables['project_deliverable_file_versions'] if row['id'] == ids['second']['version_id'])
        snapshot = manifest.check_row(version)
        completed = next(row['value'] for row in changes if row['value']['completed'])
        snapshot['checklist'] = [deepcopy(completed) if check['id'] == ids['gate'] else check for check in snapshot['checklist']]
        version['manifest'], version['manifest_sha256'] = manifest.freeze(snapshot)
        event = next(row for row in tables['project_deliverable_events'] if row['action'] == 'deliverable_version_published'
                     and row['value']['version_id'] == version['id'])
        event['value']['manifest_sha256'] = version['manifest_sha256']
        next(row for row in tables['project_planning_changes'] if row['revision'] == event['revision'])['value']['manifest_sha256'] = version['manifest_sha256']
    before = capture_baseline(store[2])
    with pytest.raises(HTTPException) as error:
        validate(value)
    assert error.value.status_code == 400 and capture_baseline(store[2]) == before


def test_old_type_json_defaults_do_not_change_published_bytes(envelope):
    value = deepcopy(envelope)
    row = value['section']['project_deliverable_type_versions'][0]
    original = json.loads(row['definition'])
    original.pop('position')
    for check in original['checklist']:
        check.pop('typology_codes')
    row['definition'], row['sha256'] = manifest.freeze(original)
    for event in value['section']['project_reference_changes']:
        for snapshot in (event['previous'], event['value']):
            snapshot = snapshot.get('published_version', snapshot)
            if snapshot.get('version_id') == row['id']:
                snapshot['sha256'] = row['sha256']
    expected = row['definition']
    validate(value)
    assert row['definition'] == expected


def test_export_refuses_unmanaged_cdc_source_files_without_database_changes(envelope, store):
    from backend.app.services.project_archive import export_archive
    validate(envelope)
    install_planning_schema(store[0].kw['bind'], backup=lambda: backup_sqlite(store[2], store[2].parent / 'before-unmanaged-export.db'))
    before = capture_baseline(store[2])
    with store[0]() as db:
        with pytest.raises(HTTPException) as error:
            export_archive(db, envelope['ids']['project'])
        assert error.value.status_code == 409
        assert 'hors stockage' in error.value.detail
        assert db.get(DeliverablePlan, envelope['ids']['deliverable']) is not None
    assert capture_baseline(store[2]) == before


@pytest.mark.parametrize('case', ['source_extra', 'nested_v2', 'source_hash', 'different_bytes', 'unknown_check',
                                  'duplicate_check', 'boolean_version', 'noncanonical', 'source_actor'])
def test_v2_manifest_rejects_forged_or_incoherent_provenance(envelope, case):
    row = next(row for row in envelope['tables']['project_deliverable_file_versions'] if row['deliverable_id'] == envelope['ids']['deliverable'])
    payload, sha = manifest.remap(row['manifest'], row['manifest_sha256'], mapping(envelope), version_id=row['id'])
    value = manifest.decode(payload, sha)
    if case == 'source_extra':
        value['source_publication']['extra'] = True
    elif case == 'nested_v2':
        value['source_publication']['manifest'] = payload
        value['source_publication']['manifest_sha256'] = sha
    elif case == 'source_hash':
        value['source_publication']['manifest_sha256'] = '0' * 64
    elif case == 'different_bytes':
        value['sha256'] = '0' * 64
    elif case == 'unknown_check':
        value['checklist'][0]['arbitrary'] = 'foreign'
    elif case == 'duplicate_check':
        value['checklist'].append(deepcopy(value['checklist'][0]))
    elif case == 'boolean_version':
        value['version'] = True
    elif case == 'source_actor':
        value['actor_id'] = 'invented'
    payload, sha = manifest.freeze(value)
    if case == 'noncanonical':
        payload = json.dumps(value)
        sha = hashlib.sha256(payload.encode()).hexdigest()
    with pytest.raises(ValueError):
        manifest.decode(payload, sha)


def test_v2_versions_can_be_inserted_with_triggers_and_globally_restored_on_copies(envelope, store, tmp_path):
    validate(envelope)
    before = capture_baseline(store[2])
    replacements = mapping(envelope)
    project, globals_, events = contract.remap_archive(Base.metadata, envelope['tables'], envelope['section'], replacements)
    rows = deepcopy(envelope['tables'])
    for name, values in rows.items():
        if name in project or name == 'project_planning_changes':
            continue
        table = Base.metadata.tables[name]
        if name in identity_archive.PROJECT_TABLES:
            rows[name] = [identity_archive.remap_identity_row(row, table, replacements) for row in values]
        else:
            for row in values:
                for column in table.c:
                    if (column.primary_key or column.foreign_keys) and row.get(column.name) is not None:
                        row[column.name] = replacements[row[column.name]]
    rows.update(project)
    rows['project_planning_changes'] = events
    refs = {name: [identity_archive.remap_identity_row(row, Base.metadata.tables[name], replacements) for row in values]
            for name, values in envelope['references'].items()}
    contract.validate(Base.metadata, rows, globals_, refs)
    erp, storage, brain = tmp_path / 'managed', tmp_path / 'storage', tmp_path / 'brain.db'
    erp.mkdir()
    storage.mkdir()
    with sqlite3.connect(brain) as db:
        db.execute('CREATE TABLE sources (id TEXT PRIMARY KEY, sha256 TEXT, original_uri TEXT, source_metadata TEXT)')
    for row in rows['project_deliverable_file_versions']:
        target = erp / 'deliverables' / (row['id'] + '.md')
        if row['source_delivery_id']:
            target = erp / 'exports' / row['project_id'] / (row['source_delivery_id'] + '.md')
            next(delivery for delivery in rows['delivery_versions'] if delivery['id'] == row['source_delivery_id'])['path'] = str(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(row['path'], target)
        next(meta for meta in rows['project_deliverable_version_metadata'] if meta['version_id'] == row['id'])['storage_path'] = str(target)
    path = erp / 'minipilot.db'
    engine = create_engine(f'sqlite:///{path}')
    configure_sqlite(engine)
    Base.metadata.create_all(engine)
    install_planning_schema(engine, backup=lambda: backup_sqlite(path, tmp_path / 'clone-before-l2.db'))
    install_deliverable_schema(engine, backup=lambda: backup_sqlite(path, tmp_path / 'clone-before-l3.db'))
    try:
        with engine.begin() as db:
            all_rows = {**rows, **refs, **globals_}
            for table in Base.metadata.sorted_tables:
                for original in all_rows.get(table.name, []):
                    row = deepcopy(original)
                    for column in table.c:
                        if isinstance(column.type, DateTime) and row.get(column.name):
                            row[column.name] = datetime.fromisoformat(row[column.name])
                    db.execute(table.insert().values(**row))
        with engine.connect() as db:
            assert db.exec_driver_sql('PRAGMA foreign_key_check').all() == []
        backup = tmp_path / 'backup-v2'
        result = create_backup(backup, brain, erp, storage)
        assert len(result['deliverable_files']) == 3
        restore = tmp_path / 'restore-v2'
        restore_backup(backup, restore)
        restored_engine = create_engine(f'sqlite:///{restore / "erp/minipilot.db"}')
        try:
            with sessionmaker(bind=restored_engine)() as db:
                for version in db.query(service.DeliverableFileVersion):
                    assert Path(service.version_file_path(db, version)).is_relative_to(restore)
                    assert service._verify_file(db, version)['sha256'] == version.sha256
                    assert manifest.decode(version.manifest, version.manifest_sha256)['version'] == 2
                assert db.get(DeliverablePlan, replacements[envelope['ids']['deliverable']]).document_status == 'validated'
        finally:
            restored_engine.dispose()
        with sqlite3.connect(restore / 'erp/minipilot.db') as db:
            for table in ('project_deliverable_file_versions', 'project_deliverable_type_versions', 'project_deliverable_events'):
                for statement in (f'UPDATE {table} SET id=id', f'DELETE FROM {table}'):
                    with pytest.raises(sqlite3.IntegrityError, match='immutable'):
                        db.execute(statement)
        assert capture_baseline(store[2]) == before
    finally:
        engine.dispose()
