"""Scoped durable document queue. Worker and schema activation stay explicit."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..db import get_db
from ..project_document_job_schemas import DocumentBatchSubmit, DocumentJobCommand
from ..project_document_publication_schemas import DocumentPublicationPreview, DocumentPublicationCommand, DocumentPublicationAbandon
from ..project_document_job_models import DocumentJob
from ..services import document_jobs as jobs, document_job_queries as queries
from ..services.document_job_worker import get_coordinator
from ..services.project_identity import _project
from ..services import document_publications
from ..services import document_publication_commands as publications

router=APIRouter(prefix='/api/v1/projects/{project_id}/documents',tags=['project-document-jobs'])


def _command(db, action, *args, **kwargs):
    try:
        value=action(db,*args,**kwargs)
        db.commit()
        return value
    except Exception:
        db.rollback()
        raise


def _can_submit(coordinator):
    if not coordinator.status()['can_submit']:
        raise HTTPException(409,'Worker documentaire indisponible : consulter l’état du traitement')


@router.get('/jobs')
def list_jobs(project_id:str, offset:int=Query(0,ge=0,le=1000000),limit:int=Query(30,ge=1,le=200),
              db:Session=Depends(get_db),coordinator=Depends(get_coordinator)):
    result=queries.list_jobs(db,project_id,offset=offset,limit=limit)
    return {**result,'worker':coordinator.status()}


@router.post('/jobs')
def submit(project_id:str,payload:DocumentBatchSubmit,db:Session=Depends(get_db),coordinator=Depends(get_coordinator)):
    _project(db,project_id,write=True)
    _can_submit(coordinator)
    try:
        value=_command(db,jobs.submit,project_id,payload)
    except IntegrityError:
        # The unique command identity can race another committed request. A
        # rollback gives a fresh read; unrelated insertion failures still fail.
        existing=db.scalar(select(DocumentJob).where(DocumentJob.project_id==project_id,
                                                     DocumentJob.command_id==payload.command_id))
        if existing is None:
            raise
        raw,digest=jobs.frozen(payload.model_dump())
        if existing.sha256!=digest or existing.snapshot!=raw:
            raise HTTPException(409,'Cette commande désigne déjà un autre lot')
        value=jobs.detail(db,project_id,existing.id)
    coordinator.wake()
    return value


@router.get('/jobs/{job_id}')
def detail(project_id:str,job_id:str,db:Session=Depends(get_db)):
    return jobs.detail(db,project_id,job_id)


@router.get('/jobs/{job_id}/events')
def events(project_id:str,job_id:str,offset:int=Query(0,ge=0,le=1000000),limit:int=Query(50,ge=1,le=200),db:Session=Depends(get_db)):
    return queries.events(db,project_id,job_id,offset=offset,limit=limit)


@router.get('/jobs/{job_id}/attempts')
def attempts(project_id:str,job_id:str,offset:int=Query(0,ge=0,le=1000000),limit:int=Query(50,ge=1,le=200),db:Session=Depends(get_db)):
    return queries.attempts(db,project_id,job_id,offset=offset,limit=limit)


@router.post('/jobs/{job_id}/cancel')
def cancel(project_id:str,job_id:str,payload:DocumentJobCommand,db:Session=Depends(get_db),coordinator=Depends(get_coordinator)):
    value=_command(db,jobs.cancel,project_id,job_id,payload.expected_revision)
    coordinator.wake()
    return value


@router.post('/jobs/{job_id}/retry')
def retry(project_id:str,job_id:str,payload:DocumentJobCommand,db:Session=Depends(get_db),coordinator=Depends(get_coordinator)):
    jobs._job(db,project_id,job_id,write=True)
    _can_submit(coordinator)
    value=_command(db,jobs.retry,project_id,job_id,payload.expected_revision)
    coordinator.wake()
    return value


@router.get('/artifacts/{artifact_id}')
def artifact(project_id:str,artifact_id:str,db:Session=Depends(get_db),coordinator=Depends(get_coordinator)):
    content,filename=jobs.artifact_content(db,project_id,artifact_id,storage_root=coordinator.storage_root)
    import hashlib
    return Response(content,media_type='application/octet-stream',headers={
        'Content-Disposition':"attachment; filename*=UTF-8''"+quote(filename,safe=''),
        'ETag':'"'+hashlib.sha256(content).hexdigest()+'"',
        'X-Agent-Network-Published':'false','Cache-Control':'private, no-store'})


@router.post('/artifacts/{artifact_id}/publication-preview')
def publication_preview(project_id:str, artifact_id:str, payload:DocumentPublicationPreview,
                        db:Session=Depends(get_db), coordinator=Depends(get_coordinator)):
    return {**document_publications.preview(db, project_id, artifact_id, payload, storage_root=coordinator.storage_root),
            'publication_command_available':True}


@router.post('/artifacts/{artifact_id}/publish')
def publish(project_id:str, artifact_id:str, payload:DocumentPublicationCommand,
            db:Session=Depends(get_db), coordinator=Depends(get_coordinator)):
    return publications.publish(db, project_id, artifact_id, payload, storage_root=coordinator.storage_root)


@router.get('/jobs/{job_id}/publications')
def list_publications(project_id:str, job_id:str, offset:int=Query(0,ge=0,le=1000000),
                      limit:int=Query(30,ge=1,le=200), artifact_id:str|None=Query(None,max_length=36), db:Session=Depends(get_db)):
    return publications.list_publications(db, project_id, job_id, offset=offset, limit=limit,artifact_id=artifact_id)


@router.post('/jobs/{job_id}/publications/{command_id}/abandon')
def abandon_publication(project_id:str,job_id:str,command_id:str,payload:DocumentPublicationAbandon,
                        db:Session=Depends(get_db)):
    return publications.abandon(db,project_id,job_id,command_id,payload)
