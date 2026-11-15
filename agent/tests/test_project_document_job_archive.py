"""Real paired v8 transport, retained capture text and portable second import."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3

from fastapi import HTTPException
import pytest
from sqlalchemy import event, select

from app.db_support import backup_sqlite
from app.services.backup import create_backup, restore_backup
from app.services.document_jobs_backup import validate_job_history, collect_files
from app.services.deliverable_manifest import freeze
from backend.app.models import NetworkLink, Project, BrainLink
from backend.app.project_document_job_models import DocumentJob, DocumentJobItem, DocumentJobArtifact, DocumentJobEvent
from backend.app.project_document_job_schemas import DocumentBatchSubmit
from backend.app.project_document_schemas import DocumentPreview
from backend.app.project_document_publication_schemas import DocumentPublicationPreview, DocumentPublicationCommand
from backend.app.services import document_publications as destinations, document_publication_commands as publications
from backend.app.services.document_worker_lease import WorkerLease
from backend.app.services import document_jobs as jobs, project_documents, document_forms as forms, project_archive as archive
from backend.app.services.document_job_schema import install_job_schema
from backend.app.services.migration_guard import capture_baseline, compare_baseline
from backend.app.services.project_operator import Operator, operator_context
from tests.test_project_document_archive import paired as paired_fixture, restore
from tests.test_project_document_packages import package, parts_for
from tests import test_project_document_archive as legacy

paired = paired_fixture
transport = legacy.transport
store = legacy.store
audio = legacy.audio
envelope = legacy.envelope
l3_store = legacy.l3_store
typed_document = legacy.typed_document


@pytest.fixture
def batch_archive(paired, monkeypatch):
    _, stores = paired
    import app.db
    import backend.app.db
    source, target = stores['source'], stores['target']
    for store in stores.values():
        install_job_schema(store['erp'].kw['bind'], backup=lambda s=store: backup_sqlite(s['erp_path'], s['home'] / 'before-jobs.db'))
    root = source['home'] / 'templates'
    root.mkdir()
    for doc, name in [('ce_request', 'CE.docx'), ('user_manual', 'Notice.docm')]:
        (root / name).write_bytes(package(parts_for(doc)))
    monkeypatch.setenv('AGENT_DOCUMENT_ROOTS', json.dumps([str(root)]))
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'owner')
    monkeypatch.delenv('AGENT_OPERATOR_PROJECT_IDS', raising=False)
    monkeypatch.delenv('AGENT_DOCUMENT_DRIVE_MAPPINGS', raising=False)
    pid = source['pid']
    with source['erp']() as db:
        link = NetworkLink(project_id=pid, code='batch', libelle='Trames', chemin=str(root))
        db.add(link)
        db.flush()
        selected = []
        for doc, name, revision, overrides in [('ce_request', 'CE.docx', 0, {}), ('user_manual', 'Notice.docm', 1, {'description': 'Notice'})]:
            forms.save_draft(db, pid, doc, expected_revision=revision, link_id=link.id, relative_path=name, overrides=overrides)
            db.commit()
            command = DocumentPreview(document_id=doc, link_id=link.id, relative_path=name, overrides=overrides)
            report = project_documents.preview(db, pid, command)
            assert report['can_prepare'], report['blockers']
            selected.append({**command.model_dump(), 'expected_source_sha256': report['source_sha256'],
                'expected_link_sha256': report['link_sha256'], 'expected_values_sha256': report['values_sha256'],
                'expected_identity_revision': report['field_values']['identity_revision'],
                'expected_planning_revision': report['field_values']['planning_revision'], 'expected_draft_revision': revision + 1})
        with operator_context(Operator(pid, 'owner')):
            job = jobs.submit(db, pid, DocumentBatchSubmit(command_id='portable', items=selected))
        db.commit()
    with operator_context(Operator(pid, 'owner')):
        jobs.run_one(source['erp'], pid, job['id'], storage_root=source['home'] / 'document-artifacts')
        with source['erp']() as db:
            state = jobs.detail(db, pid, job['id'])
            jobs.claim(db, pid, job['id'], state['revision'])
            db.commit()
    from app.models import Project as BrainProject
    with source['brain']() as brain:
        brain_id = brain.scalar(select(BrainProject.id))
    with source['erp']() as db:
        db.add(BrainLink(project_id=pid, brain_project_id=brain_id))
        db.commit()
    monkeypatch.setattr(app.db, 'SessionLocal', source['brain'])
    monkeypatch.setattr(backend.app.db, 'APP_DIR', source['home'])
    with source['erp']() as db:
        data = archive.export_archive(db, pid)
    assert data['version'] == 8 and len([f for f in data['files'] if f['area'] == 'document-job']) == 1
    monkeypatch.setattr(app.db, 'SessionLocal', target['brain'])
    monkeypatch.setattr(backend.app.db, 'APP_DIR', target['home'])
    yield data, stores


def test_v8_real_roundtrip_twice_preserves_original_text_and_success(batch_archive, tmp_path):
    data, stores = batch_archive
    source, target = stores['source'], stores['target']
    original = deepcopy(data)
    before = capture_baseline(source['erp_path']), capture_baseline(source['brain_path'])
    target_before = capture_baseline(target['erp_path']), capture_baseline(target['brain_path'])
    first = restore(target, data)
    old_job = data['tables']['project_document_jobs'][0]
    with target['erp']() as db:
        job = db.scalar(select(DocumentJob).where(DocumentJob.project_id == first['id']))
        state = jobs.detail(db, first['id'], job.id)
        assert job.snapshot == old_job['snapshot'] and job.sha256 == old_job['sha256'] and job.actor_id == old_job['actor_id']
        assert job.id != old_job['id'] and job.execution_blocked and state['status'] == 'interrupted' and not state['can_retry']
        assert [i['status'] for i in state['items']] == ['succeeded', 'interrupted']
        items = list(db.scalars(select(DocumentJobItem).where(DocumentJobItem.job_id == job.id).order_by(DocumentJobItem.position)))
        for item, raw in zip(items, sorted(data['tables']['project_document_job_items'], key=lambda r: r['position']), strict=True):
            assert (item.snapshot, item.sha256) == (raw['snapshot'], raw['sha256'])
            assert item.link_id != raw['link_id'] and item.draft_version_id != raw['draft_version_id']
        artifact = db.scalar(select(DocumentJobArtifact).where(DocumentJobArtifact.job_id == job.id))
        old_artifact = data['tables']['project_document_job_artifacts'][0]
        assert artifact.storage_key != old_artifact['storage_key'] and artifact.provenance == old_artifact['provenance']
        content, _ = jobs.artifact_content(db, first['id'], artifact.id, storage_root=target['home'] / 'document-artifacts')
        assert hashlib.sha256(content).hexdigest() == old_artifact['sha256']
        second_data = archive.export_archive(db, first['id'])
    second = restore(target, second_data, 'SECOND-0306')
    with target['erp']() as db:
        job = db.scalar(select(DocumentJob).where(DocumentJob.project_id == second['id']))
        assert (job.snapshot, job.sha256, job.actor_id) == (old_job['snapshot'], old_job['sha256'], old_job['actor_id'])
        events = list(db.scalars(select(DocumentJobEvent).where(DocumentJobEvent.job_id == job.id).order_by(DocumentJobEvent.revision)))
        assert [event.kind for event in events].count('archive_imported') == 2
        assert [event.detail for event in events[:old_job['revision']]] == [row['detail'] for row in sorted(data['tables']['project_document_job_events'], key=lambda r: r['revision'])]
        archive.export_archive(db, second['id'])
    assert data == original and before == (capture_baseline(source['erp_path']), capture_baseline(source['brain_path']))
    assert compare_baseline(target_before[0], capture_baseline(target['erp_path']))['preserved']
    assert compare_baseline(target_before[1], capture_baseline(target['brain_path']))['preserved']
    # Whole-store validation also understands remapped historical selections.
    assert len(validate_job_history(target['erp_path'])) == 2
    storage = tmp_path / 'storage'
    storage.mkdir()
    backup, output = tmp_path / 'global', tmp_path / 'restored'
    create_backup(backup, target['brain_path'], target['home'], storage)
    restore_backup(backup, output)
    assert len(collect_files(output / 'erp/minipilot.db', output / 'erp')) == 2


@pytest.mark.parametrize('replace_existing',[False,True])
def test_v8_publication_roundtrip_twice_and_global_restore_keep_receipts_without_network_replay(batch_archive, tmp_path, monkeypatch,replace_existing):
    import app.db
    import backend.app.db
    _, stores = batch_archive
    source, target = stores['source'], stores['target']
    destination = source['home'] / 'publication-target'
    destination.mkdir()
    monkeypatch.setenv('AGENT_DOCUMENT_WRITE_ROOTS',json.dumps([str(destination)]))
    with source['erp']() as db:
        job = db.scalar(select(DocumentJob))
        jobs.recover_interrupted(db,source['pid'],job.id,job.revision)
        db.commit()
        # Destination is a different link from the generation source.
        link = NetworkLink(project_id=source['pid'],code='publication',libelle='Destination fictive',chemin=str(destination))
        db.add(link)
        db.commit()
        artifact = db.scalar(select(DocumentJobArtifact))
        aid, link_id = artifact.id, link.id
        if replace_existing:
            (destination/artifact.filename).write_bytes(b'Original fictional archive publication document')
        reviewed = destinations.preview(db,source['pid'],aid,DocumentPublicationPreview(link_id=link_id,replace_existing=replace_existing),
                                         storage_root=source['home']/'document-artifacts')
    payload = DocumentPublicationCommand(command_id='portable-publication',link_id=link_id,replace_existing=replace_existing,
        expected_revision=reviewed['job_revision'],expected_preview_sha256=reviewed['preview_sha256'],reviewed=True)
    with source['erp']() as db, operator_context(Operator('publisher','owner')):
        receipt = publications.publish(db,source['pid'],aid,payload,storage_root=source['home']/'document-artifacts')
    original_files = {p.name:p.read_bytes() for p in destination.iterdir()}
    monkeypatch.setattr(app.db,'SessionLocal',source['brain'])
    monkeypatch.setattr(backend.app.db,'APP_DIR',source['home'])
    with source['erp']() as db:
        data = archive.export_archive(db,source['pid'])
    assert data['version'] == 8
    original_events = [row for row in data['tables']['project_document_job_events'] if row['kind'].startswith('publication_')]
    assert len(original_events) == (5 if replace_existing else 3) and {e['actor_id'] for e in original_events} == {'publisher'}
    monkeypatch.setattr(app.db,'SessionLocal',target['brain'])
    monkeypatch.setattr(backend.app.db,'APP_DIR',target['home'])
    for code in ('PUB-IMPORT-ONE','PUB-IMPORT-TWO'):
        restored = restore(target,data,code)
        with target['erp']() as db:
            job = db.scalar(select(DocumentJob).where(DocumentJob.project_id == restored['id']))
            journal = publications.list_publications(db,restored['id'],job.id)
            row = journal['items'][0]
            assert journal['execution_blocked'] and not row['can_resume'] and row['state'] == 'succeeded'
            assert row['receipt'] == receipt['receipt'] and row['artifact_id'] != aid
            assert row['backup_receipt'] == receipt['backup_receipt'] and row['backup']==receipt['backup']
            events = list(db.scalars(select(DocumentJobEvent).where(DocumentJobEvent.job_id == job.id,
                                                                   DocumentJobEvent.kind.like('publication_%'))))
            assert [e.detail for e in sorted(events,key=lambda e:e.revision)] == [e['detail'] for e in sorted(original_events,key=lambda e:e['revision'])]
            with monkeypatch.context() as scoped:
                scoped.setattr(publications,'_lease',lambda *args:pytest.fail('Imported receipt must not replay IO'))
                with pytest.raises(HTTPException) as failure:
                    publications.publish(db,restored['id'],row['artifact_id'],payload,storage_root=target['home']/'document-artifacts')
                assert failure.value.status_code == 409
            data = archive.export_archive(db,restored['id'])
            imported = json.loads(max((e for e in data['tables']['project_document_job_events'] if e['kind']=='archive_imported'),
                                      key=lambda e:e['revision'])['detail'])
            binding = imported['publication_bindings']['portable-publication']
            assert binding['link_id'] != link_id and binding['artifact_id'] == row['artifact_id']
            assert binding['link_id'] in {r['id'] for r in data['tables']['network_links']}
    assert len(validate_job_history(target['erp_path'])) == 2
    storage = tmp_path / 'publication-backup-storage'
    storage.mkdir()
    backup, output = tmp_path/'publication-backup', tmp_path/'publication-restored'
    lease = WorkerLease(target['erp_path'],namespace='publication')
    assert lease.acquire()
    lease.close()
    assert lease.path.is_file()
    manifest = create_backup(backup,target['brain_path'],target['home'],storage)
    assert not any(path.endswith('.lock') for path in manifest['files'])
    restore_backup(backup,output)
    assert len(collect_files(output/'erp/minipilot.db',output/'erp')) == 2
    assert original_files == {p.name:p.read_bytes() for p in destination.iterdir()}


@pytest.mark.parametrize('damage', ['missing_section', 'missing_table', 'wrong_project', 'missing_file', 'wrong_owner',
    'changed_bytes', 'wrong_binding', 'missing_version', 'bad_events', 'downgrade', 'global_preferences',
    'source_capture', 'financial_override', 'values_capture'])
def test_v8_bad_archive_changes_neither_database_nor_prepares_files(batch_archive, damage):
    data, stores = batch_archive
    target = stores['target']
    bad = deepcopy(data)
    tables = bad['tables']
    if damage == 'missing_section':
        bad.pop('document_job_references')
    elif damage == 'missing_table':
        tables.pop('project_document_job_receipts')
    elif damage == 'wrong_project':
        tables['project_document_job_items'][0]['project_id'] = 'foreign'
    elif damage == 'missing_file':
        bad['files'] = []
    elif damage == 'wrong_owner':
        bad['files'][0]['owner'] = 'foreign'
    elif damage == 'changed_bytes':
        content = b'Changed but rehashed bytes'
        bad['files'][0]['data'] = base64.b64encode(content).decode()
        bad['files'][0]['sha256'] = hashlib.sha256(content).hexdigest()
    elif damage == 'wrong_binding':
        tables['project_document_job_items'][0]['link_id'] = 'other-link'
    elif damage == 'missing_version':
        version = tables['project_document_job_items'][0]['draft_version_id']
        tables['project_document_draft_versions'] = [row for row in tables['project_document_draft_versions'] if row['id'] != version]
    elif damage == 'bad_events':
        tables['project_document_job_events'].pop(0)
    elif damage == 'downgrade':
        bad['version'] = 7
    elif damage == 'global_preferences':
        tables['project_document_search_versions'] = []
    elif damage in {'source_capture', 'financial_override', 'values_capture'}:
        item = min(tables['project_document_job_items'], key=lambda row: row['position'])
        value = json.loads(item['snapshot'])
        if damage == 'source_capture':
            value['preview']['source']['project_id'] = 'foreign'
        elif damage == 'values_capture':
            value['preview']['field_values']['values']['description'] = 'Falsification après aperçu'
        else:
            value['command']['overrides']['hourly_rate'] = '99'
            job = tables['project_document_jobs'][0]
            command = json.loads(job['snapshot'])
            command['items'][item['position']] = value['command']
            job['snapshot'], job['sha256'] = freeze(command)
        item['snapshot'], item['sha256'] = freeze(value)
    before = capture_baseline(target['erp_path']), capture_baseline(target['brain_path'])
    with pytest.raises(HTTPException) as exc:
        restore(target, bad)
    assert exc.value.status_code == 400
    assert before == (capture_baseline(target['erp_path']), capture_baseline(target['brain_path']))
    assert not (target['home'] / 'backups/archive-imports').exists()


@pytest.mark.parametrize('actor', [Operator('reader', 'reader'), Operator('editor', 'editor'),
    Operator('scoped-owner', 'owner', frozenset({'foreign'}))])
def test_v8_import_admin_scope_enforced_without_http(batch_archive, actor):
    data, stores = batch_archive
    target = stores['target']
    before = capture_baseline(target['erp_path']), capture_baseline(target['brain_path'])
    with operator_context(actor), pytest.raises(HTTPException) as exc:
        restore(target, data)
    assert exc.value.status_code == 403
    assert before == (capture_baseline(target['erp_path']), capture_baseline(target['brain_path']))
    assert not (target['home'] / 'backups/archive-imports').exists()


def test_v8_foreign_export_denied_before_schema_or_storage_access(batch_archive, monkeypatch):
    _, stores = batch_archive
    from backend.app.services import document_job_artifacts
    monkeypatch.setattr(document_job_artifacts, 'read_artifact', lambda *a, **kw: pytest.fail('Scope must precede file access'))
    with stores['source']['erp']() as db, operator_context(Operator('scoped', 'reader', frozenset({'foreign'}))):
        with pytest.raises(HTTPException) as exc:
            archive.export_archive(db, stores['source']['pid'])
        assert exc.value.status_code == 404


def test_v8_job_insert_failure_rolls_back_both_stores_and_retains_prepared_candidate(batch_archive):
    data, stores = batch_archive
    target = stores['target']
    before = capture_baseline(target['erp_path']), capture_baseline(target['brain_path'])
    engine = target['erp'].kw['bind']
    def fail(connection, cursor, statement, parameters, context, many):
        if statement.upper().startswith('INSERT INTO PROJECT_DOCUMENT_JOB_RECEIPTS'):
            raise RuntimeError('Fictitious disk failure after file preparation')
    event.listen(engine, 'before_cursor_execute', fail)
    try:
        with pytest.raises(HTTPException) as exc:
            restore(target, data)
        assert exc.value.status_code == 409
    finally:
        event.remove(engine, 'before_cursor_execute', fail)
    assert before == (capture_baseline(target['erp_path']), capture_baseline(target['brain_path']))
    candidates = list((target['home'] / 'document-artifacts').glob('*'))
    assert len(candidates) == 1
    assert hashlib.sha256(candidates[0].read_bytes()).hexdigest() == data['files'][0]['sha256']
    logs = list((target['home'] / 'backups/archive-imports').glob('*/events.ndjson'))
    assert len(logs) == 1 and 'import_failed' in logs[0].read_text(encoding='utf-8')


def test_v8_unprotected_destination_refused_before_any_preparation(batch_archive):
    data, stores = batch_archive
    target = stores['target']
    with sqlite3.connect(target['erp_path']) as db:
        db.execute('DROP TRIGGER protect_project_document_job_artifacts_update')
    before = capture_baseline(target['erp_path']), capture_baseline(target['brain_path'])
    with pytest.raises(HTTPException) as exc:
        restore(target, data)
    assert exc.value.status_code == 409
    assert before == (capture_baseline(target['erp_path']), capture_baseline(target['brain_path']))
    assert not (target['home'] / 'backups/archive-imports').exists()


def test_v8_missing_selected_link_retained_and_remapped(batch_archive, monkeypatch):
    _, stores = batch_archive
    source, target = stores['source'], stores['target']
    import app.db
    import backend.app.db
    with source['erp']() as db:
        item = db.scalar(select(DocumentJobItem).where(DocumentJobItem.project_id == source['pid']))
        missing = item.link_id
        db.delete(db.get(NetworkLink, missing))  # Only the isolated fictional fixture.
        db.commit()
    monkeypatch.setattr(app.db, 'SessionLocal', source['brain'])
    monkeypatch.setattr(backend.app.db, 'APP_DIR', source['home'])
    with source['erp']() as db:
        data = archive.export_archive(db, source['pid'])
    assert missing in data['document_job_references']['unresolved_link_ids']
    monkeypatch.setattr(app.db, 'SessionLocal', target['brain'])
    monkeypatch.setattr(backend.app.db, 'APP_DIR', target['home'])
    imported = restore(target, data)
    with target['erp']() as db:
        item = db.scalar(select(DocumentJobItem).where(DocumentJobItem.project_id == imported['id']))
        assert item.link_id != missing and db.get(NetworkLink, item.link_id) is None
        again = archive.export_archive(db, imported['id'])
        assert item.link_id in again['document_job_references']['unresolved_link_ids']


def test_v8_job_without_saved_form_transports_without_form_section(batch_archive, monkeypatch):
    _, stores = batch_archive
    source, target = stores['source'], stores['target']
    import app.db
    import backend.app.db
    root = source['home'] / 'templates'
    with source['erp']() as db:
        project = Project(code='NO-FORMS', title='Sans formulaire enregistré')
        db.add(project)
        db.flush()
        link = NetworkLink(project_id=project.id, code='no-forms', libelle='Trames', chemin=str(root))
        db.add(link)
        db.commit()
        pid, link_id = project.id, link.id
        command = DocumentPreview(document_id='ce_request', link_id=link_id, relative_path='CE.docx')
        report = project_documents.preview(db, pid, command)
        assert report['can_prepare'], report['blockers']
        payload = {**command.model_dump(), 'expected_source_sha256': report['source_sha256'],
            'expected_link_sha256': report['link_sha256'], 'expected_values_sha256': report['values_sha256'],
            'expected_identity_revision': report['field_values']['identity_revision'],
            'expected_planning_revision': report['field_values']['planning_revision'], 'expected_draft_revision': 0}
        job = jobs.submit(db, pid, DocumentBatchSubmit(command_id='no-form', items=[payload]))
        db.commit()
    jobs.run_one(source['erp'], pid, job['id'], storage_root=source['home'] / 'document-artifacts')
    monkeypatch.setattr(app.db, 'SessionLocal', source['brain'])
    monkeypatch.setattr(backend.app.db, 'APP_DIR', source['home'])
    with source['erp']() as db:
        data = archive.export_archive(db, pid)
    assert data['version'] == 8 and 'document_references' not in data
    monkeypatch.setattr(app.db, 'SessionLocal', target['brain'])
    monkeypatch.setattr(backend.app.db, 'APP_DIR', target['home'])
    imported = restore(target, data)
    with target['erp']() as db:
        item = db.scalar(select(DocumentJobItem).where(DocumentJobItem.project_id == imported['id']))
        assert item.draft_version_id is None and item.status == 'succeeded'
        assert db.get(DocumentJob, item.job_id).execution_blocked


def test_v8_combines_office_job_review_pdf_deliverables_and_recording(transport, store, audio, tmp_path, monkeypatch):
    import app.db
    import app.config
    import backend.app.db
    from backend.app.services.project_document_migration import install_document_schema
    from backend.app.project_review_models import ReviewPublication
    from app.models import MeetingRecording
    previous, target, target_brain, erp_path, _, target_root = transport
    for factory, path, label in ((store[0], store[2], 'source'), (target, erp_path, 'target')):
        install_document_schema(factory.kw['bind'], backup=lambda p=path, n=label:
            backup_sqlite(p, tmp_path / ('before-mixed-documents-' + n + '.db')))
        install_job_schema(factory.kw['bind'], backup=lambda p=path, n=label:
            backup_sqlite(p, tmp_path / ('before-mixed-jobs-' + n + '.db')))
    source_root = Path(previous['brain']['sources'][0]['original_uri']).parent.parent
    templates = source_root / 'trames'
    templates.mkdir()
    (templates / 'CE.docx').write_bytes(package(parts_for('ce_request')))
    monkeypatch.setenv('AGENT_DOCUMENT_ROOTS', json.dumps([str(templates)]))
    monkeypatch.delenv('AGENT_DOCUMENT_DRIVE_MAPPINGS', raising=False)
    pid = store[1]['project']
    with store[0]() as db:
        link = NetworkLink(project_id=pid, code='ce', libelle='Trame CE', chemin=str(templates))
        db.add(link)
        db.flush()
        forms.save_draft(db, pid, 'ce_request', expected_revision=0, link_id=link.id, relative_path='CE.docx')
        db.commit()
        choice = DocumentPreview(document_id='ce_request', link_id=link.id, relative_path='CE.docx')
        report = project_documents.preview(db, pid, choice)
        assert report['can_prepare'], report['blockers']
        payload = {**choice.model_dump(), 'expected_source_sha256': report['source_sha256'],
            'expected_link_sha256': report['link_sha256'], 'expected_values_sha256': report['values_sha256'],
            'expected_identity_revision': report['field_values']['identity_revision'],
            'expected_planning_revision': report['field_values']['planning_revision'], 'expected_draft_revision': 1}
        job = jobs.submit(db, pid, DocumentBatchSubmit(command_id='mixed', items=[payload]))
        db.commit()
    jobs.run_one(store[0], pid, job['id'], storage_root=source_root / 'document-artifacts')
    monkeypatch.setattr(app.db, 'SessionLocal', audio[0])
    monkeypatch.setattr(app.config, 'RAW_DIR', source_root / 'raw')
    monkeypatch.setattr(backend.app.db, 'APP_DIR', source_root)
    with store[0]() as db:
        data = archive.export_archive(db, pid)
    assert data['version'] == 8 and {'raw', 'document-job'} <= {entry['area'] for entry in data['files']}
    monkeypatch.setattr(app.db, 'SessionLocal', target_brain)
    monkeypatch.setattr(app.config, 'RAW_DIR', target_root / 'raw')
    monkeypatch.setattr(backend.app.db, 'APP_DIR', target_root)
    with target() as db:
        result = archive.import_archive(db, data, 'MIXED-0205')
    with target() as db:
        publication = db.scalar(select(ReviewPublication))
        raw_publication = previous['tables']['project_review_publications'][0]
        assert (publication.snapshot, publication.pdf_base64) == (raw_publication['snapshot'], raw_publication['pdf_base64'])
        assert publication.bindings['erp'][pid] == result['id']
        imported = db.scalar(select(DocumentJob))
        assert imported.execution_blocked and imported.status == 'completed'
        assert forms.draft(db, result['id'], 'ce_request')['relative_path'] == 'CE.docx'
    with target_brain() as db:
        recording = db.scalar(select(MeetingRecording))
        assert recording.erp_project_id == result['id']
