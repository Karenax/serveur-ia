"""CDC : upload + extraction page par page + moteur d'analyse IA repris de XPilot."""
from __future__ import annotations
from app.operational_limits import DOCUMENT_IMPORT_BYTES

from app.db_support import utc_iso

import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import Field
from ..schemas import DomainInput as BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..services.cdc_output import output_items
from ..db import get_db
from ..models import (CdcCheck, CdcEvidenceAnchor, CdcItem, CdcSource,
                      CdcSourcePage, Project, BusinessDecision)
from ..services.cdc_extraction import (CdcExtractionError, extract_document,
                                      validate_cdc_filename)
from ..services.cdc_generation import (CdcGenerationError, CdcSourceNotReadyError,
                                       generate_analysis)

router = APIRouter(prefix="/api/v1", tags=["cdc"])

KINDS = {"function", "constraint", "requirement", "data", "interface", "open_point"}
MODALITIES = {"mandatory", "preference", "option", "example", "information", "prohibition", "assumption"}
MAX_UPLOAD_BYTES = DOCUMENT_IMPORT_BYTES


def cdc_storage_root(*, create=True) -> Path:
    home = Path(os.environ.get("MINIPILOT_HOME", str(Path.home() / ".minipilot")))
    root = home / "cdc"
    if create:
        root.mkdir(parents=True, exist_ok=True)
    return root


def stored_original(source, root: Path) -> bool:
    if not source.storage_path:
        return False
    path = Path(source.storage_path)
    try:
        return not path.is_symlink() and path.resolve().is_relative_to(root) and path.is_file()
    except OSError:
        return False


def store_original(root: Path, project_id: str, filename: str, digest: str, data: bytes) -> Path:
    from app.services.storage_capacity import require_capacity

    target_dir = root / project_id
    target = target_dir / f"{digest[:16]}-{filename}"
    if not target_dir.resolve().is_relative_to(root) or target.is_symlink():
        raise HTTPException(409, "Le dossier de stockage du cahier des charges est indisponible.")
    def verify_existing():
        if target.is_symlink():
            raise HTTPException(409, "Le dossier de stockage du cahier des charges est indisponible.")
        with target.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                raise HTTPException(409, "Un autre fichier occupe l’emplacement de l’original.")

    if target.exists():
        verify_existing()
        return target
    require_capacity(target_dir, len(data) * 2)
    target_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target_dir, suffix='.pending', delete=False) as stream:
        pending = Path(stream.name)
        try:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            try:
                os.link(pending, target)
            except FileExistsError:
                verify_existing()
        finally:
            stream.close()
            pending.unlink(missing_ok=True)
    return target


def brain_ai_settings() -> dict:
    """Réglages IA du cœur de connaissance (base project_brain.db)."""
    import sys as _sys
    from pathlib import Path as _Path
    if str(_Path(__file__).resolve().parents[3]) not in _sys.path:
        _sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
    from app.db import SessionLocal as BrainSessionLocal
    from app.services.settings_service import get_section
    session = BrainSessionLocal()
    try:
        return get_section(session, "ai") or {}
    finally:
        session.close()


class CdcItemCreate(BaseModel):
    kind: str
    title: str = Field(min_length=1)
    normalized_wording: str = ""
    source_quote: str = Field(min_length=1)
    physical_page: int = Field(ge=1, default=1)
    modality: str = "information"
    priority: str = "unclassified"
    confidence: float = Field(ge=0, le=1, default=0.5)


@router.post("/projects/{project_id}/cdc/sources/upload")
def upload_source(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload + extraction (XPilot : texte par page, qualité, revue visuelle)."""
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Document trop volumineux (50 Mio max)")
    try:
        filename = validate_cdc_filename(file.filename or "document.pdf")
    except CdcExtractionError as exc:
        raise HTTPException(400, str(exc)) from exc

    digest = hashlib.sha256(data).hexdigest()
    root = cdc_storage_root(create=False).resolve()
    existing = db.query(CdcSource).filter_by(project_id=project_id, sha256=digest).first()
    if existing:
        if not stored_original(existing, root):
            try:
                original_name = validate_cdc_filename(existing.filename)
            except CdcExtractionError as exc:
                raise HTTPException(409, str(exc)) from exc
            target = store_original(root, project_id, original_name, digest, data)
            existing.storage_path = str(target)
            db.commit()
            return {"status": "restored", "source_id": existing.id, "pages": existing.pages,
                    "message": "Original rétabli. Les pages et preuves existantes sont conservées."}
        return {"status": "duplicate", "source_id": existing.id, "pages": existing.pages,
                "message": "Ce document est déjà enregistré (même empreinte)."}

    target = store_original(root, project_id, filename, digest, data)

    pages_out: list[dict] = []
    status = "ready"
    pages_rows: list[CdcSourcePage] = []
    try:
        extracted = extract_document(target, filename)
        for page in extracted:
            pages_out.append({"page": page.physical_page, "chars": len(page.text),
                              "quality": page.quality,
                              "visual_review_required": page.visual_review_required})
            pages_rows.append(CdcSourcePage(
                physical_page=page.physical_page, printed_page=page.printed_page,
                extracted_text=page.text, character_count=len(page.text),
                extraction_quality=page.quality,
                visual_review_required=1 if page.visual_review_required else 0))
        if any(p.visual_review_required for p in extracted):
            status = "review_required"
    except CdcExtractionError:
        status = "failed"

    revision_no = db.query(CdcSource).filter_by(project_id=project_id).count() + 1
    src = CdcSource(project_id=project_id, filename=filename, revision=f"R{revision_no}",
                    status=status, pages=len(pages_rows), size_bytes=len(data),
                    sha256=digest, storage_path=str(target),
                    content_type=file.content_type or "application/octet-stream",
                    extracted_at=datetime.now(timezone.utc) if pages_rows else None,
                    extraction_error=None if pages_rows else "extraction impossible")
    db.add(src)
    db.flush()
    for row in pages_rows:
        row.source_id = src.id
        db.add(row)
    db.commit()
    if status == "review_required":
        return {"status": "review_required", "source_id": src.id, "pages": pages_out,
                "message": "Document peu lisible ou scanné : revue visuelle requise"}
    if status == "failed":
        raise HTTPException(400, "Document illisible : extraction impossible")
    return {"status": "ready", "source_id": src.id, "pages": pages_out,
            "message": f"{len(pages_rows)} page(s) extraite(s)"}


@router.get("/projects/{project_id}/cdc/sources")
def list_sources(project_id: str, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    rows = db.query(CdcSource).filter_by(project_id=project_id).order_by(CdcSource.created_at).all()
    page_counts = dict(db.query(CdcSourcePage.source_id, func.count(CdcSourcePage.id))
                       .filter(CdcSourcePage.source_id.in_([row.id for row in rows]))
                       .group_by(CdcSourcePage.source_id).all())
    out = []
    root = cdc_storage_root(create=False).resolve()
    for n, s in enumerate(rows):
        has_text = page_counts.get(s.id, 0) > 0
        stored = stored_original(s, root)
        # analysable : texte déjà extrait, ou fichier stocké pour ré-extraire
        analyzable = has_text or stored
        reason = ""
        if not analyzable:
            reason = ("Document importé avant le moteur d'analyse : ré-importe le CDC."
                      if not s.storage_path else "Fichier stocké introuvable : ré-importe le CDC.")
        elif not has_text:
            reason = "Texte à extraire au premier lancement."
        elif s.sha256 and not stored:
            reason = "Texte extrait disponible. Réimportez le fichier d’origine pour le rattacher à cette fiche."
        out.append({
            "id": s.id, "ref": f"SRC-{n + 1:03d}", "filename": s.filename, "revision": s.revision,
            "status": "PRÊTE" if s.status == "ready" else "À VÉRIFIER",
            "pages": s.pages, "size": fmt_size(s.size_bytes),
            "extracted_pages": page_counts.get(s.id, 0),
            "analyzable": analyzable, "hint": reason})
    return out


@router.get("/projects/{project_id}/cdc/sources/{source_id}/pages")
def list_source_pages(project_id: str, source_id: str, db: Session = Depends(get_db)):
    src = db.query(CdcSource).filter_by(id=source_id, project_id=project_id).first()
    if not src:
        raise HTTPException(404, "Source introuvable")
    rows = db.query(CdcSourcePage).filter_by(source_id=src.id).order_by(CdcSourcePage.physical_page).all()
    return [{"id": r.id, "physical_page": r.physical_page, "printed_page": r.printed_page,
             "chars": r.character_count, "quality": r.extraction_quality,
             "visual_review_required": bool(r.visual_review_required),
             "text": r.extracted_text} for r in rows]


def fmt_size(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} Mo"
    if n >= 1024:
        return f"{n / 1024:.0f} Ko"
    return f"{n} o"


@router.get("/projects/{project_id}/cdc/items")
def list_items(project_id: str, db: Session = Depends(get_db)):
    from collections import defaultdict
    items = db.query(CdcItem).filter_by(project_id=project_id).all()
    anchors = defaultdict(list)
    for anchor in db.query(CdcEvidenceAnchor).filter(CdcEvidenceAnchor.item_id.in_([i.id for i in items])):
        anchors[anchor.item_id].append(anchor)
    out = []
    for i in items:
        evidence = anchors[i.id]
        out.append({"id": i.id, "human_id": i.human_id, "kind": i.kind, "title": i.title,
                    "normalized_wording": i.normalized_wording,
                    "source_quote": i.source_quote, "physical_page": i.physical_page,
                    "modality": i.modality, "priority": i.priority,
                    "knowledge_status": i.knowledge_status, "criterion": i.criterion,
                    "unit": i.unit, "acceptance_criterion": i.acceptance_criterion,
                    "responsible_party": i.responsible_party,
                    "confidence": i.confidence,
                    "estimated_hours": i.estimated_hours or 0,
                    "evidence": [{"id": e.id, "source_id": e.source_id,
                                  "page": e.physical_page, "locator": e.locator,
                                  "quote": e.quote, "confidence": e.confidence}
                                 for e in evidence]})
    return out


class CdcItemUpdate(BaseModel):
    """Retouche d'un élément par le validateur (XPilot : PATCH analysis item)."""

    actor: str = Field(default="validator", min_length=1, max_length=128)
    knowledge_status: str | None = None
    title: str | None = Field(default=None, max_length=255)
    normalized_wording: str | None = None
    modality: str | None = None
    priority: str | None = None
    criterion: str | None = None
    unit: str | None = Field(default=None, max_length=32)
    acceptance_criterion: str | None = None
    responsible_party: str | None = Field(default=None, max_length=120)
    estimated_hours: float | None = Field(default=None, ge=0, le=1e12)


KNOWLEDGE_STATUSES = {"candidate", "confirmed", "to_confirm", "not_provided",
                      "contradictory", "rejected", "superseded"}


@router.patch("/projects/{project_id}/cdc/items/{item_id}")
def update_item(project_id: str, item_id: str, payload: CdcItemUpdate,
                db: Session = Depends(get_db)):
    """Valide / rejette / retouche un élément. Les contrôles sont rejoués."""
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    item = db.query(CdcItem).filter_by(id=item_id, project_id=project_id).first()
    if not item:
        raise HTTPException(404, "Élément introuvable")
    data = payload.model_dump(exclude_none=True)
    actor = data.pop("actor")
    previous = {field: getattr(item, field) for field in data}
    if "knowledge_status" in data and data["knowledge_status"] not in KNOWLEDGE_STATUSES:
        raise HTTPException(400, f"knowledge_status invalide : {sorted(KNOWLEDGE_STATUSES)}")
    if "modality" in data and data["modality"] not in MODALITIES:
        raise HTTPException(400, f"modality invalide : {sorted(MODALITIES)}")
    for field, value in data.items():
        setattr(item, field, value.strip() if isinstance(value, str) else value)
    import json
    db.add(BusinessDecision(project_id=project_id, item_id=item.id, actor=actor, operation="cdc.review",
        previous_value=json.dumps(previous, ensure_ascii=False), new_value=json.dumps(data, ensure_ascii=False)))
    db.commit()
    from ..services.cdc_generation import run_deterministic_checks
    checks = run_deterministic_checks(db, project_id)
    db.refresh(item)
    return {"id": item.id, "human_id": item.human_id, "knowledge_status": item.knowledge_status,
            "checks": len(checks),
            "blockers": [c for c in checks if c["severity"] == "blocker" and c["item_id"] == item.id]}


@router.post("/projects/{project_id}/cdc/items/bulk-status")
def bulk_status(project_id: str, payload: dict, db: Session = Depends(get_db)):
    """Applique un statut à plusieurs éléments (validation en série)."""
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    status = payload.get("knowledge_status")
    if status not in KNOWLEDGE_STATUSES:
        raise HTTPException(400, f"knowledge_status invalide : {sorted(KNOWLEDGE_STATUSES)}")
    ids = payload.get("ids") or []
    if not isinstance(ids, list) or not ids:
        raise HTTPException(400, "ids manquants")
    rows = db.query(CdcItem).filter(CdcItem.project_id == project_id,
                                    CdcItem.id.in_(ids)).all()
    for item in rows:
        db.add(BusinessDecision(project_id=project_id, item_id=item.id, actor=str(payload.get("actor") or "validator")[:128],
            operation="cdc.bulk_review", previous_value=item.knowledge_status, new_value=status))
        item.knowledge_status = status
    db.commit()
    from ..services.cdc_generation import run_deterministic_checks
    run_deterministic_checks(db, project_id)
    return {"updated": len(rows), "knowledge_status": status}


@router.get("/projects/{project_id}/cdc/review")
def review_stats(project_id: str, db: Session = Depends(get_db)):
    """Avancement de la revue : par statut, par type, et file « à traiter »."""
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    items = db.query(CdcItem).filter_by(project_id=project_id).all()
    by_status: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for i in items:
        by_status[i.knowledge_status] = by_status.get(i.knowledge_status, 0) + 1
        by_kind[i.kind] = by_kind.get(i.kind, 0) + 1
    done = sum(1 for i in items if i.knowledge_status != "candidate")
    # sans preuve et valorisé : à traiter en priorité
    with_evidence = {r.item_id for r in db.query(CdcEvidenceAnchor).all() if r.item_id}
    unproven = sum(1 for i in items
                   if i.id not in with_evidence and i.knowledge_status != "rejected")
    checks = db.query(CdcCheck).filter_by(project_id=project_id).all()
    severity: dict[str, int] = {}
    codes: dict[str, int] = {}
    for c in checks:
        severity[c.severity] = severity.get(c.severity, 0) + 1
        codes[c.check_code] = codes.get(c.check_code, 0) + 1
    return {"total": len(items), "reviewed": done, "remaining": len(items) - done,
            "by_status": by_status, "by_kind": by_kind,
            "without_evidence": unproven,
            "check_severity": severity, "check_codes": codes}


class CdcAnalyzeRequest(BaseModel):
    source_id: str = Field(min_length=1)
    pages_per_batch: int = Field(ge=1, le=10, default=2)
    max_tokens: int = Field(ge=256, le=32000, default=4000)


@router.post("/projects/{project_id}/cdc/analyze")
def analyze(project_id: str, payload: CdcAnalyzeRequest, db: Session = Depends(get_db)):
    """Moteur XPilot : pages -> LLM -> fonctions/contraintes/exigences + preuves.

    409 IA injoignable, 502 réponse inexploitable (mêmes codes que XPilot).
    """
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    ai_cfg: dict = {}
    # Les réglages IA vivent dans la base du cœur de connaissance
    # (project_brain.db), pas dans celle du ERP.
    ai_cfg = brain_ai_settings()
    try:
        from ..services.cdc_jobs import ANALYSIS_LOCK
        with ANALYSIS_LOCK:
            return generate_analysis(db, project_id, payload.source_id, ai_cfg=ai_cfg,
                                     pages_per_batch=payload.pages_per_batch,
                                     max_tokens=payload.max_tokens)
    except CdcSourceNotReadyError as exc:
        raise HTTPException(400, str(exc)) from exc
    except CdcGenerationError as exc:
        message = str(exc)
        if "Source CDC introuvable" in message:
            raise HTTPException(404, message) from exc
        if "injoignable" in message:
            raise HTTPException(409, f"{message} (configure l'IA dans Réglages)") from exc
        raise HTTPException(502, f"Réponse IA inexploitable : {message}") from exc


@router.get("/projects/{project_id}/cdc/checks")
def list_checks(project_id: str, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    rows = db.query(CdcCheck).filter_by(project_id=project_id).all()
    return [{"id": r.id, "code": r.check_code, "severity": r.severity,
             "message": r.message, "item_id": r.item_id} for r in rows]


@router.get("/projects/{project_id}/cdc/runs")
def list_runs(project_id: str, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    from ..models import CdcLlmRun
    rows = db.query(CdcLlmRun).filter_by(project_id=project_id).order_by(CdcLlmRun.created_at.desc()).limit(20).all()
    return [{"id": r.id, "model": r.model_name, "status": r.status, "duration_ms": r.duration_ms,
             "returned": r.items_returned, "accepted": r.items_accepted,
             "rejected": r.items_rejected, "error": r.error_message} for r in rows]


@router.post("/projects/{project_id}/cdc/items", status_code=201)
def add_item(project_id: str, payload: CdcItemCreate, db: Session = Depends(get_db)):
    # Garde-fous copiés de XPilot : typage strict, citation obligatoire
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    if payload.kind not in KINDS:
        raise HTTPException(400, f"kind invalide, autorisés : {sorted(KINDS)}")
    if payload.modality not in MODALITIES:
        raise HTTPException(400, f"modality invalide, autorisées : {sorted(MODALITIES)}")
    item = CdcItem(
        project_id=project_id, kind=payload.kind, title=payload.title.strip(),
        normalized_wording=payload.normalized_wording.strip(),
        source_quote=payload.source_quote.strip(), physical_page=payload.physical_page,
        modality=payload.modality, priority=payload.priority, confidence=payload.confidence,
    )
    db.add(item)
    db.commit()
    return {"id": item.id, "kind": item.kind, "title": item.title}


@router.post("/projects/{project_id}/cdc/transfer")
def generate_transfer(project_id: str, draft: bool = False, db: Session = Depends(get_db)):
    """Transfert BE simplifié copié de XPilot : demande BE / réponse BE / arbitrage, en Markdown.

    Bloque si un élément est sans preuve (citation vide) — même garde-fou que XPilot.
    """
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Projet introuvable")
    items, checks = output_items(db, project_id, draft)
    from ..services.deliveries import save_version
    version = save_version(db, p, items, checks, draft)
    return {**version, "items": len(items), "draft": draft, "checks": checks}


@router.get("/projects/{project_id}/cdc/deliveries")
def list_deliveries(project_id: str, db: Session = Depends(get_db)):
    from ..models import DeliveryVersion
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    rows = db.query(DeliveryVersion).filter_by(project_id=project_id).order_by(DeliveryVersion.version.desc()).all()
    return [{"id": row.id, "version": row.version, "draft": row.draft, "file": row.path,
             "sha256": row.sha256, "created_at": utc_iso(row.created_at)} for row in rows]


def _delivery_file(db: Session, project_id: str, version_id: str):
    from ..models import DeliveryVersion
    row = db.get(DeliveryVersion, version_id)
    if not row or row.project_id != project_id:
        raise HTTPException(404, "Version introuvable")
    path = Path(row.path).resolve()
    from ..db import APP_DIR
    if not path.is_relative_to((APP_DIR / "exports").resolve()) or not path.is_file():
        raise HTTPException(409, "Fichier de version absent ou hors stockage")
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise HTTPException(409, "Fichier de version inaccessible") from exc
    if hashlib.sha256(content).hexdigest() != row.sha256:
        raise HTTPException(409, "Empreinte du livrable incorrecte")
    return row, path.name, content


@router.get("/projects/{project_id}/cdc/deliveries/{version_id}")
def read_delivery(project_id: str, version_id: str, db: Session = Depends(get_db)):
    row, _, content = _delivery_file(db, project_id, version_id)
    return {"id": row.id, "version": row.version, "draft": row.draft, "markdown": content.decode("utf-8"),
            "snapshot": row.snapshot, "sha256": row.sha256}


@router.get("/projects/{project_id}/cdc/deliveries/{version_id}/download")
def download_delivery(project_id: str, version_id: str, db: Session = Depends(get_db)):
    _, filename, content = _delivery_file(db, project_id, version_id)
    return Response(content, media_type="text/markdown", headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename, safe='')}",
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store",
    })


@router.post("/projects/{project_id}/cdc/jobs", status_code=202)
def queue_analysis(project_id: str, payload: CdcAnalyzeRequest, db: Session = Depends(get_db)):
    from ..services.cdc_jobs import enqueue
    return enqueue(db, project_id, payload.source_id, payload.model_dump(exclude={"source_id"}))


@router.get("/projects/{project_id}/cdc/jobs")
def analysis_jobs(project_id: str, db: Session = Depends(get_db)):
    from ..models import CdcAnalysisJob
    from ..services.cdc_jobs import describe
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    return [describe(j) for j in db.query(CdcAnalysisJob).filter_by(project_id=project_id)
            .order_by(CdcAnalysisJob.created_at.desc()).limit(50)]


@router.post("/projects/{project_id}/cdc/jobs/{job_id}/cancel")
def cancel_analysis(project_id: str, job_id: str, db: Session = Depends(get_db)):
    from ..services.cdc_jobs import change_state
    return change_state(db, project_id, job_id, "cancel")


@router.post("/projects/{project_id}/cdc/jobs/{job_id}/retry")
def retry_analysis(project_id: str, job_id: str, db: Session = Depends(get_db)):
    from ..services.cdc_jobs import change_state
    return change_state(db, project_id, job_id, "retry")



@router.get("/projects/{project_id}/cdc/decisions")
def list_decisions(project_id: str, offset: int = 0, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    rows = db.query(BusinessDecision).filter_by(project_id=project_id).order_by(
        BusinessDecision.created_at.desc()).offset(max(0, offset)).limit(200).all()
    return [{"id": row.id, "item_id": row.item_id, "actor": row.actor, "operation": row.operation,
             "before": row.previous_value, "after": row.new_value, "created_at": row.created_at}
            for row in rows]
