"""Federate the existing sources; retain selected imports and versions without deletion."""
from app.operational_limits import DOCUMENT_IMPORT_BYTES
import hashlib
import json
import os
from pathlib import Path
from typing import Literal, get_args
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import inspect
from sqlalchemy.orm import load_only, raiseload

from ..models import Project, Source, SourceArtifact, MemoryProjection
from ..source_library_models import LibraryItem, LibraryVersion, LIBRARY_TABLES
from .current_evidence import is_current_evidence
from .project_access import filter_brain, require_brain
from .library_extraction import extract

MAX_FILE = DOCUMENT_IMPORT_BYTES
PROVIDERS = {"file", "folder", "url", "drive", "calendar"}
FileFormat = Literal["all", "unknown", "pdf", "png", "jpeg", "webp", "txt", "md", "csv",
                     "docx", "doc", "xlsx", "xls", "xlsm", "pptx", "ppt", "html",
                     "wav", "mp3", "m4a", "webm", "ogg", "eml"]
_MIME_FORMATS = {
    "application/pdf": ("pdf",), "image/png": ("png",), "image/jpeg": ("jpeg",),
    "image/webp": ("webp",), "text/plain": ("txt", "md", "csv"),
    "text/markdown": ("md",), "text/x-markdown": ("md",),
    "text/csv": ("csv",), "application/csv": ("csv",),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ("docx",),
    "application/msword": ("doc",),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ("xlsx",),
    "application/vnd.ms-excel": ("xls",),
    "application/vnd.ms-excel.sheet.macroenabled.12": ("xlsm",),
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ("pptx",),
    "application/vnd.ms-powerpoint": ("ppt",),
    "text/html": ("html",), "application/xhtml+xml": ("html",),
    "audio/wav": ("wav",), "audio/x-wav": ("wav",), "audio/wave": ("wav",),
    "audio/mpeg": ("mp3",), "audio/mp4": ("m4a",), "audio/x-m4a": ("m4a",),
    "audio/webm": ("webm",), "video/webm": ("webm",),
    "audio/ogg": ("ogg",), "message/rfc822": ("eml",),
}
_SUFFIX_FORMATS = {"." + value: value for value in get_args(FileFormat) if value not in {"all", "unknown"}}
_SUFFIX_FORMATS.update({".jpg": "jpeg", ".htm": "html"})
_AUDIO_FORMATS = {"wav", "mp3", "m4a", "webm", "ogg"}


def actual_file_format(source_type, metadata, mime_type):
    """Describe retained file metadata, never turn a Note or transcript into a file.

    A recognized MIME is authoritative. Its compatible suffix may distinguish
    plain text/Markdown/CSV; absent or generic MIME can use the retained filename.
    An explicit unsupported MIME remains unknown, even with a familiar suffix.
    This classification is not byte validation or extraction readiness.
    """
    mime = str(mime_type or "").split(";", 1)[0].strip().casefold()
    if (source_type == "note" or metadata.get("origin_kind") in {"erp_note", "published_erp_note"}
            or mime == "application/vnd.agent.note+json"):
        return None
    filename = metadata.get("filename")
    suffix = Path(filename).suffix.casefold() if isinstance(filename, str) else ""
    suffix_format = _SUFFIX_FORMATS.get(suffix)
    formats = _MIME_FORMATS.get(mime)
    if formats:
        result = suffix_format if suffix_format in formats else formats[0]
    elif mime in {"", "application/octet-stream", "binary/octet-stream"}:
        result = suffix_format
    else:
        result = None
    if source_type in {"meeting", "phone"} and result not in _AUDIO_FORMATS:
        return None
    if source_type == "email" and result != "eml":
        return None
    return result


def validate_library_db(engine):
    existing = set(inspect(engine).get_table_names())
    wanted = {table.name for table in LIBRARY_TABLES}
    if engine.dialect.name == 'sqlite':
        from sqlalchemy.schema import CreateTable
        from backend.app.services.document_schema_rules import _sql
        from backend.app.services.project_planning_migration import read_connection
        with read_connection(engine) as connection:
            for table in LIBRARY_TABLES:
                if table.name not in existing:
                    continue
                actual = connection.exec_driver_sql("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table.name,)).scalar()
                if _sql(actual) != _sql(str(CreateTable(table).compile(dialect=engine.dialect))):
                    raise ValueError('Schéma Sources incompatible : ' + table.name)
    if existing & wanted and not wanted.issubset(existing):
        raise RuntimeError("Schéma Sources incomplet : restaurer sur copie avant reprise")
    return existing, wanted


def init_library_db(engine):
    from ..db_support import backup_sqlite, record_schema
    from sqlalchemy.engine import make_url
    existing, wanted = validate_library_db(engine)
    if not wanted.issubset(existing):
        if existing and engine.dialect.name == "sqlite":
            path = Path(make_url(engine.url).database)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            backup_sqlite(path, path.parent / "backups" / f"brain-library-{stamp}.db")
        for table in LIBRARY_TABLES:
            table.create(engine, checkfirst=True)
    record_schema(engine, "brain", 7)


def require_enabled(db):
    from .meeting_sessions import capabilities
    if not capabilities(db)["enabled"]:
        raise HTTPException(409, "Espace de séance désactivé")


def _safe_filename(filename):
    if (not isinstance(filename, str) or not 1 <= len(filename) <= 255 or filename in {".", ".."}
            or any(c in filename for c in '/\\:<>"|?*') or filename != filename.rstrip(" .")
            or any(ord(c) < 32 for c in filename)):
        raise HTTPException(422, "Nom de fichier simple requis")
    return filename


def extraction_state(passages, error):
    if error:
        return 'failed'
    if any(p['status'] == 'ocr_required' for p in passages):
        return 'partially_extracted' if any(p['text'].strip() for p in passages) else 'ocr_required'
    return 'extracted' if any(p['text'].strip() for p in passages) else 'empty'


def import_bytes(db, *, project_id, provider, provider_key, filename, data, mime_type=None,
                 provider_version="", provenance=None, storage=None, reinterpret_legacy_html=False):
    require_brain(project_id)
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet de connaissance introuvable")
    if provider not in PROVIDERS or not isinstance(provider_key, str) or not 1 <= len(provider_key) <= 2048:
        raise HTTPException(422, "Identité de fournisseur invalide")
    filename = _safe_filename(filename)
    if not data or len(data) > MAX_FILE:
        raise HTTPException(413, "Import de 1 octet à 50 Mio requis")
    content_hash = hashlib.sha256(data).hexdigest()
    item_id = str(uuid.uuid5(uuid.NAMESPACE_URL, json.dumps([project_id, provider, provider_key])))
    version_id = str(uuid.uuid5(uuid.UUID(item_id), content_hash))
    previous = db.get(LibraryVersion, version_id)
    if previous:
        # An old-version replay never rolls the current binding backwards.
        item = db.get(LibraryItem, item_id)
        old = db.get(Source, previous.source_id)
        if (reinterpret_legacy_html and provider == 'url' and old
                and Path((old.source_metadata or {}).get('filename', '')).suffix.casefold() in {'.html', '.htm'}
                and Path(filename).suffix.casefold() not in {'.html', '.htm', '.bin', ''}):
            return reinterpret_url_html(db, item, previous, old, filename, data, mime_type, storage)
        return {"item_id": item_id, "source_id": previous.source_id, "version_id": version_id,
                "replayed": True, "current": item.current_source_id == previous.source_id}
    from ..config import RAW_DIR
    directory = Path(storage) if storage else RAW_DIR
    from .storage_capacity import require_capacity
    require_capacity(directory, len(data) * 2)
    directory.mkdir(parents=True, exist_ok=True)
    envelope_hash = hashlib.sha256(json.dumps([item_id, content_hash], separators=(",", ":")).encode()).hexdigest()
    path = directory / (envelope_hash + Path(filename).suffix.casefold())
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != content_hash:
        raise HTTPException(409, "Original conservé incompatible")
    if not path.exists():
        temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".part")
        with temporary.open("xb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    try:
        passages = extract(path, filename)
        extraction_error = None
    except (ValueError, OSError) as exc:
        passages = []
        extraction_error = str(exc)[:500]
    item = db.get(LibraryItem, item_id)
    if not item:
        item = LibraryItem(id=item_id, project_id=project_id, provider=provider, provider_key=provider_key, title=filename)
        db.add(item)
        db.flush()
    if item.current_source_id:
        old = db.get(Source, item.current_source_id)
        if old:
            old.source_metadata = {**old.source_metadata, "superseded": True}
    source = Source(id=version_id, project_id=project_id, status="resolved", source_type="document",
                    original_uri=str(path), sha256=envelope_hash, mime_type=mime_type,
                    author="selected-import", source_metadata={"origin_kind": "library_import", "filename": filename,
                    "library_item_id": item_id, "library_version_id": version_id, "content_sha256": content_hash,
                    "provider": provider, "provider_key": provider_key, "provider_version": provider_version,
                    "labels": item.labels or [], "extraction_status": extraction_state(passages, extraction_error),
                    "extraction_error": extraction_error, "provenance": provenance or {}})
    db.add(source)
    db.flush()
    for ordinal, passage in enumerate(passages):
        db.add(SourceArtifact(source_id=source.id, kind=passage["kind"], content_text=passage["text"],
                              content_json={"ordinal": ordinal, **passage["locator"], "extraction_status": passage["status"]}))
    db.add(LibraryVersion(id=version_id, item_id=item_id, source_id=source.id, content_sha256=content_hash,
                          provider_version=provider_version, size_bytes=len(data), provenance=provenance or {}))
    item.current_source_id, item.title = source.id, filename
    if any(p["text"].strip() for p in passages):
        from .projections import enqueue
        enqueue(db, project_id, "evidence", source_id=source.id)
    db.commit()
    return {"item_id": item_id, "source_id": source.id, "version_id": version_id, "replayed": False,
            "current": True, "extraction_status": source.source_metadata["extraction_status"],
            "extraction_error": extraction_error, "passages": len(passages)}


def reinterpret_url_html(db, item, version, old, filename, data, mime_type, storage):
    """Explicit URL replay creates a separate extraction interpretation, never edits old evidence."""
    suffix = Path(filename).suffix.casefold()
    interpretation = str(uuid.uuid5(uuid.UUID(version.id), 'url-format-v1:' + suffix))
    # The retained legacy file must still match the immutable bytes version.
    from ..config import RAW_DIR
    directory = Path(storage) if storage else RAW_DIR
    original = Path(old.original_uri).resolve()
    if (not original.is_relative_to(directory.resolve()) or not original.is_file()
            or original.stat().st_size != version.size_bytes
            or hashlib.sha256(original.read_bytes()).hexdigest() != version.content_sha256):
        raise HTTPException(409, "Original historique incompatible ; reprise d'extraction refusée")
    if existing := db.get(Source, interpretation):
        retained = Path(existing.original_uri).resolve()
        if (not retained.is_relative_to(directory.resolve()) or not retained.is_file()
                or retained.stat().st_size != version.size_bytes
                or hashlib.sha256(retained.read_bytes()).hexdigest() != version.content_sha256):
            raise HTTPException(409, "Original réinterprété incompatible")
        return {'item_id': item.id, 'source_id': existing.id, 'version_id': version.id,
                'extraction_version_id': interpretation, 'reinterpreted': True, 'replayed': True,
                'current': item.current_source_id == existing.id,
                'extraction_status': existing.source_metadata['extraction_status'],
                'extraction_error': existing.source_metadata.get('extraction_error')}
    envelope = hashlib.sha256(json.dumps([item.id, version.content_sha256, interpretation],
                                        separators=(',', ':')).encode()).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (envelope + suffix)
    if path.exists() and (path.stat().st_size != version.size_bytes
                         or hashlib.sha256(path.read_bytes()).hexdigest() != version.content_sha256):
        raise HTTPException(409, "Original réinterprété incompatible")
    if not path.exists():
        temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.part')
        with temporary.open('xb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    try:
        passages, error = extract(path, filename), None
    except (ValueError, OSError) as exc:
        passages, error = [], str(exc)[:500]
    current = item.current_source_id == old.id
    receipt = {'id': interpretation, 'content_version_id': version.id, 'source_id': interpretation,
               'reinterprets_source_id': old.id, 'content_sha256': version.content_sha256,
               'format': suffix, 'extractor': 'url-format-v1'}
    metadata = {**old.source_metadata, 'filename': filename, 'extraction_version_id': interpretation,
        'reinterprets_source_id': old.id, 'extraction_receipt': receipt, 'labels': item.labels or [],
        'extraction_status': extraction_state(passages, error),
        'extraction_error': error, 'superseded': not current}
    source = Source(id=interpretation, project_id=old.project_id, status='resolved', source_type=old.source_type,
        original_uri=str(path), sha256=envelope, mime_type=mime_type, author=old.author, source_metadata=metadata)
    db.add(source)
    db.flush()
    for ordinal, passage in enumerate(passages):
        db.add(SourceArtifact(source_id=source.id, kind=passage['kind'], content_text=passage['text'],
            content_json={'ordinal': ordinal, **passage['locator'], 'extraction_status': passage['status'],
                          'extraction_version_id': interpretation, 'content_version_id': version.id}))
    if current:
        old.source_metadata = {**old.source_metadata, 'superseded': True}
        item.current_source_id, item.title = source.id, filename
        if any(p['text'].strip() for p in passages):
            from .projections import enqueue
            enqueue(db, source.project_id, 'evidence', source_id=source.id)
    db.commit()
    return {'item_id': item.id, 'source_id': source.id, 'version_id': version.id,
            'extraction_version_id': interpretation, 'reinterpreted': True, 'replayed': False,
            'current': current, 'extraction_status': metadata['extraction_status'],
            'extraction_error': error, 'passages': len(passages)}


def catalog(db, *, query="", project_id=None, source_type="all", file_format="all", label="", status="all", sort="date_desc", offset=0, limit=50):
    # The catalogue needs existence, never the text/JSON of every artifact.
    # Keep this in the source SELECT so its query count is independent of the
    # number of matching sources, including those outside the requested page.
    if file_format not in get_args(FileFormat):
        raise HTTPException(422, "Format de fichier inconnu")
    has_artifacts = db.query(SourceArtifact.id).filter(SourceArtifact.source_id == Source.id).exists()
    sources_query = filter_brain(db.query(Source, has_artifacts), Source.project_id).filter(
        Source.status != "discarded").options(load_only(Source.id, Source.project_id, Source.source_type,
        Source.status, Source.author, Source.source_metadata, Source.received_at, Source.mime_type),
        raiseload(Source.artifacts))
    if project_id:
        require_brain(project_id)
        sources_query = sources_query.filter(Source.project_id == project_id)
    projects = {p.id: p for p in filter_brain(db.query(Project.id, Project.code), Project.id)}
    items = []
    for source, extracted in sources_query:
        meta = source.source_metadata or {}
        if meta.get("superseded"):
            continue
        current = is_current_evidence(source) if source.status == "resolved" else False
        if source.status == 'resolved' and not current:
            continue
        labels = meta.get("labels") or []
        title = str(meta.get("subject") or meta.get("filename") or source.source_type)
        kind = "note" if meta.get("origin_kind") == "erp_note" else "mail" if source.source_type == "email" else source.source_type
        if source_type != "all" and kind != source_type or label and label not in labels:
            continue
        detected_format = actual_file_format(source.source_type, meta, source.mime_type)
        if file_format != "all" and (detected_format or "unknown") != file_format:
            continue
        if status != "all" and source.status != status:
            continue
        if query.casefold() not in (title + " " + (source.author or "")).casefold():
            continue
        project = projects.get(source.project_id)
        items.append({"id": source.id, "source_id": source.id, "kind": kind, "title": title,
                      "project_id": source.project_id, "project_code": project.code if project else None,
                      "erp_project_id": meta.get("erp_project_id"), "note_id": meta.get("note_id"),
                      "labels": labels, "status": source.status,
                      "current": current,
                      "date": source.received_at.isoformat(), "mime_type": source.mime_type, "file_format": detected_format,
                      "extraction_status": meta.get("extraction_status") or ("extracted" if extracted else "pending"),
                      "provider": meta.get("provider"),
                      "version_id": meta.get("note_version_id") or meta.get("library_version_id"),
                      "source_url": f"/v1/sources/{source.id}"})
    # ERP notes remain visible even while the evidence outbox is unavailable;
    # these are references to the canonical Note, never copied Source records.
    if source_type in {'all', 'note'} and file_format in {'all', 'unknown'} and not label:
        from backend.app.db import SessionLocal
        from backend.app.models import BrainLink
        from backend.app.project_note_models import ProjectNote
        from .project_access import filter_erp
        projected = {(item.get('note_id'), item.get('version_id')) for item in items}
        with SessionLocal() as erp:
            for note in filter_erp(erp.query(ProjectNote.id, ProjectNote.project_id, ProjectNote.title,
                    ProjectNote.current_version_id, ProjectNote.updated_at, BrainLink.brain_project_id).join(BrainLink,
                    BrainLink.project_id == ProjectNote.project_id), ProjectNote.project_id):
                if note.brain_project_id not in projects or (project_id and note.brain_project_id != project_id):
                    continue
                if (note.id, note.current_version_id) in projected or query.casefold() not in note.title.casefold():
                    continue
                if status not in {'all', 'projection_pending'}:
                    continue
                project = projects[note.brain_project_id]
                items.append({'id': 'erp-note:' + note.id, 'source_id': None, 'kind': 'note', 'title': note.title,
                    'project_id': note.brain_project_id, 'project_code': project.code, 'erp_project_id': note.project_id,
                    'note_id': note.id, 'labels': [], 'status': 'projection_pending', 'current': True,
                    'date': note.updated_at.isoformat(), 'mime_type': 'application/vnd.agent.note+json', 'file_format': None,
                    'extraction_status': 'canonical_note', 'index_status': 'not_indexed', 'provider': 'erp',
                    'version_id': note.current_version_id,
                    'source_url': f'/api/v1/projects/{note.project_id}/notes/{note.id}/versions/{note.current_version_id}'})
    key = (lambda row: (row["title"].casefold(), row["id"])) if sort in {"title_asc", "title_desc"} else lambda row: (row["date"], row["id"])
    items.sort(key=key, reverse=sort in {"date_desc", "title_desc"})
    page = items[offset:offset + limit]
    source_ids = [row["source_id"] for row in page if row["source_id"]]
    projections = {sid: state for sid, state in db.query(MemoryProjection.source_id, MemoryProjection.status).filter(
        MemoryProjection.purpose == "evidence", MemoryProjection.source_id.in_(source_ids))} if source_ids else {}
    for row in page:
        row["index_status"] = projections.get(row["source_id"], "not_indexed")
    return {"items": page, "total": len(items), "offset": offset, "limit": limit,
            "has_next": offset + limit < len(items), "labels": sorted({value for row in items for value in row["labels"]})}


def update_labels(db, source_id, labels):
    source = db.get(Source, source_id)
    if not source or not source.project_id or source.status == "discarded":
        raise HTTPException(404, "Source introuvable")
    require_brain(source.project_id)
    if len(labels) > 20 or any(not isinstance(value, str) or not 1 <= len(value.strip()) <= 80 for value in labels):
        raise HTTPException(422, "Vingt labels de 1 à 80 caractères maximum")
    labels = sorted(set(value.strip() for value in labels))
    source.source_metadata = {**source.source_metadata, "labels": labels}
    item_id = source.source_metadata.get("library_item_id")
    if item_id and (item := db.get(LibraryItem, item_id)):
        item.labels = labels
    db.commit()
    return {"source_id": source.id, "labels": labels}
