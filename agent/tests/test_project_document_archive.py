"""Actual v7 paired transport and global restore on fictional stores only."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from app.db import Base as BrainBase
from app.db_support import backup_sqlite, configure_sqlite
from app.models import Project as BrainProject
from app.services.backup import create_backup, restore_backup
from backend.app.db import Base
from backend.app.models import NetworkLink, Project
from backend.app.project_document_models import DOCUMENT_FORM_TABLES, DocumentDraftVersion
from backend.app.project_review_models import ReviewPublication
from backend.app.services import document_forms as forms, project_archive as archive
from backend.app.services.migration_guard import capture_baseline, compare_baseline
from backend.app.services.project_document_migration import install_document_schema
from backend.app.services.project_identity_migration import install_identity_schema
from backend.app.services.project_planning_migration import install_planning_schema
from backend.app.services.project_deliverable_migration import install_deliverable_schema
from backend.app.services.project_review_migration import install_review_schema
from backend.app.services.project_operator import Operator, operator_context
from tests import test_project_review_archive as reviews


@pytest.fixture
def paired(tmp_path, monkeypatch):
    import app.db
    import backend.app.db
    import app.config
    stores = {}
    for name in ('source', 'target'):
        home = tmp_path / name
        home.mkdir()
        erp_path, brain_path = home / 'minipilot.db', home / 'project_brain.db'
        erp = create_engine(f'sqlite:///{erp_path}')
        brain = create_engine(f'sqlite:///{brain_path}')
        configure_sqlite(erp)
        configure_sqlite(brain)
        Base.metadata.create_all(erp, tables=[table for table in Base.metadata.sorted_tables if table not in DOCUMENT_FORM_TABLES])
        BrainBase.metadata.create_all(brain)
        for installer, label in ((install_identity_schema, 'identity'), (install_planning_schema, 'planning'),
                (install_deliverable_schema, 'deliverables'), (install_review_schema, 'reviews'),
                (install_document_schema, 'documents')):
            installer(erp, backup=lambda p=erp_path, h=home, n=label: backup_sqlite(p, h / ('before-' + n + '.db')))
        stores[name] = {'erp': sessionmaker(bind=erp, autoflush=False), 'brain': sessionmaker(bind=brain),
                        'erp_path': erp_path, 'brain_path': brain_path, 'home': home}
        with stores[name]['erp']() as db:
            project = Project(code='AIRB26LTH0205-A' if name == 'source' else 'EXISTING', title='Projet ' + name,
                              hourly_rate=93, margin_pct=11, tdao_prix_vente=144, tdao_budget_h=37.5)
            db.add(project)
            db.commit()
            stores[name]['pid'] = project.id
            items = forms.default_preferences()
            items[0]['label'] = 'Préférences ' + name
            forms.save_search_preferences(db, expected_revision=0, items=items)
            db.commit()
        with stores[name]['brain']() as db:
            db.add(BrainProject(code='BRAIN-' + name, name='Projet Brain conservé'))
            db.commit()
    source, target = stores['source'], stores['target']
    with source['erp']() as db:
        pid = source['pid']
        old = NetworkLink(project_id=pid, code='same', libelle='Ancien', chemin='V:/fictitious/old')
        current = NetworkLink(project_id=pid, code='same', libelle='Actuel', chemin='V:/fictitious/current')
        db.add_all([old, current])
        db.flush()
        with operator_context(Operator(pid, 'owner')):
            forms.save_draft(db, pid, 'tdao', expected_revision=0, link_id=old.id,
                            relative_path='Etudes/TDAO.xlsx', overrides={'description': pid})
            forms.save_draft(db, pid, 'tdao', expected_revision=1, link_id=current.id,
                            overrides={'description': old.id})
            forms.save_draft(db, pid, 'user_manual', expected_revision=0, link_id=old.id)
        db.commit()
        db.delete(old)  # Fictitious legacy source already missing a retained selected link.
        db.commit()
    monkeypatch.setattr(app.db, 'SessionLocal', source['brain'])
    monkeypatch.setattr(backend.app.db, 'APP_DIR', source['home'])
    with source['erp']() as db:
        data = archive.export_archive(db, source['pid'])
    assert data['version'] == 7
    monkeypatch.setattr(app.db, 'SessionLocal', target['brain'])
    monkeypatch.setattr(backend.app.db, 'APP_DIR', target['home'])
    monkeypatch.setattr(app.config, 'RAW_DIR', target['home'] / 'raw')
    yield data, stores
    for store in stores.values():
        store['erp'].kw['bind'].dispose()
        store['brain'].kw['bind'].dispose()


def restore(target, data, code='IMPORTED-0205'):
    with target['erp']() as db:
        return archive.import_archive(db, data, code)


def test_v7_actual_roundtrip_twice_keeps_captures_missing_links_and_target_preferences(paired):
    data, stores = paired
    original = deepcopy(data)
    source, target = stores['source'], stores['target']
    before = capture_baseline(source['erp_path']), capture_baseline(source['brain_path'])
    target_before = capture_baseline(target['erp_path']), capture_baseline(target['brain_path'])
    with target['erp']() as db:
        preferences = forms.search_history(db)
    first = restore(target, data)
    with target['erp']() as db:
        history = forms.draft_history(db, first['id'], 'tdao')
        assert len(history) == 2 and all(row['value']['actor_id'] == source['pid'] for row in history)
        assert forms.draft(db, first['id'], 'user_manual')['warnings'] == ['selected_link_missing']
        assert forms.search_history(db) == preferences
        second_archive = archive.export_archive(db, first['id'])
    second = restore(target, second_archive, 'IMPORTED-0306')
    with target['erp']() as db:
        second_history = forms.draft_history(db, second['id'], 'tdao')
        assert [row['value'] for row in second_history] == [row['value'] for row in history]
        assert all(set(row['bindings']) == {'project_id', 'draft_id', 'link_id'} for row in second_history)
        assert forms.search_history(db) == preferences
        original_link = next(row for row in data['tables']['project_document_drafts'] if row['document_id'] == 'tdao')['overrides']['description']
        assert forms.draft(db, second['id'], 'tdao')['overrides']['description'] == original_link
        forms.restore_draft(db, second['id'], 'tdao', version_id=second_history[0]['id'], expected_revision=2)
        db.commit()
        reopened = forms.draft_history(db, second['id'], 'tdao')
        assert len(reopened) == 3
        assert next(row for row in reopened if row['revision'] == 3)['value']['restored_from'] == second_history[0]['id']
        archive.export_archive(db, second['id'])
    assert data == original and (capture_baseline(source['erp_path']), capture_baseline(source['brain_path'])) == before
    assert compare_baseline(target_before[0], capture_baseline(target['erp_path']))['preserved']
    assert compare_baseline(target_before[1], capture_baseline(target['brain_path']))['preserved']


@pytest.mark.parametrize('damage', ['head', 'hash', 'missing_revision', 'global_preferences', 'missing_section',
                                  'missing_links', 'cross_project', 'downgrade', 'row_collision'])
def test_bad_v7_refused_with_both_existing_databases_exact(paired, damage):
    data, stores = paired
    target = stores['target']
    corrupted = deepcopy(data)
    rows = corrupted['tables']
    if damage == 'head':
        rows['project_document_drafts'][0]['overrides']['description'] = 'Divergence'
    elif damage == 'hash':
        rows['project_document_draft_versions'][0]['sha256'] = '0' * 64
    elif damage == 'missing_revision':
        rows['project_document_draft_versions'].pop(0)
    elif damage == 'global_preferences':
        rows['project_document_search_versions'] = []
    elif damage == 'missing_section':
        corrupted.pop('document_references')
    elif damage == 'missing_links':
        corrupted['document_references']['unresolved_link_ids'] = []
    elif damage == 'cross_project':
        rows['project_document_draft_versions'][0]['project_id'] = str(uuid.uuid4())
    elif damage == 'downgrade':
        corrupted['version'] = 5
    elif damage == 'row_collision':
        rows['project_document_drafts'][0]['id'] = rows['network_links'][0]['id']
    before = capture_baseline(target['erp_path']), capture_baseline(target['brain_path'])
    with pytest.raises(HTTPException) as error:
        restore(target, corrupted)
    assert error.value.status_code == 400
    assert (capture_baseline(target['erp_path']), capture_baseline(target['brain_path'])) == before


def test_insert_failure_rolls_back_both_stores_and_preserves_source_payload(paired):
    data, stores = paired
    target = stores['target']
    before = capture_baseline(target['erp_path']), capture_baseline(target['brain_path'])
    def fail(connection, cursor, statement, parameters, context, many):
        if statement.lstrip().upper().startswith('INSERT INTO PROJECT_DOCUMENT_DRAFT_VERSIONS'):
            raise RuntimeError('Fictitious disk/write failure')
    engine = target['erp'].kw['bind']
    event.listen(engine, 'before_cursor_execute', fail)
    try:
        with pytest.raises(HTTPException) as error:
            restore(target, data)
        assert error.value.status_code == 409
    finally:
        event.remove(engine, 'before_cursor_execute', fail)
    assert (capture_baseline(target['erp_path']), capture_baseline(target['brain_path'])) == before


def test_global_backup_restore_reopens_document_forms_preferences_and_guards(paired, tmp_path):
    data, stores = paired
    target = stores['target']
    imported = restore(target, data)
    with target['erp']() as db:
        expected = forms.draft_history(db, imported['id'], 'tdao')
        preferences = forms.search_history(db)
    storage = tmp_path / 'storage'
    storage.mkdir()
    backup = tmp_path / 'global-backup'
    create_backup(backup, target['brain_path'], target['home'], storage)
    output = tmp_path / 'global-restored'
    restore_backup(backup, output)
    engine = create_engine(f'sqlite:///{output / "erp/minipilot.db"}')
    configure_sqlite(engine)
    try:
        with sessionmaker(bind=engine)() as db:
            assert forms.draft_history(db, imported['id'], 'tdao') == expected
            assert forms.search_history(db) == preferences
    finally:
        engine.dispose()


def test_global_restore_refuses_rehashed_corrupt_history_before_creating_output(paired, tmp_path):
    data, stores = paired
    target = stores['target']
    restore(target, data)
    storage = tmp_path / 'storage'
    storage.mkdir()
    backup = tmp_path / 'global-backup'
    create_backup(backup, target['brain_path'], target['home'], storage)
    database = backup / 'erp/minipilot.db'
    from backend.app.services.document_schema_rules import immutable_triggers
    trigger = 'trg_project_document_draft_versions_update_immutable'
    with sqlite3.connect(database) as db:
        db.execute('DROP TRIGGER ' + trigger)
        db.execute('UPDATE project_document_draft_versions SET sha256=?', ('0' * 64,))
        db.execute(immutable_triggers()[trigger])
    manifest_path = backup / 'backup.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['files']['erp/minipilot.db'] = hashlib.sha256(database.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    before = {p.relative_to(backup).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in backup.rglob('*') if p.is_file()}
    output = tmp_path / 'must-not-exist'
    with pytest.raises(ValueError, match='invalide'):
        restore_backup(backup, output)
    assert not output.exists()
    assert before == {p.relative_to(backup).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in backup.rglob('*') if p.is_file()}


def test_v7_import_refuses_unprotected_destination_before_writes(paired):
    data, stores = paired
    target = stores['target']
    with sqlite3.connect(target['erp_path']) as db:
        db.execute('DROP TRIGGER trg_project_document_draft_versions_update_immutable')
    before = capture_baseline(target['erp_path']), capture_baseline(target['brain_path'])
    with pytest.raises(HTTPException) as error:
        restore(target, data)
    assert error.value.status_code == 409
    assert (capture_baseline(target['erp_path']), capture_baseline(target['brain_path'])) == before


# The existing v6 recipe supplies actual RLP/PDF/audio and selected deliverables.
transport = reviews.transport
store = reviews.store
audio = reviews.audio
envelope = reviews.envelope
l3_store = reviews.l3_store
typed_document = reviews.typed_document


def test_v7_combines_forms_with_frozen_review_pdf_and_recording(transport, store, audio, tmp_path, monkeypatch):
    import app.db
    import app.config
    import backend.app.db
    previous, target, target_brain, erp_path, _, target_root = transport
    for factory, path, label in ((store[0], store[2], 'source'), (target, erp_path, 'target')):
        install_document_schema(factory.kw['bind'], backup=lambda p=path, n=label:
                                backup_sqlite(p, tmp_path / ('before-documents-' + n + '.db')))
    with store[0]() as db:
        forms.save_draft(db, store[1]['project'], 'tdao', expected_revision=0, overrides={'agency_city': 'Nantes'})
        db.commit()
    raw = Path(previous['brain']['sources'][0]['original_uri'])
    monkeypatch.setattr(app.db, 'SessionLocal', audio[0])
    monkeypatch.setattr(app.config, 'RAW_DIR', raw.parent)
    monkeypatch.setattr(backend.app.db, 'APP_DIR', raw.parent.parent)
    with store[0]() as db:
        data = archive.export_archive(db, store[1]['project'])
    assert data['version'] == 7
    monkeypatch.setattr(app.db, 'SessionLocal', target_brain)
    monkeypatch.setattr(app.config, 'RAW_DIR', target_root / 'raw')
    monkeypatch.setattr(backend.app.db, 'APP_DIR', target_root)
    with target() as db:
        result = archive.import_archive(db, data, 'MIXED-0205')
    with target() as db:
        assert forms.draft(db, result['id'], 'tdao')['overrides'] == {'agency_city': 'Nantes'}
        published = db.scalar(select(ReviewPublication))
        frozen = previous['tables']['project_review_publications'][0]
        assert (published.snapshot, published.pdf_base64) == (frozen['snapshot'], frozen['pdf_base64'])
        assert published.bindings['erp'][store[1]['project']] == result['id']
        assert db.scalar(select(DocumentDraftVersion)).bindings['project_id'] == result['id']
