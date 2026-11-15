"""Router sources: upload .eml manuel + audio manuel."""
from app.operational_limits import DOCUMENT_IMPORT_BYTES
import asyncio
from starlette.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db, SessionLocal
from ..models import Project, Source, SourceArtifact
from ..services.ingestion import sha256_bytes
from ..services.mail_ingest import ingest_eml_bytes, _audit
from ..services.memory_factory import get_memory_adapter
from ..services.project_access import require_brain
from ..config import RAW_DIR

router = APIRouter(prefix="/v1/sources", tags=["sources"])
project_router = APIRouter(prefix="/v1/projects", tags=["sources"])


@router.post("")
def ingest_envelope(payload: dict, db: Session = Depends(get_db)):
    """Ingestion générique JSON (utilisée par tests / futurs connecteurs)."""
    raw = (payload.get("raw_text") or "").encode("utf-8")
    if len(raw) > DOCUMENT_IMPORT_BYTES:
        raise HTTPException(413, "Source trop volumineuse")
    h = sha256_bytes(raw + (payload.get("subject") or "").encode())
    if db.query(Source).filter_by(sha256=h).first():
        return {"status": "duplicate", "sha256": h}
    s = Source(source_type=payload.get("source_type", "email"), status="resolution_pending",
               author=payload.get("sender"), participants=payload.get("participants", []),
               original_uri=str(RAW_DIR / f"{h}.txt"), sha256=h,
               source_metadata={"subject": payload.get("subject")})
    (RAW_DIR / f"{h}.txt").write_bytes(raw)
    db.add(s)
    db.flush()
    db.add(SourceArtifact(source_id=s.id, kind="body_text",
                          content_text=payload.get("raw_text", ""),
                          content_json={"subject": payload.get("subject")}))
    _audit(db, "source.received.v1", None, "api", {"source_id": s.id})
    db.commit()
    return {"source_id": s.id, "status": s.status, "sha256": h}


@router.post("/upload-eml")
async def upload_eml(file: UploadFile = File(...),
                     candidate_project_id: str | None = Form(default=None),
                     db: Session = Depends(get_db)):
    raw = await file.read(DOCUMENT_IMPORT_BYTES + 1)
    if not raw:
        raise HTTPException(400, "Fichier vide")
    if len(raw) > DOCUMENT_IMPORT_BYTES:
        raise HTTPException(413, "Fichier trop volumineux")
    return await run_in_threadpool(lambda: asyncio.run(ingest_eml_bytes(
        db, raw, get_memory_adapter(SessionLocal), candidate_project_id,
        origin="upload", origin_path=file.filename)))


@project_router.post("/{project_id}/import-eml")
async def import_project_eml(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    require_brain(project_id)
    project = db.get(Project, project_id)
    if project is None or project.code.upper() == "DIVERS":
        raise HTTPException(404, "Projet introuvable")
    raw = await file.read(DOCUMENT_IMPORT_BYTES + 1)
    if not raw:
        raise HTTPException(400, "Fichier vide")
    if len(raw) > DOCUMENT_IMPORT_BYTES:
        raise HTTPException(413, "Fichier trop volumineux")
    result = await run_in_threadpool(lambda: asyncio.run(ingest_eml_bytes(
        db, raw, get_memory_adapter(SessionLocal), origin="project-upload",
        origin_path=file.filename, assigned_project=project)))
    return {"status": result["status"]}


@router.post("/upload-eml-bulk")
async def upload_eml_bulk(files: list[UploadFile] = File(...),
                          candidate_project_id: str | None = Form(default=None),
                          db: Session = Depends(get_db)):
    """Import multiple .eml d'un coup (sélection dossier côté navigateur)."""
    if len(files) > 500:
        raise HTTPException(413, "500 fichiers maximum par lot")
    out = {"scanned": len(files), "imported": 0, "duplicates": 0, "details": []}
    for f in files:
        raw = await f.read(DOCUMENT_IMPORT_BYTES + 1)
        if len(raw) > DOCUMENT_IMPORT_BYTES:
            raise HTTPException(413, "Fichier trop volumineux")
        if not raw:
            continue
        res = await run_in_threadpool(lambda: asyncio.run(ingest_eml_bytes(
            db, raw, get_memory_adapter(SessionLocal), candidate_project_id,
            origin="bulk-upload", origin_path=f.filename)))
        out["details"].append({"file": f.filename, "status": res["status"]})
        if res["status"] == "duplicate":
            out["duplicates"] += 1
        else:
            out["imported"] += 1
    return out


@router.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...),
                       source_type: str = Form(default="meeting"),
                       candidate_project_id: str | None = Form(default=None),
                       transcript: str = Form(default=""),
                       db: Session = Depends(get_db)):
    raw = await file.read(DOCUMENT_IMPORT_BYTES + 1)
    if not raw or len(raw) > DOCUMENT_IMPORT_BYTES:
        raise HTTPException(413 if raw else 400, "Audio vide ou trop volumineux")
    h = sha256_bytes(raw + transcript.encode())
    if db.query(Source).filter_by(sha256=h).first():
        return {"status": "duplicate", "sha256": h}
    dest = RAW_DIR / f"{h}.audio"
    dest.write_bytes(raw)
    project_id = candidate_project_id if candidate_project_id and db.query(Project).filter_by(id=candidate_project_id).first() else None
    status = "resolved" if project_id else "resolution_pending"
    s = Source(source_type=source_type if source_type in ("phone", "meeting") else "meeting",
               status="resolution_pending", project_id=None, author="manual-upload",
               original_uri=str(dest), sha256=h, mime_type=file.content_type,
               source_metadata={"filename": file.filename})
    db.add(s)
    db.flush()
    db.add(SourceArtifact(source_id=s.id, kind="transcription" if transcript else "audio_pending",
                          content_text=transcript or "(transcription en attente — STT non branché)",
                          content_json={"filename": file.filename}))
    _audit(db, "source.received.v1", project_id, "upload-audio", {"source_id": s.id})
    db.commit()
    if project_id:
        from ..services.triage import resolve_source
        from ..services.settings_service import get_section
        return await run_in_threadpool(resolve_source, db, get_memory_adapter(SessionLocal), s,
            db.get(Project, project_id), get_section(db, "ai"), "manual-upload")
    return {"source_id": s.id, "status": status, "project_id": project_id}


@router.get("/{source_id}")
def get_source(source_id: str, db: Session = Depends(get_db)):
    s = db.query(Source).filter_by(id=source_id).first()
    if not s:
        raise HTTPException(404, "Source inconnue")
    if s.status == "discarded":
        raise HTTPException(410, "Mail écarté : contenu purgé")
    arts = db.query(SourceArtifact).filter_by(source_id=s.id).all()
    from ..services.mail_preview import mail_preview
    preview = mail_preview(s)
    return {"id": s.id, "type": s.source_type, "status": s.status, "project_id": s.project_id,
            "received_at": s.received_at.isoformat() if s.received_at else None,
            "participants": s.participants or [],
            "author": s.author, "sha256": s.sha256, "metadata": s.source_metadata,
            "artifacts": [{"kind": a.kind, "id": a.id, "text": a.content_text or ""} for a in arts],
            **preview}


@router.get("/{source_id}/attachments/{index}")
def source_attachment(source_id: str, index: int, download: bool = False, db: Session = Depends(get_db)):
    from urllib.parse import quote
    from fastapi.responses import Response
    from ..services.mail_preview import original_message, attachment_parts, PREVIEW_TYPES
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(404, "Source inconnue")
    message = original_message(source)
    if message is None:
        raise HTTPException(404, "Mail original indisponible")
    parts = attachment_parts(message)
    if index < 0 or index >= len(parts):
        raise HTTPException(404, "Pièce jointe inconnue")
    part = parts[index]
    content = part.get_payload(decode=True)
    if content is None:
        raise HTTPException(422, "Pièce jointe illisible")
    mime = part.get_content_type()
    disposition = "inline" if not download and mime in PREVIEW_TYPES else "attachment"
    filename = (part.get_filename() or "piece-jointe").replace("\\", "/").rsplit("/", 1)[-1]
    return Response(content, media_type=mime, headers={
        "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(filename, safe='')}",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox; default-src 'none'",
        "Cache-Control": "no-store",
    })


@router.get("")
def list_sources(status: str = "all", offset: int = 0, limit: int = 100, source_type: str | None = None,
                 project_id: str | None = None,
                 db: Session = Depends(get_db)):
    from ..services.project_access import filter_brain, require_brain
    if project_id:
        require_brain(project_id)
    query = filter_brain(db.query(Source), Source.project_id).filter(Source.status != "discarded")
    if status != "all":
        query = query.filter_by(status=status)
    if source_type:
        query = query.filter_by(source_type=source_type)
    if project_id:
        query = query.filter_by(project_id=project_id)
    rows = query.order_by(Source.received_at.desc()).offset(max(0, offset)).limit(min(max(1, limit), 1000)).all()
    return [{"source_id": s.id, "type": s.source_type, "status": s.status,
             "received_at": s.received_at.isoformat() if s.received_at else None,
             "excerpt": next(((a.content_text or "")[:300] for a in s.artifacts
                              if a.kind == "body_text" and a.content_text), ""),
             "project_id": s.project_id, "author": s.author, "metadata": s.source_metadata}
            for s in rows]


@router.get("/{source_id}/raw")
def raw_source(source_id: str, db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(404, "Source inconnue")
    if source.status == "discarded":
        raise HTTPException(410, "Mail écarté : contenu purgé")
    if (source.source_metadata or {}).get("library_item_id"):
        from .source_library import original
        return original(source_id, db)
    files = [p for p in RAW_DIR.glob(f"{source.sha256}*")
             if p.is_file() and p.resolve().is_relative_to(RAW_DIR.resolve())]
    if not files:
        raise HTTPException(404, "Fichier brut absent ; les artefacts restent consultables")
    return FileResponse(files[0], media_type="application/octet-stream", filename=files[0].name)


@router.post("/{source_id}/discard")
def discard_source(source_id: str, db: Session = Depends(get_db)):
    from ..services.mail_discard import discard_mail
    return discard_mail(db, get_memory_adapter(SessionLocal), source_id)
