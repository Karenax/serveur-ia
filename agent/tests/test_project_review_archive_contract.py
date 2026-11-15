"""Prepared L4 archive contract on fictional stores; no transport activation."""
from copy import deepcopy
from datetime import datetime
import json
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import sessionmaker

from app.db import Base as BrainBase
from app.db_support import backup_sqlite, configure_sqlite
from app.services.deliverable_manifest import freeze
from backend.app.db import Base
from backend.app.project_review_schemas import ReviewCommand, ReviewContent, ReviewSave
from backend.app.services import project_review_archive as contract, project_reviews as service
from backend.app.services.migration_guard import capture_baseline, compare_baseline
from backend.app.services.project_review_migration import install_review_schema, validate_review_schema
from tests import test_project_reviews as fixtures
from tests import test_project_deliverables as document_fixtures

store = fixtures.store
audio = fixtures.audio
l3_store = document_fixtures.store


def serial(row):
    return {key: value.isoformat() if isinstance(value, datetime) else value for key, value in row.items()}


def rows(factory, metadata, project):
    values = {}
    with factory() as db:
        available = set(inspect(db.get_bind()).get_table_names())
        for table in metadata.sorted_tables:
            if table.name not in available:
                continue
            if table.name == 'projects':
                query = select(table).where(table.c.id == project)
            elif 'project_id' in table.c:
                query = select(table).where(table.c.project_id == project)
            else:
                continue
            values[table.name] = [serial(row) for row in db.execute(query).mappings()]
    return values


@pytest.fixture
def envelope(store, audio):
    initial = fixtures.create(store, fixtures.content(store[1], notes=store[1]['project']))
    imported = fixtures.import_audio(store, audio, initial)
    edited = ReviewContent.model_validate(imported['content'])
    edited.items[-1].reviewed = True
    fixtures.command(store, service.save_review, initial['id'], ReviewSave, content=edited)
    fixtures.publish(store, initial['id'])
    cloned = fixtures.command(store, service.create_revision, initial['id'], ReviewCommand)
    changed = ReviewContent.model_validate(cloned['content'])
    changed.items[0].text = store[1]['deliverable']  # A UUID-looking literal is not a relationship.
    fixtures.command(store, service.save_review, cloned['id'], ReviewSave, content=changed)
    tables = rows(store[0], Base.metadata, store[1]['project'])
    with store[0]() as db:
        references = {'project_people': [serial(row) for row in db.execute(select(Base.metadata.tables['project_people'])).mappings()]}
    with audio[0]() as db:
        recording = db.execute(select(BrainBase.metadata.tables['meeting_recordings'])).mappings().one()
        brain = rows(audio[0], BrainBase.metadata, recording['project_id'])
        artifacts = BrainBase.metadata.tables['source_artifacts']
        brain['source_artifacts'] = [serial(row) for row in db.execute(select(artifacts)).mappings()]
    return {'tables': tables, 'references': references, 'deliverable_references': {}, 'brain': brain}


def validate(value):
    contract.validate(Base.metadata, **value)


def mappings(value):
    erp = {row['id']: str(uuid.uuid4()) for group in ('tables', 'references', 'deliverable_references')
           for rows in value[group].values() for row in rows if row.get('id')}
    brain = {row['id']: str(uuid.uuid4()) for rows in (value['brain'] or {}).values() for row in rows if row.get('id')}
    return erp, brain


def remap(value, erp, brain):
    result = deepcopy(value)
    # Test scaffolding remaps declared SQL relationships only. The production
    # transport is deliberately still guarded until its coordinated recipe.
    for group, metadata, mapping in (('tables', Base.metadata, erp), ('references', Base.metadata, erp),
                                    ('deliverable_references', Base.metadata, erp), ('brain', BrainBase.metadata, brain)):
        for name, values in result[group].items():
            if name in contract.PROJECT_TABLES:
                result[group][name] = [contract.remap_row(row, name, erp, brain) for row in values]
                continue
            for row in values:
                for column in metadata.tables[name].c:
                    if row.get(column.name) is not None and (column.primary_key or column.foreign_keys):
                        row[column.name] = mapping.get(row[column.name], row[column.name])
                if name == 'meeting_recordings':
                    row['erp_project_id'] = erp[row['erp_project_id']]
                elif name == 'source_artifacts':
                    row.update(contract.remap_audio_artifact(row, brain))
    return result


def test_published_audio_clone_contract_is_readonly_and_accepts_sqlite_utc(envelope, store, audio):
    before = (capture_baseline(store[2]), capture_baseline(audio[2]), deepcopy(envelope))
    validate(envelope)
    assert (capture_baseline(store[2]), capture_baseline(audio[2]), envelope) == before
    publication = envelope['tables']['project_review_publications'][0]
    assert '+00:00' in json.loads(publication['snapshot'])['published_at']
    assert '+00:00' not in publication['created_at']
    assert contract.identity_dependencies(envelope['tables']) == ({}, {store[1]['person']})


def test_twenty_rebindings_keep_pdf_snapshot_history_and_literal_text_exact(envelope, store):
    original = deepcopy(envelope)
    original_events = {row['id']: (row['previous'], row['value']) for row in envelope['tables']['project_review_events']}
    value = envelope
    for _ in range(20):
        erp, brain = mappings(value)
        value = remap(value, erp, brain)
        validate(value)
        publication = value['tables']['project_review_publications'][0]
        initial = original['tables']['project_review_publications'][0]
        for key in ('snapshot', 'sha256', 'pdf_base64', 'pdf_sha256'):
            assert publication[key] == initial[key]
        assert set(publication['bindings']) == {'erp', 'brain'}
        assert all(isinstance(target, str) for space in publication['bindings'].values() for target in space.values())
        assert [(event['previous'], event['value']) for event in value['tables']['project_review_events']] == list(original_events.values())
        live = next(row for row in value['tables']['project_reviews'] if row['number'] == 2)
        assert live['content']['notes'].startswith(store[1]['project'])
        assert live['content']['items'][0]['text'] == store[1]['deliverable']
        assert live['content']['items'][0]['id'] == 'manual-0'
        proof = next(iter(live['provenance'].values()))
        assert proof['recording_id'] == value['brain']['meeting_recordings'][0]['id']
    assert envelope == original


def test_erp_and_brain_equal_uuid_have_independent_bindings(envelope):
    erp, brain = mappings(envelope)
    pid = envelope['tables']['projects'][0]['id']
    old_brain = envelope['brain']['projects'][0]['id']
    erp = {key: key for key in erp}
    brain = {key: key for key in brain} | {old_brain: pid}
    overlapped = remap(envelope, erp, brain)
    validate(overlapped)
    erp, brain = mappings(overlapped)
    assert erp[pid] != brain[pid]
    restored = remap(overlapped, erp, brain)
    validate(restored)
    proof = next(iter(restored['tables']['project_reviews'][0]['provenance'].values()))
    assert proof['erp_project_id'] == erp[pid]
    assert proof['brain_project_id'] == brain[pid]


@pytest.mark.parametrize('kind', ['missing_person', 'missing_doc', 'missing_milestone', 'missing_recording', 'missing_source',
    'foreign_recording', 'foreign_source', 'future_transcript', 'changed_excerpt', 'changed_speaker', 'missing_event',
    'duplicate_event', 'duplicate_review', 'duplicate_publication', 'extra_column', 'null_bindings', 'invalid_action',
    'shared_revision_collision', 'noncontiguous_review_numbers', 'wrong_clone_origin', 'manual_provenance_change'])
def test_broken_closure_or_history_is_rejected_before_any_write(envelope, kind, store, audio):
    value = deepcopy(envelope)
    tables, brain = value['tables'], value['brain']
    if kind == 'missing_person':
        value['references']['project_people'] = []
    elif kind == 'missing_doc':
        tables['deliverables'] = []
    elif kind == 'missing_milestone':
        tables['milestones'] = []
    elif kind == 'missing_recording':
        brain['meeting_recordings'] = []
    elif kind == 'missing_source':
        brain['sources'] = []
    elif kind == 'foreign_recording':
        brain['meeting_recordings'][0]['erp_project_id'] = 'foreign'
    elif kind == 'foreign_source':
        brain['sources'][0]['project_id'] = 'foreign'
    elif kind == 'future_transcript':
        brain['meeting_recordings'][0]['revision'] = 2
    elif kind == 'changed_excerpt':
        brain['meeting_recordings'][0]['segments'][0]['text'] = 'Une autre phrase'
    elif kind == 'changed_speaker':
        brain['meeting_recordings'][0]['speaker_names']['speaker-1'] = 'Bob'
    elif kind == 'missing_event':
        tables['project_review_events'] = tables['project_review_events'][1:]
    elif kind == 'duplicate_event':
        tables['project_review_events'].append(deepcopy(tables['project_review_events'][0]))
    elif kind == 'duplicate_review':
        tables['project_reviews'].append(deepcopy(tables['project_reviews'][0]))
    elif kind == 'duplicate_publication':
        tables['project_review_publications'].append(deepcopy(tables['project_review_publications'][0]))
    elif kind == 'extra_column':
        tables['project_review_events'][0]['invented'] = 1
    elif kind == 'null_bindings':
        tables['project_review_events'][0]['bindings'] = None
    elif kind == 'invalid_action':
        tables['project_review_events'][0]['action'] = 'review_deleted'
    elif kind == 'shared_revision_collision':
        tables['project_planning_changes'] = [{'revision': 1}]
    elif kind == 'noncontiguous_review_numbers':
        tables['project_reviews'][1]['number'] = 3
    elif kind == 'wrong_clone_origin':
        event = next(row for row in tables['project_review_events'] if row['action'] == 'review_revision_created')
        event['previous'] = {}
    elif kind == 'manual_provenance_change':
        event = next(row for row in tables['project_review_events'] if row['action'] == 'review_recording_imported')
        event['action'] = 'review_saved'
    before = (capture_baseline(store[2]), capture_baseline(audio[2]))
    with pytest.raises(HTTPException) as error:
        validate(value)
    assert error.value.status_code == 400
    assert (capture_baseline(store[2]), capture_baseline(audio[2])) == before


@pytest.mark.parametrize('key', ['snapshot', 'sha256', 'pdf_base64', 'pdf_sha256'])
def test_publication_integrity_is_checked(envelope, key):
    value = deepcopy(envelope)
    value['tables']['project_review_publications'][0][key] += 'corrupt'
    with pytest.raises(HTTPException) as error:
        validate(value)
    assert error.value.status_code == 400


@pytest.mark.parametrize('kind', ['bool_version', 'unknown_role', 'missing_content_field', 'false_read_flag',
    'different_participant', 'wrong_publication_id', 'wrong_actor', 'wrong_timestamp', 'wrong_progress',
    'wrong_document_revision', 'wrong_review_number'])
def test_recomputed_hash_does_not_bypass_domain_validation(envelope, kind):
    value = deepcopy(envelope)
    publication = value['tables']['project_review_publications'][0]
    captured = json.loads(publication['snapshot'])
    if kind == 'bool_version':
        captured['version'] = True
    elif kind == 'unknown_role':
        captured['team'][0]['role'] = 'invented'
    elif kind == 'missing_content_field':
        captured['review']['content'].pop('notes')
    elif kind == 'false_read_flag':
        captured['review']['content']['items'][0]['reviewed'] = False
    elif kind == 'different_participant':
        captured['review']['content']['participants'][0]['name'] = 'Un autre nom'
    elif kind == 'wrong_publication_id':
        captured['publication_id'] = 'foreign'
    elif kind == 'wrong_actor':
        captured['published_by'] = 'foreign'
    elif kind == 'wrong_timestamp':
        captured['published_at'] = '2025-01-01T00:00:00+00:00'
    elif kind == 'wrong_progress':
        captured['deliverables'][0]['progress']['percentage'] = 100
    elif kind == 'wrong_document_revision':
        captured['deliverables'][0]['revision'] += 1
    else:
        captured['review']['number'] += 1
    publication['snapshot'], publication['sha256'] = freeze(captured)
    with pytest.raises(HTTPException) as error:
        validate(value)
    assert error.value.status_code == 400


def test_shared_journal_requires_every_revision(envelope):
    value = deepcopy(envelope)
    value['tables']['project_planning_states'][0]['revision'] += 1
    with pytest.raises(HTTPException, match='incomplet'):
        validate(value)


def test_save_cannot_appear_as_publication_even_with_identical_final_value(envelope):
    value = deepcopy(envelope)
    event = next(row for row in value['tables']['project_review_events'] if row['action'] == 'review_published')
    event['action'] = 'review_saved'
    with pytest.raises(HTTPException, match='sans événement'):
        validate(value)


@pytest.mark.parametrize('kind', ['missing', 'unused', 'foreign', 'wrong_namespace'])
def test_incomplete_or_extraneous_restore_bindings_are_rejected(envelope, kind):
    value = remap(envelope, *mappings(envelope))
    publication = value['tables']['project_review_publications'][0]
    key = next(iter(publication['bindings']['erp']))
    if kind == 'missing':
        publication['bindings']['erp'].pop(key)
    elif kind == 'unused':
        publication['bindings']['erp']['invented'] = 'invented'
    elif kind == 'foreign':
        publication['bindings']['erp'][key] = 'foreign'
    else:
        publication['bindings']['unexpected'] = {}
    with pytest.raises(HTTPException) as error:
        validate(value)
    assert error.value.status_code == 400


def historical(value):
    value = deepcopy(value)
    recording = value['brain']['meeting_recordings'][0]
    value['brain']['source_artifacts'].append({'id': str(uuid.uuid4()), 'source_id': recording['source_id'],
        'kind': 'transcription', 'content_text': 'Original conservé', 'created_at': recording['created_at'],
        'content_json': {'recording_id': recording['id'], 'revision': 3, 'segments': deepcopy(recording['segments']),
                         'speaker_names': deepcopy(recording['speaker_names']), 'superseded': True}})
    recording['revision'] = 4
    recording['segments'][0]['text'] = 'Transcription corrigée ultérieurement'
    recording['speaker_names']['speaker-1'] = 'Nom corrigé'
    return value


def test_later_transcript_requires_retained_revision_and_survives_rebinding(envelope):
    value = historical(envelope)
    validate(value)
    restored = remap(value, *mappings(value))
    validate(restored)
    artifact = restored['brain']['source_artifacts'][0]
    assert artifact['content_json']['recording_id'] == restored['brain']['meeting_recordings'][0]['id']
    assert artifact['content_text'] == 'Original conservé'
    assert artifact['content_json']['segments'] == value['brain']['source_artifacts'][0]['content_json']['segments']
    for _ in range(3):
        restored = remap(restored, *mappings(restored))
        validate(restored)


@pytest.mark.parametrize('kind', ['missing', 'ambiguous', 'wrong_recording', 'wrong_revision', 'changed_text', 'changed_speaker'])
def test_unavailable_or_changed_historical_transcription_rejected(envelope, kind):
    value = historical(envelope)
    artifacts = value['brain']['source_artifacts']
    if kind == 'missing':
        artifacts.clear()
    elif kind == 'ambiguous':
        artifacts.append(deepcopy(artifacts[0]))
    elif kind == 'wrong_recording':
        artifacts[0]['content_json']['recording_id'] = 'foreign'
    elif kind == 'wrong_revision':
        artifacts[0]['content_json']['revision'] = 2
    elif kind == 'changed_text':
        artifacts[0]['content_json']['segments'][0]['text'] = 'Autre texte'
    else:
        artifacts[0]['content_json']['speaker_names']['speaker-1'] = 'Autre nom'
    with pytest.raises(HTTPException) as error:
        validate(value)
    assert error.value.status_code == 400


def old_schema(store):
    # Independent, empty-review fictional copy emulates the pre-binding L4
    # preparation. No user's database or published values are modified.
    path = store[2].parent / 'old-preparation.db'
    backup_sqlite(store[2], path)
    engine = create_engine(f'sqlite:///{path}')
    configure_sqlite(engine)
    with engine.begin() as db:
        for name in ('project_review_publications', 'project_review_events'):
            db.exec_driver_sql(f'ALTER TABLE {name} DROP COLUMN bindings')
    return engine, path


def test_binding_schema_upgrade_backs_up_before_ddl_preserves_cells_and_is_idempotent(store):
    engine, path = old_schema(store)
    before = capture_baseline(path)
    backup = path.parent / 'before-bindings.db'
    try:
        plan = validate_review_schema(engine)
        assert plan['added_binding_columns'] == ['project_review_publications', 'project_review_events']
        def checked_backup():
            assert capture_baseline(path) == before
            assert all('bindings' not in {column['name'] for column in inspect(engine).get_columns(name)}
                       for name in plan['added_binding_columns'])
            backup_sqlite(path, backup)
        assert install_review_schema(engine, backup=checked_backup) == plan
        assert capture_baseline(backup) == before
        assert compare_baseline(before, capture_baseline(path))['preserved']
        assert install_review_schema(engine, backup=lambda: pytest.fail('Repeated backup')) == {
            'created_tables': [], 'created_triggers': []}
        copied = (sessionmaker(bind=engine), store[1], path, *store[3:])
        created = fixtures.create(copied)
        fixtures.publish(copied, created['id'])
        with engine.connect() as db:
            assert json.loads(db.exec_driver_sql('SELECT bindings FROM project_review_publications').scalar_one()) == {}
    finally:
        engine.dispose()


def test_binding_schema_backup_failure_changes_nothing(store):
    engine, path = old_schema(store)
    before = capture_baseline(path)
    try:
        with pytest.raises(RuntimeError, match='backup failed'):
            install_review_schema(engine, backup=lambda: (_ for _ in ()).throw(RuntimeError('backup failed')))
        assert capture_baseline(path) == before
        assert len(validate_review_schema(engine)['added_binding_columns']) == 2
    finally:
        engine.dispose()


@pytest.mark.parametrize('declaration', ['TEXT NOT NULL DEFAULT \'{}\'', 'JSON DEFAULT \'{}\''])
def test_incompatible_existing_binding_column_refused_before_backup(store, declaration):
    engine, path = old_schema(store)
    try:
        with engine.begin() as db:
            db.exec_driver_sql('ALTER TABLE project_review_events ADD COLUMN bindings ' + declaration)
        before = capture_baseline(path)
        with pytest.raises(ValueError, match='Schéma'):
            install_review_schema(engine, backup=lambda: pytest.fail('Incompatible schema cannot be hidden by backup'))
        assert capture_baseline(path) == before
    finally:
        engine.dispose()


def test_additive_upgrade_preserves_populated_frozen_publications_and_events(store):
    initial = fixtures.create(store)
    fixtures.publish(store, initial['id'])
    engine, path = old_schema(store)
    before = capture_baseline(path)
    backup = path.parent / 'populated-before-bindings.db'
    try:
        with engine.connect() as db:
            previous = db.exec_driver_sql('SELECT snapshot, sha256, pdf_base64, pdf_sha256 FROM project_review_publications').one()
            events = db.exec_driver_sql('SELECT previous, value FROM project_review_events ORDER BY planning_revision').all()
        install_review_schema(engine, backup=lambda: backup_sqlite(path, backup))
        assert capture_baseline(backup) == before
        assert compare_baseline(before, capture_baseline(path))['preserved']
        with engine.connect() as db:
            assert db.exec_driver_sql('SELECT snapshot, sha256, pdf_base64, pdf_sha256 FROM project_review_publications').one() == previous
            assert db.exec_driver_sql('SELECT previous, value FROM project_review_events ORDER BY planning_revision').all() == events
            assert json.loads(db.exec_driver_sql('SELECT bindings FROM project_review_publications').scalar_one()) == {}
            assert all(json.loads(row[0]) == {} for row in db.exec_driver_sql('SELECT bindings FROM project_review_events'))
        assert len(inspect(engine).get_foreign_keys('project_review_publications')) == 2
    finally:
        engine.dispose()


@pytest.fixture
def typed_document(l3_store):
    from backend.app.project_identity_models import ProjectMember
    from backend.app.project_deliverable_schemas import ChecklistPatch, DeliverableCreate, TypeCreate, TypeDefinition
    from backend.app.services import project_deliverables as documents
    from backend.app.services.planning_revision import revision
    factory, ids, *_ = l3_store
    install_review_schema(factory.kw['bind'], backup=lambda: backup_sqlite(l3_store[2], l3_store[2].parent / 'l3-before-review.db'))
    with fixtures.transaction(factory) as db:
        db.add(ProjectMember(project_id=ids['project'], person_id=ids['person'], role='responsable_projet'))
        kind = documents.create_type(db, TypeCreate(code='rlp-doc', label='Dossier de lancement', definition=TypeDefinition(
            checklist=[{'code': 'visa', 'label': 'Visa humain', 'is_gate': True}])))
        document = documents.create_deliverable(db, ids['project'], DeliverableCreate(expected_revision=revision(db, ids['project']),
            title='Dossier typé', type_version_id=kind['version_id'], responsible_id=ids['person'], verifier_id=ids['person'],
            milestone_ids=[ids['milestone']]))
        check = documents.read_deliverable(db, ids['project'], document['id'])['checklist'][0]['id']
    published = document_fixtures.publish(l3_store, document['id'])
    with fixtures.transaction(factory) as db:
        documents.patch_check(db, ids['project'], document['id'], check, ChecklistPatch(
            expected_revision=revision(db, ids['project']), completed=True, proof='Visa humain explicite'))
    review_store = (factory, {**ids, 'deliverable': document['id']}, *l3_store[2:])
    initial = fixtures.create(review_store)
    fixtures.publish(review_store, initial['id'])
    tables = rows(factory, Base.metadata, ids['project'])
    references, types = {}, {}
    with factory() as db:
        for name, group in (('project_people', references), ('project_deliverable_type_versions', types)):
            group[name] = [serial(row) for row in db.execute(select(Base.metadata.tables[name])).mappings()]
    value = {'tables': tables, 'references': references, 'deliverable_references': types, 'brain': None}
    return value, review_store, published, check


def test_real_typed_deliverable_captures_checks_visas_and_file_versions(typed_document):
    value, _, published, check = typed_document
    validate(value)
    captured = json.loads(value['tables']['project_review_publications'][0]['snapshot'])['deliverables'][0]
    assert captured['progress']['percentage'] == 100
    assert captured['latest_version_id'] == published['version_id']
    assert captured['checklist'][0]['id'] == check and captured['checklist'][0]['completed']
    assert not captured['validation_blockers']
    # The frozen document is historical: a later live title/visa change cannot
    # rewrite it or make its captured completion counters use today's values.
    value['tables']['deliverables'][0]['title'] = 'Titre actuel'
    value['tables']['project_deliverable_checklist'][0]['label'] = 'Libellé actuel'
    validate(value)
    erp, brain = mappings(value)
    # This recipe has no Brain namespace or worker.
    result = deepcopy(value)
    result['brain'] = {}
    restored = remap(result, erp, brain)
    validate(restored)


@pytest.mark.parametrize('kind', ['missing_check', 'missing_file', 'missing_type', 'foreign_check', 'foreign_file'])
def test_frozen_document_requires_its_own_retained_dependencies(typed_document, kind):
    value = deepcopy(typed_document[0])
    if kind == 'missing_check':
        value['tables']['project_deliverable_checklist'] = []
    elif kind == 'missing_file':
        value['tables']['project_deliverable_file_versions'] = []
    elif kind == 'missing_type':
        value['deliverable_references']['project_deliverable_type_versions'] = []
    else:
        table = 'project_deliverable_checklist' if kind == 'foreign_check' else 'project_deliverable_file_versions'
        value['tables'][table][0]['deliverable_id'] = value['tables']['deliverables'][0]['id']
        # Fixture retains another legacy document in the same project.
        captured_id = json.loads(value['tables']['project_review_publications'][0]['snapshot'])['deliverables'][0]['id']
        other = next(row['id'] for row in value['tables']['deliverables'] if row['id'] != captured_id)
        value['tables'][table][0]['deliverable_id'] = other
    with pytest.raises(HTTPException) as error:
        validate(value)
    assert error.value.status_code == 400
