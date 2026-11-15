"""Explicit selection of an ICS event as context, never a validated meeting."""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..services.session_calendar import attach_context

router = APIRouter(prefix='/api/v1/meeting-sessions', tags=['session-calendar'])


@router.post('/{sid}/calendar-context')
async def attach(sid: str, file: UploadFile = File(...), uid: str = Form(...),
                 command_id: str = Form(...), expected_revision: int = Form(..., ge=1), db: Session = Depends(get_db)):
    raw = await file.read(1024 * 1024 + 1)
    return attach_context(db, sid, raw, uid, command_id, expected_revision)
