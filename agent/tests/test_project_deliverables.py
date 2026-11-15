"""L3 foundation on fictional stores only: immutable files, gates, scope, CAS."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import shutil

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db_support import backup_sqlite, configure_sqlite
from backend.app.db import Base
from backend.app.models import Deliverable, DeliveryVersion, Milestone, Project
from backend.app.project_deliverable_models import (
    DELIVERABLE_TABLES, IMMUTABLE_TABLES, DeliverableEvent, DeliverableFileVersion,
    DeliverablePlan, DeliverableTypeVersion, DeliverableVersionMetadata,
)
from backend.app.project_deliverable_schemas import (
    ChecklistCreate, ChecklistPatch, DeliverableCreate, DeliverablePatch, DocumentTransition,
    FilePublication, TypeCreate, TypeDefinition, TypePublish, VersionMetadataPatch,
)
from backend.app.project_identity_models import ProjectPerson
from backend.app.services import project_deliverables as service
from backend.app.services.migration_guard import capture_baseline, compare_baseline
from backend.app.services.planning_revision import revision
from backend.app.services.project_deliverable_migration import install_deliverable_schema
from backend.app.services.project_deliverable_rules import file_digest, frozen_json, progress, standard_catalogue
from backend.app.services.project_operator import Operator, operator_context


@contextmanager
def transaction(factory):
    with factory() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise


@pytest.fixture
def store(tmp_path):
    path = tmp_path / 'erp.db'
    engine = create_engine(f'sqlite:///{path}', connect_args={'check_same_thread': False})
    configure_sqlite(engine)
    Base.metadata.create_all(engine, tables=[table for table in Base.metadata.sorted_tables
                                           if table not in DELIVERABLE_TABLES])
    factory = sessionmaker(bind=engine, autoflush=False)
    with transaction(factory) as db:
        project, foreign = Project(title='Recette L3'), Project(title='Autre projet')
        person = ProjectPerson(first_name='Vérificateur', last_name='Recette')
        db.add_all([project, foreign, person])
        db.flush()
        milestone, other = Milestone(project_id=project.id, title='PDR'), Milestone(project_id=foreign.id, title='Autre')
        legacy = Deliverable(project_id=project.id, title='Historique conservé', status='done')
        db.add_all([milestone, other, legacy])
        db.flush()
        ids = {'project': project.id, 'foreign': foreign.id, 'person': person.id,
               'milestone': milestone.id, 'other': other.id, 'legacy': legacy.id}
    before = capture_baseline(path)
    backup = tmp_path / 'before-l3.db'
    installed = install_deliverable_schema(engine, backup=lambda: backup_sqlite(path, backup))
    yield factory, ids, path, before, backup, installed
    engine.dispose()


def create(store, *, with_gate=True):
    factory, ids, *_ = store
    with transaction(factory) as db:
        result = service.create_deliverable(db, ids['project'], DeliverableCreate(
            expected_revision=revision(db, ids['project']), title='Analyse Fonctionnelle', verifier_id=ids['person'],
            milestone_ids=[ids['milestone']]))
        if with_gate:
            check = service.create_check(db, ids['project'], result['id'], ChecklistCreate(
                expected_revision=result['revision'], code='visa', label='Visa humain', is_gate=True,
                milestone_id=ids['milestone']))
        else:
            check = {'item': {'id': None}}
        return result['id'], check['item']['id']


def publish(store, deliverable_id, *, name='document-v1.md', content='Contenu version 1', **values):
    factory, ids, path, *_ = store
    document = path.parent / name
    document.write_text(content, encoding='utf-8')
    with transaction(factory) as db:
        return service.publish_file(db, ids['project'], deliverable_id, FilePublication(
            expected_revision=revision(db, ids['project']), reference='AF-001', **values), path=document)


def command(store, fn, *args, **values):
    factory, ids, *_ = store
    with transaction(factory) as db:
        return fn(db, ids['project'], *args, **values)


def test_migration_preserves_every_existing_cell_is_idempotent_and_backup_failure_aborts(store):
    factory, ids, path, before, backup, installed = store
    assert len(installed['created_tables']) == 9 and len(installed['created_triggers']) == 6
    assert compare_baseline(before, capture_baseline(path))['preserved']
    assert capture_baseline(backup) == before
    engine = factory.kw['bind']
    assert install_deliverable_schema(engine, backup=lambda: pytest.fail('Repeated backup')) == {
        'created_tables': [], 'created_triggers': []}
    with factory() as db:
        assert db.get(Deliverable, ids['legacy']).status == 'done'
    isolated = create_engine(f'sqlite:///{path.parent / "backup-failure.db"}')
    Base.metadata.create_all(isolated, tables=[table for table in Base.metadata.sorted_tables
                                             if table not in DELIVERABLE_TABLES])
    with pytest.raises(RuntimeError):
        install_deliverable_schema(isolated, backup=lambda: (_ for _ in ()).throw(RuntimeError('backup failed')))
    with isolated.connect() as db:
        assert not db.exec_driver_sql("SELECT name FROM sqlite_master WHERE name LIKE 'project_deliverable_%'").all()
    isolated.dispose()


def test_incompatible_table_and_trigger_are_refused_before_backup(store):
    engine = store[0].kw['bind']
    with engine.begin() as db:
        db.exec_driver_sql('DROP TRIGGER trg_project_deliverable_events_delete_immutable')
        db.exec_driver_sql('CREATE TRIGGER trg_project_deliverable_events_delete_immutable BEFORE DELETE '
                           'ON project_deliverable_events BEGIN SELECT 1; END')
    with pytest.raises(ValueError, match='Protection'):
        install_deliverable_schema(engine, backup=lambda: pytest.fail('Backup should not conceal corruption'))


def test_legacy_read_is_neutral_and_never_invents_validation(store):
    factory, ids, path, *_ = store
    before = capture_baseline(path)
    with factory() as db:
        value = service.read_deliverable(db, ids['project'], ids['legacy'])
        assert value['legacy_status'] == 'done' and value['document_status'] == 'draft'
        assert value['latest_version_id'] is None and value['progress']['state'] == 'not_applicable'
        assert db.get(DeliverablePlan, ids['legacy']) is None
    assert capture_baseline(path) == before


def test_reference_catalogue_retains_all_xpilot_types_checklists_and_typologies():
    catalogue = standard_catalogue()
    assert len(catalogue['types']) == 11 and len(catalogue['typologies']) == 3
    assert sum(len(t['definition']['checklist']) for t in catalogue['types']) == 67
    assert {'analyse_fonctionnelle', 'analyse_risque', 'conception_3d', 'conception_2d', 'calcul',
            'amdec', 'notice', 'v_and_v', 'formation', 'dossier_fdr', 'acv'} == {t['code'] for t in catalogue['types']}
    assert catalogue['source']['sha256'] == 'f9b43bee67946ad7691bff8d6683f08d1bdc31e70a15c21f6cb30b7b1de44bc5'


def test_published_types_are_frozen_and_new_version_does_not_mutate_project(store):
    factory, ids, *_ = store
    definition = TypeDefinition(checklist=[{'code': 'visa', 'label': 'Visa PDR', 'is_gate': True, 'milestone_code': 'pdr'},
                                          {'code': 'notice', 'label': 'Notice FDR', 'milestone_code': 'fdr'}])
    with transaction(factory) as db:
        reference = service.create_type(db, TypeCreate(code='af', label='AF', definition=definition))
        item = service.create_deliverable(db, ids['project'], DeliverableCreate(expected_revision=0, title='AF',
            type_version_id=reference['version_id'], milestone_ids=[ids['milestone']],
            milestone_mapping={'pdr': ids['milestone']}))
        current = service.read_deliverable(db, ids['project'], item['id'])
        assert len(current['checklist']) == 1 and current['checklist'][0]['scope_key'] == 'pdr'
        version = service.publish_type(db, reference['id'], TypePublish(expected_revision=1,
            definition=TypeDefinition(checklist=[{'code': 'another', 'label': 'Nouvelle checklist'}])))
        assert version['revision'] == 2
        assert service.read_deliverable(db, ids['project'], item['id']) == current
        assert db.get(DeliverableTypeVersion, reference['version_id']).sha256 == reference['sha256']


@pytest.mark.parametrize('table', IMMUTABLE_TABLES)
@pytest.mark.parametrize('operation', ['UPDATE', 'DELETE'])
def test_database_refuses_immutable_version_and_history_mutation(store, table, operation):
    identity, _ = create(store)
    publish(store, identity)
    with transaction(store[0]) as db:
        service.create_type(db, TypeCreate(code='af', label='AF', definition=TypeDefinition()))
    engine = store[0].kw['bind']
    with pytest.raises(IntegrityError, match='immutable'):
        with engine.begin() as db:
            sql = f'UPDATE {table} SET id=id' if operation == 'UPDATE' else f'DELETE FROM {table}'
            db.execute(text(sql))


def test_reader_scope_and_foreign_relations_are_enforced(store):
    factory, ids, *_ = store
    with operator_context(Operator('reader', 'reader', frozenset([ids['project']]))):
        with factory() as db:
            assert service.read_deliverable(db, ids['project'], ids['legacy'])['title']
        with pytest.raises(HTTPException) as error:
            command(store, service.create_deliverable, DeliverableCreate(expected_revision=0, title='Interdit'))
        assert error.value.status_code == 403
        with pytest.raises(HTTPException) as error:
            with factory() as db:
                service.read_deliverable(db, ids['foreign'], ids['legacy'])
        assert error.value.status_code == 404
    with pytest.raises(HTTPException) as error:
        command(store, service.create_deliverable, DeliverableCreate(expected_revision=0, title='Mauvais jalon',
                                                                   milestone_ids=[ids['other']]))
    assert error.value.status_code == 422
    with factory() as db:
        assert revision(db, ids['project']) == 0


def test_cas_has_one_winner_and_preserves_losing_draft(store):
    factory, ids, *_ = store
    def mutate(title):
        try:
            command(store, service.create_deliverable, DeliverableCreate(expected_revision=0, title=title))
            return 201
        except HTTPException as exc:
            return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(mutate, ['Concurrent A', 'Concurrent B'])) == [201, 409]
    with factory() as db:
        assert revision(db, ids['project']) == 1
        assert db.query(DeliverableEvent).count() == 1
        assert db.query(Deliverable).count() == 2  # legacy plus one new row


def test_generation_is_draft_and_gate_requires_file_proof_and_human(store):
    identity, gate_id = create(store)
    with pytest.raises(HTTPException, match='version publiée'):
        command(store, service.patch_check, identity, gate_id, ChecklistPatch(expected_revision=2,
                                                                            completed=True, proof='Visa'))
    version = publish(store, identity, generated=True)
    with store[0]() as db:
        value = service.read_deliverable(db, store[1]['project'], identity)
        assert value['document_status'] == 'draft' and value['checklist'][0]['completed'] is False
    command(store, service.transition, identity, DocumentTransition(expected_revision=3, status='to_verify',
                                                                    version_id=version['version_id']))
    with pytest.raises(HTTPException) as error:
        command(store, service.transition, identity, DocumentTransition(expected_revision=4, status='validated',
            version_id=version['version_id'], comment='Visa'))
    assert error.value.status_code == 409 and error.value.detail['blocking_checks']
    with operator_context(Operator('editor', 'editor')):
        with pytest.raises(HTTPException) as error:
            command(store, service.patch_check, identity, gate_id, ChecklistPatch(expected_revision=4,
                                                                                 completed=True, proof='IA'))
        assert error.value.status_code == 403
    with operator_context(Operator('verifier-login', 'editor', person_id=store[1]['person'])):
        command(store, service.patch_check, identity, gate_id, ChecklistPatch(expected_revision=4,
                                                                            completed=True, proof='Lecture du fichier'))
        result = command(store, service.transition, identity, DocumentTransition(expected_revision=5, status='validated',
            version_id=version['version_id'], comment='Vérifié le 5 octobre'))
    assert result['document_status'] == 'validated' and result['revision'] == 6
    with pytest.raises(HTTPException, match='Rouvrir'):
        command(store, service.patch_check, identity, gate_id, ChecklistPatch(expected_revision=6, completed=False))


def test_new_version_and_reopening_invalidate_visa_preserve_old_version(store):
    identity, gate_id = create(store)
    v1 = publish(store, identity)
    command(store, service.patch_check, identity, gate_id, ChecklistPatch(expected_revision=3, completed=True, proof='Visa v1'))
    command(store, service.transition, identity, DocumentTransition(expected_revision=4, status='to_verify', version_id=v1['version_id']))
    command(store, service.transition, identity, DocumentTransition(expected_revision=5, status='validated', version_id=v1['version_id'], comment='OK v1'))
    v2 = publish(store, identity, name='document-v2.md', content='Contenu v2')
    with store[0]() as db:
        value = service.read_deliverable(db, store[1]['project'], identity)
        assert value['document_status'] == 'draft' and value['checklist'][0]['completed_version_id'] is None
        old = db.get(DeliverableFileVersion, v1['version_id'])
        assert file_digest(old.path)['sha256'] == v1['sha256']
        assert old.number == 1 and json.loads(old.manifest)['reference'] == 'AF-001'
    with pytest.raises(HTTPException, match='dernière version'):
        command(store, service.transition, identity, DocumentTransition(expected_revision=v2['revision'], status='to_verify', version_id=v1['version_id']))


def test_in_place_file_modification_is_refused_without_losing_version_or_history(store):
    identity, _ = create(store)
    v1 = publish(store, identity)
    document = store[2].parent / 'document-v1.md'
    document.write_text('Modified externally', encoding='utf-8')
    before = capture_baseline(store[2])
    with pytest.raises(HTTPException, match='Fichier modifié'):
        command(store, service.transition, identity, DocumentTransition(expected_revision=3, status='to_verify', version_id=v1['version_id']))
    assert capture_baseline(store[2]) == before


def test_editable_metadata_never_rewrites_published_manifest_or_file(store):
    identity, _ = create(store)
    v1 = publish(store, identity)
    with store[0]() as db:
        original = db.get(DeliverableFileVersion, v1['version_id'])
        frozen = original.manifest, original.manifest_sha256, original.sha256
    command(store, service.patch_version_metadata, identity, v1['version_id'], VersionMetadataPatch(
        expected_revision=3, reference='AF-001-reclassé', comment='Classement corrigé'))
    with store[0]() as db:
        original = db.get(DeliverableFileVersion, v1['version_id'])
        assert (original.manifest, original.manifest_sha256, original.sha256) == frozen
        assert db.get(DeliverableVersionMetadata, v1['version_id']).reference == 'AF-001-reclassé'
        event = db.query(DeliverableEvent).filter_by(action='deliverable_version_metadata_changed').one()
        assert event.previous['reference'] == 'AF-001' and event.value['reference'] == 'AF-001-reclassé'


def test_cdc_link_keeps_original_identity_and_file_without_duplicate_generation(store):
    factory, ids, path, *_ = store
    identity, _ = create(store)
    content = path.parent / 'cdc-original.md'
    content.write_text('Transfert BE CDC conservé', encoding='utf-8')
    with transaction(factory) as db:
        source = DeliveryVersion(project_id=ids['project'], version=1, path=str(content),
                                 sha256=file_digest(content)['sha256'], snapshot={'items': [{'id': 'source-item'}]})
        db.add(source)
        db.flush()
        source_id = source.id
    before = capture_baseline(path)
    with transaction(factory) as db:
        version = service.publish_file(db, ids['project'], identity, FilePublication(
            expected_revision=2, reference='BE-001', source_delivery_id=source_id), path=content)
    # Publishing intentionally increments the shared planning revision. Only
    # the original CDC rows/files must remain byte-for-byte unchanged here.
    assert capture_baseline(path)['tables']['delivery_versions'] == before['tables']['delivery_versions']
    with factory() as db:
        row = db.get(DeliverableFileVersion, version['version_id'])
        assert row.source_delivery_id == source_id and row.generated is True and row.path == str(content.resolve())
        assert db.query(DeliveryVersion).count() == 1
    with pytest.raises(HTTPException, match='déjà reliée'):
        with transaction(factory) as db:
            service.publish_file(db, ids['project'], identity, FilePublication(
                expected_revision=3, reference='BE-002', source_delivery_id=source_id), path=content)


def test_progress_separates_transverse_and_ignores_inactive_and_noncontributing_items():
    values = [{'active': True, 'contributes': True, 'transverse': False, 'completed': True},
              {'active': True, 'contributes': True, 'transverse': False, 'completed': False},
              {'active': True, 'contributes': True, 'transverse': True, 'completed': True},
              {'active': False, 'contributes': True, 'transverse': False, 'completed': True},
              {'active': True, 'contributes': False, 'transverse': False, 'completed': True}]
    assert progress(values) == {'completed': 1, 'total': 2, 'percentage': 50, 'state': 'pending'}
    assert progress(values, transverse=True)['percentage'] == 100


def test_backup_restore_reopens_exact_files_metadata_and_history_on_copy(store):
    identity, _ = create(store)
    v1 = publish(store, identity)
    command(store, service.patch_version_metadata, identity, v1['version_id'], VersionMetadataPatch(expected_revision=3, comment='Commentaire actuel'))
    path = store[2]
    original = capture_baseline(path)
    snapshot = path.parent / 'l3-state.db'
    backup_sqlite(path, snapshot)
    restored = path.parent / 'restored'
    restored.mkdir()
    shutil.copy2(snapshot, restored / 'erp.db')
    shutil.copy2(path.parent / 'document-v1.md', restored / 'document-v1.md')
    assert capture_baseline(restored / 'erp.db') == original
    assert file_digest(restored / 'document-v1.md')['sha256'] == v1['sha256']
    engine = create_engine(f'sqlite:///{restored / "erp.db"}')
    factory = sessionmaker(bind=engine)
    with factory() as db:
        assert db.get(DeliverableVersionMetadata, v1['version_id']).comment == 'Commentaire actuel'
        assert db.query(DeliverableEvent).count() == 4
    engine.dispose()


def test_schema_rejects_privilege_money_and_duplicate_codes():
    from pydantic import ValidationError
    for values in ({'actor_id': 'owner'}, {'hourly_rate': 85}, {'margin_pct': 20}):
        with pytest.raises(ValidationError):
            DeliverableCreate(expected_revision=0, title='AF', **values)
    with pytest.raises(ValidationError, match='dupliqués'):
        TypeDefinition(checklist=[{'code': 'x', 'label': 'A'}, {'code': 'x', 'label': 'B'}])
    payload, sha = frozen_json({'a': 1, 'é': 'texte'})
    assert payload == '{"a":1,"é":"texte"}' and len(sha) == 64


def test_metadata_patch_adopts_legacy_without_changing_historical_status(store):
    factory, ids, *_ = store
    command(store, service.patch_deliverable, ids['legacy'], DeliverablePatch(expected_revision=0, comment='Complément L3'))
    with factory() as db:
        assert db.get(Deliverable, ids['legacy']).status == 'done'
        assert db.get(DeliverablePlan, ids['legacy']).document_status == 'draft'


def test_gate_cannot_be_disabled_and_missing_verifier_blocks_submission(store):
    identity, gate_id = create(store)
    version = publish(store, identity)
    with pytest.raises(HTTPException, match='désactivé'):
        command(store, service.patch_check, identity, gate_id, ChecklistPatch(expected_revision=3, active=False))
    command(store, service.patch_deliverable, identity, DeliverablePatch(expected_revision=3, verifier_id=None))
    with pytest.raises(HTTPException, match='Désigner'):
        command(store, service.transition, identity, DocumentTransition(expected_revision=4, status='to_verify',
                                                                       version_id=version['version_id']))


def test_human_proof_is_required_and_reopening_invalidates_prior_visa(store):
    identity, gate_id = create(store)
    version = publish(store, identity)
    with pytest.raises(HTTPException, match='preuve humaine'):
        command(store, service.patch_check, identity, gate_id, ChecklistPatch(expected_revision=3, completed=True))
    command(store, service.patch_check, identity, gate_id, ChecklistPatch(expected_revision=3, completed=True, proof='Contrôlé'))
    command(store, service.transition, identity, DocumentTransition(expected_revision=4, status='to_verify', version_id=version['version_id']))
    command(store, service.transition, identity, DocumentTransition(expected_revision=5, status='validated', version_id=version['version_id'], comment='Visa'))
    command(store, service.transition, identity, DocumentTransition(expected_revision=6, status='to_revise', version_id=version['version_id']))
    with store[0]() as db:
        assert not service.read_deliverable(db, store[1]['project'], identity)['checklist'][0]['completed']


def test_editing_gate_proof_invalidates_completion_until_explicit_new_visa(store):
    identity, gate_id = create(store)
    version = publish(store, identity)
    command(store, service.patch_check, identity, gate_id, ChecklistPatch(expected_revision=3, completed=True, proof='Contrôlé'))
    command(store, service.patch_check, identity, gate_id, ChecklistPatch(expected_revision=4, proof=''))
    with store[0]() as db:
        check = service.read_deliverable(db, store[1]['project'], identity)['checklist'][0]
        assert not check['completed'] and check['completed_version_id'] is None
    command(store, service.transition, identity, DocumentTransition(expected_revision=5, status='to_verify', version_id=version['version_id']))
    with pytest.raises(HTTPException) as error:
        command(store, service.transition, identity, DocumentTransition(expected_revision=6, status='validated',
            version_id=version['version_id'], comment='Visa'))
    assert error.value.status_code == 409


def test_foreign_cdc_and_version_metadata_cannot_be_attached_or_modified(store):
    factory, ids, path, *_ = store
    identity, _ = create(store)
    document = path.parent / 'other-project.md'
    document.write_text('Autre projet', encoding='utf-8')
    with transaction(factory) as db:
        source = DeliveryVersion(project_id=ids['foreign'], version=1, path=str(document),
                                 sha256=file_digest(document)['sha256'])
        db.add(source)
        db.flush()
        source_id = source.id
    with pytest.raises(HTTPException, match='absente de ce projet'):
        with transaction(factory) as db:
            service.publish_file(db, ids['project'], identity, FilePublication(expected_revision=2,
                reference='Autre', source_delivery_id=source_id), path=document)
    v1 = publish(store, identity)
    second, _ = create(store, with_gate=False)
    with pytest.raises(HTTPException) as error:
        command(store, service.patch_version_metadata, second, v1['version_id'], VersionMetadataPatch(
            expected_revision=4, comment='Interdit'))
    assert error.value.status_code == 404


def test_type_publication_conflict_and_scoped_owner_refuse_global_edit(store):
    factory, ids, *_ = store
    with transaction(factory) as db:
        reference = service.create_type(db, TypeCreate(code='ar', label='AR', definition=TypeDefinition()))
    with pytest.raises(HTTPException) as error:
        with transaction(factory) as db:
            service.publish_type(db, reference['id'], TypePublish(expected_revision=0, definition=TypeDefinition()))
    assert error.value.status_code == 409
    with operator_context(Operator('scoped', 'owner', frozenset([ids['project']]))):
        with pytest.raises(HTTPException) as error:
            with transaction(factory) as db:
                service.create_type(db, TypeCreate(code='calcul', label='Calcul', definition=TypeDefinition()))
        assert error.value.status_code == 403


def test_file_unavailable_keeps_previous_version_and_large_file_is_bounded(store):
    from backend.app.services.project_deliverable_rules import MAX_FILE_BYTES
    identity, _ = create(store)
    version = publish(store, identity)
    (store[2].parent / 'document-v1.md').rename(store[2].parent / 'temporarily-unavailable.md')
    with pytest.raises(HTTPException, match='indisponible'):
        command(store, service.transition, identity, DocumentTransition(expected_revision=3, status='to_verify', version_id=version['version_id']))
    with store[0]() as db:
        assert db.get(DeliverableFileVersion, version['version_id']) is not None
    large = store[2].parent / 'large.bin'
    with large.open('wb') as stream:
        stream.truncate(MAX_FILE_BYTES + 1)
    with pytest.raises(HTTPException) as error:
        file_digest(large)
    assert error.value.status_code == 422


def test_project_row_collection_keeps_l3_records_for_typed_transport_without_writes(store):
    from backend.app.services.project_archive import _rows
    identity, gate = create(store)
    before = capture_baseline(store[2])
    with store[0]() as db:
        rows = _rows(db, Base.metadata, store[1]['project'])
        assert rows['project_deliverable_plans'][0]['deliverable_id'] == identity
        assert rows['project_deliverable_checklist'][0]['id'] == gate
        assert len(rows['project_deliverable_events']) == 2
    assert capture_baseline(store[2]) == before
