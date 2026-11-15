"""Recherche globale + export / import JSON des projets (sauvegarde manuelle)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (CdcItem, Deliverable, Meeting, MeetingAction,
                      Milestone, NetworkLink, Project, Task)
from ..services.client_directory import client_directory
from app.services.project_access import filter_erp, require_erp

router = APIRouter(prefix="/api/v1", tags=["portfolio-tools"])


@router.get("/search")
def search(q: str, project_id: str | None = None, db: Session = Depends(get_db)):
    """Recherche globale : projets, tâches, matrice CDC, CR. q min 2 caractères.

    Si project_id est fourni, la recherche est restreinte à ce projet
    (utile pour retrouver une tâche/élément/CR sans changer de fenêtre).
    """
    needle = (q or "").strip().lower()
    if len(needle) < 2:
        raise HTTPException(400, "Recherche trop courte (2 caractères min)")
    like = f"%{needle}%"
    out: list[dict] = []
    if project_id:
        require_erp(project_id)
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(404, "Projet introuvable")
        project_filter = [Task.project_id == project_id]
        scope = f"{project.code} › "
    else:
        project_filter = []
        scope = ""
        projects = filter_erp(db.query(Project), Project.id).filter(
            (Project.code.ilike(like)) | (Project.title.ilike(like))
            | (Project.client_name.ilike(like))).all()
        out = [
            {"type": "project", "project_id": p.id, "tab": "pilotage",
             "label": f"{p.code} — {p.title}"} for p in projects
        ]
    task_query = filter_erp(db.query(Task), Task.project_id)
    if project_filter:
        task_query = task_query.filter(*project_filter)
    for task in task_query.filter(Task.title.ilike(like)).limit(50).all():
        if project_id:
            label = f"Tâche : {task.title}"
        else:
            project = db.get(Project, task.project_id)
            label = f"{project.code if project else '?'} › tâche : {task.title}"
        out.append({"type": "task", "project_id": task.project_id, "tab": "tasks",
                    "label": scope + label})
    item_query = filter_erp(db.query(CdcItem), CdcItem.project_id)
    if project_id:
        item_query = item_query.filter(CdcItem.project_id == project_id)
    for item in item_query.filter(
            (CdcItem.title.ilike(like)) | (CdcItem.source_quote.ilike(like))).limit(50).all():
        if project_id:
            label = f"CDC [{item.kind}] : {item.title}"
        else:
            project = db.get(Project, item.project_id)
            label = f"{project.code if project else '?'} › CDC [{item.kind}] : {item.title}"
        out.append({"type": "cdc", "project_id": item.project_id, "tab": "cdc",
                    "label": scope + label})
    meeting_query = filter_erp(db.query(Meeting), Meeting.project_id)
    if project_id:
        meeting_query = meeting_query.filter(Meeting.project_id == project_id)
    for meeting in meeting_query.filter(
            (Meeting.title.ilike(like)) | (Meeting.decisions.ilike(like))).limit(50).all():
        if project_id:
            label = f"CR : {meeting.title}"
        else:
            project = db.get(Project, meeting.project_id)
            label = f"{project.code if project else '?'} › CR : {meeting.title}"
        out.append({"type": "meeting", "project_id": meeting.project_id, "tab": "reviews",
                    "label": scope + label})
    return out[:100]


@router.get("/projects/{project_id}/export")
def export_project(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Projet introuvable")
    from ..services.project_archive import export_archive
    return export_archive(db, project_id)


# Legacy v1 exchange export retained for compatibility.
def export_legacy_project(project_id: str, db: Session):
    project = db.get(Project, project_id)
    meetings = []
    for meeting in db.query(Meeting).filter_by(project_id=project_id).all():
        actions = db.query(MeetingAction).filter_by(meeting_id=meeting.id).all()
        meetings.append({
            "date": meeting.date, "title": meeting.title,
            "participants": meeting.participants, "decisions": meeting.decisions,
            "actions": [{"title": a.title, "owner": a.owner, "due_date": a.due_date,
                         "as_task": bool(a.task_id)} for a in actions],
        })
    return {
        "format": "minipilot-export",
        "version": 1,
        "project": {
            "code": project.code, "title": project.title, "status": project.status,
            "hourly_rate": project.hourly_rate, "margin_pct": project.margin_pct,
            "client_name": project.client_name, "offer_number": project.offer_number,
            "tdao_prix_vente": project.tdao_prix_vente, "tdao_budget_h": project.tdao_budget_h,
        },
        "tasks": [{"title": t.title, "status": t.status, "due_date": t.due_date}
                  for t in db.query(Task).filter_by(project_id=project_id).all()],
        "milestones": [{"title": m.title, "due_date": m.due_date,
                        "contractual_date": m.contractual_date, "forecast_date": m.forecast_date,
                        "actual_date": m.actual_date, "date_sources": m.date_sources}
                       for m in db.query(Milestone).filter_by(project_id=project_id).all()],
        "deliverables": [{"title": d.title, "status": d.status}
                         for d in db.query(Deliverable).filter_by(project_id=project_id).all()],
        "cdc_items": [{
            "kind": i.kind, "title": i.title, "normalized_wording": i.normalized_wording,
            "source_quote": i.source_quote, "physical_page": i.physical_page,
            "modality": i.modality, "priority": i.priority, "confidence": i.confidence,
            "estimated_hours": i.estimated_hours, "unit_price": i.unit_price,
        } for i in db.query(CdcItem).filter_by(project_id=project_id).all()],
        "network_links": [{
            "code": link.code, "libelle": link.libelle, "chemin": link.chemin,
            "ordre": link.ordre,
        } for link in db.query(NetworkLink).filter_by(project_id=project_id)
            .order_by(NetworkLink.ordre).all()],
        "meetings": meetings,
    }


class ImportJsonRequest(BaseModel):
    data: dict
    code: str | None = None


@router.post("/projects/import-json", status_code=201)
def import_json(payload: ImportJsonRequest, db: Session = Depends(get_db)):
    data = payload.data or {}
    if data.get("format") == "agent-project-archive":
        from ..services.project_archive import import_archive
        return import_archive(db, data, payload.code)
    if data.get("format") != "minipilot-export":
        raise HTTPException(400, "Fichier non reconnu (format minipilot-export attendu)")
    info = data.get("project", {})
    code = (payload.code or info.get("code") or "").strip()
    if not code:
        raise HTTPException(400, "Code projet manquant")
    if db.query(Project).filter_by(code=code).first():
        raise HTTPException(409, f"Un projet '{code}' existe déjà")
    project = Project(
        code=code, title=info.get("title", code), status=info.get("status", "active"),
        hourly_rate=info.get("hourly_rate", 85), margin_pct=info.get("margin_pct", 10),
        client_name=info.get("client_name", ""), offer_number=info.get("offer_number", ""),
        tdao_prix_vente=info.get("tdao_prix_vente", 0), tdao_budget_h=info.get("tdao_budget_h", 0),
    )
    db.add(project)
    db.flush()
    for task in data.get("tasks", []):
        db.add(Task(project_id=project.id, title=task.get("title", "?"),
                    status=task.get("status", "todo"), due_date=task.get("due_date", "")))
    for milestone in data.get("milestones", []):
        db.add(Milestone(project_id=project.id, title=milestone.get("title", "?"),
                         due_date=milestone.get("forecast_date") or milestone.get("contractual_date") or milestone.get("due_date", ""),
                         contractual_date=milestone.get("contractual_date", ""),
                         forecast_date=milestone.get("forecast_date", milestone.get("due_date", "")),
                         actual_date=milestone.get("actual_date", ""), date_sources=milestone.get("date_sources", {})))
    for deliverable in data.get("deliverables", []):
        db.add(Deliverable(project_id=project.id, title=deliverable.get("title", "?"),
                           status=deliverable.get("status", "todo")))
    for item in data.get("cdc_items", []):
        if item.get("kind") not in ("function", "constraint", "requirement",
                                    "data", "interface", "open_point"):
            continue
        db.add(CdcItem(project_id=project.id, kind=item["kind"], title=item.get("title", "?"),
                       normalized_wording=item.get("normalized_wording", ""),
                       source_quote=item.get("source_quote", "?"),
                       physical_page=item.get("physical_page", 1),
                       modality=item.get("modality", "information"),
                       priority=item.get("priority", "unclassified"),
                       confidence=item.get("confidence", 0.5),
                       estimated_hours=item.get("estimated_hours", 0),
                       unit_price=item.get("unit_price", 0)))
    for link in data.get("network_links", []):
        if not link.get("code"):
            continue
        db.add(NetworkLink(project_id=project.id, code=link["code"],
                           libelle=link.get("libelle", link["code"]),
                           chemin=link.get("chemin"), ordre=link.get("ordre", 0)))
    for meeting in data.get("meetings", []):
        new_meeting = Meeting(project_id=project.id, date=meeting.get("date", ""),
                              title=meeting.get("title", "?"),
                              participants=meeting.get("participants", ""),
                              decisions=meeting.get("decisions", ""))
        db.add(new_meeting)
        db.flush()
        for action in meeting.get("actions", []):
            new_action = MeetingAction(
                meeting_id=new_meeting.id, project_id=project.id,
                title=action.get("title", "?"), owner=action.get("owner", ""),
                due_date=action.get("due_date", ""))
            db.add(new_action)
            db.flush()
            if action.get("as_task"):
                task = Task(project_id=project.id,
                            title=new_action.title + (f" ({new_action.owner})" if new_action.owner else ""),
                            status="todo", due_date=new_action.due_date)
                db.add(task)
                db.flush()
                new_action.task_id = task.id
    with client_directory(db, project.id):
        db.commit()
    return {"id": project.id, "code": project.code, "title": project.title}


@router.get("/projects/{project_id}/planning")
def planning(project_id: str, db: Session = Depends(get_db)):
    """Échéancier : jalons + tâches datées triés, retards, charge restante."""
    from datetime import date
    from ..services.planning_revision import revision

    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Projet introuvable")
    today = date.today().isoformat()
    entries = []
    for milestone in db.query(Milestone).filter_by(project_id=project_id).all():
        entries.append({"type": "milestone", "id": milestone.id, "title": milestone.title,
                        "due_date": milestone.due_date or "",
                        "contractual_date": milestone.contractual_date, "forecast_date": milestone.forecast_date,
                        "actual_date": milestone.actual_date, "status": "done" if milestone.actual_date else "todo",
                        "overdue": bool(not milestone.actual_date and milestone.due_date and milestone.due_date < today)})
    for task in db.query(Task).filter_by(project_id=project_id).all():
        closed = (task.status or "") in ("done", "cancelled")
        entries.append({"type": "task", "id": task.id, "title": task.title,
                        "due_date": task.due_date or "", "status": task.status,
                        "overdue": bool(not closed and task.due_date and task.due_date < today)})
    entries.sort(key=lambda e: (e["due_date"] or "9999", e["title"]))
    from ..models import TimeEntry, SagePointage
    from ..services.work_hours import sage_hours, project_hours
    from ..routers.workshop import _for_project
    items = db.query(CdcItem).filter(CdcItem.project_id == project_id,
                                    CdcItem.knowledge_status.notin_(["rejected", "superseded"])).all()
    budget_h = sum(i.estimated_hours or 0 for i in items) or project.tdao_budget_h or 0
    consumed = sum(t.hours or 0 for t in db.query(TimeEntry).filter_by(project_id=project_id))
    consumed += sum(sage_hours(row.payload) for row in _for_project(db, SagePointage, project.code))
    hours = project_hours(project, budget_h, consumed)
    return {
        "entries": entries,
        "planning_revision": revision(db, project_id),
        "overdue_count": sum(1 for e in entries if e["overdue"]),
        "undated_count": sum(1 for e in entries if not e["due_date"]),
        "remaining_hours": hours["raf"], "consumed_hours": hours["consumed_hours"],
        "remaining_mode": hours["remaining_mode"], "overrun_hours": hours["overrun_hours"],
        "budget_hours": budget_h,
        "consumed_pct": round(consumed / budget_h * 100) if budget_h else None,
    }
