"""Scoped RLP drafts, immutable publications and explicit local audio import."""
import json
from copy import deepcopy

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import get_db as get_brain
from ..db import get_db
from ..project_review_schemas import (
    RecordingImport, ReviewCommand, ReviewCreate, ReviewPublish, ReviewSave,
)
from ..services import project_reviews as service
from .project_planning import _command

router = APIRouter(prefix='/api/v1/projects/{project_id}/reviews', tags=['project-reviews'])
catalogue_router = APIRouter(prefix='/api/v1/review-types', tags=['project-reviews'])


@catalogue_router.get('')
def catalogue():
    return service.catalogue()


@router.get('')
def reviews(project_id: str, offset: int = Query(0, ge=0, le=1000000),
            limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    return service.list_reviews(db, project_id, offset=offset, limit=limit)


@router.post('', status_code=201)
def create(project_id: str, payload: ReviewCreate, db: Session = Depends(get_db)):
    return _command(db, service.create_review, project_id, payload)


@router.get('/recording-choices')
def recordings(project_id: str, offset: int = Query(0, ge=0, le=1000000),
               limit: int = Query(25, ge=1, le=100), db: Session = Depends(get_db),
               brain: Session = Depends(get_brain)):
    return service.recording_choices(db, brain, project_id, offset=offset, limit=limit)


@router.get('/{review_id}')
def read(project_id: str, review_id: str, db: Session = Depends(get_db)):
    return service.read_review(db, project_id, review_id)


@router.put('/{review_id}')
def save(project_id: str, review_id: str, payload: ReviewSave, db: Session = Depends(get_db)):
    return _command(db, service.save_review, project_id, review_id, payload)


@router.post('/{review_id}/revision', status_code=201)
def revision(project_id: str, review_id: str, payload: ReviewCommand, db: Session = Depends(get_db)):
    return _command(db, service.create_revision, project_id, review_id, payload)


@router.post('/{review_id}/publish')
def publish(project_id: str, review_id: str, payload: ReviewPublish, db: Session = Depends(get_db)):
    return _command(db, service.publish_review, project_id, review_id, payload)


@router.post('/{review_id}/recordings')
def import_recording(project_id: str, review_id: str, payload: RecordingImport,
                     db: Session = Depends(get_db), brain: Session = Depends(get_brain)):
    return _command(db, service.import_recording, brain, project_id, review_id, payload)


@router.get('/{review_id}/publication')
def publication(project_id: str, review_id: str, db: Session = Depends(get_db)):
    row, _ = service.publication(db, project_id, review_id)
    return {'id': row.id, 'sha256': row.sha256, 'pdf_sha256': row.pdf_sha256,
            'snapshot': json.loads(row.snapshot), 'bindings': deepcopy(row.bindings)}


@router.get('/{review_id}/pdf')
def pdf(project_id: str, review_id: str, db: Session = Depends(get_db)):
    row, content = service.publication(db, project_id, review_id)
    return Response(content, media_type='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="rlp-{row.id}.pdf"',
        'ETag': f'"{row.pdf_sha256}"', 'Cache-Control': 'private, no-store'})


@router.get('/{review_id}/history')
def history(project_id: str, review_id: str, offset: int = Query(0, ge=0, le=1000000),
            limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    return service.history(db, project_id, review_id, offset=offset, limit=limit)


@router.get('/{review_id}/history/{event_id}')
def event(project_id: str, review_id: str, event_id: str, db: Session = Depends(get_db)):
    return service.history_detail(db, project_id, review_id, event_id)
