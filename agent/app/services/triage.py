"""Tri des mails : classement IA à valider, projet DIVERS en filet de sécurité.

Traçabilité de l'analyse : un mail est « analysé » dès qu'une proposition
`project_attach` de raison `triage IA%` existe pour lui
(`is_analyzed()`, tout statut). Aucune table supplémentaire : la proposition
elle-même fait foi, même après validation (source résolue) ou remplacement.

Architecture :
- `ensure_divers_project` : le projet DIVERS existe toujours (créé si besoin).
- `triage_pending` : pour chaque mail en attente → résolution déterministe +
  indices IA → crée UNE proposition `project_attach` vers le meilleur projet,
  ou vers DIVERS si aucun candidat fiable.
  - `force=False` (nouveaux uniquement) : ignore les mails déjà analysés.
  - `force=True` (tout ré-analyser) : les anciennes propositions de tri en
    cours sont soldées (`superseded`) puis remplacées par une analyse fraîche.
  Idempotent dans les deux modes : relancer ne duplique rien.
- `resolve_source` : validation effective (accept/assign/confirm) → rattache
  la source, indexe l'evidence, extrait les items à valider, clôt les autres
  propositions de rattachement de la source.

Règle : DIVERS est un vrai projet explicite (file de ré-examen), jamais une
affectation arbitraire silencieuse. Une suggestion atteignant le seuil des
réglages mails (75 % par défaut) est classée automatiquement ; les autres
restent à valider.
"""
from __future__ import annotations

import json
import threading

from sqlalchemy.orm import Session

from ..models import (AuditLog, MemoryDatasetMapping, MemoryProjection,
                      Project, Proposal, Source, SourceArtifact, KnowledgeItem, ProvenanceLink,
                      ValidationDecision)
from .ingestion import extract_candidates
from .resolution import choose_candidate, merge_ai_hints, resolve_project
from .mail_learning import build_learning_context, reply_headers

DIVERS_CODE = "DIVERS"
DIVERS_NAME = "Divers — mails non classés"

# Seuil de confiance pour proposer un projet plutôt que DIVERS.
TRIAGE_THRESHOLD = 0.75
# Manual, automatic and durable analyses share the same local classifier.
TRIAGE_LOCK = threading.RLock()


def ensure_divers_project(db: Session) -> Project:
    divers = db.query(Project).filter_by(code=DIVERS_CODE).first()
    if not divers:
        divers = Project(code=DIVERS_CODE, name=DIVERS_NAME, status="active",
                         aliases=[])
        db.add(divers)
        db.commit()
        db.refresh(divers)
    return divers


def _real_projects(db: Session) -> list[Project]:
    """Projets candidats au classement (DIVERS exclu : le mot « divers » est
    trop courant pour servir de signal)."""
    return [p for p in db.query(Project).all() if (p.code or "").upper() != DIVERS_CODE]


def _mail_text(db: Session, source: Source) -> str:
    arts = db.query(SourceArtifact).filter(SourceArtifact.source_id == source.id, SourceArtifact.kind.in_(["body_text", "transcription", "ocr"])).all()
    return "\n".join((a.content_text or "") for a in arts if not (a.content_json or {}).get("superseded"))


def _pending_attaches(db: Session, source_id: str) -> list[Proposal]:
    return db.query(Proposal).filter_by(
        source_id=source_id, kind="project_attach", status="pending").all()


def is_analyzed(db: Session, source_id: str) -> bool:
    """Un mail est analysé dès qu'une proposition de tri existe pour lui,
    quel que soit son statut (en cours, acceptée, soldée)."""
    source = db.get(Source, source_id)
    if source and source.status in ("discarded", "rejected"):
        return True
    return db.query(Proposal).filter_by(source_id=source_id, kind="project_attach").filter(
        Proposal.reason.like("triage IA%")).count() > 0


def pending_triage_query(db: Session, force: bool = False):
    """Shared eligibility for the batch and its initial progress denominator."""
    from sqlalchemy import exists
    query = db.query(Source).filter_by(status="resolution_pending", source_type="email")
    if not force:
        already_triaged = exists().where(
            Proposal.source_id == Source.id, Proposal.kind == "project_attach",
            Proposal.status == "pending", Proposal.reason.like("triage IA%"))
        query = query.filter(~already_triaged)
    return query


def triage_pending(db: Session, mem, ai_cfg: dict | None, limit: int = 50,
                   offset: int = 0, force: bool = False,
                   source_ids: list[str] | None = None, run_id: str | None = None) -> dict:
    with TRIAGE_LOCK:
        return _triage_pending(db, mem, ai_cfg, limit, offset, force, source_ids, run_id)


def _triage_pending(db: Session, mem, ai_cfg: dict | None, limit: int,
                    offset: int, force: bool, source_ids: list[str] | None,
                    run_id: str | None) -> dict:
    divers = ensure_divers_project(db)
    projects = _real_projects(db)
    learning = build_learning_context(db, projects)
    proj_dicts = [{"code": p.code, "name": p.name, "aliases": p.aliases or [], **learning.describe(p.id)}
                  for p in projects]

    query = pending_triage_query(db, force)
    if source_ids is not None:
        query = query.filter(Source.id.in_(source_ids))
    pendings = (query.order_by(Source.received_at.asc(), Source.id.asc())
                .offset(max(0, offset)).limit(min(max(1, limit), 1000)).all())
    stats = {"scanned": 0, "triaged": 0, "divers": 0,
             "skipped": 0, "auto_classified": 0, "errors": [], "force": force}
    for s in pendings:
        if stats["triaged"] + len(stats["errors"]) >= limit:
            break
        stats["scanned"] += 1
        try:
            old = _pending_attaches(db, s.id)
            if not force and any((p.reason or "").startswith("triage IA") for p in old):
                stats["skipped"] += 1
                continue
            meta = s.source_metadata or {}
            parsed = {"subject": meta.get("subject", ""), "body_text": _mail_text(db, s),
                      "sender": s.author or "", "participants": s.participants or [],
                      **reply_headers(meta, s.original_uri),
                      "attachments": meta.get("attachments", [])}
            reso = resolve_project(parsed, projects, None, learning)
            ai_summary = ""
            if ai_cfg and ai_cfg.get("enabled"):
                from .ai_client import classify_email
                clf = classify_email(
                    ai_cfg, parsed["subject"], parsed["body_text"], parsed["sender"],
                    proj_dicts, None, parsed["participants"]) or {}
                ai_summary = str(clf.get("summary", "") or "")
                merge_ai_hints(reso, projects, clf.get("project_hints", []))
            # L'IA peut prendre du temps : revérifier l'exclusion avant tout
            # changement et prendre le verrou SQLite jusqu'au commit.
            active = db.query(Source).filter_by(id=s.id, status="resolution_pending").update(
                {Source.status: Source.status}, synchronize_session=False)
            if not active:
                db.rollback()
                stats["skipped"] += 1
                continue
            old = _pending_attaches(db, s.id)
            if force:
                for o in old:
                    if (o.reason or "").startswith("triage IA"):
                        o.status = "superseded"
                db.add(AuditLog(event_type="triage.superseded.v1", project_id=None,
                                actor="triage", payload={"source_id": s.id}))
            for o in old:
                if (o.reason or "").startswith("triage IA"):
                    continue
                o.status = "rejected"
                db.add(ValidationDecision(proposal_id=o.id, decision="reject",
                                          actor="triage", comment="remplacée par proposition de tri"))
            best = choose_candidate(reso["candidates"], TRIAGE_THRESHOLD)
            if best:
                target_id, confidence = best["project_id"], float(best["score"])
                reason = "triage IA : " + ", ".join(best.get("reasons", []))
            else:
                target_id, confidence = divers.id, 0.35
                reason = ("triage IA : plusieurs projets possibles → DIVERS"
                          if reso["candidates"] and reso["candidates"][0]["score"] >= TRIAGE_THRESHOLD
                          else "triage IA : aucun projet fiable → DIVERS")
                stats["divers"] += 1
            proposal = Proposal(
                project_id=target_id, source_id=s.id, kind="project_attach",
                subject=f"Classer : {parsed['subject'][:120] or '(sans objet)'}",
                value=json.dumps({"sender": parsed["sender"], "subject": parsed["subject"],
                                  "summary": ai_summary[:500],
                                  "candidates": reso["candidates"][:3]},
                                 ensure_ascii=False),
                confidence=confidence, reason=reason)
            db.add(proposal)
            db.add(AuditLog(event_type="triage.proposed.v1", project_id=target_id,
                            actor="triage", payload={"source_id": s.id}, correlation_id=run_id))
            db.flush()
            if auto_classify_proposal(db, proposal, ai_cfg):
                stats["auto_classified"] += 1
            else:
                db.commit()
            stats["triaged"] += 1
        except Exception as exc:  # un mail en échec ne bloque pas le lot
            db.rollback()
            stats["errors"].append({"source_id": s.id, "error": str(exc)[:200]})
    return stats


def _ensure_evidence_mapping(db: Session, project_id: str) -> MemoryDatasetMapping:
    m = db.query(MemoryDatasetMapping).filter_by(
        project_id=project_id, purpose="evidence", engine="eg2").first()
    if not m:
        m = MemoryDatasetMapping(project_id=project_id, purpose="evidence", engine="eg2",
                                 dataset_name=f"pb_{project_id}__evidence")
        db.add(m)
        db.flush()
    return m


def _extract_items(db: Session, source: Source, project_id: str, ai_cfg: dict | None) -> int:
    """Crée les propositions d'items d'une source qui vient d'être rattachée."""
    body = _mail_text(db, source)
    subject = (source.source_metadata or {}).get("subject", "")
    items, origin = extract_mail_candidates(subject, body, source.author or "", ai_cfg, source.participants)
    return store_mail_candidates(db, source, project_id, items, origin)


def extract_mail_candidates(subject, body, author, ai_cfg, participants=None, require_ai=False):
    """Inference without a database session or SQLite write lock."""
    from .ai_client import classify_email
    items: list[dict] = []
    origin = "heuristique"
    if ai_cfg and ai_cfg.get("enabled"):
        clf = classify_email(ai_cfg, subject, body, author, [], None, participants)
        if clf is None and require_ai:
            raise RuntimeError("Le LLM n’a pas fourni de réponse exploitable ; extraction à reprendre")
        clf = clf or {}
        if clf.get("items"):
            items = clf["items"]
            origin = "IA"
    if not items and body.strip():
        items = extract_candidates(body, subject)
    return items, origin


def store_mail_candidates(db, source, project_id, items, origin):
    n = 0
    for c in items:
        value = str(c.get("value", "")).strip()
        if not value or db.query(Proposal).filter_by(source_id=source.id, project_id=project_id, kind=str(c.get("kind", "free_information")), value=value).first():
            continue
        proposal = Proposal(project_id=project_id, source_id=source.id,
                        kind=str(c.get("kind", "free_information")),
                        subject=str(c.get("subject", ""))[:512],
                        value=str(c.get("value", "")),
                        confidence=float(c.get("confidence", 0.5)),
                        reason=f"[{origin}] {c.get('reason', '')}")
        db.add(proposal)
        db.flush()
        from .knowledge_defaults import accept_by_default
        accept_by_default(db, proposal)
        n += 1
    return n


def auto_classification_threshold(db: Session) -> float:
    from .settings_service import get_section
    try:
        value = float(get_section(db, "mail").get("auto_classification_threshold", 0.75))
        return value if 0.01 <= value <= 1.0 else 0.75
    except (TypeError, ValueError):
        return 0.75


def auto_classification_target(db: Session, proposal: Proposal) -> tuple[str, float] | None:
    """Recover the selected candidate of a historical DIVERS fallback."""
    threshold = auto_classification_threshold(db)
    if proposal.kind != "project_attach" or proposal.status != "pending":
        return None
    project = db.get(Project, proposal.project_id) if proposal.project_id else None
    if not project:
        return None
    if (project.code or "").upper() != DIVERS_CODE:
        return ((project.id, proposal.confidence) if proposal.confidence is not None
                and threshold <= proposal.confidence <= 1.0 else None)
    from .resolution import proposal_details
    candidate = choose_candidate(proposal_details(proposal.value, proposal.project_id)["candidates"], threshold)
    if candidate and threshold <= candidate["score"] <= 1.0:
        target = db.get(Project, candidate["project_id"])
        if target and (target.code or "").upper() != DIVERS_CODE:
            return target.id, float(candidate["score"])
    return None


def auto_classify_proposal(db: Session, proposal: Proposal, ai_cfg: dict | None = None) -> bool:
    """Apply the configured threshold to pending email decisions under the write guard."""
    threshold = auto_classification_threshold(db)
    selection = auto_classification_target(db, proposal)
    if not selection:
        return False
    project = db.get(Project, selection[0])
    source = db.get(Source, proposal.source_id) if proposal.source_id else None
    if not project or (project.code or "").upper() == DIVERS_CODE or not source:
        return False
    if source.source_type != "email" or source.status != "resolution_pending":
        return False
    active = db.query(Source).filter_by(id=source.id, source_type="email", status="resolution_pending").update(
        {Source.status: Source.status}, synchronize_session=False)
    if not active:
        return False
    db.refresh(proposal)
    selection = auto_classification_target(db, proposal)
    if not selection or selection[0] != project.id:
        return False
    if any(p.id != proposal.id and p.project_id != project.id for p in _pending_attaches(db, source.id)):
        return False
    if proposal.project_id != project.id:
        proposal.project_id, proposal.confidence = selection
        proposal.reason = "triage IA : candidat historique repris au seuil automatique"
    actor = "auto-confidence-100" if proposal.confidence == 1.0 else "auto-confidence-threshold"
    db.add(AuditLog(event_type="triage.auto_classified.v1", project_id=project.id,
                    actor=actor, payload={"source_id": source.id,
                    "proposal_id": proposal.id, "confidence": proposal.confidence, "threshold": threshold}))
    resolve_source(db, None, source, project, ai_cfg, actor,
                   defer_enrichment=True, accepted_proposal_id=proposal.id)
    return True


def auto_classify_pending(db: Session, ai_cfg: dict | None = None) -> dict:
    """Apply the configured threshold to existing pending suggestions, preserving human decisions."""
    with TRIAGE_LOCK:
        ids = [row.id for row in db.query(Proposal).join(Source, Proposal.source_id == Source.id).filter(
            Proposal.kind == "project_attach", Proposal.status == "pending",
            Source.status == "resolution_pending", Source.source_type == "email").all()
               if auto_classification_target(db, row)]
        result = {"eligible": len(ids), "auto_classified": 0, "skipped": 0, "errors": []}
        for pid in ids:
            try:
                proposal = db.get(Proposal, pid)
                if proposal and auto_classify_proposal(db, proposal, ai_cfg):
                    result["auto_classified"] += 1
                else:
                    db.rollback()
                    result["skipped"] += 1
            except Exception as exc:
                db.rollback()
                result["errors"].append({"proposal_id": pid, "error": str(exc)[:200]})
        return result


def resolve_source(db: Session, mem, source: Source, project: Project,
                   ai_cfg: dict | None, actor: str, defer_enrichment: bool = False,
                   accepted_proposal_id: str | None = None, pending_only: bool = False) -> dict:
    """Rattache une source à un projet : evidence + extraction + clôture."""
    import asyncio
    from .projections import enqueue, process
    from fastapi import HTTPException
    # Verrou d'écriture conditionnel : une exclusion ne peut être réactivée.
    candidate = db.query(Source).filter(Source.id == source.id, Source.status.notin_(("discarded", "rejected")))
    if pending_only:
        candidate = candidate.filter((Source.status == "resolution_pending") |
                                     ((Source.status == "resolved") & (Source.project_id == project.id)))
    active = candidate.update(
        {Source.status: Source.status}, synchronize_session=False)
    if not active:
        db.rollback()
        if pending_only:
            raise HTTPException(409, "La source n’est plus à rattacher. Actualisez la liste.")
        raise HTTPException(409, "Ce mail a été écarté et ne peut plus être classé")
    db.refresh(source)
    previous = source.project_id
    if source.status == "resolved" and previous == project.id:
        return {"source_id": source.id, "project_id": project.id, "status": "resolved", "items": 0}
    if previous and previous != project.id:
        for projection in db.query(MemoryProjection).filter_by(source_id=source.id).all():
            projection.status = "obsolete"
        for proposal in db.query(Proposal).filter_by(source_id=source.id, status="pending").all():
            proposal.status = "superseded"
        links = db.query(ProvenanceLink).filter_by(source_id=source.id).all()
        for link in links:
            item = db.get(KnowledgeItem, link.knowledge_item_id)
            if item and item.status == "validated":
                item.status = "invalidated"
                for projection in db.query(MemoryProjection).filter_by(knowledge_item_id=item.id).all():
                    projection.status = "obsolete"
        db.add(AuditLog(event_type="source.reclassified.v1", project_id=project.id,
                        actor=actor, payload={"source_id": source.id, "previous_project": previous}))
    source.project_id = project.id
    source.status = "resolved"
    db.flush()
    enqueue(db, project.id, "evidence", source_id=source.id)
    deferred = defer_enrichment and source.source_type == "email"
    n_items = 0 if deferred and ai_cfg and ai_cfg.get("enabled") else _extract_items(db, source, project.id, ai_cfg)
    # Les autres propositions de rattachement de cette source deviennent caduques.
    for old in db.query(Proposal).filter_by(
            source_id=source.id, kind="project_attach", status="pending").all():
        accepted = old.id == accepted_proposal_id
        old.status = "accepted" if accepted else "rejected"
        db.add(ValidationDecision(proposal_id=old.id, decision="accept" if accepted else "reject", actor=actor,
                                  comment=f"classement automatique : confiance {old.confidence * 100:g} %" if accepted
                                  else "remplacée par la validation"))
    db.add(AuditLog(event_type="source.processed.v1", project_id=project.id,
                    actor=actor, payload={"source_id": source.id, "items": n_items}))
    enrichment = None
    if deferred:
        from .mail_enrichment import enqueue
        enrichment = enqueue(db, source, project, bool(ai_cfg and ai_cfg.get("enabled")), n_items)
    db.commit()
    from .mail_team import sync_classified_mail
    sync_classified_mail(source)
    if enrichment:
        from .mail_enrichment import wake
        wake()
    else:
        asyncio.run(process(db, mem))
    from backend.app.services.milestone_scan import notify_brain_project
    notify_brain_project(project.id)
    return {"source_id": source.id, "project_id": project.id,
            "status": "resolved", "items": n_items,
            **({"enrichment_id": enrichment.id, "enrichment_status": "queued"} if enrichment else {})}
