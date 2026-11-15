"""Durable incremental scan of explicitly associated project sources."""
import hashlib
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import update

from ..db import SessionLocal
from ..models import (BrainLink, CdcSource, CdcSourcePage, Meeting, Milestone,
                      MilestoneInput, MilestoneScanJob, NetworkLink, Project)
from . import milestones

logger = logging.getLogger(__name__)
_stop, _wake = threading.Event(), threading.Event()
_thread = None
_lock = threading.RLock()
MAX_BATCH = 30
CHUNK_SIZE = 10000
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_DOCUMENT_TEXT = 300000
VERSION = "milestones-v1"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def describe(job):
    from app.db_support import utc_iso
    return {"id": job.id, "status": job.status, "processed": job.processed, "total": job.total,
            "proposed": job.proposed, "warnings": job.warnings or [], "error": job.error,
            "updated_at": utc_iso(job.updated_at)}


def enqueue(db, project_id):
    with _lock:
        previous = db.query(MilestoneScanJob).filter_by(project_id=project_id).filter(
            MilestoneScanJob.status.in_(["queued", "running"])).first()
        if previous:
            return describe(previous)
        job = db.query(MilestoneScanJob).filter_by(project_id=project_id).order_by(MilestoneScanJob.created_at.desc()).first()
        if job is None:
            job = MilestoneScanJob(project_id=project_id)
            db.add(job)
        else:
            job.status, job.processed, job.total, job.proposed = "queued", 0, 0, 0
            job.warnings, job.error = [], None
            job.updated_at = datetime.now(timezone.utc)
        db.commit()
        _wake.set()
        return describe(job)


def notify_brain_project(brain_project_id):
    """Best-effort wake after a committed classification; the periodic scan is durable fallback."""
    try:
        with SessionLocal() as db:
            ids = [link.project_id for link in db.query(BrainLink).filter_by(brain_project_id=brain_project_id)]
            for project_id in ids:
                enqueue(db, project_id)
    except Exception:
        logger.exception("Réveil des jalons ; reprise au prochain passage périodique")


def network_files(links, warnings, *, project_id=None):
    """Never follow a symlink/junction outside an explicitly associated root."""
    from fastapi import HTTPException
    from .cdc_extraction import ALLOWED_CDC_SUFFIXES
    from .document_file_access import _mapped, configured_policy, resolve_root

    use_policy = any(os.environ.get(name) for name in (
        'AGENT_KIARA_KEY', 'AGENT_DOCUMENT_ROOTS', 'AGENT_DOCUMENT_DRIVE_MAPPINGS', 'AGENT_DOCUMENT_PROJECT_ROOT',
    ))
    try:
        policy = configured_policy(project_id) if use_policy else None
    except HTTPException:
        warnings.append('Configuration des racines documentaires invalide ; liens réseau ignorés.')
        return

    seen, visited = set(), 0
    for link in links:
        if not link:
            continue
        try:
            configured = _mapped(link, policy) if policy is not None else Path(link)
            if policy is not None:
                allowed = [base for value in policy.roots if configured.is_relative_to(base := Path(value))]
                if not allowed:
                    warnings.append(f'Lien hors des racines documentaires autorisées : {link}')
                    continue
            root = configured.resolve(strict=True)
            if policy is not None and not any(root.is_relative_to(resolve_root(base, policy)) for base in allowed):
                warnings.append(f'Lien hors des racines documentaires autorisées : {link}')
                continue
        except (HTTPException, OSError, ValueError, RuntimeError):
            warnings.append(f"Chemin inaccessible : {link}")
            continue
        if root.is_file():
            entries = [root]
        else:
            entries = []
            def on_error(error):
                warnings.append(f"Dossier illisible : {error.filename}")
            for folder, dirs, names in os.walk(root, followlinks=False, onerror=on_error):
                current = Path(folder)
                kept = []
                for directory in dirs:
                    try:
                        child = current / directory
                        if (not directory.startswith((".", "~")) and not child.is_symlink() and
                                not child.is_junction() and child.resolve().is_relative_to(root)):
                            kept.append(directory)
                    except OSError:
                        warnings.append(f"Sous-dossier inaccessible : {directory}")
                dirs[:] = sorted(kept)
                if len(current.relative_to(root).parts) >= 5:
                    if dirs:
                        warnings.append(f"Sous-dossiers au-delà de 5 niveaux non explorés : {folder}")
                    dirs[:] = []
                entries.extend(current / name for name in sorted(names)
                               if not name.startswith((".", "~")) and Path(name).suffix.casefold() in ALLOWED_CDC_SUFFIXES)
                visited += len(names)
                if visited > 5000 or len(entries) >= 500:
                    warnings.append("Exploration réseau limitée à 500 documents / 5000 entrées ; préciser les liens projet")
                    break
        for path in entries:
            try:
                path = path.resolve()
            except OSError:
                warnings.append(f"Document inaccessible : {path.name}")
                continue
            if path in seen or (root.is_dir() and not path.is_relative_to(root)):
                continue
            seen.add(path)
            if path.suffix.casefold() not in ALLOWED_CDC_SUFFIXES:
                warnings.append(f"Format non analysé : {path.name}")
                continue
            yield path


def collect(project_id, warnings, previous):
    """Yield text and immutable evidence snapshots; no live DB during inference."""
    from app.db import SessionLocal as BrainSession
    from app.models import Source, SourceArtifact
    with SessionLocal() as db:
        link = db.get(BrainLink, project_id)
        brain_id = link.brain_project_id if link else None
        pages = db.query(CdcSourcePage, CdcSource).join(CdcSource).filter(CdcSource.project_id == project_id).all()
        meetings = db.query(Meeting).filter_by(project_id=project_id).all()
        links = [x.chemin for x in db.query(NetworkLink).filter_by(project_id=project_id) if x.chemin]
        local = [(page.extracted_text, {"kind": "cdc", "page_id": page.id,
                  "label": f"{source.filename} · page {page.physical_page}",
                  "hash": digest(page.extracted_text)}) for page, source in pages]
        local += [(meeting.decisions, {"kind": "meeting", "meeting_id": meeting.id,
                   "label": f"CR : {meeting.title}", "hash": digest(meeting.decisions)}) for meeting in meetings]
    if brain_id:
        with BrainSession() as db:
            # Only canonical texts. AI summaries are not primary evidence.
            rows = db.query(SourceArtifact, Source).join(Source).filter(
                Source.project_id == brain_id, Source.status == "resolved",
                SourceArtifact.kind.in_(["body_text", "transcription", "ocr", "document_text"])).all()
            local += [(art.content_text or "", {"kind": "brain", "source_id": src.id, "artifact_id": art.id,
                       "label": (src.source_metadata or {}).get("subject") or f"{src.source_type} · {src.id[:8]}",
                       "hash": digest(art.content_text or "")}) for art, src in rows
                      if not (art.content_json or {}).get("superseded")]
            # Attachments remain in the original EML; inspect readable attachments in memory.
            mails = [(src.id, src.original_uri, dict(src.source_metadata or {})) for src in db.query(Source).filter_by(
                project_id=brain_id, status="resolved", source_type="email")]
    yield from local
    if brain_id:
        for source_id, uri, meta in mails:
            if not meta.get("attachments"):
                continue
            raw_path = Path(meta.get("raw_path") or uri)
            if not raw_path.is_file():
                warnings.append(f"Original du mail inaccessible : {source_id[:8]}")
                continue
            # Raw files are managed files, not arbitrary source-provided locations.
            from app.config import settings
            if not raw_path.resolve().is_relative_to(Path(settings.storage_dir).resolve()) or raw_path.stat().st_size > MAX_FILE_BYTES:
                warnings.append(f"Original du mail hors stockage ou trop volumineux : {source_id[:8]}")
                continue
            from email import message_from_bytes, policy
            from tempfile import TemporaryDirectory
            from .cdc_extraction import extract_document, ALLOWED_CDC_SUFFIXES
            original = raw_path.read_bytes()
            raw_hash = hashlib.sha256(original).hexdigest()
            message = message_from_bytes(original, policy=policy.default)
            for index, part in enumerate(message.walk()):
                filename = part.get_filename()
                if not filename or Path(filename).suffix.casefold() not in ALLOWED_CDC_SUFFIXES:
                    continue
                if previous.get((source_id, index)) == raw_hash:
                    continue
                raw = part.get_payload(decode=True) or b""
                if len(raw) > MAX_FILE_BYTES:
                    warnings.append(f"Pièce jointe trop volumineuse : {filename}")
                    continue
                # Reuse the proven extractor, without changing CDC sources or writing on the network.
                try:
                    with TemporaryDirectory(prefix="agent-milestone-") as temp:
                        path = Path(temp) / ("attachment" + Path(filename).suffix)
                        path.write_bytes(raw)
                        text = "\n".join(page.text for page in extract_document(path, filename))
                    # Attachment evidence is guarded by the parent source + exact original hash.
                    evidence = {"kind": "attachment", "source_id": source_id, "index": index,
                                "label": f"Pièce jointe : {filename}", "path": str(raw_path),
                                "hash": raw_hash, "brain_project_id": brain_id}
                    yield text, evidence
                except Exception:
                    warnings.append(f"Pièce jointe illisible : {filename}")
    from .cdc_extraction import extract_document
    for path in network_files(links, warnings, project_id=project_id):
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                warnings.append(f"Document trop volumineux (>20 Mo) : {path.name}")
                continue
            content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            # Skip extraction if all chunks of an unchanged document succeeded with this AI configuration.
            evidence = {"kind": "network", "path": str(path), "label": path.name, "hash": content_hash}
            if previous.get("file:" + str(path)) == content_hash:
                continue
            pages = extract_document(path, path.name)
            if any(page.visual_review_required for page in pages):
                warnings.append(f"Texte incomplet / revue visuelle nécessaire : {path.name}")
            text = "\n".join(f"Page {p.physical_page}\n{p.text}" for p in pages)
            yield text, evidence
        except Exception:
            warnings.append(f"Document illisible : {path.name}")


def scan(job_id, should_stop=lambda: False):
    from app.services.inference_scheduler import priority_scope
    from ..routers.cdc import brain_ai_settings
    cfg = brain_ai_settings()
    cfg_hash = digest(str((VERSION, cfg.get("provider"), cfg.get("base_url"), cfg.get("model"), cfg.get("enabled"))))
    with SessionLocal() as db:
        job = db.get(MilestoneScanJob, job_id)
        project_id = job.project_id
        code = db.get(Project, project_id).code
        titles = [m.title for m in db.query(Milestone).filter_by(project_id=project_id)]
        ledger = db.query(MilestoneInput).filter_by(project_id=project_id).all()
        prior = {x.input_key: (x.content_hash, x.status, (x.evidence or {}).get("hash")) for x in ledger}
        completed_documents = {}
        for row in ledger:
            ev = row.evidence or {}
            if ev.get("scan_cfg") != cfg_hash or row.status != "completed":
                continue
            if ev.get("kind") == "network":
                key = "file:" + ev["path"]
            elif ev.get("kind") == "attachment":
                key = (ev["source_id"], ev["index"])
            else:
                continue
            completed_documents.setdefault((key, ev["hash"]), []).append(ev)
        cached = {key: content_hash for (key, content_hash), group in completed_documents.items()
                  if len(group) == group[0].get("chunk_count")}
    warnings, pending = [], []
    # The ledger is per text chunk, with a configuration hash. No permanently skipped mail after the first batch.
    for text, evidence in collect(project_id, warnings, cached):
        if should_stop():
            break
        import re
        codes = {x.upper() for x in re.findall(r"\b[A-Z]{2,10}\d{2}LT[A-Z]?\d{4}-[A-Z]\b", text, re.IGNORECASE)}
        if codes and code and code.upper() not in codes and len(codes) == 1:
            warnings.append(f"Source portant un autre numéro de projet, ignorée : {evidence['label']}")
            continue
        if len(text) > MAX_DOCUMENT_TEXT:
            warnings.append(f"Texte limité à {MAX_DOCUMENT_TEXT} caractères : {evidence['label']}")
        text = text[:MAX_DOCUMENT_TEXT]
        chunk_count = len(range(0, len(text), CHUNK_SIZE - 500))
        for offset in range(0, len(text), CHUNK_SIZE - 500):
            chunk = text[offset:offset + CHUNK_SIZE]
            key = digest(str((evidence.get("kind"), evidence.get("artifact_id") or evidence.get("page_id") or
                              evidence.get("meeting_id") or evidence.get("source_id"), evidence.get("path"), evidence.get("index"), offset)))
            value_hash = digest(chunk + cfg_hash)
            if prior.get(key) == (value_hash, "completed", evidence.get("hash")):
                continue
            pending.append((key, value_hash, chunk, evidence, chunk_count))
            if len(pending) > MAX_BATCH:
                break
        if len(pending) > MAX_BATCH:
            break
    with SessionLocal() as db:
        job = db.get(MilestoneScanJob, job_id)
        if should_stop():
            job.status, job.error = "queued", "Reprise après interruption"
            db.commit()
            return
        job.total = min(len(pending), MAX_BATCH)
        job.warnings = list(dict.fromkeys(warnings))[:30]
        db.commit()
    remaining = len(pending) > MAX_BATCH
    failures = 0
    for key, value_hash, text, evidence, chunk_count in pending[:MAX_BATCH]:
        if should_stop():
            with SessionLocal() as db:
                job = db.get(MilestoneScanJob, job_id)
                job.status, job.error = "queued", "Reprise après interruption"
                db.commit()
            return
        with priority_scope('background'):
            items, failed = milestones.extract(text, cfg, titles)
        with SessionLocal() as db:
            # Results from moved/edited sources are not attached to the old project.
            valid = milestones.evidence_current(evidence, project_id)
            count = milestones.store_candidates(db, project_id, text, items, evidence) if valid else 0
            row = db.query(MilestoneInput).filter_by(project_id=project_id, input_key=key).first()
            if row is None:
                row = MilestoneInput(project_id=project_id, input_key=key, content_hash=value_hash)
                db.add(row)
            row.content_hash, row.evidence = value_hash, {**evidence, "scan_cfg": cfg_hash, "chunk_count": chunk_count}
            row.status = "failed" if failed or not valid else "completed"
            row.error = "IA indisponible ; extraction explicite de secours, reprise nécessaire" if failed else "Source modifiée" if not valid else None
            failures += bool(failed or not valid)
            job = db.get(MilestoneScanJob, job_id)
            job.processed += 1
            job.proposed += count
            job.updated_at = datetime.now(timezone.utc)
            db.commit()
    with SessionLocal() as db:
        job = db.get(MilestoneScanJob, job_id)
        job.status = "failed" if failures else "completed"
        job.error = f"{failures} source(s) à reprendre ; propositions déjà trouvées conservées" if failures else None
        if remaining:
            job.warnings = [*(job.warnings or []), "D'autres sources attendent le prochain passage automatique"]
        job.updated_at = datetime.now(timezone.utc)
        db.commit()


def process_next(should_stop=lambda: False):
    with SessionLocal() as db:
        # A periodic retry reuses the job row. Its original creation time must
        # not put it ahead of projects that were already waiting in the queue.
        job = db.query(MilestoneScanJob).filter_by(status="queued").order_by(
            MilestoneScanJob.updated_at, MilestoneScanJob.created_at, MilestoneScanJob.id).first()
        if not job:
            return False
        key = job.id
        claim = db.execute(update(MilestoneScanJob).where(MilestoneScanJob.id == key, MilestoneScanJob.status == "queued")
                           .values(status="running", processed=0, total=0, proposed=0, error=None,
                                   updated_at=datetime.now(timezone.utc)))
        db.commit()
        if claim.rowcount != 1:
            return True
    try:
        scan(key, should_stop)
    except Exception as exc:
        logger.exception("Recherche des jalons interrompue %s", key)
        with SessionLocal() as db:
            job = db.get(MilestoneScanJob, key)
            job.status, job.error = "failed", f"Recherche à reprendre : {type(exc).__name__}"
            job.updated_at = datetime.now(timezone.utc)
            db.commit()
    return True


def start_worker():
    global _thread
    if os.environ.get("AGENT_TESTING") == "1" or (_thread and _thread.is_alive()):
        return
    with SessionLocal() as db:
        db.query(MilestoneScanJob).filter_by(status="running").update({"status": "queued"})
        for project in db.query(Project).all():
            milestones.seed(db, project.id)
        db.commit()
    _stop.clear()
    def loop():
        scheduled = 0
        while not _stop.is_set():
            try:
                if time.monotonic() - scheduled >= 300:
                    with SessionLocal() as db:
                        ids = [p.id for p in db.query(Project).filter_by(status="active")]
                        for project_id in ids:
                            enqueue(db, project_id)
                    scheduled = time.monotonic()
                if process_next(_stop.is_set):
                    continue
            except Exception:
                logger.exception("Worker des jalons")
            _wake.wait(3)
            _wake.clear()
    _thread = threading.Thread(target=loop, name="milestone-worker", daemon=True)
    _thread.start()


def stop_worker():
    _stop.set()
    _wake.set()
    if _thread and _thread is not threading.current_thread():
        _thread.join(timeout=5)
