"""Voluntary multipart import, confirmation replay and retained originals."""
import json
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..project_note_import_schemas import NoteImportCommand
from ..services import project_note_imports as service, project_notes as notes
from ..services.project_identity import _project
from ..services.project_note_source_preview import preview_source
from ..services.project_note_upload_selection import acquire_uploads

router = APIRouter(prefix='/api/v1/projects/{project_id}/notes', tags=['project-notes'])


def _json(value):
    from ..services.project_note_conversion import _unique
    try:
        return json.loads(value, object_pairs_hook=_unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('JSON fini requis')))
    except (ValueError, TypeError, RecursionError) as exc:
        raise HTTPException(422, 'JSON de sélection invalide') from exc


@router.post('/imports/preview')
def preview(project_id: str, planned_note_id: str = Form(..., min_length=36, max_length=36),
            mode: str = Form('rich', max_length=5), paths: str = Form(..., max_length=220000),
            files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    _project(db, project_id, write=True)
    notes._ready(db, write=True)
    try:
        return preview_source(acquire_uploads(files, _json(paths)), planned_note_id=planned_note_id, mode=mode)
    except (ValueError, TypeError, UnicodeDecodeError, RecursionError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post('/imports', status_code=201)
def apply(project_id: str, command: str = Form(..., max_length=10000),
          paths: str = Form(..., max_length=220000), files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    _project(db, project_id, write=True)
    try:
        payload = NoteImportCommand.model_validate(_json(command))
        if payload.source.kind != 'upload':
            raise HTTPException(422, 'Ce parcours attend une sélection téléversée')
        result = service.import_selected(db, project_id, payload, acquire=lambda _: acquire_uploads(files, _json(paths)))
        db.commit()
        return result
    except ValidationError as exc:
        db.rollback()
        raise HTTPException(422, 'Commande d’import fermée invalide') from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'Import concurrent ; reprendre la commande exacte après relecture') from exc
    except Exception:
        db.rollback()
        raise


@router.get('/{note_id}/source')
def source(project_id: str, note_id: str, db: Session = Depends(get_db)):
    return service.read_import(db, project_id, note_id)


@router.post('/imports/replay')
def replay(project_id: str, payload: NoteImportCommand, db: Session = Depends(get_db)):
    try:
        result = service.replay_import(db, project_id, payload)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


@router.get('/{note_id}/originals/download')
def original(project_id: str, note_id: str, relative_path: str = Query(..., min_length=1, max_length=1024),
             db: Session = Depends(get_db)):
    data, item = service.original_file(db, project_id, note_id, relative_path)
    return Response(data, media_type='application/octet-stream', headers={
        'Content-Disposition': "attachment; filename*=UTF-8''" + quote(item['filename'], safe=''),
        'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'private, no-store',
        'Content-Security-Policy': "default-src 'none'; sandbox", 'ETag': '"' + item['sha256'] + '"'})
