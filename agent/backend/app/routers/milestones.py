"""Evidence review and durable scanning for the project's milestone table."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Milestone, MilestoneCandidate, MilestoneChange, MilestoneScanJob, Project
from ..schemas import DomainInput
from ..services import milestones, milestone_scan
from ..services.planning_revision import revision
from ..services.project_operator import require_project_access

router = APIRouter(prefix="/api/v1/projects/{project_id}/milestones", tags=["milestones"])


def require_project(db, project_id):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")


@router.get("/review")
def review(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    rows = db.query(MilestoneCandidate).filter_by(project_id=project_id, status="pending").order_by(
        MilestoneCandidate.created_at.desc()).limit(300).all()
    candidates = []
    for row in rows:
        target = milestones.matching(db, project_id, row.title)
        current = (getattr(target, row.date_type) or "") if target else ""
        candidates.append({"id": row.id, "title": row.title, "date_type": row.date_type, "date": row.value,
                           "quote": row.quote, "evidence": row.evidence, "confidence": row.confidence,
                           "current_value": current, "conflict": bool(current and current != row.value),
                           "milestone_id": target.id if target else None})
    latest = db.query(MilestoneScanJob).filter_by(project_id=project_id).order_by(MilestoneScanJob.created_at.desc()).first()
    return {"planning_revision": revision(db, project_id), "candidates": candidates, "pending_total": db.query(MilestoneCandidate).filter_by(
        project_id=project_id, status="pending").count(), "job": milestone_scan.describe(latest) if latest else None}


@router.post("/scan", status_code=202)
def scan(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    return milestone_scan.enqueue(db, project_id)


class Decision(DomainInput):
    decision: str = Field(pattern="^(accept|reject)$")
    expected_value: str = ""
    milestone_id: str | None = None
    expected_revision: int | None = Field(default=None, ge=0)


@router.post("/candidates/{candidate_id}/decision")
def decide(project_id: str, candidate_id: str, payload: Decision, db: Session = Depends(get_db)):
    require_project_access(project_id, write=True)
    candidate = db.query(MilestoneCandidate).filter_by(id=candidate_id, project_id=project_id).first()
    if not candidate:
        raise HTTPException(404, "Proposition introuvable")
    # Serialize business changes in SQLite, re-check after obtaining the write lock.
    db.query(MilestoneCandidate).filter_by(id=candidate_id).update({"status": candidate.status}, synchronize_session=False)
    db.refresh(candidate)
    if candidate.status != "pending":
        raise HTTPException(409, "Proposition déjà traitée")
    if payload.decision == "reject":
        candidate.status = "rejected"
        result = {"status": "rejected"}
    else:
        result = milestones.accept_candidate(db, candidate, payload.expected_value, payload.milestone_id,
                                             expected_revision=payload.expected_revision)
    db.commit()
    return result


@router.get("/{milestone_id}/history")
def history(project_id: str, milestone_id: str, db: Session = Depends(get_db)):
    if not db.query(Milestone).filter_by(id=milestone_id, project_id=project_id).first():
        raise HTTPException(404, "Jalon introuvable")
    from app.db_support import utc_iso
    return [{"id": row.id, "field": row.field, "previous": row.previous, "value": row.value,
             "evidence": row.evidence, "created_at": utc_iso(row.created_at)} for row in
            db.query(MilestoneChange).filter_by(milestone_id=milestone_id, project_id=project_id)
            .order_by(MilestoneChange.created_at.desc()).limit(200)]
