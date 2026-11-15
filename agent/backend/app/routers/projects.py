from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from ..schemas import DomainInput as BaseModel, IsoDate, TaskStatus, ProjectStatus, ProjectCode
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CdcItem, Deliverable, Milestone, Project, Task, TimeEntry, SagePointage, BrainLink
from ..services import milestones as milestone_service
from ..services import project_planning as planning_service
from ..services import project_deliverables as deliverable_service
from ..services.client_directory import client_directory
from ..services.planning_revision import begin_change, record_change
from ..project_planning_schemas import PlanningTaskStatus
from app.services.project_access import filter_erp

router = APIRouter(prefix="/api/v1", tags=["projects"])


class ProjectCreate(BaseModel):
    code: ProjectCode = ""
    title: str = Field(min_length=1)
    status: ProjectStatus = "active"


class TaskCreate(BaseModel):
    title: str = Field(min_length=1)
    status: TaskStatus = "todo"
    due_date: IsoDate = ""
    expected_revision: int | None = Field(default=None, ge=0)


class DeliverableCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    status: TaskStatus = "todo"
    expected_revision: int | None = Field(default=None, ge=0)


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=1)
    due_date: IsoDate = ""
    contractual_date: IsoDate = ""
    forecast_date: IsoDate = ""
    actual_date: IsoDate = ""
    expected_revision: int | None = Field(default=None, ge=0)


def _overdue(tasks: list) -> int:
    from datetime import date

    today = date.today().isoformat()
    n = 0
    for t in tasks:
        if (t.status or "") in ("done", "cancelled"):
            continue
        if t.due_date and t.due_date < today:
            n += 1
    return n


@router.get("/project-catalogue")
def project_catalogue(db: Session = Depends(get_db)):
    projects = db.query(Project.id, Project.code, Project.title, Project.status, BrainLink.brain_project_id)
    projects = projects.outerjoin(BrainLink, BrainLink.project_id == Project.id)
    projects = filter_erp(projects, Project.id).order_by(Project.created_at.desc(), Project.id)
    return [{"id": project.id, "code": project.code, "title": project.title,
             "status": project.status, "brain_project_id": project.brain_project_id}
            for project in projects]


@router.get("/portfolio")
def portfolio(db: Session = Depends(get_db)):
    """Operational portfolio. Hours and decisions, with no financial calculation."""
    from collections import defaultdict
    from ..services.work_hours import sage_hours, project_hours
    groups = {}
    for name, model in (("tasks", Task), ("milestones", Milestone), ("items", CdcItem), ("time", TimeEntry)):
        grouped = defaultdict(list)
        for row in db.query(model).all():
            grouped[row.project_id].append(row)
        groups[name] = grouped
    sage = defaultdict(float)
    for row in db.query(SagePointage).all():
        sage[(row.affaire or "").strip().casefold()] += sage_hours(row.payload)
    links = {link.project_id: link for link in db.query(BrainLink).all()}
    out = []
    for p in filter_erp(db.query(Project), Project.id).order_by(Project.created_at.desc()).all():
        tasks = groups["tasks"][p.id]
        jalons = sorted((m for m in groups["milestones"][p.id] if not m.actual_date),
                        key=lambda m: (not bool(m.due_date), m.due_date or "", milestone_service.order(m)))
        items = [i for i in groups["items"][p.id] if i.knowledge_status not in {"rejected", "superseded"}]
        done_t = [t for t in tasks if (t.status or "") == "done"]
        consumed = sum(t.hours or 0 for t in groups["time"][p.id]) + (sage[p.code.strip().casefold()] if p.code.strip() else 0)
        hours = project_hours(p, sum(i.estimated_hours or 0 for i in items), consumed)
        pending = sum(1 for i in items if i.knowledge_status != "confirmed")
        open_points = sum(1 for i in items if i.kind == "open_point")
        corrections = sum(1 for i in items if i.knowledge_status != "confirmed" or i.kind == "open_point")
        link = links.get(p.id)
        progress = round(len(done_t) / len(tasks) * 100) if tasks else 0
        out.append({
            "id": p.id, "code": p.code, "title": p.title, "status": p.status,
            "client_name": p.client_name or "",
            "jalon_en_cours": jalons[0].title if jalons else "—",
            "jalon_echeance": jalons[0].due_date if jalons and jalons[0].due_date else "",
            "avancement": progress,
            **hours,
            "unconfirmed": pending, "open_points": open_points,
            "brain_project_id": link.brain_project_id if link else None,
            "brain_code": link.brain_code if link else None,
            "taches": f"{len(done_t)}/{len(tasks)}",
            "en_retard": _overdue(tasks),
            "corrections": corrections,
            "correction_label": (
                f"{corrections} action(s) à corriger" if corrections else "RAS"
            ),
        })
    return out


class ProjectPatch(BaseModel):
    code: ProjectCode | None = None
    title: str | None = Field(default=None, min_length=1)
    status: ProjectStatus | None = None
    remaining_hours: float | None = Field(default=None, ge=0, le=1e12)


@router.patch("/projects/{project_id}")
def patch_project(project_id: str, payload: ProjectPatch, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Projet introuvable")
    for field in ("code", "title", "status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(p, field, value)
    if "remaining_hours" in payload.model_fields_set:
        p.remaining_hours = payload.remaining_hours
    db.commit()
    return {"id": p.id, "code": p.code, "title": p.title, "status": p.status}


@router.post("/projects", status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    p = Project(code=payload.code, title=payload.title, status=payload.status)
    db.add(p)
    db.flush()
    from .network_links import _ensure_required
    _ensure_required(db, p.id)
    milestone_service.seed(db, p.id)
    with client_directory(db, p.id):
        db.commit()
    db.refresh(p)
    return {"id": p.id, "code": p.code, "title": p.title, "status": p.status}


@router.get("/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Projet introuvable")
    planning = planning_service.read_planning(db, project_id)
    livrables = db.query(Deliverable).filter_by(project_id=project_id).all()
    return {
        "id": p.id, "code": p.code, "title": p.title, "status": p.status,
        "remaining_hours": p.remaining_hours,
        "planning_revision": planning["revision"],
        "tasks": planning["tasks"],
        "deliverables": [{"id": d.id, "title": d.title, "status": d.status} for d in livrables],
        "milestones": planning["milestones"],
    }


@router.post("/projects/{project_id}/tasks", status_code=201)
def add_task(project_id: str, payload: TaskCreate, db: Session = Depends(get_db)):
    actor, state = begin_change(db, project_id, payload.expected_revision)
    t = Task(project_id=project_id, title=payload.title, status=payload.status, due_date=payload.due_date)
    db.add(t)
    db.flush()
    result = {"id": t.id, "title": t.title, "status": t.status,
              "due_date": t.due_date, "revision": state.revision}
    record_change(db, actor, state, "task_created", {}, {"task": result})
    db.commit()
    return result


class TaskPatch(BaseModel):
    title: str | None = None
    status: PlanningTaskStatus | None = None
    due_date: IsoDate | None = None
    expected_revision: int | None = Field(default=None, ge=0)


class MilestonePatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    due_date: IsoDate | None = None
    contractual_date: IsoDate | None = None
    forecast_date: IsoDate | None = None
    actual_date: IsoDate | None = None
    workflow_status: Literal['pending', 'open', 'validated', 'blocked', 'skipped'] | None = None
    expected_revision: int | None = Field(default=None, ge=0)


class DeliverablePatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: TaskStatus | None = None
    expected_revision: int | None = Field(default=None, ge=0)


@router.patch("/projects/{project_id}/tasks/{task_id}")
def patch_task(project_id: str, task_id: str, payload: TaskPatch,
               db: Session = Depends(get_db)):
    result = planning_service.patch_legacy_task(db, project_id, task_id,
        payload.model_dump(exclude_unset=True, exclude={"expected_revision"}), payload.expected_revision)
    db.commit()
    return {**result["task"], "revision": result["revision"]}


@router.patch("/projects/{project_id}/milestones/{milestone_id}")
def patch_milestone(project_id: str, milestone_id: str, payload: MilestonePatch,
                    db: Session = Depends(get_db)):
    result = planning_service.patch_legacy_milestone(db, project_id, milestone_id,
        payload.model_dump(exclude_unset=True, exclude={"expected_revision"}), payload.expected_revision)
    db.commit()
    return {**result["milestone"], "revision": result["revision"]}


@router.patch("/projects/{project_id}/deliverables/{deliverable_id}")
def patch_deliverable(project_id: str, deliverable_id: str, payload: DeliverablePatch,
                      db: Session = Depends(get_db)):
    try:
        result = deliverable_service.patch_legacy_deliverable(db, project_id, deliverable_id,
            payload.model_dump(exclude_unset=True, exclude={'expected_revision'}), payload.expected_revision)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


@router.post("/projects/{project_id}/deliverables", status_code=201)
def add_deliverable(project_id: str, payload: DeliverableCreate, db: Session = Depends(get_db)):
    try:
        result = deliverable_service.create_legacy_deliverable(db, project_id, **payload.model_dump())
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


@router.post("/projects/{project_id}/milestones", status_code=201)
def add_milestone(project_id: str, payload: MilestoneCreate, db: Session = Depends(get_db)):
    actor, state = begin_change(db, project_id, payload.expected_revision)
    from ..services.milestones import apply_dates, describe
    m = Milestone(project_id=project_id, title=payload.title)
    db.add(m)
    db.flush()
    apply_dates(db, m, {"contractual_date": payload.contractual_date,
                       "forecast_date": payload.forecast_date or payload.due_date,
                       "actual_date": payload.actual_date}, {"kind": "manual", "label": "Saisie manuelle", "actor": actor.id})
    result = {**describe(m), "revision": state.revision}
    record_change(db, actor, state, "milestone_created", {}, {"milestone": result})
    db.commit()
    return result
