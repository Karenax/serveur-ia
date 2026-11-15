"""Persisted enrichment after a committed human mail classification."""
import asyncio
import logging
import os
import threading
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import or_, update

from ..db import SessionLocal
from ..models import Source, MemoryProjection, ProvenanceLink
from ..workspace_models import MailEnrichmentJob

logger = logging.getLogger(__name__)
_stop = threading.Event()
_wake = threading.Event()
_threads = {}


def wake():
    _wake.set()


def enqueue(db, source, project, needs_ai, items=0):
    db.flush()
    knowledge_ids = [row.knowledge_item_id for row in db.query(ProvenanceLink).filter_by(source_id=source.id)]
    ids = [row.id for row in db.query(MemoryProjection).filter(or_(
        MemoryProjection.source_id == source.id, MemoryProjection.knowledge_item_id.in_(knowledge_ids)))]
    job = db.query(MailEnrichmentJob).filter_by(source_id=source.id).first()
    if job is None:
        job = MailEnrichmentJob(source_id=source.id, project_id=project.id)
        db.add(job)
    else:
        job.revision += 1
        job.project_id = project.id
    job.projection_ids = sorted(set(ids + (job.projection_ids or [])))
    job.status, job.stage, job.error = "queued", "extraction" if needs_ai else "memory", None
    job.items = items
    job.updated_at = datetime.now(timezone.utc)
    db.flush()
    return job


def retry(db, job_id):
    job = db.get(MailEnrichmentJob, job_id)
    if not job:
        raise HTTPException(404, "Enrichissement introuvable")
    if job.status != "failed":
        raise HTTPException(409, "Cet enrichissement ne nécessite pas de reprise")
    source = db.get(Source, job.source_id)
    if not source or source.status != "resolved" or source.project_id != job.project_id:
        raise HTTPException(409, "Le classement du mail a changé")
    job.status, job.error = "queued", None
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    wake()
    return {"id": job.id, "status": job.status}


def recover_interrupted(db):
    db.query(MailEnrichmentJob).filter_by(status="running").update(
        {"status": "queued", "error": "Reprise après interruption"})
    db.commit()


def _current(db, job_id, revision, project_id):
    db.expire_all()
    job = db.get(MailEnrichmentJob, job_id)
    if not job or job.revision != revision or job.status != "running":
        return None
    source = db.get(Source, job.source_id)
    if not source or source.status != "resolved" or source.project_id != project_id:
        job.status, job.error = "cancelled", "Classement modifié ; résultat ignoré"
        db.commit()
        return None
    return job


def process_next(source_id=None, worker_stage=None):
    from .triage import _mail_text, extract_mail_candidates, store_mail_candidates
    from .settings_service import get_section
    from .memory_factory import get_memory_adapter
    from .projections import process
    with SessionLocal() as db:
        query = db.query(MailEnrichmentJob).filter_by(status="queued")
        if worker_stage:
            query = query.filter_by(stage=worker_stage)
        if source_id:
            query = query.filter_by(source_id=source_id)
        job = query.order_by(MailEnrichmentJob.updated_at, MailEnrichmentJob.id).first()
        if not job:
            return False
        key, revision, project_id = job.id, job.revision, job.project_id
        claimed = db.execute(update(MailEnrichmentJob).where(
            MailEnrichmentJob.id == key, MailEnrichmentJob.status == "queued", MailEnrichmentJob.revision == revision)
            .where(MailEnrichmentJob.stage == job.stage)
            .values(status="running", error=None, updated_at=datetime.now(timezone.utc)))
        db.commit()
        if claimed.rowcount != 1:
            return True
        job = _current(db, key, revision, project_id)
        if not job:
            return True
        source = db.get(Source, job.source_id)
        source_key, stage = source.id, job.stage
        subject, body, author = (source.source_metadata or {}).get("subject", ""), _mail_text(db, source), source.author or ""
        cfg = get_section(db, "ai")
    # AI runs with no live transaction/session. Other classifications can commit.
    try:
        candidates, origin = extract_mail_candidates(subject, body, author, cfg, require_ai=True) if stage == "extraction" else ([], "")
        with SessionLocal() as db:
            # Acquire a short write lock and recheck revision/status before applying inference.
            valid = db.query(Source).filter_by(id=source_key, status="resolved", project_id=project_id).update(
                {Source.status: "resolved"}, synchronize_session=False)
            job = _current(db, key, revision, project_id)
            if not valid or not job:
                db.rollback()
                return True
            if stage == "extraction":
                job.items = store_mail_candidates(db, db.get(Source, source_key), project_id, candidates, origin)
            job.stage = "memory"
            if worker_stage == "extraction":
                # Persist the handoff before any SDK call. Slow memory must not hold up AI extraction.
                job.status = "queued"
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
                wake()
                return True
            ids = list(job.projection_ids)
            db.commit()
            result = asyncio.run(process(db, get_memory_adapter(SessionLocal), projection_ids=ids, limit=max(1, len(ids))))
            job = _current(db, key, revision, project_id)
            if not job:
                return True
            job.status = "failed" if result["failed"] else "completed"
            job.error = "Indexation à reprendre ; le mail reste classé" if result["failed"] else None
            if not result["failed"]:
                job.stage = "completed"
            job.updated_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as exc:
        with SessionLocal() as db:
            job = _current(db, key, revision, project_id)
            if job:
                job.status, job.error = "failed", "Enrichissement à reprendre : " + type(exc).__name__
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
        logger.exception("Échec de l'enrichissement %s", key)
    return True


def start_worker():
    if os.environ.get("AGENT_TESTING") == "1" or any(thread.is_alive() for thread in _threads.values()):
        return
    with SessionLocal() as db:
        recover_interrupted(db)
    _stop.clear()

    def work(stage):
        while not _stop.is_set():
            try:
                if process_next(worker_stage=stage):
                    continue
            except Exception:
                logger.exception("Worker d'enrichissement des mails")
            _wake.wait(timeout=2)
            _wake.clear()
    for stage in ("extraction", "memory"):
        thread = threading.Thread(target=work, args=(stage,), name=f"mail-{stage}-worker", daemon=True)
        _threads[stage] = thread
        thread.start()


def stop_worker():
    _stop.set()
    wake()
    for thread in _threads.values():
        if thread is not threading.current_thread():
            thread.join(timeout=5)
