"""Notes overview and private notebook of the current Kiara operator."""
from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Project
from ..project_note_models import ProjectNote
from ..project_note_schemas import Closed, NoteCreate, NoteRestore, NoteSave
from ..services import personal_notes as personal, project_notes
from ..services.project_operator import current_operator
from .project_note_files import apply_paste, file_response
from .project_notes import _command

router = APIRouter(prefix='/api/v1/notes', tags=['notes'])


@router.get('/projects')
def catalogue(db: Session = Depends(get_db)):
    operator = current_operator()
    available = project_notes._ready(db)
    if not available:
        return {'projects': [], 'can_edit': False}
    has_notes = select(ProjectNote.id).where(ProjectNote.project_id == Project.id).exists()
    statement = select(Project.id, Project.code, Project.title, has_notes.label('has_notes'))\
        .where(Project.status == 'active').order_by(Project.code, Project.title, Project.id)
    if operator.project_ids is not None:
        statement = statement.where(Project.id.in_(operator.project_ids))
    return {'projects': [dict(row) for row in db.execute(statement).mappings()], 'can_edit': operator.role != 'reader'}


@router.get('/personal')
def listing(query: str = Query('', max_length=200), limit: int = Query(30, ge=1, le=100),
            offset: int = Query(0, ge=0, le=10000), db: Session = Depends(get_db)):
    return personal.listing(db, query, limit, offset)


@router.post('/personal', status_code=201)
def create(payload: NoteCreate, db: Session = Depends(get_db)):
    return _command(db, personal.save, None, payload)


@router.post('/personal/paste-image', status_code=201)
def paste_new_image(command: UploadFile = File(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    return apply_paste(db, personal.save, command, file, None)


@router.get('/personal/{note_id}')
def detail(note_id: str, db: Session = Depends(get_db)):
    return personal.read(db, note_id)


@router.put('/personal/{note_id}')
def save(note_id: str, payload: NoteSave, db: Session = Depends(get_db)):
    return _command(db, personal.save, note_id, payload)


@router.post('/personal/{note_id}/paste-image')
def paste_image(note_id: str, command: UploadFile = File(...), file: UploadFile = File(...),
                db: Session = Depends(get_db)):
    return apply_paste(db, personal.save, command, file, note_id)


@router.get('/personal/{note_id}/history')
def history(note_id: str, limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0, le=10000),
            db: Session = Depends(get_db)):
    return personal.history(db, note_id, limit, offset)


@router.get('/personal/{note_id}/versions/{version_id}')
def version(note_id: str, version_id: str, db: Session = Depends(get_db)):
    return personal.version(db, note_id, version_id)


@router.post('/personal/{note_id}/restore')
def restore(note_id: str, payload: NoteRestore, db: Session = Depends(get_db)):
    return _command(db, personal.save, note_id, payload, restore=True)


@router.get('/personal/{note_id}/attachments/{attachment_id}/image')
def image(note_id: str, attachment_id: str, db: Session = Depends(get_db)):
    return file_response(*personal.read_image(db, note_id, attachment_id), inline=True)


class CopyNote(Closed):
    project_id: str = Field(min_length=1, max_length=36)
    version_id: str = Field(min_length=36, max_length=36)


@router.post('/personal/{note_id}/copy-to-project', status_code=201)
def copy_to_project(note_id: str, payload: CopyNote, db: Session = Depends(get_db)):
    return _command(db, personal.copy_to_project, note_id, payload.project_id, payload.version_id)
