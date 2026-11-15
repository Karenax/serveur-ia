"""Explicit project-link note import; reads require configured server roots."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, field_validator, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.project_note_schemas import Closed
from backend.app.project_note_import_schemas import SourceDescriptor, NoteImportCommand, canonical_uuid
from backend.app.services import project_note_imports as imports, project_notes as notes
from backend.app.services.project_identity import _project
from backend.app.services.project_note_network import acquire_note
from backend.app.services.project_note_source_preview import preview_source

router = APIRouter(prefix='/api/v1/projects/{project_id}/notes/imports/network', tags=['project-notes'])


class NetworkNotePreview(Closed):
    planned_note_id: str = Field(pattern=r'^[0-9a-f-]{36}$')
    mode: Literal['rich', 'plain'] = 'rich'
    source: SourceDescriptor

    @field_validator('planned_note_id')
    @classmethod
    def note_identity(cls, value):
        return canonical_uuid(value)

    @model_validator(mode='after')
    def linked_origin(self):
        if self.source.kind != 'project_link':
            raise ValueError('Lien de ce projet et chemin relatif requis')
        return self


@router.post('/preview')
def preview(project_id: str, payload: NetworkNotePreview, db: Session = Depends(get_db)):
    _project(db, project_id, write=True)
    notes._ready(db, write=True)
    try:
        return preview_source(acquire_note(db, project_id, payload.source),
                              planned_note_id=payload.planned_note_id, mode=payload.mode)
    except (ValueError, TypeError, UnicodeDecodeError, RecursionError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post('', status_code=201)
def apply(project_id: str, payload: NoteImportCommand, db: Session = Depends(get_db)):
    _project(db, project_id, write=True)
    if payload.source.kind != 'project_link':
        raise HTTPException(422, 'Ce parcours attend une note choisie dans un lien de ce projet')
    try:
        result = imports.import_selected(db, project_id, payload,
            acquire=lambda descriptor: acquire_note(db, project_id, descriptor))
        db.commit()
        return result
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'Import concurrent ; reprendre la commande exacte après relecture') from exc
    except Exception:
        db.rollback()
        raise
