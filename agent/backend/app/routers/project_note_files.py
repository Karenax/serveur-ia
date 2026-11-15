"""Explicit attachment copy and verified download, scoped to one project note."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import project_note_files as files

router = APIRouter(prefix='/api/v1/projects/{project_id}/notes/{note_id}/attachments', tags=['project-notes'])


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


def _response(db, project_id, note_id, attachment_id, *, inline=False):
    data, item = files.download(db, project_id, note_id, attachment_id, inline=inline)
    disposition = 'inline' if inline else 'attachment'
    return Response(data, media_type=item['content_type'] if inline else 'application/octet-stream', headers={
        'Content-Disposition': disposition + "; filename*=UTF-8''" + quote(item['filename'], safe=''),
        'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'private, no-store',
        'Content-Security-Policy': "default-src 'none'; sandbox", 'ETag': '"' + item['sha256'] + '"'})


@router.get('/{attachment_id}/download')
def download(project_id: str, note_id: str, attachment_id: str, db: Session = Depends(get_db)):
    return _response(db, project_id, note_id, attachment_id)


@router.get('/{attachment_id}/image')
def image(project_id: str, note_id: str, attachment_id: str, db: Session = Depends(get_db)):
    return _response(db, project_id, note_id, attachment_id, inline=True)
