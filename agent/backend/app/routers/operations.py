"""Read-only operational dashboard and verification of the last coordinated backup."""
import json
import shutil
import sqlite3
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.engine import make_url

from ..db import get_db, APP_DIR
from ..models import Project, Task, Milestone, CdcItem, BrainLink, CdcAnalysisJob, MilestoneCandidate
from app.config import STORAGE_DIR, settings
from app.db import SessionLocal as BrainSession
from app.models import Source, Proposal
from app.services.project_access import erp_ids, filter_erp

router = APIRouter(prefix="/api/v1", tags=["operations"])


@router.get("/actions")
def actions(project_id: str | None = None, db: Session = Depends(get_db)):
    projects = {p.id: p for p in filter_erp(db.query(Project), Project.id).all()}
    if project_id and project_id not in projects:
        raise HTTPException(404, "Projet introuvable")
    active = {pid for pid, p in projects.items() if p.status == "active" and (not project_id or pid == project_id)}
    today, horizon = date.today().isoformat(), (date.today() + timedelta(days=14)).isoformat()
    rows = []

    def add(pid, kind, title, count=1, due_date="", tab="pilotage"):
        if pid in active:
            rows.append({"project_id": pid, "project_code": projects[pid].code, "kind": kind,
                         "title": title, "count": count, "due_date": due_date, "tab": tab})

    for task in db.query(Task).filter(Task.project_id.in_(active), Task.status.notin_(["done", "cancelled"])).all():
        if task.due_date and task.due_date <= horizon:
            add(task.project_id, "overdue" if task.due_date < today else "deadline", task.title,
                due_date=task.due_date, tab="planification")
    for milestone in db.query(Milestone).filter(Milestone.project_id.in_(active)).all():
        if not milestone.actual_date and milestone.due_date and milestone.due_date <= horizon:
            add(milestone.project_id, "overdue" if milestone.due_date < today else "milestone",
                milestone.title, due_date=milestone.due_date, tab="planification")
    dates_pending = Counter(row.project_id for row in db.query(MilestoneCandidate).filter_by(status="pending"))
    for pid, count in dates_pending.items():
        add(pid, "knowledge", "Dates de jalons à valider", count=count, tab="planification")
    unconfirmed, open_points = Counter(), Counter()
    for item in db.query(CdcItem).filter(CdcItem.project_id.in_(active), CdcItem.knowledge_status.notin_(["rejected", "superseded"])):
        if item.knowledge_status != "confirmed":
            unconfirmed[item.project_id] += 1
        if item.kind == "open_point":
            open_points[item.project_id] += 1
    for pid, count in unconfirmed.items():
        add(pid, "cdc_review", "Exigences CDC à confirmer", count=count, tab="cdc")
    for pid, count in open_points.items():
        add(pid, "open_point", "Points techniques ouverts", count=count, tab="cdc")
    for job in db.query(CdcAnalysisJob).filter(CdcAnalysisJob.project_id.in_(active), CdcAnalysisJob.status.in_(["failed", "cancelled", "interrupted"])):
        add(job.project_id, "analysis", "Analyse CDC à reprendre", tab="cdc")
    links = {link.brain_project_id: link.project_id for link in db.query(BrainLink).all()}
    with BrainSession() as brain:
        pending_mails = (brain.query(Source).filter_by(status="resolution_pending", source_type="email").count()
                         if erp_ids() is None else 0)
        proposals = Counter(p.project_id for p in brain.query(Proposal).filter(
            Proposal.status == "pending", Proposal.kind != "project_attach").all())
        for pid, count in proposals.items():
            if pid in links:
                add(links[pid], "knowledge", "Décisions de connaissance attendues", count=count, tab="connaissance")
    priority = {"overdue": 0, "analysis": 1, "deadline": 2, "milestone": 3, "cdc_review": 4, "open_point": 5, "knowledge": 6}
    rows.sort(key=lambda row: (priority[row["kind"]], row["due_date"], row["project_code"], row["title"]))
    return {"actions": rows, "pending_mails": pending_mails, "total": sum(row["count"] for row in rows),
            "horizon_days": 14}


def _marker():
    path = STORAGE_DIR / "backup-status.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "unreadable"}


@router.get("/operations/status")
def operation_status():
    brain = Path(make_url(settings.database_url).database)
    files = list((APP_DIR / "backups").glob("*.db")) + list((brain.parent / "backups").glob("brain-*.db"))
    files = list(set(p.resolve() for p in files if p.is_file()))
    marker = _marker()
    free = shutil.disk_usage(APP_DIR).free
    from app.services.storage_capacity import WARNING_BYTES, RESERVE_BYTES
    return {"backup": marker, "migration_backups": {"count": len(files), "bytes": sum(p.stat().st_size for p in files)},
            "disk_free_bytes": free, "disk_low": free < RESERVE_BYTES,
            "disk_warning": free < WARNING_BYTES, "disk_warning_bytes": WARNING_BYTES,
            "databases": {"brain_bytes": brain.stat().st_size if brain.exists() else 0,
                          "erp_bytes": (APP_DIR / "minipilot.db").stat().st_size if (APP_DIR / "minipilot.db").exists() else 0}}


@router.post("/operations/backup/verify")
def verify_last_backup():
    marker = _marker()
    if not marker or not marker.get("directory"):
        raise HTTPException(409, "Aucune sauvegarde globale enregistrée ; utiliser scripts/agent_backup.py hors ligne.")
    source = Path(marker["directory"]).resolve()
    try:
        from app.services.backup import verify_backup
        verification = verify_backup(source)
    except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
        marker["status"] = "verification_failed"
        (STORAGE_DIR / "backup-status.json").write_text(json.dumps(marker), encoding="utf-8")
        raise HTTPException(409, "Sauvegarde non vérifiée : " + str(exc)) from exc
    marker.update(verification)
    (STORAGE_DIR / "backup-status.json").write_text(json.dumps(marker), encoding="utf-8")
    return marker
