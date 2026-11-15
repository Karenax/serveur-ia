"""V5 transport on fictional stores: bytes, frozen evidence, CAS history and legacy."""
import base64
from copy import deepcopy
import hashlib
from pathlib import Path
import shutil
import sqlite3
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.db_support import backup_sqlite
from app.services import deliverable_manifest as manifest
from app.services.backup import create_backup, restore_backup
from app.models import Project as BrainProject, Proposal, Source, SourceArtifact
from backend.app.db import Base
from backend.app.models import DeliveryVersion, Project
from backend.app.project_deliverable_models import (
    DeliverableFileVersion, DeliverablePlan, DeliverableType, DeliverableVersionMetadata,
)
from backend.app.project_deliverable_schemas import DeliverableCreate, FilePublication
from backend.app.project_planning_models import PlanningBaseline
from backend.app.services import project_archive as archive, project_deliverable_archive as contract
from backend.app.services import project_deliverables as service
from backend.app.services.migration_guard import capture_baseline
from backend.app.services.planning_revision import revision
from backend.app.services.project_deliverable_migration import install_deliverable_schema
from backend.app.services.project_planning_migration import install_planning_schema
from tests.test_project_deliverable_archive_contract import envelope, store
from tests.test_project_deliverable_archive_store import target
from tests import test_project_planning_archive as planning_fixtures
from tests.test_project_deliverables import transaction

__all__ = ['envelope', 'store', 'target', 'stores']
stores = planning_fixtures.stores


@pytest.fixture
def transport(envelope, store, target, tmp_path, monkeypatch):
    import app.db
    import backend.app.db
    source_root, target_root = tmp_path / 'source-files', tmp_path / 'target-files'
    monkeypatch.setattr(backend.app.db, 'APP_DIR', source_root)
    brain_engine = create_engine(f'sqlite:///{tmp_path / "empty-brain.db"}')
    monkeypatch.setattr(app.db, 'SessionLocal', sessionmaker(bind=brain_engine))
    for name, factory, database in (('source', store[0], store[2]), ('target', target[0], target[1])):
        install_planning_schema(factory.kw['bind'], backup=lambda p=database, n=name:
            backup_sqlite(p, tmp_path / (n + '-before-planning-triggers.db')))
    with transaction(store[0]) as db:
        versions = db.query(DeliverableFileVersion).all()
        for row in versions:
            if row.source_delivery_id:
                path = source_root / 'exports' / row.project_id / (row.source_delivery_id + '.md')
                db.get(DeliveryVersion, row.source_delivery_id).path = str(path)
            else:
                path = source_root / 'deliverables' / row.project_id / (row.id + '.md')
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(row.path, path)
            db.get(DeliverableVersionMetadata, row.id).storage_path = str(path)
    before = capture_baseline(store[2])
    with store[0]() as db:
        data = archive.export_archive(db, envelope['ids']['project'])
    assert data['version'] == 5 and capture_baseline(store[2]) == before
    monkeypatch.setattr(backend.app.db, 'APP_DIR', target_root)
    yield data, source_root, target_root
    brain_engine.dispose()


def restore(factory, data, code='IMPORTED-0205'):
    with transaction(factory) as db:
        return archive.import_archive(db, data, code=code)


def test_v5_roundtrip_keeps_checklists_visa_bytes_original_paths_and_shared_history(transport, envelope, store, target):
    data, source_root, target_root = transport
    original = deepcopy(data)
    source_before = capture_baseline(store[2])
    assert len(data['files']) == 3 and {row['area'] for row in data['files']} == {'delivery', 'deliverable'}
    result = restore(target[0], data)
    assert result['version'] == 5 and data == original and capture_baseline(store[2]) == source_before
    source_by_number = {(row['deliverable_id'], row['number']): row for row in data['tables']['project_deliverable_file_versions']}
    with target[0]() as db:
        versions = db.query(DeliverableFileVersion).all()
        assert len(versions) == 3
        for row in versions:
            snapshot = manifest.check_row({key: getattr(row, key) for key in ('manifest', 'manifest_sha256', 'project_id',
                'deliverable_id', 'number', 'filename', 'sha256', 'size_bytes', 'source_delivery_id', 'generated', 'actor_id')})
            source = snapshot['source_publication']
            source_row = next(item for item in source_by_number.values() if item['id'] == source['version_id'])
            assert source['manifest'] == source_row['manifest'] and source['manifest_sha256'] == source_row['manifest_sha256']
            assert row.path == source_row['path'] and row.filename == source_row['filename']
            metadata = db.get(DeliverableVersionMetadata, row.id)
            assert Path(metadata.storage_path).is_relative_to(target_root)
            assert hashlib.sha256(Path(metadata.storage_path).read_bytes()).hexdigest() == row.sha256
            service._verify_file(db, row)
            if row.source_delivery_id:
                assert metadata.storage_path == db.get(DeliveryVersion, row.source_delivery_id).path
        plan = db.query(DeliverablePlan).filter_by(document_status='validated').one()
        view = service.read_deliverable(db, result['id'], plan.deliverable_id)
        assert view['checklist'][0]['proof'] == envelope['ids']['deliverable']
        assert view['checklist'][0]['label'] == envelope['ids']['project'] and not view['validation_blockers']
        assert db.execute(text('PRAGMA foreign_key_check')).all() == []
        assert len(db.execute(text("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_project_deliverable_%_immutable'")).all()) == 6
        second = archive.export_archive(db, result['id'])
    assert second['version'] == 5
    assert len(second['tables']['project_planning_changes']) == len(data['tables']['project_planning_changes'])
    for row in second['tables']['project_deliverable_file_versions']:
        assert manifest.check_row(row)['source_publication']['version_id'] in {item['id'] for item in data['tables']['project_deliverable_file_versions']}
    assert source_root.exists()


def test_same_store_import_reuses_exact_catalogue_without_duplicate_versions_or_global_history(transport, envelope, store):
    data, *_ = transport
    with store[0]() as db:
        counts = {name: db.execute(select(Base.metadata.tables[name])).all() for name in contract.REFERENCE_TABLES}
    result = restore(store[0], data)
    assert result['id'] != envelope['ids']['project']
    with store[0]() as db:
        assert all(db.execute(select(Base.metadata.tables[name])).all() == rows for name, rows in counts.items())
        assert db.query(Project).count() == 3


def test_imported_v5_files_and_visas_survive_global_backup_restore_on_new_copy(transport, target, tmp_path):
    data, _, target_root = transport
    result = restore(target[0], data)
    before = capture_baseline(target[1])
    backup_sqlite(target[1], target_root / 'minipilot.db')
    brain, storage = tmp_path / 'backup-brain.db', tmp_path / 'storage'
    storage.mkdir()
    with sqlite3.connect(brain) as db:
        db.execute('CREATE TABLE sources (id TEXT PRIMARY KEY, sha256 TEXT, original_uri TEXT, source_metadata TEXT)')
    backup = tmp_path / 'global-backup'
    saved = create_backup(backup, brain, target_root, storage)
    assert len(saved['deliverable_files']) == 3
    destination = tmp_path / 'global-restored'
    restore_backup(backup, destination)
    engine = create_engine(f'sqlite:///{destination / "erp/minipilot.db"}')
    try:
        with sessionmaker(bind=engine)() as db:
            for row in db.query(DeliverableFileVersion):
                assert Path(service.version_file_path(db, row)).is_relative_to(destination)
                service._verify_file(db, row)
            assert db.query(DeliverablePlan).filter_by(project_id=result['id'], document_status='validated').one()
            assert not db.execute(text('PRAGMA foreign_key_check')).all()
        with sqlite3.connect(destination / 'erp/minipilot.db') as db:
            for table in ('project_deliverable_type_versions', 'project_deliverable_file_versions', 'project_deliverable_events'):
                for statement in (f'UPDATE {table} SET id=id', f'DELETE FROM {table}'):
                    with pytest.raises(sqlite3.IntegrityError, match='immutable'):
                        db.execute(statement)
    finally:
        engine.dispose()
    assert capture_baseline(target[1]) == before


def test_explicit_l3_startup_installs_protected_schema_without_repeat_backup_or_seed(tmp_path, monkeypatch):
    import backend.app.db
    path = tmp_path / 'legacy-startup.db'
    engine = create_engine(f'sqlite:///{path}')
    monkeypatch.setattr(backend.app.db, 'engine', engine)
    monkeypatch.setattr(backend.app.db, 'APP_DIR', tmp_path)
    monkeypatch.setattr(backend.app.db, 'DB_PATH', path)
    try:
        backend.app.db.init_db()
        with engine.connect() as db:
            assert len(db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'project_deliverable_%'")).all()) == 9
            assert len(db.execute(text("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_project_deliverable_%_immutable'")).all()) == 6
            assert db.execute(text('SELECT count(*) FROM project_deliverable_types')).scalar_one() == 0
        before = capture_baseline(path)
        backups_before = list((tmp_path / 'backups').glob('*.db'))
        backend.app.db.init_db()
        assert capture_baseline(path) == before
        assert list((tmp_path / 'backups').glob('*.db')) == backups_before
    finally:
        engine.dispose()


@pytest.mark.parametrize('case', ['missing_globals', 'missing_type', 'missing_file', 'duplicate_file', 'unknown_area',
                                  'wrong_bytes_rehashed', 'wrong_delivery_rehashed', 'wrong_metadata', 'changed_fixed_check',
                                  'bad_shared_event', 'unknown_event', 'malformed_events', 'bad_origin', 'global_in_tables'])
def test_invalid_v5_refused_before_destination_files_or_project_writes(transport, target, case):
    data, _, target_root = transport
    value = deepcopy(data)
    if case == 'missing_globals':
        del value['deliverable_references']
    elif case == 'missing_type':
        value['deliverable_references']['project_deliverable_types'].pop()
    elif case == 'missing_file':
        value['files'].pop()
    elif case == 'duplicate_file':
        value['files'].append(deepcopy(value['files'][0]))
    elif case == 'unknown_area':
        value['files'][0]['area'] = 'network'
    elif case in {'wrong_bytes_rehashed', 'wrong_delivery_rehashed'}:
        piece = next(row for row in value['files'] if row['area'] == ('delivery' if case == 'wrong_delivery_rehashed' else 'deliverable'))
        piece['data'] = base64.b64encode(b'Different bytes').decode('ascii')
        piece['sha256'] = hashlib.sha256(b'Different bytes').hexdigest()
    elif case == 'wrong_metadata':
        value['tables']['project_deliverable_version_metadata'].pop()
    elif case == 'changed_fixed_check':
        value['tables']['project_deliverable_checklist'][0]['is_gate'] = False
    elif case == 'bad_shared_event':
        value['tables']['project_planning_changes'][0]['value']['title'] = 'Différent'
    elif case == 'unknown_event':
        value['tables']['project_planning_changes'][0]['action'] = 'unknown_action'
    elif case == 'malformed_events':
        value['tables']['project_planning_changes'] = 'broken'
    elif case == 'bad_origin':
        value['tables']['project_deliverable_file_versions'][0]['manifest_sha256'] = '0' * 64
    else:
        value['tables']['project_deliverable_types'] = value['deliverable_references']['project_deliverable_types']
    before = capture_baseline(target[1])
    with pytest.raises(HTTPException) as error:
        restore(target[0], value)
    assert error.value.status_code == 400 and capture_baseline(target[1]) == before and not target_root.exists()


@pytest.mark.parametrize('version', [2, 3, 4])
def test_old_envelopes_cannot_silently_import_l3_data(transport, target, version):
    data, _, target_root = transport
    value = deepcopy(data)
    value['version'] = version
    value.pop('deliverable_references')
    before = capture_baseline(target[1])
    with pytest.raises(HTTPException) as error:
        restore(target[0], value)
    assert error.value.status_code == 400 and 'version 5' in error.value.detail
    assert capture_baseline(target[1]) == before and not target_root.exists()


def test_reference_conflict_refused_before_any_file_is_written(transport, target):
    data, _, target_root = transport
    with transaction(target[0]) as db:
        original = data['deliverable_references']['project_deliverable_types'][0]
        db.add(DeliverableType(code=original['code'], label='Different destination'))
    before = capture_baseline(target[1])
    with pytest.raises(HTTPException) as error:
        restore(target[0], data)
    assert error.value.status_code == 409 and capture_baseline(target[1]) == before and not target_root.exists()


def test_composition_only_roundtrip_preserves_absent_planning_state(transport, target):
    data, _, target_root = transport
    value = deepcopy(data)
    value['files'] = []
    for name in contract.PROJECT_TABLES | {'project_planning_states', 'project_planning_changes', 'delivery_versions'}:
        value['tables'][name] = []
    value['references']['project_people'] = []
    result = restore(target[0], value)
    with target[0]() as db:
        assert not db.execute(select(Base.metadata.tables['project_planning_states'])).all()
        actual = archive.export_archive(db, result['id'])
        assert actual['version'] == 5 and not actual['tables'].get('project_planning_states')
    assert not target_root.exists()


@pytest.mark.parametrize('same_store', [False, True])
def test_v5_combines_l2_templates_baselines_and_brain_uuid_namespaces(stores, tmp_path, same_store):
    import backend.app.db
    factories, engines, monkeypatch = stores
    for name in ('source', 'target'):
        path = tmp_path / (name + '.db')
        install_deliverable_schema(engines[name], backup=lambda p=path: backup_sqlite(p, p.with_suffix('.l3-backup.db')))
    _, ids = planning_fixtures.build(stores, with_brain=True)
    root = tmp_path / 'source-files'
    monkeypatch.setattr(backend.app.db, 'APP_DIR', root)
    path = root / 'deliverables' / 'note.md'
    path.parent.mkdir(parents=True)
    path.write_text('Note validable', encoding='utf-8')
    with transaction(factories['source']) as db:
        created = service.create_deliverable(db, ids['project_id'], DeliverableCreate(
            expected_revision=revision(db, ids['project_id']), title=ids['task_id']))
        service.publish_file(db, ids['project_id'], created['id'], FilePublication(
            expected_revision=revision(db, ids['project_id']), reference='NOTE-001'), path=path)
    with factories['source']() as db:
        data = archive.export_archive(db, ids['project_id'])
    assert data['version'] == 5 and len(data['planning_references']['project_planning_templates']) == 2
    monkeypatch.setattr(backend.app.db, 'APP_DIR', tmp_path / 'target-files')
    result = planning_fixtures.restore(stores, data, same_store=same_store)
    with factories['source' if same_store else 'target']() as db:
        actual = archive.export_archive(db, result['id'])
        baseline = db.query(PlanningBaseline).filter_by(project_id=result['id']).one()
        assert baseline.sha256 != ids['baseline']['sha256']
        assert db.execute(text('PRAGMA foreign_key_check')).all() == []
        moved = next(row for row in actual['tables']['milestones'] if row['date_sources'].get('contractual_date'))
        source_id = actual['brain']['sources'][0]['id']
        assert moved['date_sources']['contractual_date']['source_id'] == source_id
        assert actual['tables']['project_planning_changes'][-1]['action'] in {'deliverable_created', 'deliverable_version_published',
                                                                              'task_changed', 'baseline_created', 'template_applied'}


@pytest.mark.parametrize('version', [3, 4, 5])
def test_archives_include_only_referenced_inbox_mail_parents_and_preserve_unclassified_status(stores, tmp_path, version):
    factories, engines, monkeypatch = stores
    _, ids = planning_fixtures.build(stores, with_brain=True)
    with transaction(factories['source_brain']) as db:
        mail = Source(project_id=None, source_type='eml', status='unresolved', original_uri='', sha256='a' * 64)
        unrelated = Source(project_id=None, source_type='eml', status='unresolved', original_uri='', sha256='b' * 64)
        db.add_all([mail, unrelated])
        db.flush()
        source_id, unrelated_id = mail.id, unrelated.id
        db.add(SourceArtifact(source_id=mail.id, kind='body_text', content_text='Texte du mail parent conservé'))
        db.add(Proposal(project_id=ids['project_id'], source_id=mail.id, kind='fact', subject='Proposition liée', value='À relire'))
    with factories['source']() as db:
        data = archive.export_archive(db, ids['project_id'])
    assert source_id in {row['id'] for row in data['brain']['sources']} and unrelated_id not in {row['id'] for row in data['brain']['sources']}
    assert next(row for row in data['brain']['sources'] if row['id'] == source_id)['project_id'] is None
    if version == 3:
        # Keep a genuine v3 payload, with its original project/Brain data and no L2.
        from backend.app.services import project_planning_archive
        data['version'] = 3
        data.pop('planning_references')
        for name in project_planning_archive.PROJECT_TABLES:
            data['tables'].pop(name, None)
        data['references']['project_people'] = []
    elif version == 5:
        for name in ('source', 'target'):
            path = tmp_path / (name + '.db')
            install_deliverable_schema(engines[name], backup=lambda p=path: backup_sqlite(p, p.with_suffix('.inbox-l3.db')))
        data['version'] = 5
        data['deliverable_references'] = {name: [] for name in contract.REFERENCE_TABLES}
    result = planning_fixtures.restore(stores, data)
    with factories['target_brain']() as db:
        proposal = db.query(Proposal).one()
        parent = db.get(Source, proposal.source_id)
        assert parent.project_id is None and parent.status == 'unresolved'
        assert db.query(SourceArtifact).filter_by(source_id=parent.id).one().content_text == 'Texte du mail parent conservé'
        assert db.get(BrainProject, proposal.project_id)
    assert result['version'] == version


def test_export_refuses_foreign_project_evidence_without_omission_or_source_changes(stores):
    factories, engines, _ = stores
    _, ids = planning_fixtures.build(stores, with_brain=True)
    with transaction(factories['source_brain']) as db:
        other = BrainProject(id=str(uuid.uuid4()), code='FOREIGN', name='Autre projet')
        db.add(other)
        db.flush()
        source = Source(project_id=other.id, source_type='eml', status='resolved', original_uri='', sha256='c' * 64)
        db.add(source)
        db.flush()
        db.add(Proposal(project_id=ids['project_id'], source_id=source.id, kind='fact', subject='Ancienne piste', value='Conservée'))
    before = capture_baseline(Path(engines['source_brain'].url.database))
    with factories['source']() as db, pytest.raises(HTTPException) as error:
        archive.export_archive(db, ids['project_id'])
    assert error.value.status_code == 409 and 'sauvegarde globale' in error.value.detail
    assert capture_baseline(Path(engines['source_brain'].url.database)) == before


def test_injected_unrelated_inbox_source_is_refused_before_import(stores):
    factories, _, _ = stores
    data, _ = planning_fixtures.build(stores, with_brain=True)
    injected = deepcopy(data['brain']['sources'][0])
    injected.update(id=str(uuid.uuid4()), project_id=None)
    data['brain']['sources'].append(injected)
    with pytest.raises(HTTPException) as error:
        planning_fixtures.restore(stores, data)
    assert error.value.status_code == 400 and 'import global interdit' in error.value.detail
    with factories['target']() as db:
        assert not db.query(Project).all()


def test_existing_hash_in_other_brain_refuses_import_before_writing_source_files(stores, tmp_path):
    factories, _, _ = stores
    data, _ = planning_fixtures.build(stores, with_brain=True)
    incoming = data['brain']['sources'][0]
    with transaction(factories['target_brain']) as db:
        other = BrainProject(code='ALREADY-THERE', name='Canonique conservé')
        db.add(other)
        db.flush()
        db.add(Source(project_id=other.id, source_type=incoming['source_type'], status='resolved',
                      original_uri='', sha256=incoming['sha256']))
    # Even a correct incoming raw file must not be written before this conflict.
    content = b'Archived raw data'
    data['files'].append({'area': 'raw', 'owner': incoming['id'], 'name': 'mail.eml',
                          'sha256': hashlib.sha256(content).hexdigest(), 'data': base64.b64encode(content).decode('ascii')})
    before = capture_baseline(Path(factories['target_brain'].kw['bind'].url.database))
    with pytest.raises(HTTPException) as error:
        planning_fixtures.restore(stores, data)
    assert error.value.status_code == 409 and 'cœur canonique' in error.value.detail
    assert not (tmp_path / 'raw').exists()
    assert capture_baseline(Path(factories['target_brain'].kw['bind'].url.database)) == before


def test_archive_size_limit_refuses_complete_file_set_without_database_changes(transport, store, monkeypatch):
    import backend.app.db
    data, source_root, _ = transport
    monkeypatch.setattr(backend.app.db, 'APP_DIR', source_root)
    monkeypatch.setattr(archive, 'MAX_ARCHIVE_BYTES', 1)
    before = capture_baseline(store[2])
    with store[0]() as db, pytest.raises(HTTPException) as error:
        archive.export_archive(db, data['tables']['projects'][0]['id'])
    assert error.value.status_code == 413 and 'sauvegarde globale' in error.value.detail
    assert capture_baseline(store[2]) == before
