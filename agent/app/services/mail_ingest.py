"""Ingestion mail partagée (upload, bulk, scan dossier)."""
from app.operational_limits import DOCUMENT_IMPORT_BYTES
from sqlalchemy.orm import Session
from ..models import Project, Source, SourceArtifact, Proposal, MemoryDatasetMapping, AuditLog
from .ingestion import sha256_bytes, parse_eml, extract_candidates
from .resolution import choose_candidate, merge_ai_hints, resolve_project
from .mail_learning import build_learning_context
import json
from ..config import RAW_DIR
import uuid
from pathlib import Path


def _audit(db: Session, event_type: str, project_id: str | None, actor: str, payload: dict):
    db.add(AuditLog(event_type=event_type, project_id=project_id, actor=actor,
                    payload=payload, correlation_id=str(uuid.uuid4())))


def _ensure_mapping(db: Session, project_id: str, purpose: str) -> MemoryDatasetMapping:
    m = db.query(MemoryDatasetMapping).filter_by(project_id=project_id, purpose=purpose, engine="eg2").first()
    if not m:
        m = MemoryDatasetMapping(project_id=project_id, purpose=purpose, engine="eg2",
                                 dataset_name=__import__("app.services.eg2_memory", fromlist=["dataset_name_for"]).dataset_name_for(project_id, purpose),
                                 engine_version="eg2-v1")
        db.add(m)
        db.flush()
    return m


async def ingest_eml_bytes(db: Session, raw: bytes, mem, candidate_project_id: str | None = None,
                           origin: str = "upload", origin_path: str | None = None,
                           defer_analysis: bool = False, *, assigned_project: Project | None = None) -> dict:
    """Ingère un .eml brut. Idempotent par sha256. IA locale/API si configurée, sinon heuristique."""
    h = sha256_bytes(raw)
    from .mail_identity import fingerprint, remember_identity
    from ..models import MailIdentity
    identity = db.get(MailIdentity, fingerprint(raw))
    existing = db.query(Source).filter_by(sha256=h).first()
    if not existing and identity:
        existing = db.get(Source, identity.source_id)
    if existing:
        return {"status": "duplicate", "source_id": existing.id, "sha256": h}
    parsed = parse_eml(raw)
    if assigned_project is not None and not (parsed["sender"] or parsed["subject"] or parsed["message_id"]):
        from fastapi import HTTPException
        raise HTTPException(422, "Le fichier ne contient pas de message EML reconnu.")
    dest = RAW_DIR / f"{h}.eml"
    if not dest.exists():
        dest.write_bytes(raw)
    from .triage import DIVERS_CODE, TRIAGE_THRESHOLD
    projects = [assigned_project] if assigned_project is not None else [
        p for p in db.query(Project).all() if (p.code or "").upper() != DIVERS_CODE
    ]
    learning = build_learning_context(db, projects)
    reso = resolve_project(parsed, projects, None, learning)
    # --- IA : boost résolution + extraction ---
    ai_used = False
    ai_summary = None
    ai_items: list[dict] | None = None
    try:
        from .settings_service import get_section
        from .ai_client import classify_email
        ai_cfg = get_section(db, "ai")
        if ai_cfg.get("enabled") and not defer_analysis:
            proj_dicts = [{"code": p.code, "name": p.name, "aliases": p.aliases or [],
                           **learning.describe(p.id)} for p in projects]
            clf = classify_email(ai_cfg, parsed["subject"], parsed["body_text"], parsed["sender"], proj_dicts,
                                 None, parsed["to"] + parsed["cc"])
            if clf:
                ai_used = True
                ai_summary = clf.get("summary")
                ai_items = clf.get("items", [])
                # croise hints IA avec projets connus -> complète la résolution déterministe
                merge_ai_hints(reso, projects, clf.get("project_hints", []))
                # Les indices IA suggèrent un projet ; ils ne le valident pas.
    except Exception:
        pass
    project_id = None
    auto_classified = False
    status = "resolution_pending"
    if assigned_project is not None:
        project_id = assigned_project.id
        status = "resolved"
    elif reso["auto"] and not defer_analysis:
        project_id = reso["candidates"][0]["project_id"]
        status = "resolved"
    elif not defer_analysis and candidate_project_id and db.query(Project).filter_by(id=candidate_project_id).first():
        project_id = candidate_project_id
        status = "resolved"
    s = Source(source_type="email", status=status, project_id=project_id,
               author=parsed["sender"], participants=parsed["to"] + parsed["cc"],
               original_uri=str(dest), sha256=h, mime_type="message/rfc822",
               captured_at=parsed["captured_at"],
               source_metadata={"subject": parsed["subject"], "message_id": parsed["message_id"],
                                "in_reply_to": parsed["in_reply_to"], "references": parsed["references"],
                                "attachments": parsed["attachments"], "resolution": reso,
                                "origin": origin, "origin_path": origin_path, "raw_path": str(dest),
                                "ai_used": ai_used, "ai_summary": ai_summary})
    db.add(s)
    db.flush()
    remember_identity(db, s.id, raw)
    db.add(SourceArtifact(source_id=s.id, kind="body_text", content_text=parsed["body_text"],
                          content_json={"subject": parsed["subject"]}))
    if ai_summary:
        db.add(SourceArtifact(source_id=s.id, kind="ai_summary", content_text=ai_summary,
                              content_json={"provider": "ai"}))
    _audit(db, "source.received.v1", project_id, origin, {"source_id": s.id, "origin_path": origin_path,
                                                          "ai_used": ai_used})
    if status == "resolved":
        from .projections import enqueue
        enqueue(db, project_id, "evidence", source_id=s.id)
        cands = ai_items if ai_items else extract_candidates(parsed["body_text"], parsed["subject"])
        from .triage import store_mail_candidates
        item_count = store_mail_candidates(db, s, project_id, cands, 'IA' if ai_items else 'heuristique')
        if assigned_project is not None:
            from .mail_enrichment import enqueue as enqueue_enrichment
            enqueue_enrichment(db, s, assigned_project, needs_ai=False, items=item_count)
        _audit(db, "proposal.created.v1", project_id, "system", {"source_id": s.id})
    else:
        _audit(db, "project.resolution_required.v1", None, "system",
               {"source_id": s.id, "candidates": reso["candidates"]})
        best = choose_candidate(reso["candidates"], TRIAGE_THRESHOLD)
        suggested = best if best and any(p.id == best["project_id"] for p in projects) else None
        proposal = Proposal(project_id=suggested["project_id"] if suggested else None,
                        source_id=s.id, kind="project_attach",
                        subject=f"Rattacher mail: {parsed['subject'][:100]}",
                        value=json.dumps({"candidates": reso["candidates"][:3]}, ensure_ascii=False),
                        confidence=suggested["score"] if suggested else 0.3,
                        reason=("suggestion de projet : " + ", ".join(suggested.get("reasons", [])))
                        if suggested else "résolution ambiguë")
        db.add(proposal)
        db.flush()
        if not defer_analysis:
            from .triage import auto_classify_proposal
            if auto_classify_proposal(db, proposal, {"enabled": ai_used}):
                auto_classified = True
                project_id, status = s.project_id, s.status
    db.commit()
    if status == "resolved":
        from .mail_team import sync_classified_mail
        sync_classified_mail(s)
    if assigned_project is not None:
        from .mail_enrichment import wake
        wake()
    elif project_id and not auto_classified:
        from .projections import process
        await process(db, mem, project_id)
    return {"status": status, "source_id": s.id, "sha256": h,
            "project_id": project_id, "candidates": reso["candidates"],
            "subject": parsed["subject"]}


DEFAULT_WATCH_DIR = str(Path.home() / "Downloads" / "Infomaniak-IA")


def mail_scan_directory(folder, allowed):
    from backend.app.services.document_file_access import _absolute

    requested, root = Path(_absolute(folder)), Path(_absolute(allowed))
    if not requested.is_relative_to(root):
        raise PermissionError('Dossier EML hors périmètre')
    canonical_root = root.resolve()
    resolved = requested.resolve()
    if not resolved.is_relative_to(canonical_root):
        raise PermissionError('Dossier EML hors périmètre')
    return resolved


def scan_folder(folder: str | Path, db_factory, mem, candidate_project_id: str | None = None,
                limit: int = 500) -> dict:
    """Scan synchrone d'un dossier *.eml (appelé depuis endpoint)."""
    import asyncio
    from backend.app.services.document_file_access import _handle_path

    p = folder if isinstance(folder, Path) else Path(folder).resolve()
    if not p.is_dir():
        return {"error": f"Dossier introuvable: {folder}", "scanned": 0}
    files = sorted(p.glob("*.eml"))
    stats = {"folder": str(p), "scanned": 0, "imported": 0, "duplicates": 0,
             "resolved": 0, "pending": 0, "errors": []}
    for f in files:
        if stats["imported"] + len(stats["errors"]) >= limit:
            break
        stats["scanned"] += 1
        try:
            if f.resolve(strict=True) != f or not f.is_file():
                raise ValueError('Fichier EML redirigé ou non régulier')
            with f.open('rb') as stream:
                if _handle_path(stream) != f:
                    raise ValueError('Emplacement du fichier EML modifié')
                raw = stream.read(DOCUMENT_IMPORT_BYTES + 1)
            if len(raw) > DOCUMENT_IMPORT_BYTES:
                raise ValueError('fichier trop volumineux')
            with db_factory() as db:
                res = asyncio.run(ingest_eml_bytes(db, raw, mem, candidate_project_id,
                                                   origin="folder-scan", origin_path=str(f)))
            if res["status"] == "duplicate":
                stats["duplicates"] += 1
            else:
                stats["imported"] += 1
                if res["status"] == "resolved":
                    stats["resolved"] += 1
                else:
                    stats["pending"] += 1
        except Exception as e:
            stats["errors"].append(f"{f.name}: {e}")
    return stats
