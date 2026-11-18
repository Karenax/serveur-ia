"""Project-scoped rich notes and immutable history in the single Agent server."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..project_note_schemas import NoteCreate, NoteSave, NoteRestore
from ..services import project_notes as service

router = APIRouter(prefix='/api/v1/projects/{project_id}/notes', tags=['project-notes'])


def _command(db, action, *args, **kwargs):
    try:
        result = action(db, *args, **kwargs)
        db.commit()
        return result
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'La note a changé ; conserver la saisie et relire les versions') from exc
    except Exception:
        db.rollback()
        raise


@router.get('')
def listing(project_id: str, query: str = Query('', max_length=200),
            limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0, le=10000), db: Session = Depends(get_db)):
    return service.list_notes(db, project_id, query=query, limit=limit, offset=offset)


@router.post('', status_code=201)
def create(project_id: str, payload: NoteCreate, db: Session = Depends(get_db)):
    return _command(db, service.create_note, project_id, payload)


@router.get('/{note_id}')
def detail(project_id: str, note_id: str, db: Session = Depends(get_db)):
    return service.read_note(db, project_id, note_id)


@router.put('/{note_id}')
def save(project_id: str, note_id: str, payload: NoteSave, db: Session = Depends(get_db)):
    return _command(db, service.save_note, project_id, note_id, payload)


@router.get('/{note_id}/history')
def history(project_id: str, note_id: str, limit: int = Query(30, ge=1, le=100),
            offset: int = Query(0, ge=0, le=10000), db: Session = Depends(get_db)):
    return service.history(db, project_id, note_id, limit=limit, offset=offset)


@router.get('/{note_id}/versions/{version_id}')
def version(project_id: str, note_id: str, version_id: str, db: Session = Depends(get_db)):
    return service.read_version(db, project_id, note_id, version_id)


@router.post('/{note_id}/restore')
def restore(project_id: str, note_id: str, payload: NoteRestore, db: Session = Depends(get_db)):
    return _command(db, service.restore_note, project_id, note_id, payload)
