"""Portable real queue artifacts and offline recovery on fictional stores."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db_support import backup_sqlite, configure_sqlite
from app.services.backup import create_backup, restore_backup
from app.services.document_jobs_backup import validate_job_history, collect_files, suspend_restored_jobs
from app.services.deliverable_manifest import freeze
from backend.app.project_document_job_models import DocumentJob, DocumentJobArtifact
from backend.app.services import document_jobs as jobs
from backend.app.services.document_job_artifacts import write_artifact
from backend.app.services.document_job_schema_rules import specification, protections, validate_queue_schema
from backend.app.services.document_job_worker import DocumentCoordinator
from backend.app.services.project_archive import _rows
from backend.app.db import Base
from tests.test_project_document_jobs import queue as queue_fixture, install, enqueue

queue = queue_fixture


def test_offline_schema_and_protections_match_models(queue):
    install(queue)
    with sqlite3.connect(queue[4]) as db:
        assert validate_queue_schema(db)
    contract = specification()
    for table in jobs.DOCUMENT_JOB_TABLES:
        assert set(contract['tables'][table.name]['columns']) == set(table.c.keys())
        mutable = ({'status', 'revision', 'cancel_requested', 'execution_blocked', 'active_attempt_id', 'updated_at'}
            if table.name == 'project_document_jobs' else {'status', 'last_attempt_id'} if table.name.endswith('_items') else set())
        expected = ' OR '.join(f'NEW.{c.name} IS NOT OLD.{c.name}' for c in table.c if c.name not in mutable)
        assert f'WHEN {expected} BEGIN' in protections()['protect_' + table.name + '_update']


def test_offline_import_does_not_initialize_runtime(queue, tmp_path):
    install(queue)
    enqueue(queue)
    forbidden = tmp_path / 'forbidden-home'
    code = """import sys
from app.services.document_jobs_backup import validate_job_history
validate_job_history(sys.argv[1])
assert not {'backend.app.db','backend.app.models','app.db','app.config','backend.app.services.document_file_access'} & set(sys.modules)
print('offline-only')
"""
    result = subprocess.run([sys.executable, '-c', code, str(queue[4])], cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, 'MINIPILOT_HOME': str(forbidden)}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'offline-only' and not forbidden.exists()


@pytest.fixture
def snapshot(queue, tmp_path):
    install(queue)
    job = enqueue(queue, both=True)
    jobs.run_one(queue[1], 'project', job['id'], storage_root=queue[3])
    with queue[1]() as db:
        state = jobs.detail(db, 'project', job['id'])
        jobs.claim(db, 'project', job['id'], state['revision'])
        db.commit()
    candidate = str(uuid4())
    write_artifact(queue[3], candidate, b'Uncommitted candidate retained')
    erp, storage, brain = tmp_path / 'erp-home', tmp_path / 'storage', tmp_path / 'brain.db'
    erp.mkdir()
    storage.mkdir()
    with sqlite3.connect(queue[4]) as db:
        db.execute('CREATE TABLE cdc_sources (id TEXT, storage_path TEXT)')
    backup_sqlite(queue[4], erp / 'minipilot.db')
    shutil.copytree(queue[3], erp / 'document-artifacts')
    (erp / 'minipilot.db.document-worker.lock').write_bytes(b'0')
    with sqlite3.connect(brain) as db:
        db.execute('CREATE TABLE sources (id TEXT PRIMARY KEY, sha256 TEXT, original_uri TEXT, source_metadata TEXT)')
    target = tmp_path / 'archive'
    manifest = create_backup(target, brain, erp, storage)
    return {'archive': target, 'manifest': manifest, 'job': job, 'candidate': candidate, 'erp': erp}


def test_portable_restore_closes_attempt_retains_success_and_never_executes(queue, snapshot, tmp_path, monkeypatch):
    original = hashlib.sha256(queue[4].read_bytes()).hexdigest()
    destination = tmp_path / 'restored'
    restore_backup(snapshot['archive'], destination)
    assert hashlib.sha256(queue[4].read_bytes()).hexdigest() == original
    assert len(snapshot['manifest']['document_job_files']) == 1
    assert not (destination / 'erp/minipilot.db.document-worker.lock').exists()
    assert (destination / 'erp/document-artifacts' / snapshot['candidate']).read_bytes() == b'Uncommitted candidate retained'
    database = destination / 'erp/minipilot.db'
    assert len(collect_files(database, destination / 'erp')) == 1
    engine = create_engine(f'sqlite:///{database}', connect_args={'check_same_thread': False})
    configure_sqlite(engine)
    factory = sessionmaker(bind=engine)
    coordinator = DocumentCoordinator(factory, storage_root=destination / 'erp/document-artifacts')
    try:
        with factory() as db:
            state = jobs.detail(db, 'project', snapshot['job']['id'])
            assert state['execution_blocked'] and not state['can_retry'] and not state['can_cancel']
            assert state['status'] == 'interrupted' and [item['status'] for item in state['items']] == ['succeeded', 'interrupted']
            content, _ = jobs.artifact_content(db, 'project', state['items'][0]['artifact_id'], storage_root=coordinator.storage_root)
            assert content.startswith(b'PK')
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                jobs.retry(db, 'project', state['id'], state['revision'])
            assert exc.value.status_code == 409
            with pytest.raises(HTTPException):
                jobs.claim(db, 'project', state['id'], state['revision'])
            raw = db.get(DocumentJob, state['id']).snapshot
        monkeypatch.setattr(jobs, 'run_one', lambda *a, **kw: pytest.fail('Restored history must not execute'))
        assert coordinator.start(enabled=True)['running']
        assert coordinator._next() is None
        assert coordinator.stop()
        suspend_restored_jobs(database)  # Idempotent, no duplicate recovery events.
        with factory() as db:
            again = jobs.detail(db, 'project', state['id'])
            assert again == state and db.get(DocumentJob, state['id']).snapshot == raw
        validate_job_history(database)
    finally:
        coordinator.stop()
        engine.dispose()


@pytest.mark.parametrize('damage', ['copy', 'inventory', 'manifest', 'receipt', 'event', 'active', 'trigger', 'column', 'command', 'preview'])
def test_damage_refused_before_restore_destination(snapshot, tmp_path, damage):
    archive = snapshot['archive']
    database = archive / 'erp/minipilot.db'
    manifest = snapshot['manifest']
    binding = manifest['document_job_files'][0]
    if damage == 'copy':
        file = archive / 'erp/document-artifacts' / binding['storage_key']
        file.write_bytes(b'Changed copy')
        manifest['files'][file.relative_to(archive).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    elif damage == 'inventory':
        manifest['document_job_files'] = []
    elif damage == 'manifest':
        manifest['files'].pop('erp/document-artifacts/' + binding['storage_key'])
    else:
        with sqlite3.connect(database) as db:
            if damage == 'receipt':
                trigger = 'protect_project_document_job_receipts_update'
                db.execute('DROP TRIGGER ' + trigger)
                db.execute("UPDATE project_document_job_receipts SET artifact_id=NULL,outcome='failed'")
                db.execute(protections()[trigger])
            elif damage == 'event':
                trigger = 'protect_project_document_job_events_delete'
                db.execute('DROP TRIGGER ' + trigger)
                db.execute('DELETE FROM project_document_job_events WHERE revision=1')
                db.execute(protections()[trigger])
            elif damage == 'active':
                db.execute('UPDATE project_document_jobs SET active_attempt_id=NULL')
            elif damage == 'trigger':
                db.execute('DROP TRIGGER protect_project_document_job_artifacts_update')
            elif damage == 'column':
                db.execute('ALTER TABLE project_document_jobs ADD COLUMN extra TEXT')
            elif damage in {'command', 'preview'}:
                table = 'project_document_jobs' if damage == 'command' else 'project_document_job_items'
                row_id, raw = db.execute(f'SELECT id,snapshot FROM {table} LIMIT 1').fetchone()
                value = json.loads(raw)
                if damage == 'command':
                    value['output_root'] = 'V:/forged'
                else:
                    value['preview']['source_sha256'] = '0' * 64
                capture, digest = freeze(value)
                trigger = 'protect_' + table + '_update'
                db.execute('DROP TRIGGER ' + trigger)
                db.execute(f'UPDATE {table} SET snapshot=?,sha256=? WHERE id=?', (capture, digest, row_id))
                db.execute(protections()[trigger])
        manifest['files']['erp/minipilot.db'] = hashlib.sha256(database.read_bytes()).hexdigest()
    (archive / 'backup.json').write_text(json.dumps(manifest), encoding='utf-8')
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    output = tmp_path / 'must-not-create'
    with pytest.raises(ValueError):
        restore_backup(archive, output)
    assert not output.exists() and hashlib.sha256(database.read_bytes()).hexdigest() == before


def test_selective_export_refuses_to_silently_omit_queue(queue):
    install(queue)
    enqueue(queue)
    from fastapi import HTTPException
    with queue[1]() as db:
        with pytest.raises(HTTPException, match='archive projet typée') as exc:
            _rows(db, Base.metadata, 'project', include_documents=True)
        assert exc.value.status_code == 409
        assert db.scalar(select(DocumentJobArtifact)) is None
