"""Private discovery for the Kiara service, never exposed through its client gateway."""

import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select, tuple_, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.db import get_db
from app.meeting_session_models import MeetingAudioChunk, MeetingSession
from app.models import AuditLog, MeetingRecording
from app.services.project_access import filter_erp, require_brain, require_erp
from app.services.unified_search import search
from backend.app.db import get_db as get_erp_db
from backend.app.models import BrainLink, KiaraConversation, KiaraProjectMemory, Project
from backend.app.services.project_operator import current_operator

router = APIRouter(prefix='/internal/kiara', tags=['kiara-internal'])


class ConversationCommand(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['conversation_save', 'conversation_archive', 'conversation_move', 'conversation_delete']
    id: str = Field(pattern=r'^[0-9a-f]{32}$')
    revision: int = Field(default=0, ge=0, strict=True)
    title: str | None = Field(default=None, min_length=1, max_length=120)
    messages: list[dict] | None = Field(default=None, max_length=1000)
    archived: bool | None = Field(default=None, strict=True)
    destination: str | None = Field(default=None, max_length=36)


class MemoryCommand(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    action: Literal['memory_create', 'memory_save', 'memory_delete']
    id: str | None = Field(default=None, pattern=r'^[0-9a-f]{32}$')
    revision: str | None = Field(default=None, pattern=r'^[1-9][0-9]{0,14}$')
    text: str | None = Field(default=None, min_length=1, max_length=2000)


def project_scope(project_id, erp, *, write=False):
    if not os.environ.get('AGENT_KIARA_KEY'):
        raise HTTPException(404, 'Fonction indisponible')
    require_erp(project_id)
    project = erp.get(Project, project_id)
    if project is None:
        raise HTTPException(404, 'Projet introuvable')
    operator = current_operator()
    if write and operator.role == 'reader':
        raise HTTPException(403, 'Accès en lecture seule')
    return project, operator.id


@router.get('/transcriptions')
def transcription_events(erp: Session = Depends(get_erp_db), brain: Session = Depends(get_db)):
    if not os.environ.get('AGENT_KIARA_KEY'):
        raise HTTPException(404, 'Fonction indisponible')
    project_ids = [row[0] for row in filter_erp(erp.query(Project.id), Project.id)]
    links = [(row.project_id, row.brain_project_id) for row in erp.query(BrainLink).filter(
        BrainLink.project_id.in_(project_ids))]
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    rows = (brain.query(AuditLog.id, MeetingRecording.erp_project_id, AuditLog.created_at)
            .join(MeetingRecording, MeetingRecording.id == AuditLog.payload['recording_id'].as_string())
            .filter(AuditLog.event_type == 'meeting.transcription.completed.v1',
                    AuditLog.project_id == MeetingRecording.project_id,
                    tuple_(MeetingRecording.erp_project_id, MeetingRecording.project_id).in_(links),
                    AuditLog.created_at >= cutoff)
            .order_by(AuditLog.created_at.desc(), AuditLog.id).limit(1000))
    events = [{'id': row.id, 'project': row.erp_project_id,
               'created': row.created_at.replace(tzinfo=timezone.utc).timestamp()} for row in rows]
    return {'projects': project_ids, 'events': events}


def private_memories(erp, operator):
    return erp.query(KiaraProjectMemory).filter(KiaraProjectMemory.operator_id == operator)


@router.get('/memories')
def memory_index(project: str | None = Query(default=None, max_length=36), erp: Session = Depends(get_erp_db)):
    if not os.environ.get('AGENT_KIARA_KEY'):
        raise HTTPException(404, 'Fonction indisponible')
    query = private_memories(erp, current_operator().id).join(Project, Project.id == KiaraProjectMemory.project_id)
    if project is not None:
        require_erp(project)
        query = query.filter(KiaraProjectMemory.project_id == project)
    rows = filter_erp(query, KiaraProjectMemory.project_id).order_by(KiaraProjectMemory.updated.desc())
    return [{'id': row.id, 'project': row.project_id, 'text': row.text, 'revision': str(row.revision)} for row in rows]


@router.post('/projects/{project_id}/memories')
def change_memory(project_id: str, command: MemoryCommand, erp: Session = Depends(get_erp_db)):
    # SQLite serializes the limit check with concurrent writes from other requests.
    erp.connection().exec_driver_sql('BEGIN IMMEDIATE')
    project, operator = project_scope(project_id, erp, write=True)
    if project.status == 'archived':
        raise HTTPException(409, 'Projet archivé')
    model = KiaraProjectMemory
    if command.action != 'memory_delete' and (command.text is None or '\x00' in command.text):
        raise HTTPException(422, 'Texte invalide')
    if command.action == 'memory_create':
        if private_memories(erp, operator).filter(model.project_id == project_id).count() >= 50:
            raise HTTPException(422, 'Maximum 50 souvenirs dans ce projet')
        row = model(id=secrets.token_hex(16), operator_id=operator, project_id=project_id, text=command.text,
                    revision=1, updated=time.time())
        erp.add(row)
        result = {'id': row.id, 'revision': '1'}
    else:
        if command.id is None or command.revision is None:
            raise HTTPException(422, 'Identifiant ou révision invalide')
        expected = int(command.revision)
        condition = (model.id == command.id, model.operator_id == operator,
                     model.project_id == project_id, model.revision == expected)
        statement = delete(model) if command.action == 'memory_delete' else update(model).values(
            text=command.text, revision=expected + 1, updated=time.time())
        if erp.execute(statement.where(*condition)).rowcount != 1:
            raise HTTPException(409, 'Ce souvenir a changé')
        result = {'deleted': True} if command.action == 'memory_delete' else {'revision': str(expected + 1)}
    erp.commit()
    return result


def describe_conversation(row):
    return {'id': row.id, 'project': row.project_id, 'title': row.title, 'revision': row.revision,
            'archived': row.archived, 'updated': row.updated}


@router.get('/conversations')
def conversation_index(erp: Session = Depends(get_erp_db)):
    if not os.environ.get('AGENT_KIARA_KEY'):
        raise HTTPException(404, 'Fonction indisponible')
    query = erp.query(KiaraConversation).join(Project, Project.id == KiaraConversation.project_id)
    rows = filter_erp(query, KiaraConversation.project_id).filter(
        KiaraConversation.operator_id == current_operator().id).order_by(KiaraConversation.updated.desc())
    return [describe_conversation(row) for row in rows]


@router.get('/projects/{project_id}/conversations')
def read_conversation(project_id: str, id: str = Query(pattern=r'^[0-9a-f]{32}$'),
                      erp: Session = Depends(get_erp_db)):
    _, operator = project_scope(project_id, erp)
    row = erp.get(KiaraConversation, (operator, id))
    if row is None or row.project_id != project_id:
        raise HTTPException(404, 'Discussion introuvable')
    return {**describe_conversation(row), 'messages': row.messages}


@router.post('/projects/{project_id}/conversations')
def change_conversation(project_id: str, command: ConversationCommand, erp: Session = Depends(get_erp_db)):
    project, operator = project_scope(project_id, erp, write=True)
    model = KiaraConversation
    condition = (model.operator_id == operator, model.id == command.id,
                 model.project_id == project_id, model.revision == command.revision)
    changes = {'updated': time.time(), 'revision': command.revision + 1}
    if command.action == 'conversation_save':
        from kiara_shared.attachments import validate_message
        if project.status == 'archived':
            raise HTTPException(409, 'Projet archivé')
        if command.title is None or not command.title.strip() or command.messages is None:
            raise HTTPException(422, 'Titre ou messages invalides')
        try:
            for message in command.messages:
                validate_message(message)
            if len(json.dumps(command.messages, ensure_ascii=False).encode()) > 9 * 1024 * 1024:
                raise ValueError('Discussion trop volumineuse')
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        changes.update(title=command.title.strip(), messages=command.messages)
    if command.archived is not None:
        changes['archived'] = command.archived
    if command.action == 'conversation_archive' and command.archived is None:
        raise HTTPException(422, 'Archivage invalide')
    if command.action == 'conversation_move':
        destination, _ = project_scope(command.destination, erp, write=True)
        if destination.status == 'archived':
            raise HTTPException(409, 'Projet archivé')
        changes['project_id'] = destination.id
    if command.action == 'conversation_delete':
        statement = delete(model).where(*condition)
    elif command.action == 'conversation_save' and command.revision == 0:
        statement = insert(model).values(operator_id=operator, id=command.id, project_id=project_id,
                                         **changes).on_conflict_do_nothing()
    else:
        statement = update(model).where(*condition).values(**changes)
    if erp.execute(statement).rowcount != 1:
        raise HTTPException(409, 'Discussion modifiée ailleurs')
    erp.commit()
    return {'deleted': True} if command.action == 'conversation_delete' else {'revision': changes['revision']}


@router.get('/projects/{project_id}/context')
async def project_context(project_id: str, q: str = Query(default='', max_length=500),
                          erp: Session = Depends(get_erp_db), brain: Session = Depends(get_db)):
    if not os.environ.get('AGENT_KIARA_KEY'):
        raise HTTPException(404, 'Fonction indisponible')
    require_erp(project_id)
    project = erp.get(Project, project_id)
    if project is None:
        raise HTTPException(404, 'Projet introuvable')
    if project.status == 'archived':
        raise HTTPException(409, 'Projet archivé')
    link = erp.get(BrainLink, project_id)
    items = []
    if link and len(q.strip()) >= 2:
        require_brain(link.brain_project_id)
        result = await search(brain, query=q.strip(), project_id=link.brain_project_id, limit=6)
        items = result['items']
    return {'title': project.title, 'items': items}


@router.get('/personal-sessions')
def personal_sessions(db: Session = Depends(get_db)):
    operator = current_operator()
    if not os.environ.get('AGENT_KIARA_KEY') or operator.id != 'kiara-service' or operator.role != 'owner' or operator.project_ids is not None:
        raise HTTPException(404, 'Fonction indisponible')
    count = (select(func.count(MeetingAudioChunk.id)).where(MeetingAudioChunk.session_id == MeetingSession.id)
             .correlate(MeetingSession).scalar_subquery())
    rows = db.execute(select(MeetingSession.id, MeetingSession.title, MeetingSession.date,
                             MeetingSession.operator_id, MeetingSession.state, count)
                      .where(MeetingSession.project_id.is_(None))
                      .order_by(MeetingSession.created_at.desc()).limit(1001)).all()
    return {'sessions': [{'id': row[0], 'title': row[1], 'date': row[2], 'operator_id': row[3],
                          'state': row[4], 'audio_chunks': row[5]} for row in rows[:1000]],
            'sessions_truncated': len(rows) > 1000}
