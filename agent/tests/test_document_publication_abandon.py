"""Explicit closure is serialized, CAS protected, offline and retains all bytes."""
import json
from copy import deepcopy
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
import pytest

from app.services.deliverable_manifest import freeze
from app.services.document_jobs_backup import validate_job_history, suspend_restored_jobs
from app.db_support import backup_sqlite
from backend.app.project_document_publication_schemas import DocumentPublicationAbandon
from backend.app.services import document_publication_commands as publications, document_job_history
from backend.app.services.project_document_job_archive import import_rows
from backend.app.services.document_worker_lease import WorkerLease
from backend.app.services.document_publication_io import AnchoredDirectory
from tests.test_document_publication_commands import command,publish,records,tables
from tests.test_document_publication_preview import prepared as prepared_fixture, failure
from tests.test_project_document_jobs import queue as queue_fixture
from tests.test_project_document_jobs import command as batch_command
from tests.test_project_document_job_api import api as api_fixture,HEADERS,ROOT
from backend.app.services import document_jobs as jobs
from backend.app.project_document_publication_schemas import DocumentPublicationPreview

queue=queue_fixture
prepared=prepared_fixture
api=api_fixture


def uncertain(prepared,monkeypatch):
    payload=command(prepared)
    append=publications._append
    def fail_prepared(db,pid,jid,kind,detail,**kwargs):
        if kind=='publication_prepared':
            raise OSError('Simulated stop before durable prepared receipt')
        return append(db,pid,jid,kind,detail,**kwargs)
    with monkeypatch.context() as scoped:
        scoped.setattr(publications,'_append',fail_prepared)
        with pytest.raises(OSError):
            publish(prepared,payload)
    assert records(prepared)['items'][0]['state']=='requested'
    return payload


def close(prepared,payload):
    queue,_,_=prepared
    history=records(prepared)
    with queue[1]() as db:
        return publications.abandon(db,'project',history['job_id'],'publish-once',payload)


def test_explicit_closure_retains_unknown_files_and_nonce_and_allows_new_reviewed_command(prepared,monkeypatch):
    original=uncertain(prepared,monkeypatch)
    history=records(prepared)
    ack=DocumentPublicationAbandon(expected_revision=history['job_revision'],retain_files=True,reviewed=True)
    files={p.name:p.read_bytes() for p in prepared[0][2].iterdir()}
    with monkeypatch.context() as scoped:
        scoped.setattr(publications,'AnchoredDirectory',lambda *args:pytest.fail('Closure must not probe filesystem'))
        value=close(prepared,ack)
        assert value['state']=='abandoned' and not value['can_resume'] and not value['can_abandon']
        before=tables(prepared[0])
        assert close(prepared,ack)==value and tables(prepared[0])==before
        failure(409,lambda:publish(prepared,original))
    assert files=={p.name:p.read_bytes() for p in prepared[0][2].iterdir()}
    assert publish(prepared,command(prepared,cid='new-explicit-command'))['state']=='succeeded'
    assert all((prepared[0][2]/name).read_bytes()==content for name,content in files.items())
    assert validate_job_history(prepared[0][4])


def test_closure_requires_fresh_revision_and_rejects_prepared_or_success_receipts(prepared,monkeypatch):
    uncertain(prepared,monkeypatch)
    failure(409,lambda:close(prepared,DocumentPublicationAbandon(expected_revision=1,retain_files=True,reviewed=True)))
    assert records(prepared)['items'][0]['state']=='requested'
    with pytest.raises(ValidationError):
        DocumentPublicationAbandon(expected_revision=True,retain_files=True,reviewed=True)
    for key in ('retain_files','reviewed'):
        for value in (False,1,'true'):
            with pytest.raises(ValidationError):
                DocumentPublicationAbandon.model_validate({'expected_revision':4,'retain_files':True,'reviewed':True,key:value})


def test_held_publication_lease_prevents_closure_during_io(prepared,monkeypatch):
    uncertain(prepared,monkeypatch)
    ack=DocumentPublicationAbandon(expected_revision=records(prepared)['job_revision'],retain_files=True,reviewed=True)
    lease=WorkerLease(prepared[0][4],namespace='publication')
    assert lease.acquire()
    try:
        failure(409,lambda:close(prepared,ack))
        assert records(prepared)['items'][0]['state']=='requested'
    finally:
        lease.close()
    assert close(prepared,ack)['state']=='abandoned'


def test_success_closure_rejected_and_filter_cannot_select_foreign_artifact(prepared):
    publish(prepared)
    history=records(prepared)
    ack=DocumentPublicationAbandon(expected_revision=history['job_revision'],retain_files=True,reviewed=True)
    failure(409,lambda:close(prepared,ack))
    with prepared[0][1]() as db:
        filtered=publications.list_publications(db,'project',history['job_id'],artifact_id=prepared[1])
        assert filtered['total']==1
        failure(404,lambda:publications.list_publications(db,'project',history['job_id'],artifact_id='foreign'))


def test_scoped_reader_cannot_close_and_closure_transports_twice_without_replay(prepared,monkeypatch,tmp_path):
    uncertain(prepared,monkeypatch)
    ack=DocumentPublicationAbandon(expected_revision=records(prepared)['job_revision'],retain_files=True,reviewed=True)
    monkeypatch.setenv('AGENT_OPERATOR_ROLE','reader')
    assert not records(prepared)['items'][0]['can_abandon']
    failure(403,lambda:close(prepared,ack))
    monkeypatch.setenv('AGENT_OPERATOR_ROLE','owner')
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS','["foreign"]')
    failure(404,lambda:close(prepared,ack))
    monkeypatch.delenv('AGENT_OPERATOR_PROJECT_IDS')
    close(prepared,ack)
    raw=tables(prepared[0])
    original=[e['detail'] for e in raw['project_document_job_events']]
    for _ in range(2):
        mapping={row['id']:str(uuid4()) for rows in raw.values() for row in rows}
        mapped=import_rows(raw,mapping,actor='trusted-import')
        raw={'projects':[{'id':mapping[raw['projects'][0]['id']]}],
             'network_links':[{**row,'id':mapping[row['id']],'project_id':mapping[row['project_id']]} for row in raw['network_links']],**mapped}
        assert document_job_history.validate(raw)
        assert [e['detail'] for e in raw['project_document_job_events'][:len(original)]]==original
    restored=tmp_path/'closed-restored.db'
    backup_sqlite(prepared[0][4],restored)
    suspend_restored_jobs(restored)
    assert validate_job_history(restored)


@pytest.mark.parametrize('damage',['retain_false','extra_column','false_revision','prepared_after_close'])
def test_offline_forged_closure_is_rejected(prepared,monkeypatch,damage):
    uncertain(prepared,monkeypatch)
    close(prepared,DocumentPublicationAbandon(expected_revision=records(prepared)['job_revision'],retain_files=True,reviewed=True))
    raw=deepcopy(tables(prepared[0]))
    event=next(e for e in raw['project_document_job_events'] if e['kind']=='publication_abandoned')
    detail=json.loads(event['detail'])
    if damage=='retain_false':
        detail['retain_files']=False
    elif damage=='extra_column':
        detail['delete_files']=True
    elif damage=='false_revision':
        detail['expected_revision']=1
    else:
        event['kind']='publication_prepared'
    event['detail']=freeze(detail)[0]
    with pytest.raises((ValueError,HTTPException)):
        document_job_history.validate(raw)


def test_prepared_receipt_cannot_be_abandoned(prepared,monkeypatch):
    payload=command(prepared)
    def stop(*args):
        raise OSError('Stop before promotion')
    monkeypatch.setattr(AnchoredDirectory,'promote',stop)
    with pytest.raises(OSError):
        publish(prepared,payload)
    assert records(prepared)['items'][0]['state']=='prepared'
    failure(409,lambda:close(prepared,DocumentPublicationAbandon(expected_revision=records(prepared)['job_revision'],retain_files=True,reviewed=True)))


def test_real_http_closure_strict_ack_scope_token_and_repeat(api,monkeypatch):
    client,queue,_,_=api
    batch=client.post(ROOT+'/jobs',json=batch_command(queue).model_dump(),headers=HEADERS).json()
    job=jobs.run_one(queue[1],'project',batch['id'],storage_root=queue[3])
    aid=job['items'][0]['artifact_id']
    monkeypatch.setenv('AGENT_DOCUMENT_WRITE_ROOTS',json.dumps([str(queue[2])]))
    chosen=(queue,aid,DocumentPublicationPreview(link_id='link'))
    uncertain(chosen,monkeypatch)
    history=client.get(ROOT+'/jobs/'+job['id']+'/publications?artifact_id='+aid).json()
    assert history['items'][0]['can_abandon']
    path=ROOT+'/jobs/'+job['id']+'/publications/publish-once/abandon'
    body={'expected_revision':history['job_revision'],'retain_files':True,'reviewed':True}
    assert client.post(path,json=body).status_code==403
    assert client.post(path,json={**body,'retain_files':1},headers=HEADERS).status_code==422
    monkeypatch.setenv('AGENT_OPERATOR_ROLE','reader')
    assert client.post(path,json=body,headers=HEADERS).status_code==403
    monkeypatch.setenv('AGENT_OPERATOR_ROLE','owner')
    reply=client.post(path,json=body,headers=HEADERS)
    assert reply.status_code==200 and reply.json()['state']=='abandoned'
    assert client.post(path,json=body,headers=HEADERS).json()==reply.json()
    assert client.get(ROOT+'/jobs/'+job['id']+'/publications?artifact_id=foreign').status_code==404
