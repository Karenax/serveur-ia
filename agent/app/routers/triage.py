"""Tri des mails : file de validation du classement IA + projet DIVERS.

- `POST /run` : classe les mails en attente (déterministe + IA), crée une
  proposition `project_attach` par mail (vers un projet ou DIVERS).
- `GET /queue` : file à valider, la plus ancienne d'abord.
- `POST /{id}/accept` : valide la suggestion (rattache + indexe + extrait).
- `POST /{id}/assign` : valide vers un autre projet choisi.
- `GET /stats` : compteurs pour l'app Mails.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import SessionLocal, get_db
from ..models import Project, Proposal, Source, ValidationDecision
from ..services.memory_factory import get_memory_adapter
from ..services.triage import ensure_divers_project, resolve_source, triage_pending, pending_triage_query
from ..services.resolution import proposal_details
from ..services.mail_discard_learning import build_discard_context

router = APIRouter(prefix="/v1/triage", tags=["triage"])


def _ai_cfg(db: Session) -> dict:
    from ..services.settings_service import get_section
    try:
        return get_section(db, "ai") or {}
    except Exception:
        return {}


@router.post("/run")
def run_triage(limit: int = 50, offset: int = 0, force: bool = False,
               db: Session = Depends(get_db)):
    """Classe jusqu'à `limit` mails en attente (idempotent).

    `force=False` : nouveaux mails uniquement (déjà analysés ignorés).
    `force=True` : ré-analyse tout, anciennes propositions soldées."""
    from ..services.workspace_jobs import active_job
    from ..services.triage import TRIAGE_LOCK
    if active_job(db):
        raise HTTPException(409, "Une analyse durable des mails est déjà en attente ou en cours")
    with TRIAGE_LOCK:
        if active_job(db):
            raise HTTPException(409, "Une analyse durable des mails est déjà en attente ou en cours")
        return triage_pending(db, get_memory_adapter(SessionLocal), _ai_cfg(db),
                              limit=limit, offset=offset, force=force)


@router.get("/queue")
def triage_queue(offset: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    """File de validation : une entrée par mail à classer."""
    props = (db.query(Proposal)
             .filter_by(kind="project_attach", status="pending")
             .order_by(Proposal.created_at.asc()).offset(max(0, offset)).limit(min(max(1, limit), 1000)).all())
    out = []
    discard_context = build_discard_context(db)
    for p in props:
        s = db.query(Source).filter_by(id=p.source_id).first() if p.source_id else None
        if not s:
            continue
        target = db.query(Project).filter_by(id=p.project_id).first() if p.project_id else None
        meta = s.source_metadata or {}
        arts = s.artifacts or []
        excerpt = next(((a.content_text or "")[:400] for a in arts
                        if a.kind == "body_text" and a.content_text), "")
        out.append({
            "proposal_id": p.id,
            "source_id": s.id,
            "sender": s.author or "",
            "subject": meta.get("subject", ""),
            "received_at": s.received_at.isoformat() if s.received_at else None,
            "excerpt": excerpt,
            "target_project_id": target.id if target else None,
            "target_code": target.code if target else None,
            "target_name": target.name if target else None,
            "confidence": p.confidence,
            "reason": p.reason or "",
            "discard_suggestion": discard_context.estimate(s),
            **proposal_details(p.value, p.project_id),
        })
    return out


@router.get("/learning")
def triage_learning(db: Session = Depends(get_db)):
    """Critères appris des classements validés, sans modifier les données."""
    from ..services.mail_learning import build_learning_context
    from ..services.triage import _real_projects
    projects = _real_projects(db)
    context = build_learning_context(db, projects)
    return {"validated_mails": sum(context.samples.values()),
            "projects": [{"project_id": p.id, "code": p.code, **context.describe(p.id)} for p in projects]}


@router.get("/stats")
def triage_stats(db: Session = Depends(get_db)):
    divers = ensure_divers_project(db)
    pending = pending_triage_query(db, force=True).count()
    new_sources = pending_triage_query(db).count()
    queued = db.query(Proposal).filter_by(kind="project_attach", status="pending").count()
    divers_count = db.query(Source).filter_by(project_id=divers.id).count()
    return {"pending_sources": pending, "new_sources": new_sources, "queued": queued,
            "divers_project_id": divers.id, "divers_count": divers_count}


class TriageDecision(BaseModel):
    actor: str = "validator"
    comment: str | None = None


def _validate(db: Session, proposal_id: str, project_id: str | None,
              actor: str, comment: str | None) -> dict:
    from ..services.project_access import brain_ids, require_brain, require_mail_proposal
    from backend.app.services.project_operator import current_operator
    scope = brain_ids()
    if scope is not None:
        # Take the SQLite write lock before checking the proposal and its source.
        db.query(Proposal).filter_by(id=proposal_id, kind='project_attach', status='pending').update(
            {Proposal.status: Proposal.status}, synchronize_session=False)
        require_mail_proposal(db, proposal_id, scope)
        actor = current_operator().id
    prop = db.query(Proposal).filter_by(id=proposal_id).first()
    if not prop or prop.status != "pending" or prop.kind != "project_attach":
        raise HTTPException(404, "Proposition de classement introuvable ou déjà traitée")
    target_id = project_id or prop.project_id
    if scope is not None:
        require_brain(target_id)
    target = db.query(Project).filter_by(id=target_id).first()
    if not target:
        raise HTTPException(404, "Projet cible introuvable")
    source = db.query(Source).filter_by(id=prop.source_id).first()
    if not source:
        raise HTTPException(404, "Source introuvable")
    # Commit the human decision before inference/indexing; those run durably later.
    deferred = source.source_type == "email"
    res = resolve_source(db, None if deferred else get_memory_adapter(SessionLocal), source, target,
                         _ai_cfg(db), actor, defer_enrichment=deferred)
    prop.status = "accepted"
    suggested = db.query(Project).filter_by(id=prop.project_id).first()
    note = (comment or "") + (f" [suggestion IA : {suggested.code}]"
                              if suggested and suggested.id != target.id else "")
    db.add(ValidationDecision(proposal_id=prop.id, decision="accept", actor=actor,
                              comment=note.strip() or None,
                              resulting_knowledge_id=None))
    db.commit()
    return {**res, "proposal_id": prop.id, "validated_to": target.code}


@router.post("/{proposal_id}/accept")
def triage_accept(proposal_id: str, body: TriageDecision, db: Session = Depends(get_db)):
    """Valide le classement suggéré par l'IA."""
    return _validate(db, proposal_id, None, body.actor, body.comment)


@router.post("/{proposal_id}/reject")
def triage_reject(proposal_id: str, db: Session = Depends(get_db)):
    from backend.app.services.project_operator import current_operator
    from ..services.project_access import brain_ids, require_mail_proposal

    # Serialize with analysis and validation before checking the current scope.
    db.query(Proposal).filter_by(id=proposal_id, kind="project_attach", status="pending").update(
        {Proposal.status: Proposal.status}, synchronize_session=False)
    scope = brain_ids()
    require_mail_proposal(db, proposal_id, scope)
    proposal = db.get(Proposal, proposal_id)
    source = db.get(Source, proposal.source_id)
    pending = db.query(Proposal).filter_by(
        source_id=source.id, kind="project_attach", status="pending").all()
    if scope is not None and any(item.project_id not in scope for item in pending):
        raise HTTPException(404, "Proposition de classement introuvable ou déjà traitée")

    actor = current_operator().id
    source.status = "rejected"
    for item in pending:
        item.status = "rejected"
        db.add(ValidationDecision(proposal_id=item.id, decision="reject", actor=actor,
                                  comment="Mail exclu du classement"))
    db.commit()
    return {"source_id": source.id, "status": "rejected"}


class TriageAssign(BaseModel):
    project_id: str = Field(min_length=1, max_length=36)
    actor: str = "validator"
    comment: str | None = None


@router.post("/{proposal_id}/assign")
def triage_assign(proposal_id: str, body: TriageAssign, db: Session = Depends(get_db)):
    """Valide vers un autre projet que celui suggéré."""
    return _validate(db, proposal_id, body.project_id, body.actor, body.comment)
