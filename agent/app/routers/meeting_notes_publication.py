"""Notes-only report publication, explicitly reviewed by the operator."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.meeting_notes_publication_schemas import PublishNotes
from app.services.meeting_notes_publication import publish_notes

router = APIRouter(prefix='/api/v1/meeting-sessions', tags=['meeting-notes-publication'])


@router.post('/{sid}/publish-notes')
def publish(sid: str, body: PublishNotes, db: Session = Depends(get_db)):
    return publish_notes(db, sid, body)
