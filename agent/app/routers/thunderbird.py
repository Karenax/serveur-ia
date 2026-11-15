"""API Agent pour l'extension Thunderbird : import, présence et brouillons."""
from app.operational_limits import DOCUMENT_IMPORT_BYTES
import base64

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from backend.app.services.project_operator import current_operator

from ..db import SessionLocal, get_db
from ..models import AppSetting, Source, ThunderbirdJob
from ..services.mail_ingest import ingest_eml_bytes
from ..services.memory_factory import get_memory_adapter
from ..services.thunderbird import heartbeat, mail_control, presence_connected

router = APIRouter(prefix="/v1/thunderbird", tags=["thunderbird"])


class Presence(BaseModel):
    version: str = Field(max_length=40)
    accounts: list[dict] = Field(default_factory=list, max_length=50)
    folders: list[dict] = Field(default_factory=list, max_length=10000)
    sync: dict = Field(default_factory=dict)


@router.post("/bridge/heartbeat")
def report(body: Presence, db: Session = Depends(get_db)):
    return heartbeat(db, body.model_dump())


@router.get("/status")
def status(db: Session = Depends(get_db)):
    row = db.get(AppSetting, "thunderbird_status")
    value = row.value if row else {}
    seen = value.get("last_seen")
    connected = presence_connected(seen)
    if current_operator().id == 'kiara-thunderbird-reply':
        return {'connected': connected, 'reply_only': True, 'accounts': [
            {'id': account['id'], 'identities': account.get('identities', [])}
            for account in value.get('accounts', []) if isinstance(account, dict) and 'id' in account]}
    jobs = db.query(ThunderbirdJob).order_by(ThunderbirdJob.created_at.desc()).limit(20).all()
    return {**value, "connected": connected,
            "mail_config": mail_control(db),
            "jobs": [{"id": j.id, "kind": j.kind, "status": j.status, "result": j.result} for j in jobs]}


@router.post("/bridge/import")
async def import_mail(file: UploadFile = File(...), account_id: str = Form(""), folder_id: str = Form(""),
                      db: Session = Depends(get_db)):
    from ..services.thunderbird import mail_control
    control = mail_control(db)
    manual = db.query(ThunderbirdJob).filter_by(kind="sync", status="running").first()
    if control["source"] != "thunderbird" or (not control["auto_scan"] and not manual):
        raise HTTPException(409, "Synchronisation Thunderbird suspendue par les réglages des mails")
    selected = control["folder_ids"]
    if selected is not None and folder_id not in selected:
        raise HTTPException(409, "Ce dossier Thunderbird ne fait pas partie de la sélection")
    raw = await file.read(DOCUMENT_IMPORT_BYTES + 1)
    if not raw or len(raw) > DOCUMENT_IMPORT_BYTES:
        raise HTTPException(413 if raw else 400, "Mail vide ou trop volumineux")
    return await run_in_threadpool(lambda: __import__("asyncio").run(ingest_eml_bytes(
        db, raw, get_memory_adapter(SessionLocal), origin="thunderbird",
        origin_path=f"{account_id[:128]}/{folder_id[:512]}", defer_analysis=True)))


class SyncRequest(BaseModel):
    folder_ids: list[str] = Field(default_factory=list, max_length=1000)


@router.post("/sync")
def sync(body: SyncRequest, db: Session = Depends(get_db)):
    from ..services.settings_service import get_section, save_section
    if get_section(db, "mail").get("source") != "thunderbird":
        raise HTTPException(409, "Choisissez Thunderbird comme source dans Réglages → Mails")
    if not body.folder_ids:
        raise HTTPException(400, "Sélectionnez au moins un dossier Thunderbird")
    save_section(db, "mail", {"thunderbird_folder_ids": list(dict.fromkeys(body.folder_ids))})
    existing = db.query(ThunderbirdJob).filter_by(kind="sync", status="queued").first()
    if existing:
        existing.payload = body.model_dump()
        db.commit()
        return {"job_id": existing.id, "status": existing.status}
    job = ThunderbirdJob(kind="sync", payload=body.model_dump())
    db.add(job)
    db.commit()
    return {"job_id": job.id, "status": job.status}


@router.post("/bridge/configure")
def configure_selection(body: SyncRequest, db: Session = Depends(get_db)):
    return sync(body, db)


class Attachment(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    content_base64: str = Field(max_length=28_000_000)
    content_type: str = Field(default="application/octet-stream", max_length=128)


class DraftRequest(BaseModel):
    to: list[str] = Field(min_length=1, max_length=100)
    cc: list[str] = Field(default_factory=list, max_length=100)
    subject: str = Field(max_length=998)
    body: str = Field(max_length=500_000)
    identity_id: str = Field(min_length=1, max_length=128)
    reply_source_id: str | None = None
    open_window: bool = False
    attachments: list[Attachment] = Field(default_factory=list, max_length=20)


@router.post("/drafts")
def draft(body: DraftRequest, db: Session = Depends(get_db)):
    scoped = current_operator().id == 'kiara-thunderbird-reply'
    if scoped and not body.reply_source_id:
        raise HTTPException(403, 'Ouvrez un mail classé dans vos projets pour préparer une réponse')
    for address in body.to + body.cc:
        if "\r" in address or "\n" in address or "@" not in address:
            raise HTTPException(422, "Destinataire invalide")
    if "\r" in body.subject or "\n" in body.subject:
        raise HTTPException(422, "Objet invalide")
    total = 0
    for attachment in body.attachments:
        try:
            total += len(base64.b64decode(attachment.content_base64, validate=True))
        except ValueError:
            raise HTTPException(422, "Pièce jointe invalide") from None
    if total > 20 * 1024 * 1024:
        raise HTTPException(413, "20 Mio maximum de pièces jointes")
    payload = body.model_dump()
    if body.reply_source_id:
        source = db.get(Source, body.reply_source_id)
        if scoped:
            from ..services.project_access import brain_ids
            if (not source or source.source_type != 'email' or source.status != 'resolved'
                    or source.project_id not in brain_ids()):
                raise HTTPException(404, 'Mail introuvable dans vos projets')
        if not source or source.status == "discarded":
            raise HTTPException(409, "Mail d'origine absent ou écarté")
        message_id = (source.source_metadata or {}).get("message_id")
        if not message_id:
            raise HTTPException(409, "Message-ID du mail d'origine absent")
        payload["reply_message_id"] = message_id.strip("<>")
    job = ThunderbirdJob(kind="draft", payload=payload)
    db.add(job)
    db.commit()
    return {"job_id": job.id, "status": job.status}


@router.post("/bridge/jobs/claim")
def claim(db: Session = Depends(get_db)):
    job = db.query(ThunderbirdJob).filter_by(status="queued").order_by(ThunderbirdJob.created_at).first()
    if not job:
        return {"job": None}
    changed = db.query(ThunderbirdJob).filter_by(id=job.id, status="queued").update(
        {ThunderbirdJob.status: "running"})
    if not changed:
        db.rollback()
        return {"job": None}
    db.commit()
    return {"job": {"id": job.id, "kind": job.kind, "payload": job.payload}}


class Result(BaseModel):
    status: str = Field(pattern="^(done|failed|uncertain)$")
    result: dict = Field(default_factory=dict)


@router.post("/bridge/jobs/{job_id}/result")
def complete(job_id: str, body: Result, db: Session = Depends(get_db)):
    job = db.get(ThunderbirdJob, job_id)
    if not job:
        raise HTTPException(404, "Commande inconnue")
    if job.status not in ("running", body.status):
        raise HTTPException(409, "Commande déjà terminée")
    job.status = body.status
    job.result = body.result
    # Le contenu du brouillon appartient désormais à Thunderbird.
    job.payload = {}
    db.commit()
    return {"status": job.status}
