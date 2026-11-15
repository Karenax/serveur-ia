"""Single local worker and a durable SQLite queue, resumable at batch boundaries."""
import logging
import threading
from datetime import datetime, timezone

from fastapi import HTTPException
from app.db_support import utc_iso
from sqlalchemy import update

from ..db import SessionLocal
from ..models import CdcAnalysisJob, CdcSource, Project

logger = logging.getLogger(__name__)
ANALYSIS_LOCK = threading.RLock()
_wake = threading.Event()
_stop = threading.Event()
_thread = None
_queue_lock = threading.RLock()


def describe(job):
    return {"id": job.id, "project_id": job.project_id, "source_id": job.source_id,
            "status": job.status, "cancel_requested": job.cancel_requested,
            "completed_batches": job.completed_batches, "total_batches": job.total_batches,
            "progress": (round(job.completed_batches / job.total_batches * 95) if job.total_batches else 0)
                        if job.status != "completed" else 100,
            "result": job.result, "error": job.error, "created_at": utc_iso(job.created_at),
            "updated_at": utc_iso(job.updated_at)}


def enqueue(db, project_id, source_id, options):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    source = db.get(CdcSource, source_id)
    if not source or source.project_id != project_id:
        raise HTTPException(404, "Source CDC introuvable")
    with _queue_lock:
        previous = db.query(CdcAnalysisJob).filter_by(project_id=project_id, source_id=source_id).filter(
            CdcAnalysisJob.status.in_(["queued", "running"])).first()
        if previous:
            return describe(previous)
        job = CdcAnalysisJob(project_id=project_id, source_id=source_id, options=options)
        db.add(job)
        db.commit()
        _wake.set()
        return describe(job)


def recover_interrupted(db):
    db.query(CdcAnalysisJob).filter_by(status="running").update({"status": "queued", "error": "Reprise après interruption"})
    db.commit()


def process_next(should_stop=None):
    from ..routers.cdc import brain_ai_settings
    from .cdc_generation import generate_analysis, CdcAnalysisCancelled, CdcAnalysisInterrupted
    with ANALYSIS_LOCK, SessionLocal() as db:
        job = db.query(CdcAnalysisJob).filter_by(status="queued").order_by(CdcAnalysisJob.created_at, CdcAnalysisJob.id).first()
        if job is None:
            return False
        claimed = db.execute(update(CdcAnalysisJob).where(CdcAnalysisJob.id == job.id, CdcAnalysisJob.status == "queued")
                             .values(status="running", error=None, updated_at=datetime.now(timezone.utc)))
        db.commit()
        if claimed.rowcount != 1:
            return True
        db.refresh(job)
        try:
            job.result = generate_analysis(db, job.project_id, job.source_id, ai_cfg=brain_ai_settings(),
                                           **job.options, job_id=job.id, should_stop=should_stop)
            job.status = "completed"
            job.error = None
        except CdcAnalysisCancelled:
            db.rollback()
            db.refresh(job)
            job.status = "cancelled"
            job.error = "Analyse annulée ; les lots déjà enregistrés sont conservés."
        except CdcAnalysisInterrupted:
            db.rollback()
            db.refresh(job)
            job.status = "queued"
            job.error = "Reprise au prochain démarrage"
        except Exception as exc:
            db.rollback()
            db.refresh(job)
            job.status = "failed"
            job.error = "Analyse interrompue : " + (str(exc)[:500] if type(exc).__name__.startswith("Cdc") else type(exc).__name__)
            logger.exception("Échec du job CDC %s", job.id)
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        return True


def change_state(db, project_id, job_id, action):
    with _queue_lock:
        return _change_state(db, project_id, job_id, action)


def _change_state(db, project_id, job_id, action):
    job = db.get(CdcAnalysisJob, job_id)
    if not job or job.project_id != project_id:
        raise HTTPException(404, "Analyse introuvable")
    if action == "cancel":
        if job.status not in {"queued", "running"}:
            raise HTTPException(409, "Cette analyse est déjà terminée")
        job.cancel_requested = True
        if job.status == "queued":
            job.status = "cancelled"
    elif action == "retry":
        if job.status not in {"failed", "cancelled", "interrupted"}:
            raise HTTPException(409, "Cette analyse ne nécessite pas de reprise")
        if db.query(CdcAnalysisJob).filter(CdcAnalysisJob.project_id == project_id,
            CdcAnalysisJob.source_id == job.source_id, CdcAnalysisJob.id != job.id,
            CdcAnalysisJob.status.in_(["queued", "running"])).first():
            raise HTTPException(409, "Une analyse de cette source est déjà en attente ou en cours")
        job.cancel_requested = False
        job.status = "queued"
        job.error = None
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    _wake.set()
    return describe(job)


def _loop():
    while not _stop.is_set():
        try:
            if process_next(_stop.is_set):
                continue
        except Exception:
            logger.exception("Échec du worker CDC")
        _wake.wait(timeout=2)
        _wake.clear()


def start_worker():
    global _thread
    if _thread and _thread.is_alive():
        return
    with SessionLocal() as db:
        recover_interrupted(db)
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="cdc-worker", daemon=True)
    _thread.start()


def stop_worker():
    _stop.set()
    _wake.set()
    if _thread and _thread is not threading.current_thread():
        _thread.join(timeout=5)
