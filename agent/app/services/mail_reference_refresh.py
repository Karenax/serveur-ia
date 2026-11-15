"""Répare les suggestions en attente, sans changer les décisions humaines."""
import json

from sqlalchemy.orm import Session

from ..models import AuditLog, Proposal, Source
from .resolution import choose_candidate, resolve_project
from .mail_learning import build_learning_context, reply_headers
from .triage import _mail_text, _pending_attaches, _real_projects


def refresh_reference_suggestions(db: Session, *, apply: bool = False, learned: bool = False,
                                  exclude_source_ids: set[str] | None = None) -> dict:
    projects = _real_projects(db)
    learning = build_learning_context(db, projects) if learned else None
    result = {"updated": 0, "eligible": 0, "conflicts": 0, "by_code": {}}
    sources = db.query(Source).filter_by(status="resolution_pending", source_type="email").all()
    for source in sources:
        if source.id in (exclude_source_ids or set()):
            continue
        parsed = {"subject": (source.source_metadata or {}).get("subject", ""),
                  "body_text": _mail_text(db, source), "sender": source.author or "",
                  "participants": source.participants,
                  "attachments": (source.source_metadata or {}).get("attachments", []),
                  **reply_headers(source.source_metadata or {}, source.original_uri)}
        candidates = resolve_project(parsed, projects, None, learning)["candidates"]
        explicit = [c for c in candidates if
                    {"explicit_code", "explicit_alias"}.intersection(c["reasons"])]
        if len(explicit) > 1:
            result["conflicts"] += 1
        best = choose_candidate(candidates)
        if not best or (not learned and len(explicit) != 1):
            continue
        old = _pending_attaches(db, source.id)
        if not old or (len(old) == 1 and old[0].project_id == best["project_id"]
                       and (old[0].confidence or 0) >= best["score"] - 0.03):
            continue
        result["eligible"] += 1
        result["by_code"][best["code"]] = result["by_code"].get(best["code"], 0) + 1
        if not apply:
            continue
        # Même garde contre les validations/exclusions concurrentes que le tri.
        active = db.query(Source).filter_by(id=source.id, status="resolution_pending").update(
            {Source.status: Source.status}, synchronize_session=False)
        if not active:
            continue
        old = _pending_attaches(db, source.id)
        if not old:
            continue
        previous_ids = [p.id for p in old]
        for proposal in old:
            proposal.status = "superseded"
        db.add(Proposal(
            project_id=best["project_id"], source_id=source.id, kind="project_attach",
            subject=f"Classer : {parsed['subject'][:120] or '(sans objet)'}",
            value=json.dumps({"sender": parsed["sender"], "subject": parsed["subject"],
                              "candidates": candidates[:3]}, ensure_ascii=False),
            confidence=best["score"], reason="triage IA : " + ", ".join(best["reasons"])))
        db.add(AuditLog(
            event_type="triage.reference_refreshed.v1", actor="reference-refresh",
            project_id=best["project_id"],
            payload={"source_id": source.id, "superseded_proposal_ids": previous_ids}))
        result["updated"] += 1
    if apply:
        db.commit()
        from .settings_service import get_section
        from .triage import auto_classify_proposal
        result["auto_classified"] = 0
        for source in sources:
            if source.id in (exclude_source_ids or set()):
                continue
            for proposal in _pending_attaches(db, source.id):
                if auto_classify_proposal(db, proposal, get_section(db, "ai")):
                    result["auto_classified"] += 1
                    break
        db.commit()
    return result
