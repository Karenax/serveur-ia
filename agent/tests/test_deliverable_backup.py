"""Portable global L3 backups on fictional stores; never edit original evidence."""
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db_support import backup_sqlite
from app.services.backup import create_backup, restore_backup
from backend.app.models import DeliveryVersion
from backend.app.project_deliverable_models import DeliverableFileVersion, IMMUTABLE_TABLES
from backend.app.project_deliverable_schemas import (
    ChecklistPatch, DocumentTransition, FilePublication, TypeCreate, TypeDefinition,
)
from backend.app.services import project_deliverables as service
from backend.app.services.migration_guard import capture_baseline, compare_baseline
from backend.app.services.planning_revision import revision
from backend.app.services.project_deliverable_migration import install_deliverable_schema
from tests import test_project_deliverables as fixtures
from tests.test_project_deliverables import transaction

store = fixtures.store


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def managed(store, tmp_path):
    erp, storage, brain = tmp_path / 'managed', tmp_path / 'storage', tmp_path / 'brain.db'
    erp.mkdir()
    storage.mkdir()
    with sqlite3.connect(brain) as db:
        db.execute('CREATE TABLE sources (id TEXT PRIMARY KEY, sha256 TEXT, original_uri TEXT, source_metadata TEXT)')
    with transaction(store[0]) as db:
        service.create_type(db, TypeCreate(code='recovery', label='Type conservé', definition=TypeDefinition()))
    versions, identities, paths = [], [], []
    locations = [erp / 'deliverables/document.md', erp / 'exports/document.md', storage / 'documents/document.md']
    for index, path in enumerate(locations):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'Pièce indépendante {index}', encoding='utf-8')
        identity, gate = fixtures.create(store, with_gate=index == 0)
        identities.append(identity)
        paths.append(path)
        with transaction(store[0]) as db:
            source_id = None
            if index == 1:
                source = DeliveryVersion(project_id=store[1]['project'], version=1, path=str(path), sha256=sha(path))
                db.add(source)
                db.flush()
                source_id = source.id
            version = service.publish_file(db, store[1]['project'], identity, FilePublication(
                expected_revision=revision(db, store[1]['project']), reference=f'REF-{index}',
                comment=f'Commentaire {index}', source_delivery_id=source_id), path=path)
            versions.append(version['version_id'])
        if index == 0:
            with transaction(store[0]) as db:
                project = store[1]['project']
                service.patch_check(db, project, identity, gate, ChecklistPatch(
                    expected_revision=revision(db, project), completed=True, proof='Fichier lu et vérifié'))
                service.transition(db, project, identity, DocumentTransition(
                    expected_revision=revision(db, project), status='to_verify', version_id=versions[-1]))
                service.transition(db, project, identity, DocumentTransition(
                    expected_revision=revision(db, project), status='validated', version_id=versions[-1], comment='Visa humain'))
    backup_sqlite(store[2], erp / 'minipilot.db')
    return {'erp': erp, 'storage': storage, 'brain': brain, 'versions': versions,
            'identities': identities, 'paths': paths, 'project': store[1]['project']}


def snapshot(managed, tmp_path):
    backup = tmp_path / 'snapshot'
    manifest = create_backup(backup, managed['brain'], managed['erp'], managed['storage'])
    return backup, manifest


def read_rows(path, table):
    with sqlite3.connect(path) as db:
        return db.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall()


def test_relocation_preserves_versions_manifests_visa_history_and_cdc_link(managed, tmp_path):
    source_db = managed['erp'] / 'minipilot.db'
    original = capture_baseline(source_db)
    backup, manifest = snapshot(managed, tmp_path)
    saved_db_sha, saved_manifest_sha = sha(backup / 'erp/minipilot.db'), sha(backup / 'backup.json')
    assert set(manifest['deliverable_files']) == set(managed['versions'])
    assert {row['area'] for row in manifest['deliverable_files'].values()} == {'erp', 'storage'}
    destination = tmp_path / 'new-location'
    restore_backup(backup, destination)
    restored_db = destination / 'erp/minipilot.db'
    for table in IMMUTABLE_TABLES:
        assert read_rows(source_db, table) == read_rows(restored_db, table)
    for table in ('project_deliverable_checklist', 'project_deliverable_plans', 'project_planning_changes'):
        assert read_rows(source_db, table) == read_rows(restored_db, table)
    assert capture_baseline(source_db) == original
    assert sha(backup / 'erp/minipilot.db') == saved_db_sha and sha(backup / 'backup.json') == saved_manifest_sha
    # All originals become unavailable; restored service must use its own files.
    for path in managed['paths']:
        path.rename(path.with_suffix('.unavailable'))
    engine = create_engine(f'sqlite:///{restored_db}')
    with sessionmaker(bind=engine)() as db:
        for index, identity in enumerate(managed['versions']):
            version = db.get(DeliverableFileVersion, identity)
            path = Path(service.version_file_path(db, version))
            assert path.is_relative_to(destination) and path.is_file()
            assert version.path == str(managed['paths'][index])
            assert service._verify_file(db, version)['sha256'] == version.sha256
            metadata = db.get(service.DeliverableVersionMetadata, identity)
            assert metadata.reference == f'REF-{index}' and metadata.comment == f'Commentaire {index}'
        assert service.read_deliverable(db, managed['project'], managed['identities'][0])['document_status'] == 'validated'
        linked = db.get(DeliverableFileVersion, managed['versions'][1])
        assert service.version_file_path(db, linked) == db.get(DeliveryVersion, linked.source_delivery_id).path
    engine.dispose()
    with sqlite3.connect(restored_db) as db:
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
        assert len(db.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_project_deliverable_%'").fetchall()) == 6
        for table in IMMUTABLE_TABLES:
            assert db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] > 0
            for statement in (f'DELETE FROM {table}', f'UPDATE {table} SET id=id'):
                with pytest.raises(sqlite3.IntegrityError, match='immutable'):
                    db.execute(statement)
    # The restored result can itself be backed up and restored without old roots.
    again = tmp_path / 'snapshot-again'
    create_backup(again, destination / 'brain/project_brain.db', destination / 'erp', destination / 'storage')
    restore_backup(again, tmp_path / 'restored-again')


@pytest.mark.parametrize('field,value', [
    ('name', '../escape.md'), ('name', 'documents/../notice.md'), ('name', 'C:/outside.md'),
    ('name', 'documents\\notice.md'), ('name', './notice.md'), ('area', 'brain'), ('area', []),
    ('project_id', 'foreign'), ('size_bytes', 0), ('sha256', '0' * 64), ('extra', True),
])
def test_invalid_binding_is_rejected_before_destination_exists(managed, tmp_path, field, value):
    backup, manifest = snapshot(managed, tmp_path)
    manifest['deliverable_files'][managed['versions'][0]][field] = value
    (backup / 'backup.json').write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError):
        restore_backup(backup, tmp_path / 'rejected')
    assert not (tmp_path / 'rejected').exists()


@pytest.mark.parametrize('change', ['missing_binding', 'unknown_binding', 'corrupt_file', 'missing_file', 'omitted_file'])
def test_incomplete_backup_cannot_restore_l3_files(managed, tmp_path, change):
    backup, manifest = snapshot(managed, tmp_path)
    key = managed['versions'][0]
    entry = manifest['deliverable_files'][key]
    file = backup / entry['area'] / entry['name']
    if change == 'missing_binding':
        del manifest['deliverable_files'][key]
    elif change == 'unknown_binding':
        manifest['deliverable_files']['unknown'] = entry
    elif change == 'corrupt_file':
        file.write_text('Altération', encoding='utf-8')
    elif change == 'missing_file':
        file.rename(file.with_suffix('.missing'))
    else:
        del manifest['files'][entry['area'] + '/' + entry['name']]
    (backup / 'backup.json').write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises((ValueError, FileNotFoundError)):
        restore_backup(backup, tmp_path / 'rejected')
    assert not (tmp_path / 'rejected').exists()


@pytest.mark.parametrize('name', [
    '../snapshot/erp/deliverables/document.md', 'erp/../erp/deliverables/document.md',
    'erp//deliverables/document.md', './erp/deliverables/document.md',
    'erp\\deliverables\\document.md', 'absolute',
])
def test_all_manifest_paths_are_canonical_and_cannot_write_outside_destination(managed, tmp_path, name):
    backup, manifest = snapshot(managed, tmp_path)
    path = backup / 'erp/deliverables/document.md'
    if name == 'absolute':
        name = str(path)
    manifest['files'][name] = sha(path)
    saved_sha = sha(path)
    (backup / 'backup.json').write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='Chemin'):
        restore_backup(backup, tmp_path / 'rejected')
    assert not (tmp_path / 'rejected').exists()
    assert sha(path) == saved_sha


@pytest.mark.parametrize('kind', ['list', 'null', 'digest_object', 'envelope_list'])
def test_malformed_global_manifest_has_controlled_error_without_creating_output(managed, tmp_path, kind):
    backup, manifest = snapshot(managed, tmp_path)
    if kind == 'envelope_list':
        manifest = []
    elif kind == 'digest_object':
        manifest['files']['erp/minipilot.db'] = {'sha256': manifest['files']['erp/minipilot.db']}
    else:
        manifest['files'] = [] if kind == 'list' else None
    (backup / 'backup.json').write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError):
        restore_backup(backup, tmp_path / 'rejected')
    assert not (tmp_path / 'rejected').exists()


@pytest.mark.parametrize('change', ['missing', 'modified', 'outside_managed', 'missing_metadata', 'wrong_project'])
def test_invalid_live_file_or_metadata_refuses_backup_without_source_changes(managed, tmp_path, change):
    path = managed['paths'][0]
    if change == 'missing':
        path.rename(path.with_suffix('.missing'))
    elif change == 'modified':
        path.write_text('Version altérée', encoding='utf-8')
    elif change == 'outside_managed':
        outside = tmp_path / 'external.md'
        outside.write_bytes(path.read_bytes())
        with sqlite3.connect(managed['erp'] / 'minipilot.db') as db:
            db.execute('UPDATE project_deliverable_version_metadata SET storage_path=? WHERE version_id=?',
                       (str(outside), managed['versions'][0]))
    else:
        with sqlite3.connect(managed['erp'] / 'minipilot.db') as db:
            if change == 'missing_metadata':
                db.execute('DELETE FROM project_deliverable_version_metadata WHERE version_id=?', (managed['versions'][0],))
            else:
                db.execute("UPDATE project_deliverable_version_metadata SET project_id='foreign' WHERE version_id=?",
                           (managed['versions'][0],))
    before = capture_baseline(managed['erp'] / 'minipilot.db')
    with pytest.raises(ValueError):
        snapshot(managed, tmp_path)
    assert capture_baseline(managed['erp'] / 'minipilot.db') == before
    assert not (tmp_path / 'snapshot/backup.json').exists()


def test_file_changed_during_copy_never_produces_complete_backup(managed, tmp_path, monkeypatch):
    from app.services import backup as service_backup
    original_copy = service_backup.shutil.copy2
    def altered_copy(source, target):
        value = original_copy(source, target)
        if Path(source) == managed['paths'][0]:
            Path(target).write_text('Altération après copie', encoding='utf-8')
        return value
    monkeypatch.setattr(service_backup.shutil, 'copy2', altered_copy)
    original_db = capture_baseline(managed['erp'] / 'minipilot.db')
    original_file_sha = sha(managed['paths'][0])
    with pytest.raises(ValueError, match='incohérent'):
        snapshot(managed, tmp_path)
    assert not (tmp_path / 'snapshot/backup.json').exists()
    assert sha(managed['paths'][0]) == original_file_sha
    assert capture_baseline(managed['erp'] / 'minipilot.db') == original_db


def test_old_offline_snapshot_resolves_exact_hashes_and_adds_only_portable_column(managed, tmp_path):
    with sqlite3.connect(managed['erp'] / 'minipilot.db') as db:
        db.execute('ALTER TABLE project_deliverable_version_metadata DROP COLUMN storage_path')
    backup, manifest = snapshot(managed, tmp_path)
    del manifest['deliverable_files']
    (backup / 'backup.json').write_text(json.dumps(manifest), encoding='utf-8')
    before = capture_baseline(backup / 'erp/minipilot.db')
    restored = tmp_path / 'legacy-restored'
    restore_backup(backup, restored)
    after = capture_baseline(restored / 'erp/minipilot.db')
    # Only CDC DeliveryVersion.path is expected to move among existing columns.
    after['tables']['delivery_versions'] = before['tables']['delivery_versions']
    assert compare_baseline(before, after)['preserved']
    assert capture_baseline(backup / 'erp/minipilot.db') == before
    engine = create_engine(f'sqlite:///{restored / "erp/minipilot.db"}')
    assert install_deliverable_schema(engine, backup=lambda: pytest.fail('Already upgraded')) == {
        'created_tables': [], 'created_triggers': []}
    engine.dispose()


def test_portable_column_migration_backs_up_before_ddl_and_is_idempotent(managed, tmp_path):
    path = managed['erp'] / 'minipilot.db'
    with sqlite3.connect(path) as db:
        db.execute('ALTER TABLE project_deliverable_version_metadata DROP COLUMN storage_path')
    before = capture_baseline(path)
    engine = create_engine(f'sqlite:///{path}')
    def fail_backup():
        raise RuntimeError('backup failed')
    with pytest.raises(RuntimeError, match='backup failed'):
        install_deliverable_schema(engine, backup=fail_backup)
    assert capture_baseline(path) == before
    saved = tmp_path / 'before-portable.db'
    installed = install_deliverable_schema(engine, backup=lambda: backup_sqlite(path, saved))
    assert installed == {'created_tables': [], 'created_triggers': [],
                         'added_columns': ['project_deliverable_version_metadata.storage_path']}
    assert capture_baseline(saved) == before
    assert compare_baseline(before, capture_baseline(path))['preserved']
    assert install_deliverable_schema(engine, backup=lambda: pytest.fail('Repeated backup')) == {
        'created_tables': [], 'created_triggers': []}
    engine.dispose()
