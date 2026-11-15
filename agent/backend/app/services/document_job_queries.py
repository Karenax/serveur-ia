"""Bounded SQL queues and journals. Reads do not scan document shares."""
import json

from fastapi import HTTPException
from sqlalchemy import case, func, select

from app.db_support import utc_iso
from ..project_document_job_models import DocumentJob, DocumentJobItem, DocumentJobEvent, DocumentJobAttempt, DocumentJobReceipt
from . import document_jobs as jobs
from .project_identity import _project
from .project_operator import current_operator


def _page(offset, limit):
    if type(offset) is not int or type(limit) is not int or not 0 <= offset <= 1000000 or not 1 <= limit <= 200:
        raise HTTPException(422, 'Pagination de la file documentaire invalide')


def list_jobs(db, project_id, *, offset=0, limit=30):
    _project(db, project_id)
    _page(offset, limit)
    if not jobs._ready(db):
        return {'available':False, 'items':[], 'total':0, 'offset':offset, 'limit':limit}
    total=db.scalar(select(func.count()).select_from(DocumentJob).where(DocumentJob.project_id==project_id))
    rows=list(db.scalars(select(DocumentJob).where(DocumentJob.project_id==project_id)
        .order_by(DocumentJob.created_at.desc(),DocumentJob.id.desc()).offset(offset).limit(limit)))
    ids=[row.id for row in rows]
    terminal={'succeeded','failed','interrupted','cancelled'}
    counts={row.job_id:row for row in db.execute(select(DocumentJobItem.job_id,
        func.count().label('item_total'),func.sum(case((DocumentJobItem.status.in_(terminal),1),else_=0)).label('processed'),
        func.sum(case((DocumentJobItem.status=='succeeded',1),else_=0)).label('succeeded'))
        .where(DocumentJobItem.job_id.in_(ids)).group_by(DocumentJobItem.job_id))}
    items=[]
    for row in rows:
        count=counts.get(row.id)
        if count is None or count.item_total!=row.total:
            raise HTTPException(409,'Nombre de fichiers du lot incohérent')
        items.append({'id':row.id,'project_id':project_id,'status':row.status,'revision':row.revision,
            'total':row.total,'processed':count.processed,'succeeded':count.succeeded,
            'progress':round(100*count.processed/row.total,1),'cancel_requested':row.cancel_requested,
            'execution_blocked':row.execution_blocked,
            'created_at':utc_iso(row.created_at),'updated_at':utc_iso(row.updated_at),
            'can_cancel':not row.execution_blocked and current_operator().role!='reader' and row.status in {'queued','running'} and not row.cancel_requested,
            'can_retry':not row.execution_blocked and current_operator().role!='reader' and row.status in {'failed','interrupted','cancelled'} and count.succeeded<row.total})
    return {'available':True,'items':items,'total':total,'offset':offset,'limit':limit}


def events(db, project_id, job_id, *, offset=0, limit=50):
    job=jobs._job(db,project_id,job_id)
    _page(offset,limit)
    query=select(DocumentJobEvent).where(DocumentJobEvent.job_id==job.id)
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    rows=db.scalars(query.order_by(DocumentJobEvent.revision.desc()).offset(offset).limit(limit))
    return {'items':[{'id':row.id,'revision':row.revision,'kind':row.kind,'actor_id':row.actor_id,
        'detail':json.loads(row.detail),'created_at':utc_iso(row.created_at)} for row in rows],
        'total':total,'offset':offset,'limit':limit}


def attempts(db, project_id, job_id, *, offset=0, limit=50):
    job=jobs._job(db,project_id,job_id)
    _page(offset,limit)
    query=select(DocumentJobAttempt).where(DocumentJobAttempt.job_id==job.id)
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    selected=query.order_by(DocumentJobAttempt.created_at.desc(),DocumentJobAttempt.id.desc()).offset(offset).limit(limit).subquery()
    rows=db.execute(select(selected,DocumentJobReceipt.artifact_id,DocumentJobReceipt.outcome,
        DocumentJobReceipt.error,DocumentJobReceipt.created_at.label('finished_at'))
        .outerjoin(DocumentJobReceipt,DocumentJobReceipt.attempt_id==selected.c.id)
        .order_by(selected.c.created_at.desc(),selected.c.id.desc())).mappings()
    return {'items':[{'id':row['id'],'item_id':row['item_id'],'number':row['number'],'actor_id':row['actor_id'],
        'created_at':utc_iso(row['created_at']),'finished_at':utc_iso(row['finished_at']) if row['finished_at'] else None,
        'outcome':row['outcome'] or 'running','artifact_id':row['artifact_id'],'error':row['error'] or ''} for row in rows],
        'total':total,'offset':offset,'limit':limit}
