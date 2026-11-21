from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from ..db import get_db
from ..services.session_export import discard_export, export

router = APIRouter(prefix='/api/v1/meeting-sessions', tags=['session-export'])


@router.get('/{sid}/export')
def download(sid: str, db: Session = Depends(get_db)):
    path = export(db, sid)
    return FileResponse(path, media_type='application/zip', filename=f'seance-{sid}.zip',
                        headers={'Cache-Control': 'private, no-store'}, background=BackgroundTask(discard_export, path))
