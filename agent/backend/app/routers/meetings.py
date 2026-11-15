"""Comptes rendus de réunion : décisions + actions convertibles en tâches, export Markdown."""
from __future__ import annotations

import hashlib
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import Field
from ..schemas import DomainInput as BaseModel, IsoDate
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Meeting, MeetingAction, Project, Task
from ..services.planning_revision import begin_change, record_change
from ..services.project_operator import require_project_access

router = APIRouter(prefix="/api/v1", tags=["meetings"])


class MeetingCreate(BaseModel):
    date: IsoDate = ""
    title: str = Field(min_length=1)
    participants: str = ""
    decisions: str = ""


class ActionCreate(BaseModel):
    title: str = Field(min_length=1)
    owner: str = ""
    due_date: IsoDate = ""


def _get_meeting(db: Session, project_id: str, meeting_id: str) -> Meeting:
    meeting = db.query(Meeting).filter_by(id=meeting_id, project_id=project_id).first()
    if not meeting:
        raise HTTPException(404, "CR introuvable")
    return meeting


def _actions(db: Session, meeting_id: str) -> list[dict]:
    return [
        {"id": a.id, "title": a.title, "owner": a.owner, "due_date": a.due_date,
         "task_id": a.task_id}
        for a in db.query(MeetingAction).filter_by(meeting_id=meeting_id).all()
    ]


@router.get("/projects/{project_id}/meetings")
def list_meetings(project_id: str, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    out = []
    for m in db.query(Meeting).filter_by(project_id=project_id).order_by(Meeting.date.desc()).all():
        actions = _actions(db, m.id)
        out.append({"id": m.id, "date": m.date, "title": m.title,
                    "participants": m.participants, "decisions": m.decisions,
                    "actions": actions,
                    "open_actions": sum(1 for a in actions if not a["task_id"])})
    return out


@router.post("/projects/{project_id}/meetings", status_code=201)
def create_meeting(project_id: str, payload: MeetingCreate, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    meeting = Meeting(project_id=project_id, date=payload.date, title=payload.title,
                      participants=payload.participants, decisions=payload.decisions)
    db.add(meeting)
    db.commit()
    return {"id": meeting.id, "title": meeting.title}


@router.post("/projects/{project_id}/meetings/{meeting_id}/actions", status_code=201)
def add_action(project_id: str, meeting_id: str, payload: ActionCreate,
               db: Session = Depends(get_db)):
    _get_meeting(db, project_id, meeting_id)
    action = MeetingAction(meeting_id=meeting_id, project_id=project_id,
                           title=payload.title, owner=payload.owner,
                           due_date=payload.due_date)
    db.add(action)
    db.commit()
    return {"id": action.id, "title": action.title}


@router.post("/projects/{project_id}/meetings/{meeting_id}/actions/{action_id}/to-task",
             status_code=201)
def action_to_task(project_id: str, meeting_id: str, action_id: str,
                   db: Session = Depends(get_db), expected_revision: int | None = None):
    if expected_revision is not None and expected_revision < 0:
        raise HTTPException(422, "Révision positive requise")
    actor, state = begin_change(db, project_id, expected_revision)
    _get_meeting(db, project_id, meeting_id)
    action = db.query(MeetingAction).filter_by(id=action_id, meeting_id=meeting_id).first()
    if not action:
        raise HTTPException(404, "Action introuvable")
    if action.task_id and db.get(Task, action.task_id):
        raise HTTPException(409, "Action déjà convertie en tâche")
    label = action.title
    if action.owner:
        label += f" ({action.owner})"
    task = Task(project_id=project_id, title=label, status="todo", due_date=action.due_date)
    db.add(task)
    db.flush()
    action.task_id = task.id
    result = {"id": task.id, "title": task.title, "revision": state.revision}
    record_change(db, actor, state, "meeting_action_converted", {},
                  {"task": result, "meeting_id": meeting_id, "action_id": action_id})
    db.commit()
    return result


@router.get("/projects/{project_id}/meetings/{meeting_id}/export")
def export_meeting(project_id: str, meeting_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Projet introuvable")
    meeting = _get_meeting(db, project_id, meeting_id)
    actions = _actions(db, meeting.id)
    lines = [
        f"# CR — {project.code} {project.title}".strip(),
        f"**{meeting.date} — {meeting.title}**",
        "",
        f"Participants : {meeting.participants or '—'}",
        "",
        "## Décisions",
        "",
        meeting.decisions or "—",
        "",
        "## Actions",
        "",
    ]
    for action in actions:
        status = "✅ transférée en tâche" if action["task_id"] else "⏳ à traiter"
        extra = f" — {action['owner']}" if action["owner"] else ""
        extra += f" (échéance {action['due_date']})" if action["due_date"] else ""
        lines.append(f"- [ ] {action['title']}{extra} — {status}")
    content = "\n".join(lines)
    # A consultation must not create or overwrite a server-side export. Keep
    # the historical JSON contract; download bytes through the dedicated URL.
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    name = re.sub(r'[^A-Za-z0-9_-]', '_', meeting.id)
    filename = f"cr-{name}-{digest[:12]}.md"
    return {"file": filename, "filename": filename, "markdown": content, "sha256": digest,
            "download_url": f"/api/v1/projects/{project_id}/meetings/{meeting_id}/markdown"}


@router.get('/projects/{project_id}/meetings/{meeting_id}/markdown')
def download_meeting_markdown(project_id: str, meeting_id: str, db: Session = Depends(get_db)):
    require_project_access(project_id)
    result = export_meeting(project_id, meeting_id, db)
    return Response(result['markdown'], media_type='text/markdown; charset=utf-8', headers={
        'Content-Disposition': f'attachment; filename="{result["filename"]}"',
        'Cache-Control': 'private, no-store'})


@router.get('/projects/{project_id}/meetings/{meeting_id}/pdf')
def export_meeting_pdf(project_id: str, meeting_id: str, db: Session = Depends(get_db)):
    require_project_access(project_id)
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, 'Projet introuvable')
    meeting = _get_meeting(db, project_id, meeting_id)
    from ..services.meeting_report_pdf import build_pdf
    content = build_pdf({'code': project.code, 'title': project.title},
        {key: getattr(meeting, key) for key in ('title', 'date', 'participants', 'decisions')}, _actions(db, meeting.id))
    name = re.sub(r'[^A-Za-z0-9_-]', '_', meeting.id)
    return Response(content, media_type='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="cr-{name}.pdf"', 'Cache-Control': 'private, no-store'})
