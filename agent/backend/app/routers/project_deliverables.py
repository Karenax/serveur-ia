"""Scoped L3 HTTP commands registered in Agent's mono-server."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..project_deliverable_schemas import (
    ChecklistCreate, ChecklistPatch, DeliverableCreate, DeliverablePatch, DocumentStatus, DocumentTransition,
    FilePublication, SelectionApply, SelectionPreview, TypeCreate, TypePatch, TypePublish,
    TypologyTypesPatch, VersionMetadataPatch,
)
from ..services import deliverable_catalogue as catalogue, deliverable_files as files
from ..services import deliverable_queries as reads, project_deliverables as commands
from ..services.deliverable_gates import milestone_gate_page, milestone_gates

router = APIRouter(prefix='/api/v1/projects/{project_id}/deliverable-plan', tags=['project-deliverables'])
catalog_router = APIRouter(prefix='/api/v1/deliverable-types', tags=['deliverable-types'])
typology_router = APIRouter(prefix='/api/v1/project-references/{typology_id}/deliverable-types', tags=['deliverable-types'])


def _command(db, action, *args, **kwargs):
    try:
        result = action(db, *args, **kwargs)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


@router.get('')
def list_items(project_id: str, search: str = Query('', max_length=200), include_inactive: bool = False,
               status: DocumentStatus | None = None, category: str | None = Query(None, max_length=32),
               milestone_id: str | None = Query(None, max_length=36), responsible_id: str | None = Query(None, max_length=36),
               verifier_id: str | None = Query(None, max_length=36), offset: int = Query(0, ge=0, le=1000000),
               limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    return reads.list_deliverables(db, project_id, search=search, include_inactive=include_inactive, status=status,
        category=category, milestone_id=milestone_id, responsible_id=responsible_id, verifier_id=verifier_id,
        offset=offset, limit=limit)


@router.post('', status_code=201)
def create(project_id: str, payload: DeliverableCreate, db: Session = Depends(get_db)):
    return _command(db, commands.create_deliverable, project_id, payload)


@router.post('/selection/preview')
def preview(project_id: str, payload: SelectionPreview, db: Session = Depends(get_db)):
    return catalogue.preview_selection(db, project_id, payload)


@router.post('/selection/apply')
def apply(project_id: str, payload: SelectionApply, db: Session = Depends(get_db)):
    return _command(db, catalogue.apply_selection, project_id, payload)


@router.get('/{deliverable_id}')
def detail(project_id: str, deliverable_id: str, db: Session = Depends(get_db)):
    return reads.detail(db, project_id, deliverable_id)


@router.get('/milestones/{milestone_id}/gates')
def gates(project_id: str, milestone_id: str, db: Session = Depends(get_db)):
    return milestone_gates(db, project_id, milestone_id)


@router.get('/milestones/{milestone_id}/gates/page')
def gate_page(project_id: str, milestone_id: str, include_ready: bool = False,
              offset: int = Query(0, ge=0, le=1000000), limit: int = Query(50, ge=1, le=200),
              db: Session = Depends(get_db)):
    return milestone_gate_page(db, project_id, milestone_id, include_ready=include_ready, offset=offset, limit=limit)


@router.patch('/{deliverable_id}')
def patch(project_id: str, deliverable_id: str, payload: DeliverablePatch, db: Session = Depends(get_db)):
    return _command(db, commands.patch_deliverable, project_id, deliverable_id, payload)


@router.get('/{deliverable_id}/checklist')
def checklist(project_id: str, deliverable_id: str, search: str = Query('', max_length=200), include_inactive: bool = False,
              offset: int = Query(0, ge=0, le=1000000), limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    return reads.checklist(db, project_id, deliverable_id, search=search, include_inactive=include_inactive, offset=offset, limit=limit)


@router.post('/{deliverable_id}/checklist', status_code=201)
def create_check(project_id: str, deliverable_id: str, payload: ChecklistCreate, db: Session = Depends(get_db)):
    return _command(db, commands.create_check, project_id, deliverable_id, payload)


@router.patch('/{deliverable_id}/checklist/{item_id}')
def patch_check(project_id: str, deliverable_id: str, item_id: str, payload: ChecklistPatch, db: Session = Depends(get_db)):
    return _command(db, commands.patch_check, project_id, deliverable_id, item_id, payload)


@router.get('/{deliverable_id}/versions')
def versions(project_id: str, deliverable_id: str, offset: int = Query(0, ge=0, le=1000000),
             limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    return reads.versions(db, project_id, deliverable_id, offset=offset, limit=limit)


@router.get('/{deliverable_id}/versions/{version_id}')
def version_detail(project_id: str, deliverable_id: str, version_id: str, db: Session = Depends(get_db)):
    return reads.version_detail(db, project_id, deliverable_id, version_id)


@router.get('/{deliverable_id}/versions/{version_id}/file')
def download(project_id: str, deliverable_id: str, version_id: str, db: Session = Depends(get_db)):
    data, filename = files.download(db, project_id, deliverable_id, version_id)
    return Response(data, media_type='application/octet-stream', headers={
        'Content-Disposition': "attachment; filename*=UTF-8''" + quote(filename, safe=''),
        'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store'})


@router.get('/{deliverable_id}/versions/{version_id}/manifest')
def manifest(project_id: str, deliverable_id: str, version_id: str, db: Session = Depends(get_db)):
    reads.version_detail(db, project_id, deliverable_id, version_id)
    row, _ = reads._version(db, project_id, deliverable_id, version_id)
    return Response(row.manifest.encode('utf-8'), media_type='application/json', headers={
        'Content-Disposition': f'attachment; filename="manifest-v{row.number}.json"',
        'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store'})


@router.patch('/{deliverable_id}/versions/{version_id}')
def patch_version(project_id: str, deliverable_id: str, version_id: str, payload: VersionMetadataPatch,
                  db: Session = Depends(get_db)):
    return _command(db, commands.patch_version_metadata, project_id, deliverable_id, version_id, payload)


@router.post('/{deliverable_id}/versions/upload', status_code=201)
def upload(project_id: str, deliverable_id: str, expected_revision: int = Form(..., ge=0),
           reference: str = Form(..., min_length=1, max_length=120), comment: str = Form('', max_length=20000),
           generated: bool = Form(False), file: UploadFile = File(...), db: Session = Depends(get_db)):
    payload = FilePublication(expected_revision=expected_revision, reference=reference, comment=comment, generated=generated)
    return _command(db, files.publish_upload, project_id, deliverable_id, payload, filename=file.filename, stream=file.file)


class NetworkPublication(FilePublication):
    link_id: str = Field(min_length=1, max_length=36)
    relative_path: str = Field(default='', max_length=2048)


@router.post('/{deliverable_id}/versions/network', status_code=201)
def network(project_id: str, deliverable_id: str, payload: NetworkPublication, db: Session = Depends(get_db)):
    command = FilePublication.model_validate(payload.model_dump(exclude={'link_id', 'relative_path'}))
    return _command(db, files.publish_network, project_id, deliverable_id, command,
                    link_id=payload.link_id, relative_path=payload.relative_path)


class CdcPublication(FilePublication):
    source_delivery_id: str = Field(min_length=1, max_length=36)


@router.post('/{deliverable_id}/versions/cdc', status_code=201)
def cdc(project_id: str, deliverable_id: str, payload: CdcPublication, db: Session = Depends(get_db)):
    return _command(db, files.publish_cdc, project_id, deliverable_id, payload)


@router.post('/{deliverable_id}/transition')
def transition(project_id: str, deliverable_id: str, payload: DocumentTransition, db: Session = Depends(get_db)):
    return _command(db, commands.transition, project_id, deliverable_id, payload)


@router.get('/{deliverable_id}/history')
def history(project_id: str, deliverable_id: str, offset: int = Query(0, ge=0, le=1000000),
            limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    return reads.history(db, project_id, deliverable_id, offset=offset, limit=limit)


@router.get('/{deliverable_id}/history/{event_id}')
def history_detail(project_id: str, deliverable_id: str, event_id: str, db: Session = Depends(get_db)):
    return reads.history_detail(db, project_id, deliverable_id, event_id)


@catalog_router.get('')
def list_types(search: str = Query('', max_length=200), include_inactive: bool = False,
               typology_id: str | None = Query(None, max_length=36), offset: int = Query(0, ge=0, le=1000000),
               limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    return catalogue.list_types(db, search=search, include_inactive=include_inactive, typology_id=typology_id, offset=offset, limit=limit)


@catalog_router.get('/standard-definition')
def standard_definition():
    from ..services.project_deliverable_rules import standard_catalogue
    return standard_catalogue()


@catalog_router.get('/condition-typologies')
def condition_typologies(search: str = Query('', max_length=200), include_inactive: bool = False,
                        offset: int = Query(0, ge=0, le=1000000), limit: int = Query(50, ge=1, le=200),
                        db: Session = Depends(get_db)):
    return catalogue.condition_typologies(db, search=search, include_inactive=include_inactive,
                                         offset=offset, limit=limit)


@catalog_router.post('', status_code=201)
def create_type(payload: TypeCreate, db: Session = Depends(get_db)):
    return _command(db, commands.create_type, payload)


@catalog_router.get('/{type_id}')
def type_detail(type_id: str, db: Session = Depends(get_db)):
    return catalogue.type_detail(db, type_id)


@catalog_router.patch('/{type_id}')
def patch_type(type_id: str, payload: TypePatch, db: Session = Depends(get_db)):
    return _command(db, catalogue.patch_type, type_id, payload)


@catalog_router.get('/{type_id}/versions')
def type_versions(type_id: str, offset: int = Query(0, ge=0, le=1000000),
                  limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    return catalogue.versions(db, type_id, offset=offset, limit=limit)


@catalog_router.get('/{type_id}/versions/{version_id}')
def type_version(type_id: str, version_id: str, db: Session = Depends(get_db)):
    return catalogue.version_detail(db, type_id, version_id)


@catalog_router.post('/{type_id}/versions', status_code=201)
def publish_type(type_id: str, payload: TypePublish, db: Session = Depends(get_db)):
    return _command(db, commands.publish_type, type_id, payload)


@typology_router.get('')
def typology_types(typology_id: str, db: Session = Depends(get_db)):
    return catalogue.typology_types(db, typology_id)


@typology_router.patch('')
def patch_typology_types(typology_id: str, payload: TypologyTypesPatch, db: Session = Depends(get_db)):
    return _command(db, catalogue.patch_typology_types, typology_id, payload)
