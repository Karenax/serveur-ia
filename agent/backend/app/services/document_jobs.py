"""Transactional preparation queue. Caller commits commands; worker owns its sessions.

Import starts neither a worker thread nor network publication. Trusted coordinator
must ensure a previous worker has stopped before explicit interruption recovery.
"""
import hashlib
import json
from pathlib import PurePosixPath

from fastapi import HTTPException
from sqlalchemy import func, inspect, select, update

from app.db_support import utc_iso
from ..project_document_job_models import DOCUMENT_JOB_TABLES, DocumentJob, DocumentJobItem, DocumentJobAttempt, DocumentJobArtifact, DocumentJobReceipt, DocumentJobEvent
from ..project_document_job_schemas import DocumentBatchSubmit
from ..project_document_schemas import DocumentPrepare
from ..project_identity_models import now, uid
from . import document_forms, project_documents
from .document_job_artifacts import read_artifact, write_artifact
from .document_job_schema import validate_job_schema
from .document_paths import _relative
from .document_template_catalogue import catalogue
from .project_identity import _project
from .project_operator import current_operator


def frozen(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    if len(raw.encode())>4*1024*1024:
        raise HTTPException(422, 'Capture documentaire trop volumineuse (4 Mio maximum)')
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def _ready(db, *, write=False):
    names = set(inspect(db.connection()).get_table_names())
    present = {table.name for table in DOCUMENT_JOB_TABLES} & names
    if not present:
        if write:
            raise HTTPException(409, 'File documentaire à installer explicitement')
        return False
    try:
        plan = validate_job_schema(db.get_bind())
    except ValueError as exc:
        raise HTTPException(409, 'Schéma de file documentaire incompatible') from exc
    if plan['created_tables'] or plan['created_triggers']:
        raise HTTPException(409, 'File documentaire partielle ou non protégée')
    return True


def _job(db, project_id, job_id, *, write=False):
    _project(db, project_id, write=write)
    _ready(db, write=True)
    job = db.scalar(select(DocumentJob).where(DocumentJob.project_id == project_id, DocumentJob.id == job_id)
                    .execution_options(populate_existing=True))
    if job is None:
        raise HTTPException(404, 'Lot documentaire introuvable')
    if hashlib.sha256(job.snapshot.encode()).hexdigest() != job.sha256:
        raise HTTPException(409, 'Capture du lot documentaire incohérente')
    return job


def _items(db, job):
    return list(db.scalars(select(DocumentJobItem).where(DocumentJobItem.job_id == job.id)
                           .order_by(DocumentJobItem.position).execution_options(populate_existing=True)))


def _event(db, job, kind, detail=None):
    db.add(DocumentJobEvent(project_id=job.project_id, job_id=job.id, revision=job.revision, kind=kind,
                            actor_id=document_forms._actor(current_operator()), detail=frozen(detail or {})[0]))


def _change(db, job, expected_revision, **values):
    if type(expected_revision) is not int or expected_revision < 1:
        raise HTTPException(422, 'Révision entière du lot requise')
    changed = db.execute(update(DocumentJob).where(DocumentJob.id == job.id, DocumentJob.revision == expected_revision)
                         .values(**values, revision=expected_revision + 1, updated_at=now())
                         .execution_options(synchronize_session=False)).rowcount
    if changed != 1:
        raise HTTPException(409, 'Lot modifié : relire avant de réessayer')
    db.refresh(job)


def source_destination(item):
    """Derive the suggested publication location from the approved source."""
    if hashlib.sha256(item.snapshot.encode()).hexdigest() != item.sha256:
        raise HTTPException(409, 'Aperçu de la copie modifié')
    report = json.loads(item.snapshot)['preview']
    source = report['source']
    relative = _relative(source['relative_path'])
    if not relative:
        return None
    parent = str(PurePosixPath(relative).parent)
    return {'link_id': source['link_id'], 'relative_directory': '' if parent == '.' else parent,
            'replace_existing': source['filename'].casefold() == report['output_filename'].casefold()}


def detail(db, project_id, job_id):
    job = _job(db, project_id, job_id)
    items = _items(db, job)
    if len(items) != job.total:
        raise HTTPException(409, 'Nombre de fichiers du lot incohérent')
    processed = sum(item.status in {'succeeded', 'failed', 'cancelled', 'interrupted'} for item in items)
    last = [item.last_attempt_id for item in items if item.last_attempt_id]
    receipts = {r.attempt_id: r for r in db.scalars(select(DocumentJobReceipt).where(
        DocumentJobReceipt.job_id == job.id, DocumentJobReceipt.attempt_id.in_(last)))}
    return {'id': job.id, 'project_id': job.project_id, 'revision': job.revision, 'status': job.status,
            'processed': processed, 'total': job.total, 'progress': round(100 * processed / job.total, 1),
            'cancel_requested': job.cancel_requested, 'actor_id': job.actor_id,
            'execution_blocked': job.execution_blocked,
            'created_at': utc_iso(job.created_at), 'updated_at': utc_iso(job.updated_at),
            'can_cancel': not job.execution_blocked and current_operator().role != 'reader' and job.status in {'queued', 'running'} and not job.cancel_requested,
            'can_retry': not job.execution_blocked and current_operator().role != 'reader' and job.status in {'failed', 'interrupted', 'cancelled'} and any(i.status != 'succeeded' for i in items),
            'items': [{'id': i.id, 'document_id': i.document_id, 'position': i.position, 'status': i.status,
                       'last_attempt_id': i.last_attempt_id,
                       'artifact_id': receipts[i.last_attempt_id].artifact_id if i.last_attempt_id in receipts else None,
                       'error': receipts[i.last_attempt_id].error if i.last_attempt_id in receipts else '',
                       'publication_suggestion': source_destination(i) if i.status == 'succeeded' and not job.execution_blocked else None}
                      for i in items]}


def submit(db, project_id, command: DocumentBatchSubmit):
    _project(db, project_id, write=True)
    _ready(db, write=True)
    raw, digest = frozen(command.model_dump())
    existing = db.scalar(select(DocumentJob).where(DocumentJob.project_id == project_id, DocumentJob.command_id == command.command_id))
    if existing:
        if existing.sha256 != digest or existing.snapshot != raw:
            raise HTTPException(409, 'Cette commande désigne déjà un autre lot')
        return detail(db, project_id, existing.id)  # No disk reread on replay.
    captures = []
    for item in command.items:
        draft = document_forms.draft(db, project_id, item.document_id)
        if draft['revision'] != item.expected_draft_revision:
            raise HTTPException(409, 'Choix documentaires modifiés depuis la vérification')
        report = project_documents.preview(db, project_id, item)
        expected = (item.expected_source_sha256, item.expected_link_sha256, item.expected_values_sha256,
                    item.expected_identity_revision, item.expected_planning_revision)
        actual = (report['source_sha256'], report['link_sha256'], report['values_sha256'],
                  report['field_values']['identity_revision'], report['field_values']['planning_revision'])
        if expected != actual or not report['can_prepare']:
            raise HTTPException(409, 'Aperçu documentaire modifié ou incomplet : vérifier de nouveau')
        captures.append({'command': item.model_dump(), 'preview': report,
                         'catalogue_sha256': frozen(catalogue())[1], 'draft_version_id': draft['version_id']})
    # Validate every bounded capture before the first write, including callers
    # that manage a larger transaction and cannot immediately roll it back.
    validated = [(value, *frozen(value)) for value in captures]
    job = DocumentJob(project_id=project_id, command_id=command.command_id, snapshot=raw, sha256=digest,
                      actor_id=document_forms._actor(current_operator()), total=len(captures), revision=1, status='queued')
    db.add(job)
    db.flush()
    for position, (value, capture, item_digest) in enumerate(validated):
        db.add(DocumentJobItem(project_id=project_id, job_id=job.id, document_id=value['command']['document_id'],
                               link_id=value['command']['link_id'], draft_version_id=value['draft_version_id'],
                               position=position, snapshot=capture, sha256=item_digest, status='queued'))
    _event(db, job, 'submitted')
    db.flush()
    return detail(db, project_id, job.id)


def cancel(db, project_id, job_id, expected_revision):
    job = _job(db, project_id, job_id, write=True)
    if job.execution_blocked or job.status not in {'queued', 'running'} or job.cancel_requested:
        raise HTTPException(409, 'Ce lot ne peut plus être arrêté')
    _change(db, job, expected_revision, cancel_requested=True,
            status='running' if job.active_attempt_id else 'cancelled')
    for item in _items(db, job):
        if item.status == 'queued':
            item.status = 'cancelled'
    _event(db, job, 'cancel_requested')
    db.flush()
    return detail(db, project_id, job.id)


def retry(db, project_id, job_id, expected_revision):
    job = _job(db, project_id, job_id, write=True)
    if job.execution_blocked or job.status not in {'failed', 'cancelled', 'interrupted'} or job.active_attempt_id:
        raise HTTPException(409, 'Lot encore actif ou déjà terminé')
    _change(db, job, expected_revision, status='queued', cancel_requested=False)
    for item in _items(db, job):
        if item.status != 'succeeded':
            item.status = 'queued'
    _event(db, job, 'retry_requested')
    db.flush()
    return detail(db, project_id, job.id)


def claim(db, project_id, job_id, expected_revision):
    job = _job(db, project_id, job_id, write=True)
    if job.execution_blocked or job.status not in {'queued', 'running'} or job.cancel_requested or job.active_attempt_id:
        raise HTTPException(409, 'Lot arrêté ou déjà pris en charge')
    item = next((i for i in _items(db, job) if i.status == 'queued'), None)
    if item is None:
        raise HTTPException(409, 'Aucun fichier en attente dans ce lot')
    if hashlib.sha256(item.snapshot.encode()).hexdigest() != item.sha256:
        raise HTTPException(409, 'Capture du fichier incohérente')
    attempt_id = uid()
    _change(db, job, expected_revision, status='running', active_attempt_id=attempt_id)
    number = (db.scalar(select(func.max(DocumentJobAttempt.number)).where(DocumentJobAttempt.item_id == item.id)) or 0) + 1
    attempt = DocumentJobAttempt(id=attempt_id, project_id=project_id, job_id=job.id, item_id=item.id,
                                 number=number, actor_id=document_forms._actor(current_operator()))
    db.add(attempt)
    item.status, item.last_attempt_id = 'running', attempt_id
    _event(db, job, 'item_started', {'item_id': item.id, 'attempt_id': attempt_id})
    db.flush()
    return {'attempt_id': attempt_id, 'item_id': item.id, 'snapshot': item.snapshot, 'revision': job.revision,
            'link_id': item.link_id, 'draft_version_id': item.draft_version_id}


def finish(db, project_id, job_id, attempt_id, *, artifact=None, error='', interrupted=False):
    job = _job(db, project_id, job_id, write=True)
    if job.status != 'running' or job.active_attempt_id != attempt_id:
        raise HTTPException(409, 'Tentative déjà terminée ou remplacée')
    attempt = db.get(DocumentJobAttempt, attempt_id)
    item = db.get(DocumentJobItem, attempt.item_id) if attempt and attempt.job_id == job.id else None
    if item is None or item.status != 'running' or item.last_attempt_id != attempt_id:
        raise HTTPException(409, 'Tentative de fichier incohérente')
    outcome = 'interrupted' if interrupted else 'succeeded' if artifact is not None else 'failed'
    if interrupted and artifact is not None:
        raise HTTPException(422, 'Tentative interrompue sans résultat validé')
    _change(db, job, job.revision, active_attempt_id=None)
    artifact_id = None
    if artifact is not None:
        artifact_id = uid()
        db.add(DocumentJobArtifact(id=artifact_id, project_id=project_id, job_id=job.id,
            item_id=item.id, attempt_id=attempt_id, **artifact))
        db.flush()
    db.add(DocumentJobReceipt(project_id=project_id, job_id=job.id, item_id=item.id, attempt_id=attempt_id,
        artifact_id=artifact_id, outcome=outcome, error='' if artifact else str(error)[:1000]))
    item.status = outcome
    db.flush()
    items = _items(db, job)
    if interrupted:
        job.status = 'interrupted'
        for row in items:
            if row.status == 'queued':
                row.status = 'interrupted'
    elif job.cancel_requested:
        job.status = 'cancelled'
    elif not any(row.status == 'queued' for row in items):
        job.status = 'completed' if all(row.status == 'succeeded' for row in items) else 'failed'
    _event(db, job, 'item_' + outcome, {'item_id': item.id, 'attempt_id': attempt_id, 'artifact_id': artifact_id})
    db.flush()
    return detail(db, project_id, job.id)


def recover_interrupted(db, project_id, job_id, expected_revision):
    """Call only after coordinator has verified the former worker is stopped."""
    job = _job(db, project_id, job_id, write=True)
    if job.revision != expected_revision or job.status != 'running':
        raise HTTPException(409, 'Aucune tentative interrompue à reprendre')
    if not job.active_attempt_id:
        _change(db, job, expected_revision, status='interrupted')
        for item in _items(db, job):
            if item.status == 'queued':
                item.status = 'interrupted'
        _event(db, job, 'worker_interrupted')
        db.flush()
        return detail(db, project_id, job.id)
    return finish(db, project_id, job_id, job.active_attempt_id, interrupted=True,
                  error='Traitement interrompu avant validation du reçu')


def run_one(factory, project_id, job_id, *, storage_root):
    """Trusted worker: durable claim, IO outside transaction, durable outcome."""
    with factory() as db:
        state = detail(db, project_id, job_id)
        capture = claim(db, project_id, job_id, state['revision'])
        db.commit()
    artifact, error = None, ''
    try:
        value = json.loads(capture['snapshot'])
        if value['catalogue_sha256'] != frozen(catalogue())[1]:
            raise HTTPException(409, 'Catalogue documentaire modifié depuis la soumission')
        command = dict(value['command'])
        command.pop('expected_draft_revision')
        command['link_id'] = capture['link_id']
        payload = DocumentPrepare.model_validate(command)
        with factory() as db:
            content, report = project_documents.prepare_copy(db, project_id, payload)
        key = uid()
        artifact = {**write_artifact(storage_root, key, content), 'filename': report['output_filename'],
                    'provenance': frozen(report)[0]}
    except Exception as exc:
        error = str(exc.detail) if isinstance(exc, HTTPException) else 'Préparation documentaire impossible ; consulter le journal serveur'
    # Cancel may race completion: reread the current revision, preserving the
    # same owned bytes and attempt. Never regenerate content on a CAS conflict.
    for count in range(3):
        with factory() as db:
            try:
                result = finish(db, project_id, job_id, capture['attempt_id'], artifact=artifact, error=error)
                db.commit()
                return result
            except HTTPException as exc:
                db.rollback()
                if exc.status_code != 409 or count == 2:
                    raise


def artifact_content(db, project_id, artifact_id, *, storage_root):
    _project(db, project_id)
    _ready(db, write=True)
    artifact = db.scalar(select(DocumentJobArtifact).where(DocumentJobArtifact.project_id == project_id,
                                                          DocumentJobArtifact.id == artifact_id))
    if artifact is None:
        raise HTTPException(404, 'Copie documentaire introuvable')
    receipt = db.scalar(select(DocumentJobReceipt).where(DocumentJobReceipt.artifact_id == artifact.id,
                                                         DocumentJobReceipt.outcome == 'succeeded'))
    if receipt is None:
        raise HTTPException(409, 'Copie sans reçu validé')
    return read_artifact(storage_root, artifact), artifact.filename
