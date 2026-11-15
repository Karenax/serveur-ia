"""Interactive project document workspace; preparation returns a separate copy."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..project_document_schemas import DocumentDiscover, DocumentPrepare, DocumentPreview, DocumentId
from ..project_document_form_schemas import DocumentDraftSave, DocumentFormRestore, DocumentSearchSave
from ..services.document_discovery import discover as discover_templates
from ..services.document_search_rules import SearchRule
from ..services import document_forms as forms
from ..services import project_documents as service

router = APIRouter(prefix='/api/v1/projects/{project_id}/documents', tags=['project-documents'])
settings_router = APIRouter(prefix='/api/v1/document-settings', tags=['document-settings'])


def _command(db, action, *args, **kwargs):
    try:
        result = action(db, *args, **kwargs)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


@router.get('')
def workspace(project_id: str, offset: int = Query(0, ge=0, le=1_000_000),
              limit: int = Query(100, ge=1, le=200), db: Session = Depends(get_db)):
    return service.workspace(db, project_id, offset=offset, limit=limit)


@router.post('/preview')
def preview(project_id: str, payload: DocumentPreview, db: Session = Depends(get_db)):
    return service.preview(db, project_id, payload)


@router.post('/discover')
def discover(project_id: str, payload: DocumentDiscover, db: Session = Depends(get_db)):
    preferences = forms.effective_preferences(db, project_id)
    item = next(row for row in preferences['items'] if row['document_id'] == payload.document_id)
    if not item['active']:
        raise HTTPException(409, 'Recherche désactivée pour cette trame dans les réglages documentaires')
    rule = SearchRule(payload.document_id, tuple(item['relative_paths']), tuple(item['filename_patterns']),
                      tuple(item['excluded_tokens']), item['preferred_version'])
    result = discover_templates(db, project_id, link_id=payload.link_id, document_id=payload.document_id, rule=rule)
    return {**result, 'preferences_revision': preferences['revision'], 'preferences_version_id': preferences['version_id']}


@router.get('/forms/{document_id}')
def form(project_id: str, document_id: DocumentId, db: Session = Depends(get_db)):
    return forms.draft(db, project_id, document_id)


@router.put('/forms/{document_id}')
def save_form(project_id: str, document_id: DocumentId, payload: DocumentDraftSave, db: Session = Depends(get_db)):
    return _command(db, forms.save_draft, project_id, document_id, **payload.model_dump())


@router.get('/forms/{document_id}/history')
def form_history(project_id: str, document_id: DocumentId, offset: int = Query(0, ge=0, le=1000000),
                 limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    return forms.draft_history_page(db, project_id, document_id, offset=offset, limit=limit)


@router.post('/forms/{document_id}/restore')
def restore_form(project_id: str, document_id: DocumentId, payload: DocumentFormRestore, db: Session = Depends(get_db)):
    return _command(db, forms.restore_draft, project_id, document_id, **payload.model_dump())


@settings_router.get('')
def settings(db: Session = Depends(get_db)):
    return forms.search_preferences(db)


@settings_router.put('')
def save_settings(payload: DocumentSearchSave, db: Session = Depends(get_db)):
    return _command(db, forms.save_search_preferences, **payload.model_dump())


@settings_router.get('/history')
def settings_history(offset: int = Query(0, ge=0, le=1000000), limit: int = Query(50, ge=1, le=200),
                     db: Session = Depends(get_db)):
    return forms.search_history_page(db, offset=offset, limit=limit)


@settings_router.post('/restore')
def restore_settings(payload: DocumentFormRestore, db: Session = Depends(get_db)):
    return _command(db, forms.restore_search_preferences, **payload.model_dump())


@router.post('/prepare-copy')
def prepare_copy(project_id: str, payload: DocumentPrepare, db: Session = Depends(get_db)):
    content, report = service.prepare_copy(db, project_id, payload)
    return Response(content, media_type='application/octet-stream', headers={
        'Content-Disposition': "attachment; filename*=UTF-8''" + quote(report['output_filename'], safe=''),
        'ETag': '"' + report['preparation']['output_sha256'] + '"',
        'X-Agent-Source-Sha256': report['source_sha256'], 'X-Agent-Values-Sha256': report['values_sha256'],
        'X-Agent-Link-Sha256': report['link_sha256'],
        'X-Agent-Network-Published': 'false', 'Cache-Control': 'private, no-store'})
