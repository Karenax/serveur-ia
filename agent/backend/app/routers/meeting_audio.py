"""Three explicit phases: transcription, speaker review, LLM synthesis/publication."""
from app.operational_limits import AUDIO_IMPORT_BYTES
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import Field
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.config import RAW_DIR
from app.db import SessionLocal as BrainSession, get_db as brain_db
from app.models import AuditLog, MeetingRecording, Project as BrainProject, Source
from app.services import meeting_audio as service
from ..db import SessionLocal as ERP
from ..models import BrainLink, Project
from ..schemas import DomainInput, IsoDate

router = APIRouter(prefix="/api/v1", tags=["meeting-audio"])

MAX_BYTES = AUDIO_IMPORT_BYTES
EXTENSIONS = {".wav", ".mp3", ".m4a", ".mp4", ".ogg", ".opus", ".webm", ".flac", ".aac", ".wma"}
MIMES = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".mp4": "video/mp4",
         ".ogg": "audio/ogg", ".opus": "audio/ogg", ".webm": "audio/webm", ".flac": "audio/flac",
         ".aac": "audio/aac", ".wma": "audio/x-ms-wma"}


def linked_project(project_id):
    with ERP() as erp:
        if not erp.get(Project, project_id):
            raise HTTPException(404, "Projet introuvable")
        link = erp.get(BrainLink, project_id)
        if not link:
            raise HTTPException(409, "Relier ce projet au cœur de connaissance dans l’onglet Connaissance avant d’importer une réunion")
        return link.brain_project_id


def recording(db, project_id, recording_id):
    brain_id = linked_project(project_id)
    row = db.query(MeetingRecording).filter_by(id=recording_id, erp_project_id=project_id, project_id=brain_id).first()
    if not row:
        raise HTTPException(404, "Enregistrement introuvable dans ce projet")
    return row


@router.get("/meeting-audio/status")
def audio_status():
    runtime = service.runtime_status()
    return {k: v for k, v in runtime.items() if k not in {"python", "models_dir"}}


@router.get("/projects/{project_id}/recordings")
def list_recordings(project_id: str, db: Session = Depends(brain_db)):
    with ERP() as erp:
        if not erp.get(Project, project_id):
            raise HTTPException(404, "Projet introuvable")
        link = erp.get(BrainLink, project_id)
        if not link:
            return []
        brain_id = link.brain_project_id
    rows = db.query(MeetingRecording).filter_by(erp_project_id=project_id, project_id=brain_id).order_by(MeetingRecording.created_at.desc()).limit(100).all()
    return [{k: v for k, v in service.public_recording(row).items() if k not in {"segments", "speaker_names", "summary"}} for row in rows]


def _verify_original(path, digest, size=None, *, sync=False):
    """Never acknowledge an existing path until its contents match the import."""
    try:
        root = RAW_DIR.resolve(strict=True)
        candidate = Path(path).resolve(strict=True)
        if not candidate.is_relative_to(root):
            raise ValueError('outside audio storage')
        with candidate.open('r+b' if sync else 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size < 1 or info.st_size > MAX_BYTES or (size is not None and info.st_size != size):
                raise ValueError('different size or non-regular file')
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != digest:
                raise ValueError('different audio')
            if sync:
                try:
                    os.fsync(stream.fileno())
                except OSError as error:
                    raise HTTPException(503, 'La copie audio ne peut pas être confirmée sur le stockage ; conservez le fichier local.') from error
            after = os.fstat(stream.fileno())
            if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (
                    after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError('audio changed while being checked')
            return {'sha256': actual, 'size': info.st_size}
    except (OSError, ValueError, TypeError) as error:
        raise HTTPException(409, 'La copie audio déjà présente est inaccessible ou différente ; aucune copie n’a été remplacée.') from error


def _install_original(destination, raw, digest):
    """Stage a synced copy and publish it without replacing any existing file."""
    if destination.exists():
        _verify_original(destination, digest, len(raw), sync=True)
        return
    staged = None
    installed = False
    try:
        descriptor, name = tempfile.mkstemp(prefix=f'.{digest[:12]}-', suffix='.pending', dir=RAW_DIR)
        staged = Path(name)
        with os.fdopen(descriptor, 'wb') as stream:
            if stream.write(raw) != len(raw):
                raise OSError('incomplete audio staging')
            stream.flush()
            os.fsync(stream.fileno())
        _verify_original(staged, digest, len(raw))
        try:
            os.link(staged, destination)
        except FileExistsError:
            pass  # Another writer won; its file still has to be verified.
        except OSError:
            # Some filesystems do not support hard links. Exclusive creation
            # still prevents replacement; an interrupted partial file is kept
            # and rejected on a later retry rather than acknowledged.
            try:
                with destination.open('xb') as stream:
                    if stream.write(raw) != len(raw):
                        raise OSError('incomplete audio publication')
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError:
                pass
        _verify_original(destination, digest, len(raw), sync=True)
        installed = True
    except HTTPException:
        raise
    except OSError as error:
        raise HTTPException(503, 'La copie audio n’a pas pu être enregistrée ; réessayez en conservant le fichier local.') from error
    finally:
        if installed and staged is not None:
            try:
                staged.unlink()
            except OSError:
                pass  # A verified destination exists; leave the staged copy for later inspection.


def import_audio(project_id, title, date, speakers, filename, mime_type, raw):
    brain_id = linked_project(project_id)
    digest = hashlib.sha256(raw).hexdigest()
    with service._lock, BrainSession() as db:
        if not db.get(BrainProject, brain_id):
            raise HTTPException(409, "Liaison vers un projet Brain introuvable")
        source = db.query(Source).filter_by(sha256=digest).first()
        if source:
            previous = db.query(MeetingRecording).filter_by(source_id=source.id, erp_project_id=project_id, project_id=brain_id).first()
            if previous and previous.erp_project_id == project_id and previous.project_id == brain_id:
                _verify_original(source.original_uri, digest, len(raw))
                return service.public_recording(previous)
            raise HTTPException(409, "Cet audio est déjà conservé comme source ; utiliser son enregistrement existant")
        destination = RAW_DIR / f"{digest}{Path(filename).suffix.lower()}"
        _install_original(destination, raw, digest)
        source = Source(project_id=brain_id, source_type="meeting", status="resolved", author="meeting-upload",
                        original_uri=str(destination), sha256=digest, mime_type=mime_type,
                        source_metadata={"filename": filename, "subject": title, "raw_path": str(destination)})
        db.add(source)
        db.flush()
        row = MeetingRecording(project_id=brain_id, source_id=source.id, erp_project_id=project_id,
                               title=title, date=date, num_speakers=speakers, filename=filename)
        db.add(row)
        db.flush()
        db.add(AuditLog(event_type="meeting.audio.received.v1", project_id=brain_id, actor="user", payload={"recording_id": row.id, "source_id": source.id}))
        db.commit()
        return service.public_recording(row)


@router.post("/projects/{project_id}/recordings", status_code=201)
async def upload_recording(project_id: str, file: UploadFile = File(...), title: str = Form(...),
                           date: IsoDate = Form(""), num_speakers: int = Form(0, ge=0, le=20)):
    filename = Path((file.filename or "").replace("\\", "/")).name
    if Path(filename).suffix.lower() not in EXTENSIONS:
        raise HTTPException(400, "Format audio non pris en charge : WAV, MP3, M4A, MP4, OGG, WebM, FLAC, AAC ou WMA")
    if not title.strip() or len(title.strip()) > 255 or len(filename) > 255:
        raise HTTPException(422, "Titre et nom de fichier limités à 255 caractères")
    raw = await file.read(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES:
        raise HTTPException(413 if raw else 400, "Audio vide ou supérieur à 256 Mio")
    return await run_in_threadpool(import_audio, project_id, title.strip(), date, num_speakers, filename, file.content_type, raw)


@router.get("/projects/{project_id}/recordings/{recording_id}")
def get_recording(project_id: str, recording_id: str, db: Session = Depends(brain_db)):
    return service.public_recording(recording(db, project_id, recording_id))


@router.get("/projects/{project_id}/recordings/{recording_id}/audio")
def get_audio(project_id: str, recording_id: str, db: Session = Depends(brain_db)):
    row = recording(db, project_id, recording_id)
    source = db.get(Source, row.source_id)
    path = Path(source.original_uri).resolve()
    if not path.is_relative_to(RAW_DIR.resolve()) or not path.is_file():
        raise HTTPException(404, "Fichier audio indisponible dans le stockage local")
    return FileResponse(path, media_type=MIMES.get(Path(row.filename).suffix.lower(), "application/octet-stream"),
                        filename=row.filename, content_disposition_type="inline", headers={"X-Content-Type-Options": "nosniff"})


@router.get("/projects/{project_id}/recordings/{recording_id}/audio-integrity")
def audio_integrity(project_id: str, recording_id: str, response: Response, db: Session = Depends(brain_db)):
    row = recording(db, project_id, recording_id)
    source = db.get(Source, row.source_id)
    if not source or not isinstance(source.sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', source.sha256):
        raise HTTPException(409, 'La copie audio du serveur ne peut pas être vérifiée.')
    verified = _verify_original(source.original_uri, source.sha256, sync=True)
    response.headers['Cache-Control'] = 'no-store'
    return {'recording_id': row.id, 'source_id': source.id, **verified}


@router.post("/projects/{project_id}/recordings/{recording_id}/transcribe", status_code=202)
def transcribe(project_id: str, recording_id: str, db: Session = Depends(brain_db)):
    with service._lock:
        row = recording(db, project_id, recording_id)
        try:
            service.queue_job(db, row, "transcription")
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return service.public_recording(row)


class TranscriptReview(DomainInput):
    revision: int = Field(ge=1)
    segments: list[service.TranscriptSegment] = Field(min_length=1, max_length=20000)
    speaker_names: dict[str, str] = Field(default_factory=dict)
    confirm: bool = Field(default=False, alias="validate")


@router.put("/projects/{project_id}/recordings/{recording_id}/transcript")
def review_transcript(project_id: str, recording_id: str, payload: TranscriptReview, background: BackgroundTasks,
                      db: Session = Depends(brain_db)):
    with service._lock:
        row = recording(db, project_id, recording_id)
        try:
            service.save_review(db, row, payload.segments, payload.speaker_names, payload.revision, payload.confirm)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        if payload.confirm:
            background.add_task(service.index_project, row.project_id)
        return service.public_recording(row)


@router.post("/projects/{project_id}/recordings/{recording_id}/synthesize", status_code=202)
def synthesize(project_id: str, recording_id: str, db: Session = Depends(brain_db)):
    with service._lock:
        row = recording(db, project_id, recording_id)
        try:
            service.queue_job(db, row, "synthesis")
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return service.public_recording(row)


@router.post("/projects/{project_id}/recordings/{recording_id}/cancel")
def cancel(project_id: str, recording_id: str, db: Session = Depends(brain_db)):
    with service._lock:
        row = recording(db, project_id, recording_id)
        if row.job_status in service.BUSY:
            row.cancel_requested = True
            if row.job_status == "queued":
                row.job_status = "cancelled"
            db.commit()
        return service.public_recording(row)


class PublishSummary(DomainInput):
    revision: int = Field(ge=1)
    summary: service.MeetingSummary


@router.post("/projects/{project_id}/recordings/{recording_id}/publish")
def publish_summary(project_id: str, recording_id: str, payload: PublishSummary, background: BackgroundTasks,
                    db: Session = Depends(brain_db)):
    with service._lock:
        row = recording(db, project_id, recording_id)
        try:
            service.publish(db, row, payload.summary, payload.revision)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        background.add_task(service.index_project, row.project_id)
        return service.public_recording(row)
