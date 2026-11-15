"""Offline queue/file closure and restoration suspension. No runtime imports."""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from .deliverable_manifest import freeze
from backend.app.services.document_job_artifacts import read_artifact
from backend.app.services.document_job_history import JOB_TABLES, MAX_ROWS, validate
from backend.app.services.document_job_schema_rules import validate_queue_schema


def validate_job_history(database):
    """Return verified artifacts from bounded rows; absent queues create nothing."""
    try:
        artifacts = []
        with sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True) as db:
            if not validate_queue_schema(db):
                return []
            db.row_factory = sqlite3.Row
            for name in JOB_TABLES:
                if db.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0] > MAX_ROWS:
                    raise ValueError('Historique documentaire trop volumineux')
            pids = {row[0] for name in JOB_TABLES for row in db.execute(f'SELECT DISTINCT project_id FROM {name}')}
            for pid in pids:
                tables = {'projects': [dict(row) for row in db.execute('SELECT * FROM projects WHERE id=?', (pid,))]}
                for name in JOB_TABLES:
                    tables[name] = [dict(row) for row in db.execute(f'SELECT * FROM {name} WHERE project_id=?', (pid,))]
                ledger = validate(tables)
                existing = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                for item in ledger['job_items'].values():
                    if item['draft_version_id'] is not None and ('project_document_draft_versions' not in existing or not db.execute(
                            'SELECT 1 FROM project_document_draft_versions WHERE id=? AND project_id=? AND document_id=?',
                            (item['draft_version_id'], pid, item['document_id'])).fetchone()):
                        raise ValueError('Version de formulaire documentaire absente')
                artifacts.extend(ledger['job_artifacts'].values())
        return artifacts
    except (HTTPException, ValidationError, ValueError, TypeError, KeyError, sqlite3.Error, OverflowError) as exc:
        raise ValueError('Historique de file documentaire invalide') from exc


def collect_files(database, erp_home):
    rows = validate_job_history(database)
    bindings = []
    for row in rows:
        try:
            read_artifact(Path(erp_home) / 'document-artifacts', SimpleNamespace(**row))
        except HTTPException as exc:
            raise ValueError('Copie documentaire absente ou modifiée') from exc
        bindings.append({key: row[key] for key in ('id', 'project_id', 'storage_key', 'sha256', 'size_bytes')})
    return sorted(bindings, key=lambda row: row['id'])


def validate_files(database, source, manifest):
    expected = collect_files(database, Path(source) / 'erp')
    provided = manifest.get('document_job_files', [])
    if (not isinstance(provided, list) or provided != expected
            or any(not isinstance(row, dict) or set(row) != {'id', 'project_id', 'storage_key', 'sha256', 'size_bytes'}
                   or type(row['size_bytes']) is not int for row in provided)):
        raise ValueError('Inventaire des copies documentaires incohérent')
    for row in expected:
        path = 'erp/document-artifacts/' + row['storage_key']
        if manifest['files'].get(path) != row['sha256']:
            raise ValueError('Copie documentaire absente du manifeste de sauvegarde')
    return expected


def suspend_restored_jobs(database):
    """New offline destination only. Append recovery evidence, never replay IO."""
    validate_job_history(database)
    with sqlite3.connect(database) as db:
        if not validate_queue_schema(db):
            return
        db.execute('PRAGMA foreign_keys=ON')
        db.row_factory = sqlite3.Row
        timestamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=' ')
        for job in db.execute('SELECT * FROM project_document_jobs ORDER BY id').fetchall():
            if job['execution_blocked']:
                continue
            if job['active_attempt_id']:
                attempt = db.execute('SELECT * FROM project_document_job_attempts WHERE id=?', (job['active_attempt_id'],)).fetchone()
                db.execute('INSERT INTO project_document_job_receipts '
                    '(id,project_id,job_id,item_id,attempt_id,artifact_id,outcome,error,created_at) VALUES (?,?,?,?,?,NULL,?,?,?)',
                    (str(uuid4()), job['project_id'], job['id'], attempt['item_id'], attempt['id'], 'interrupted',
                     'Sauvegarde restaurée : génération historique suspendue', timestamp))
            db.execute("UPDATE project_document_job_items SET status='interrupted' WHERE job_id=? AND status IN ('queued','running')", (job['id'],))
            status = 'interrupted' if job['status'] in {'queued', 'running'} else job['status']
            revision = job['revision'] + 1
            db.execute('UPDATE project_document_jobs SET execution_blocked=1,status=?,revision=?,active_attempt_id=NULL,updated_at=? WHERE id=?',
                       (status, revision, timestamp, job['id']))
            db.execute('INSERT INTO project_document_job_events (id,project_id,job_id,revision,kind,actor_id,detail,created_at) VALUES (?,?,?,?,?,?,?,?)',
                       (str(uuid4()), job['project_id'], job['id'], revision, 'store_restored', 'offline-restore',
                        freeze({'execution_blocked': True, 'previous_status': job['status']})[0], timestamp))
    validate_job_history(database)
