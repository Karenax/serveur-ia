"""Router scan dossier mails."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
from sqlalchemy.orm import Session
from ..db import get_db, SessionLocal
from ..services.mail_ingest import scan_folder, mail_scan_directory, DEFAULT_WATCH_DIR
from ..services.memory_factory import get_memory_adapter

router = APIRouter(prefix="/v1/ingest", tags=["ingest"])


class ScanRequest(BaseModel):
    folder: str | None = None
    candidate_project_id: str | None = None
    limit: int = Field(default=500, ge=1, le=1000)


@router.get("/default-folder")
def default_folder(db: Session = Depends(get_db)):
    from ..services.settings_service import get_section
    folder = get_section(db, "mail").get("folder") or DEFAULT_WATCH_DIR
    auto = get_section(db, "mail").get("auto_scan", True)
    ai_cfg = get_section(db, "ai")
    p = Path(folder)
    n = len(list(p.glob("*.eml"))) if p.exists() else 0
    return {"folder": folder, "exists": p.exists(), "eml_count": n, "auto_scan": auto,
            "ai": {"provider": ai_cfg.get("provider"), "model": ai_cfg.get("model"),
                   "enabled": ai_cfg.get("enabled")}}


@router.post("/scan")
def scan(req: ScanRequest, db: Session = Depends(get_db)):
    from ..services.settings_service import get_section
    config = get_section(db, "mail")
    if not req.folder and config.get("source") == "thunderbird":
        from .thunderbird import sync, SyncRequest, status
        folders = config.get("thunderbird_folder_ids")
        if folders is None:
            folders = (status(db).get("sync") or {}).get("folder_ids", [])
        result = sync(SyncRequest(folder_ids=folders), db)
        return {**result, "source": "thunderbird", "scanned": 0, "imported": 0, "duplicates": 0}
    allowed = config.get("folder") or DEFAULT_WATCH_DIR
    try:
        folder = mail_scan_directory(req.folder or allowed, allowed)
    except PermissionError as exc:
        raise HTTPException(403, "Le dossier est hors de l’emplacement EML configuré") from exc
    except ValueError as exc:
        raise HTTPException(400, "Un chemin de dossier EML absolu est requis") from exc
    except (OSError, RuntimeError) as exc:
        raise HTTPException(400, "Impossible d’accéder au dossier EML") from exc
    stats = scan_folder(folder, SessionLocal, get_memory_adapter(SessionLocal), req.candidate_project_id, req.limit)
    return stats


@router.get("/auto-status")
def auto_status():
    """État du scan automatique périodique (nouveaux mails uniquement)."""
    from ..services.auto_scan import AUTO_SCAN_STATE
    from ..services.settings_service import get_section
    from ..db import SessionLocal as _SessionLocal
    db = _SessionLocal()
    try:
        mail_cfg = get_section(db, "mail")
    finally:
        db.close()
    return {**AUTO_SCAN_STATE,
            "source": mail_cfg.get("source", "thunderbird"),
            "enabled": mail_cfg.get("auto_scan", True),
            "interval_minutes": mail_cfg.get("scan_interval_minutes", 5),
            "folder": mail_cfg.get("folder") or DEFAULT_WATCH_DIR}


@router.post("/reanalyze-pending")
def reanalyze_pending(limit: int = 20, db: Session = Depends(get_db)):
    """Relance l'IA sur les sources pending (sans réimporter les fichiers)."""
    from ..services.settings_service import get_section
    from ..services.triage import triage_pending
    from ..services.workspace_jobs import active_job
    from ..services.triage import TRIAGE_LOCK
    from fastapi import HTTPException
    if active_job(db):
        raise HTTPException(409, "Une analyse durable des mails est déjà en attente ou en cours")
    with TRIAGE_LOCK:
        if active_job(db):
            raise HTTPException(409, "Une analyse durable des mails est déjà en attente ou en cours")
        return triage_pending(db, get_memory_adapter(SessionLocal), get_section(db, "ai"), limit=limit)
