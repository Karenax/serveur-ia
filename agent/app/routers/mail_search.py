"""Search whole mail folders before pagination, with a stable server-side sort."""
import unicodedata
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from ..db_support import utc_iso
from ..db import get_db
from ..models import Source, SourceArtifact, Proposal, Project, AuditLog
from ..services.resolution import proposal_details
from ..services.mail_discard_learning import build_discard_context

router = APIRouter(prefix="/v1/mail", tags=["mail"])


@router.get("/project-usage")
def project_usage(db: Session = Depends(get_db)):
    """Current mail assignments, weighted by time of actual classification."""
    import math
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    latest = {}
    rows = db.query(AuditLog.project_id, AuditLog.created_at, Source.id).join(
        Source, Source.id == AuditLog.payload["source_id"].as_string()).filter(
        AuditLog.event_type == "source.processed.v1", Source.source_type == "email",
        Source.status == "resolved", Source.project_id == AuditLog.project_id)
    from ..services.project_access import filter_brain
    rows = filter_brain(rows, Source.project_id)
    for project_id, created_at, source_id in rows:
        stamp = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at
        if source_id not in latest or stamp > latest[source_id][1]:
            latest[source_id] = (project_id, stamp)
    result = {}
    for project_id, stamp in latest.values():
        days = max(0, (now - stamp).total_seconds() / 86400)
        row = result.setdefault(project_id, {"project_id": project_id, "score": 0.0, "count": 0, "last_used": stamp.isoformat()})
        row["score"] += math.exp(-days / 30)
        row["count"] += 1
        row["last_used"] = max(row["last_used"], stamp.isoformat())
    return {"projects": sorted(result.values(), key=lambda row: (-row["score"], row["project_id"]))}


@router.get("/page")
def mail_page(scope: Literal["pending", "resolved", "rejected"] = "resolved", q: str = Query(default="", max_length=500),
              sort: Literal["newest", "oldest"] = "newest", project_id: str | None = None,
              offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=200),
              db: Session = Depends(get_db)):
    from ..services.project_access import brain_ids, filter_brain, pending_mail_scope, rejected_mail_scope
    projects = brain_ids()
    from backend.app.services.project_operator import current_operator
    if scope == 'pending' and projects is not None and current_operator().role == 'reader':
        raise HTTPException(403, 'La file de validation est réservée aux opérateurs qui peuvent classer les mails.')
    needle = "".join(c for c in unicodedata.normalize("NFKD", q.strip().casefold())
                     if not unicodedata.combining(c))
    query = db.query(Proposal if scope == "pending" else Source)
    if scope == "pending":
        query = query.join(Source, Source.id == Proposal.source_id).filter(
            Proposal.kind == "project_attach", Proposal.status == "pending", Source.status == "resolution_pending")
        query = pending_mail_scope(query, projects)
        target_column = Proposal.project_id
    elif scope == "rejected":
        query = rejected_mail_scope(query, projects)
        target_column = Source.project_id
    else:
        query = query.filter(Source.status == "resolved")
        query = filter_brain(query, Source.project_id)
        target_column = Source.project_id
    query = query.filter(Source.source_type == "email")
    if project_id:
        query = query.filter(target_column == project_id)
    if needle:
        project_match = db.query(Project.id).filter(func.agent_fold(Project.code).contains(needle, autoescape=True))
        query = query.filter(or_(
            func.agent_fold(Source.author).contains(needle, autoescape=True),
            func.agent_fold(Source.source_metadata["subject"].as_string()).contains(needle, autoescape=True),
            Source.artifacts.any(func.agent_fold(SourceArtifact.content_text).contains(needle, autoescape=True)),
            target_column.in_(project_match)))
    total = query.count()
    order = Source.received_at.desc() if sort == "newest" else Source.received_at.asc()
    query = query.order_by(order, Source.id.asc())
    if scope == "pending":
        # Source and target are fetched once per page, without one SQL call per mail.
        props = query.offset(offset).limit(limit).all()
        ids = [p.source_id for p in props]
        sources = {s.id: s for s in db.query(Source).options(selectinload(Source.artifacts)).filter(Source.id.in_(ids))}
        targets = {p.id: p for p in db.query(Project).filter(Project.id.in_([p.project_id for p in props]))}
        rows = []
        discard_context = build_discard_context(db) if projects is None else None
        for prop in props:
            source, target = sources[prop.source_id], targets.get(prop.project_id)
            details = proposal_details(prop.value, prop.project_id)
            if projects is not None:
                details['candidates'] = [c for c in details['candidates'] if c.get('project_id') in projects]
            rows.append({"proposal_id": prop.id, "source_id": source.id, "sender": source.author or "",
                         "subject": (source.source_metadata or {}).get("subject", ""),
                         "received_at": utc_iso(source.received_at), "excerpt": _excerpt(source, needle, 400),
                         "target_project_id": target.id if target else None, "target_code": target.code if target else None,
                         "target_name": target.name if target else None, "confidence": prop.confidence, "reason": prop.reason or "",
                         "discard_suggestion": discard_context.estimate(source) if discard_context else None,
                         **details})
    else:
        sources = query.options(selectinload(Source.artifacts)).offset(offset).limit(limit).all()
        rows = [{"source_id": s.id, "type": s.source_type, "status": s.status, "received_at": utc_iso(s.received_at),
                 "excerpt": _excerpt(s, needle, 400), "project_id": s.project_id,
                 "author": s.author, "metadata": s.source_metadata} for s in sources]
    return {"rows": rows, "total": total, "offset": offset, "limit": limit, "has_next": offset + len(rows) < total}


def _excerpt(source, needle, size):
    texts = [a.content_text for a in source.artifacts if a.content_text and a.kind in {"body_text", "transcription", "ocr"}]
    text = next((t for t in texts if needle and needle.casefold() in t.casefold()), texts[0] if texts else "")
    start = max(0, text.casefold().find(needle) - 100) if needle else 0
    return text[start:start + size]
