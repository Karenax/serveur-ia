"""Sources catalog and explicit selected imports in the single Agent service."""
import json
import re
from pathlib import Path
from typing import Literal
from urllib.parse import unquote, urlsplit

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from fastapi.responses import FileResponse, Response
from pydantic import Field
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..db import get_db
from ..models import Source, SourceArtifact
from ..meeting_session_schemas import Closed as BaseModel
from ..services import source_library as library
from ..services.project_access import require_brain
from ..services.source_connectors import fetch_selected, calendar_preview

router = APIRouter(prefix="/api/v1/workspace/sources", tags=["sources-library"])
URL_FORMATS = {
    'application/pdf': ('.pdf',),
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ('.docx',),
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ('.xlsx',),
    'application/vnd.ms-excel.sheet.macroenabled.12': ('.xlsm',),
    'text/html': ('.html', '.htm'), 'application/xhtml+xml': ('.html', '.htm'),
    'text/plain': ('.txt', '.md', '.csv'), 'text/markdown': ('.md',),
    'text/csv': ('.csv',), 'application/csv': ('.csv',),
    'image/png': ('.png',), 'image/jpeg': ('.jpg', '.jpeg'), 'image/webp': ('.webp',),
    'audio/wav': ('.wav',), 'audio/x-wav': ('.wav',), 'audio/wave': ('.wav',),
    'audio/mpeg': ('.mp3',), 'audio/mp4': ('.m4a',), 'audio/x-m4a': ('.m4a',),
    'audio/webm': ('.webm',), 'video/webm': ('.webm',), 'audio/ogg': ('.ogg',),
}


class Labels(BaseModel):
    labels: list[str] = Field(default_factory=list, max_length=20)


class URLImport(BaseModel):
    project_id: str
    url: str = Field(min_length=8, max_length=2048)
    filename: str | None = Field(default=None, min_length=1, max_length=255)


class DriveImport(BaseModel):
    project_id: str
    file_id: str = Field(pattern=r"^[A-Za-z0-9_-]{5,200}$")


class DriveConnection(BaseModel):
    access_token: str = Field(min_length=20, max_length=4096)


def url_filename(url: str, mime: str, requested: str | None = None) -> str:
    """Keep the reported document format instead of extracting every URL as HTML.

    The MIME returned by the checked fetch selects a supported extension. For
    generic/unknown MIME, keep an explicit or URL-path extension; an opaque
    download stays .bin and is reported unsupported rather than fake HTML.
    """
    if requested is not None:
        name = library._safe_filename(requested)
    else:
        name = unquote(urlsplit(url).path.rsplit('/', 1)[-1])
        name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', name).rstrip(' .')
        name = name[:240] or 'source'
    suffix = Path(name).suffix.casefold()
    extensions = URL_FORMATS.get(mime.split(';', 1)[0].strip().casefold())
    if extensions and suffix not in extensions:
        stem = name[:-len(suffix)] if suffix else name
        name = stem[:255 - len(extensions[0])] + extensions[0]
    elif not suffix:
        name += '.bin'
    return library._safe_filename(name)


@router.get("")
def sources(query: str = Query("", max_length=2000), project_id: str | None = None,
            source_type: str = "all", file_format: library.FileFormat = "all", label: str = "", status: str = "all",
            sort: Literal["title_asc", "title_desc", "date_asc", "date_desc"] = "date_desc",
            offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    from ..services.project_access import current_operator
    operator = current_operator()
    result = library.catalog(db, query=query, project_id=project_id, source_type=source_type, file_format=file_format,
                             label=label, status=status, sort=sort, offset=offset, limit=limit)
    result["can_import_audio"] = operator.role != "reader" and operator.project_ids is None
    return result


@router.post("/imports/file", status_code=201)
async def import_file(project_id: str = Form(...), file: UploadFile = File(...),
                      provider_key: str | None = Form(None), provider: Literal["file", "folder"] = Form("file"),
                      db: Session = Depends(get_db)):
    library.require_enabled(db)
    require_brain(project_id)
    data = await file.read(library.MAX_FILE + 1)
    return await run_in_threadpool(library.import_bytes, db, project_id=project_id, provider=provider,
                                  provider_key=provider_key or file.filename, filename=file.filename,
                                  data=data, mime_type=file.content_type)


@router.post("/imports/url", status_code=201)
def import_url(body: URLImport, db: Session = Depends(get_db)):
    library.require_enabled(db)
    require_brain(body.project_id)
    data, mime = fetch_selected(body.url)
    filename = url_filename(body.url, mime, body.filename)
    return library.import_bytes(db, project_id=body.project_id, provider="url", provider_key=body.url,
                                filename=filename, data=data, mime_type=mime, provenance={"url": body.url},
                                reinterpret_legacy_html=mime.split(';', 1)[0].strip().casefold() in URL_FORMATS)


@router.get("/connectors/drive")
def drive_status(db: Session = Depends(get_db)):
    from ..services.settings_service import get_section
    value = get_section(db, "foresight_drive")
    return {"enabled": drive_enabled(db), "configured": bool(value.get("access_token")), "last_import": value.get("last_import"),
            "connection_scope": "Agent", "token_expiry": "controlled_by_google"}


def drive_enabled(db: Session) -> bool:
    from ..services.settings_service import get_section
    return get_section(db, "foresight").get("drive_enabled") is True


def require_drive_enabled(db: Session) -> None:
    if not drive_enabled(db):
        raise HTTPException(409, "Le connecteur Google Drive est désactivé dans Agent")


@router.put("/connectors/drive")
def configure_drive(body: DriveConnection, db: Session = Depends(get_db)):
    from backend.app.services.project_operator import require_reference_write
    require_reference_write()
    require_drive_enabled(db)
    from ..services.secrets_store import protect
    from ..services.settings_service import save_section
    save_section(db, "foresight_drive", {"access_token": protect(body.access_token)})
    return drive_status(db)


@router.post("/imports/drive", status_code=201)
def import_drive(body: DriveImport, db: Session = Depends(get_db)):
    library.require_enabled(db)
    require_brain(body.project_id)
    require_drive_enabled(db)
    from ..services.settings_service import get_section, save_section
    from ..services.secrets_store import reveal
    from datetime import datetime, timezone
    value = get_section(db, "foresight_drive")
    if not value.get("access_token"):
        raise HTTPException(409, "Connecter Google Drive dans Agent")
    token = reveal(value["access_token"])
    base = "https://www.googleapis.com/drive/v3/files/" + body.file_id
    raw, _ = fetch_selected(base + "?fields=id,name,mimeType,modifiedTime,version", bearer=token)
    meta = json.loads(raw)
    mime = meta["mimeType"]
    title = meta["name"]
    exports = {"application/vnd.google-apps.document": ("application/pdf", ".pdf"),
               "application/vnd.google-apps.spreadsheet": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
               "application/vnd.google-apps.presentation": ("application/pdf", ".pdf")}
    if mime in exports:
        from urllib.parse import quote
        target_mime, extension = exports[mime]
        data, mime = fetch_selected(base + "/export?mimeType=" + quote(target_mime, safe=""), bearer=token)
        title += extension
    elif mime.startswith("application/vnd.google-apps."):
        raise HTTPException(422, "Ce type Google Drive n'est pas un fichier importable")
    else:
        data, mime = fetch_selected(base + "?alt=media", bearer=token)
    result = library.import_bytes(db, project_id=body.project_id, provider="drive", provider_key=body.file_id,
                                  filename=title, data=data, mime_type=mime, provider_version=str(meta.get("version", "")),
                                  provenance={"drive_file_id": body.file_id, "modified_time": meta.get("modifiedTime")})
    save_section(db, "foresight_drive", {"last_import": datetime.now(timezone.utc).isoformat()})
    return result


@router.post("/calendar/preview")
async def preview_calendar(file: UploadFile = File(...)):
    return calendar_preview(await file.read(1024 * 1024 + 1))


@router.put("/{source_id}/labels")
def labels(source_id: str, body: Labels, db: Session = Depends(get_db)):
    library.require_enabled(db)
    return library.update_labels(db, source_id, body.labels)


@router.post("/{source_id}/ocr")
def recognize_scan(source_id: str, db: Session = Depends(get_db)):
    from ..services.library_ocr import recognize_source
    return recognize_source(db, source_id)


@router.post('/{source_id}/ocr/cancel')
def cancel_recognition(source_id: str, db: Session = Depends(get_db)):
    from ..services.library_ocr import cancel_source
    return cancel_source(db, source_id)


@router.get("/{source_id}/original")
def original(source_id: str, db: Session = Depends(get_db)):
    from pathlib import Path
    from ..config import RAW_DIR
    source = db.get(Source, source_id)
    if not source or not source.project_id or source.status == "discarded":
        raise HTTPException(404, "Source introuvable")
    require_brain(source.project_id)
    meta = source.source_metadata or {}
    if meta.get('note_id') and meta.get('note_version_id') and meta.get('erp_project_id'):
        from backend.app.db import SessionLocal
        from backend.app.project_note_models import NoteVersion
        from backend.app.services.project_operator import require_project_access
        require_project_access(meta['erp_project_id'])
        with SessionLocal() as erp:
            version = erp.get(NoteVersion, meta['note_version_id'])
            if not version or (version.note_id, version.project_id) != (meta['note_id'], meta['erp_project_id']):
                raise HTTPException(404, 'Version de note conservée indisponible')
            return Response(version.snapshot.encode('utf-8'), media_type='application/json',
                headers={'Content-Disposition': f'attachment; filename="note-{version.note_id}-v{version.revision}.json"',
                         'Cache-Control': 'private, no-store'})
    path = Path(source.original_uri).resolve()
    if not path.is_relative_to(RAW_DIR.resolve()) or not path.is_file() or path.is_symlink():
        raise HTTPException(404, "Original conservé indisponible")
    filename = re.sub(r"[\\/:*?\"<>|]", "_", str(source.source_metadata.get("filename") or path.name))
    return FileResponse(path, filename=filename, media_type=source.mime_type or "application/octet-stream")


@router.get("/{source_id}/passages")
def passages(source_id: str, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source or not source.project_id or source.status == "discarded":
        raise HTTPException(404, "Source introuvable")
    require_brain(source.project_id)
    return {"source_id": source.id, "version_id": source.source_metadata.get("library_version_id") or source.source_metadata.get('note_version_id'),
            "passages": [{"id": a.id, "text": a.content_text, "locator": a.content_json}
                         for a in db.query(SourceArtifact).filter_by(source_id=source.id)]}
