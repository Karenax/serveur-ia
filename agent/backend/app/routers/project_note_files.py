"""Explicit attachment copy and verified download, scoped to one project note."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..project_note_schemas import NotePaste
from ..services import note_clipboard
from ..services import project_note_files as files
from .project_notes import _command

router = APIRouter(prefix='/api/v1/projects/{project_id}/notes/{note_id}/attachments', tags=['project-notes'])
clipboard_router = APIRouter(prefix='/api/v1/projects/{project_id}/notes', tags=['project-notes'])


def apply_paste(db, action, command, file, *args, **kwargs):
    try:
        payload = NotePaste.model_validate_json(command.file.read(2_100_001))
    except ValidationError as exc:
        raise HTTPException(422, 'Vérifiez le titre et le contenu de la note avant de coller l’image') from exc
    image = note_clipboard.read_image(file.filename, file.file)
    try:
        return _command(db, action, *args, payload, image=image, **kwargs)
    except ValidationError as exc:
        raise HTTPException(422, 'L’image dépasse la taille maximale de la note') from exc


@clipboard_router.post('/paste-image', status_code=201)
def paste_new_image(project_id: str, command: UploadFile = File(...), file: UploadFile = File(...),
                    db: Session = Depends(get_db)):
    return apply_paste(db, note_clipboard.paste_project, command, file, project_id, None)


@clipboard_router.post('/{note_id}/paste-image')
def paste_image(project_id: str, note_id: str, command: UploadFile = File(...), file: UploadFile = File(...),
                db: Session = Depends(get_db)):
    return apply_paste(db, note_clipboard.paste_project, command, file, project_id, note_id)


@router.get('')
def listing(project_id: str, note_id: str, db: Session = Depends(get_db)):
    return files.listing(db, project_id, note_id)


@router.post('', status_code=201)
def upload(project_id: str, note_id: str, command_id: str = Form(..., min_length=36, max_length=36),
           file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        result = files.upload(db, project_id, note_id, command_id=command_id,
                              filename=file.filename, stream=file.file)
        db.commit()
        return result
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'La note a changé ; réessayer avec la même commande de pièce jointe') from exc
    except Exception:
        db.rollback()
        raise


def file_response(data, item, *, inline=False):
    disposition = 'inline' if inline else 'attachment'
    return Response(data, media_type=item['content_type'] if inline else 'application/octet-stream', headers={
        'Content-Disposition': disposition + "; filename*=UTF-8''" + quote(item['filename'], safe=''),
        'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'private, no-store',
        'Content-Security-Policy': "default-src 'none'; sandbox", 'ETag': '"' + item['sha256'] + '"'})


@router.get('/{attachment_id}/download')
def download(project_id: str, note_id: str, attachment_id: str, db: Session = Depends(get_db)):
    return file_response(*files.download(db, project_id, note_id, attachment_id))


@router.get('/{attachment_id}/image')
def image(project_id: str, note_id: str, attachment_id: str, db: Session = Depends(get_db)):
    return file_response(*files.download(db, project_id, note_id, attachment_id, inline=True), inline=True)
