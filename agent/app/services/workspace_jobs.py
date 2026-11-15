"""Durable mail analysis, with a stable snapshot and an atomic per-mail audit."""
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import inspect, update, text
from sqlalchemy.engine import make_url

from app.db import SessionLocal, engine
from app.db_support import backup_sqlite, record_schema, utc_iso
from app.models import AuditLog, Source
from app.workspace_models import AssistantThread, TriageJob, MailEnrichmentJob
from .triage import TRIAGE_LOCK, pending_triage_query, triage_pending

logger = logging.getLogger(__name__)
_queue_lock = threading.RLock()
_stop = threading.Event()
_wake = threading.Event()
_thread = None
BATCH_SIZE = 5


def init_workspace_db():
    """Call before the canonical init_db: preserve a pre-migration SQLite copy."""
    tables = inspect(engine).get_table_names()
    targets = [TriageJob.__table__, AssistantThread.__table__, MailEnrichmentJob.__table__]
    if tables and any(table.name not in tables for table in targets) and engine.dialect.name == "sqlite":
        path = Path(make_url(str(engine.url)).database)
        if path.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            backup_sqlite(path, path.parent / "backups" / f"brain-workspace-{stamp}.db")
    # Existing projects remain authoritative; these tables contain UI/job state only.
    for table in targets:
        table.create(bind=engine, checkfirst=True)
    _audit_index()
    record_schema(engine, "brain", 6)
    record_schema(engine, "brain", 7)


def _audit_index():
    if engine.dialect.name == "sqlite" and "audit_logs" in inspect(engine).get_table_names():
        with engine.begin() as connection:
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_logs_triage_job "
                                    "ON audit_logs (correlation_id, event_type)"))


def describe(job):
    active = job.status in {"queued", "running"}
    return {"id": job.id, "status": job.status, "force": job.force,
            "processed": job.processed, "total": job.total,
            "progress": round(job.processed / job.total * 100, 1) if job.total else (100 if job.status == "completed" else 0),
            "cancel_requested": job.cancel_requested, "result": job.result or {}, "error": job.error,
            "can_cancel": active and not job.cancel_requested,
            "can_retry": job.status in {"failed", "cancelled", "interrupted"} and
                         (job.processed < job.total or bool((job.result or {}).get("errors"))),
            "created_at": utc_iso(job.created_at), "updated_at": utc_iso(job.updated_at)}


def active_job(db):
    return db.query(TriageJob).filter(TriageJob.status.in_(["queued", "running"])).first()


def enqueue(db, force=False):
    with _queue_lock:
        previous = active_job(db)
        if previous:
            if previous.force != force:
                raise HTTPException(409, "Une analyse des mails est déjà en attente ou en cours")
            return describe(previous)
        ids = [row.id for row in pending_triage_query(db, force).with_entities(Source.id)
               .order_by(Source.received_at, Source.id).all()]
        job = TriageJob(force=force, source_ids=ids, total=len(ids),
                        status="queued" if ids else "completed",
                        result={"triaged": 0, "skipped": 0, "divers": 0, "errors": []})
        db.add(job)
        db.commit()
        _wake.set()
        return describe(job)


def change_state(db, job_id, action):
    with _queue_lock:
        job = db.get(TriageJob, job_id)
        if not job:
            raise HTTPException(404, "Analyse des mails introuvable")
        if action == "cancel":
            if job.status not in {"queued", "running"}:
                raise HTTPException(409, "Cette analyse est déjà terminée")
            job.cancel_requested = True
            if job.status == "queued":
                job.status = "cancelled"
        elif action == "retry":
            if not describe(job)["can_retry"]:
                raise HTTPException(409, "Cette analyse ne nécessite pas de reprise")
            previous = active_job(db)
            if previous and previous.id != job.id:
                raise HTTPException(409, "Une autre analyse des mails est déjà en cours")
            job.cancel_requested = False
            job.status = "queued"
            job.error = None
            if (job.result or {}).get("errors"):
                # Revisit the same snapshot, skipping every committed mail by
                # its audit. This retries failures without forced re-analysis.
                job.processed = 0
                job.result = {"triaged": 0, "skipped": 0, "divers": 0, "errors": []}
        else:
            raise HTTPException(400, "Opération inconnue")
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        _wake.set()
        return describe(job)


def recover_interrupted(db):
    # A committed proposal and its job audit are atomic. On restart, a batch
    # whose counter was not yet committed skips those mails, including force mode.
    db.query(TriageJob).filter_by(status="running").update(
        {"status": "queued", "error": "Reprise après interruption"})
    db.commit()


def process_next(should_stop=None):
    from .memory_factory import get_memory_adapter
    from .settings_service import get_section
    with TRIAGE_LOCK, SessionLocal() as db:
        job = db.query(TriageJob).filter_by(status="queued").order_by(TriageJob.created_at, TriageJob.id).first()
        if not job:
            return False
        claimed = db.execute(update(TriageJob).where(TriageJob.id == job.id, TriageJob.status == "queued")
                             .values(status="running", error=None, updated_at=datetime.now(timezone.utc)))
        db.commit()
        if claimed.rowcount != 1:
            return True
        db.refresh(job)
        try:
            while job.processed < job.total:
                db.refresh(job)
                if job.cancel_requested:
                    job.status = "cancelled"
                    job.error = "Analyse annulée ; les propositions déjà enregistrées sont conservées."
                    break
                if should_stop and should_stop():
                    job.status = "queued"
                    job.error = "Reprise au prochain démarrage"
                    break
                batch = job.source_ids[job.processed:job.processed + BATCH_SIZE]
                done = {row.payload.get("source_id") for row in db.query(AuditLog).filter_by(
                    correlation_id=job.id, event_type="triage.proposed.v1").filter(
                    AuditLog.payload["source_id"].as_string().in_(batch)).all()}
                remaining = [sid for sid in batch if sid not in done]
                stats = triage_pending(db, get_memory_adapter(SessionLocal), get_section(db, "ai"),
                                       limit=BATCH_SIZE, force=job.force, source_ids=remaining, run_id=job.id)
                # triage commits each mail; reload cancellation and job state
                # rather than overwriting a concurrent API request.
                db.refresh(job)
                result = dict(job.result or {})
                for key in ("triaged", "divers", "skipped", "auto_classified"):
                    result[key] = result.get(key, 0) + stats.get(key, 0)
                result["triaged"] += len(batch) - len(remaining)
                result["skipped"] += len(remaining) - stats.get("scanned", 0)
                result["errors"] = result.get("errors", []) + stats.get("errors", [])
                job.result = result
                job.processed += len(batch)
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
            else:
                job.status = "failed" if (job.result or {}).get("errors") else "completed"
                job.error = (f"{len((job.result or {}).get('errors', []))} mail(s) en échec ; consulter les détails"
                             if (job.result or {}).get("errors") else None)
        except Exception as exc:
            db.rollback()
            db.refresh(job)
            job.status = "failed"
            job.error = "Analyse interrompue : " + type(exc).__name__
            logger.exception("Échec de l'analyse des mails %s", job.id)
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        return True


def _loop():
    while not _stop.is_set():
        try:
            if process_next(_stop.is_set):
                continue
        except Exception:
            logger.exception("Échec du worker de classement des mails")
        _wake.wait(timeout=2)
        _wake.clear()


def start_worker():
    global _thread
    if os.environ.get("AGENT_TESTING") == "1" or (_thread and _thread.is_alive()):
        return
    _audit_index()
    with SessionLocal() as db:
        recover_interrupted(db)
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="mail-triage-worker", daemon=True)
    _thread.start()


def stop_worker():
    _stop.set()
    _wake.set()
    if _thread and _thread is not threading.current_thread():
        _thread.join(timeout=5)
