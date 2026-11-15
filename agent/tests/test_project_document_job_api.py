"""Guarded queue routes, actual transactional commands, pagination and artifact reads."""
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from threading import Barrier

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.security import local_guard, session, SESSION_TOKEN
from backend.app.db import get_db
from backend.app.project_document_job_models import DocumentJob, DocumentJobEvent
from backend.app.routers import project_document_jobs as http
from backend.app.services import document_jobs as jobs
from backend.app.services.document_job_worker import DocumentCoordinator, get_coordinator
from tests.test_project_document_jobs import queue as queue_fixture
from tests.test_project_document_jobs import command, install
from tests.test_project_document_worker import wait_for

queue=queue_fixture


class HeldCoordinator:
    """Hold dispatch for deterministic command tests; real worker tested separately."""
    def __init__(self,root):
        self.storage_root=root
        self.ready=True
        self.wakes=0
    def status(self):
        return {'state':'running' if self.ready else 'lease_busy','can_submit':self.ready,'enabled':True,'running':self.ready,'error':''}
    def wake(self):
        self.wakes+=1


@pytest.fixture
def api(queue,monkeypatch):
    install(queue)
    monkeypatch.delenv('AGENT_TESTING',raising=False)
    application=FastAPI()
    application.middleware('http')(local_guard)
    application.get('/api/v1/session')(session)
    application.include_router(http.router)
    coordinator=HeldCoordinator(queue[3])
    def dependency():
        with queue[1]() as db:
            yield db
    application.dependency_overrides[get_db]=dependency
    application.dependency_overrides[get_coordinator]=lambda:coordinator
    with TestClient(application,base_url='http://127.0.0.1') as client:
        yield client,queue,coordinator,dependency


HEADERS={'X-Agent-Token':SESSION_TOKEN}
ROOT='/api/v1/projects/project/documents'


def submit(api):
    response=api[0].post(ROOT+'/jobs',json=command(api[1]).model_dump(),headers=HEADERS)
    assert response.status_code==200, response.text
    return response.json()


def test_commands_commit_replay_cancel_retry_and_bounded_journals(api):
    job=submit(api)
    again=submit(api)
    assert again['id']==job['id'] and again['revision']==1
    assert api[0].get(ROOT+'/jobs?limit=1').json()['total']==1
    cancelled=api[0].post(ROOT+'/jobs/'+job['id']+'/cancel',json={'expected_revision':1},headers=HEADERS)
    assert cancelled.status_code==200 and cancelled.json()['status']=='cancelled'
    stale=api[0].post(ROOT+'/jobs/'+job['id']+'/retry',json={'expected_revision':1},headers=HEADERS)
    assert stale.status_code==409
    retry=api[0].post(ROOT+'/jobs/'+job['id']+'/retry',json={'expected_revision':cancelled.json()['revision']},headers=HEADERS)
    assert retry.status_code==200 and retry.json()['status']=='queued'
    with api[1][1]() as db:
        assert db.scalar(select(DocumentJob)).revision==3
        assert len(list(db.scalars(select(DocumentJobEvent))))==3
    events=api[0].get(ROOT+'/jobs/'+job['id']+'/events?limit=1&offset=1').json()
    assert events['total']==3 and events['items'][0]['kind']=='cancel_requested'
    assert api[2].wakes==4


def test_concurrent_identical_submission_is_one_committed_job(api):
    payload=command(api[1]).model_dump()
    barrier=Barrier(2)
    def post():
        barrier.wait()
        return api[0].post(ROOT+'/jobs',json=payload,headers=HEADERS)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies=list(pool.map(lambda _:post(),range(2)))
    assert all(reply.status_code==200 for reply in replies),[reply.text for reply in replies]
    assert replies[0].json()['id']==replies[1].json()['id']
    with api[1][1]() as db:
        assert len(list(db.scalars(select(DocumentJob))))==1
        assert len(list(db.scalars(select(DocumentJobEvent))))==1


def test_paused_worker_blocks_submit_and_retry_but_allows_read_and_cancel(api):
    job=submit(api)
    api[2].ready=False
    assert api[0].get(ROOT+'/jobs').json()['worker']['state']=='lease_busy'
    assert api[0].post(ROOT+'/jobs',json=command(api[1],command_id='new').model_dump(),headers=HEADERS).status_code==409
    cancelled=api[0].post(ROOT+'/jobs/'+job['id']+'/cancel',json={'expected_revision':1},headers=HEADERS).json()
    assert cancelled['status']=='cancelled'
    assert api[0].post(ROOT+'/jobs/'+job['id']+'/retry',json={'expected_revision':cancelled['revision']},headers=HEADERS).status_code==409
    assert api[0].get(ROOT+'/jobs/'+job['id']).status_code==200


def test_reader_scope_and_forged_headers_do_not_grant_control(api,monkeypatch):
    job=submit(api)
    monkeypatch.setenv('AGENT_OPERATOR_ROLE','reader')
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS',json.dumps(['project']))
    assert api[0].get(ROOT+'/jobs').status_code==200
    assert not api[0].get(ROOT+'/jobs/'+job['id']).json()['can_cancel']
    headers={**HEADERS,'X-Agent-Role':'owner','X-Agent-Actor':'forged'}
    assert api[0].post(ROOT+'/jobs/'+job['id']+'/cancel',json={'expected_revision':1},headers=headers).status_code==403
    assert api[0].get('/api/v1/projects/foreign/documents/jobs').status_code==404
    assert api[0].get('/api/v1/projects/foreign/documents/jobs/'+job['id']).status_code==404


def test_csrf_origin_bounds_and_strict_commands(api):
    cmd=command(api[1]).model_dump()
    assert api[0].post(ROOT+'/jobs',json=cmd).status_code==403
    assert api[0].post(ROOT+'/jobs',json=cmd,headers={**HEADERS,'Origin':'http://foreign.invalid'}).status_code==403
    for key,value in [('actor_id','forged'),('root','V:/other'),('price',42),('output_path','V:/out')]:
        assert api[0].post(ROOT+'/jobs',json={**cmd,key:value},headers=HEADERS).status_code==422
    for query in ['?limit=201','?offset=-1','?limit=0']:
        assert api[0].get(ROOT+'/jobs'+query).status_code==422
    job=submit(api)
    assert api[0].post(ROOT+'/jobs/'+job['id']+'/cancel',json={'expected_revision':True},headers=HEADERS).status_code==422


def test_artifact_verified_download_foreign_refusal_and_tampering(api,monkeypatch):
    job=submit(api)
    completed=jobs.run_one(api[1][1],'project',job['id'],storage_root=api[1][3])
    aid=completed['items'][0]['artifact_id']
    monkeypatch.setenv('AGENT_OPERATOR_ROLE','reader')
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS',json.dumps(['project']))
    result=api[0].get(ROOT+'/artifacts/'+aid)
    assert result.status_code==200 and result.headers['X-Agent-Network-Published']=='false'
    assert result.headers['ETag']=='"'+hashlib.sha256(result.content).hexdigest()+'"'
    assert 'Demande%20de%20CE.docx' in result.headers['Content-Disposition']
    assert api[0].get('/api/v1/projects/foreign/documents/artifacts/'+aid).status_code==404
    (next(api[1][3].iterdir())).write_bytes(b'corrupt')
    assert api[0].get(ROOT+'/artifacts/'+aid).status_code==409
    history=api[0].get(ROOT+'/jobs/'+job['id']+'/attempts?limit=1').json()
    assert history['total']==1 and history['items'][0]['outcome']=='succeeded'


def test_real_http_worker_end_to_end_without_other_background_services(queue,monkeypatch):
    install(queue)
    monkeypatch.delenv('AGENT_TESTING',raising=False)
    coordinator=DocumentCoordinator(queue[1],storage_root=queue[3])
    @asynccontextmanager
    async def lifespan(_app):
        assert coordinator.start(enabled=True)['can_submit']
        try:
            yield
        finally:
            assert coordinator.stop(timeout=5)
    application=FastAPI(lifespan=lifespan)
    application.middleware('http')(local_guard)
    application.include_router(http.router)
    def dependency():
        with queue[1]() as db:
            yield db
    application.dependency_overrides[get_db]=dependency
    application.dependency_overrides[get_coordinator]=lambda:coordinator
    with TestClient(application,base_url='http://127.0.0.1') as client:
        result=client.post(ROOT+'/jobs',json=command(queue,both=True).model_dump(),headers=HEADERS)
        assert result.status_code==200,result.text
        jid=result.json()['id']
        def completed():
            response=client.get(ROOT+'/jobs/'+jid)
            assert response.status_code==200,response.text
            state=response.json()
            return state if state['status']=='completed' else None
        end=wait_for(completed)
        assert end['total']==end['processed']==2
        assert client.get(ROOT+'/jobs/'+jid+'/attempts').json()['total']==2
        assert client.get(ROOT+'/artifacts/'+end['items'][0]['artifact_id']).status_code==200


def test_native_application_registers_guarded_jobs_routes(api,monkeypatch):
    from app.main import app
    monkeypatch.setenv('AGENT_OPERATOR_ROLE','editor')
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS',json.dumps(['project']))
    previous=dict(app.dependency_overrides)
    app.dependency_overrides[get_db]=api[3]
    app.dependency_overrides[get_coordinator]=lambda:api[2]
    try:
        # Deliberately no lifespan: fake ERP is initialized; other workers stay off.
        client=TestClient(app,base_url='http://127.0.0.1')
        assert client.get(ROOT+'/jobs').status_code==200
        response=client.post(ROOT+'/jobs',json=command(api[1]).model_dump(),headers=HEADERS)
        assert response.status_code==200,response.text
        assert client.get(ROOT+'/jobs/'+response.json()['id']+'/events').status_code==200
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_startup_failure_stops_previously_started_services_without_migration(queue,monkeypatch):
    import asyncio
    from app import main
    from app.services import auto_scan, workspace_jobs, meeting_audio, mail_enrichment, logging_setup
    from backend.app.services import cdc_jobs, milestone_scan, document_job_worker
    monkeypatch.setattr(main,'init_db',lambda:None)
    monkeypatch.setattr(main,'mp_init_db',lambda:None)
    monkeypatch.setattr(workspace_jobs,'init_workspace_db',lambda:None)
    monkeypatch.setattr(logging_setup,'configure_logging',lambda:None)
    started,stopped=[],[]
    modules=[(auto_scan,'start_auto_scan','stop_auto_scan'),(cdc_jobs,'start_worker','stop_worker'),
        (meeting_audio,'start_worker','stop_worker'),(workspace_jobs,'start_worker','stop_worker'),
        (mail_enrichment,'start_worker','stop_worker'),(milestone_scan,'start_worker','stop_worker')]
    for module,start,stop in modules:
        monkeypatch.setattr(module,start,lambda name=module.__name__:started.append(name))
        monkeypatch.setattr(module,stop,lambda name=module.__name__:stopped.append(name))
    def failure():
        raise RuntimeError('Document worker preflight failure')
    monkeypatch.setattr(document_job_worker,'start_worker',failure)
    monkeypatch.setattr(document_job_worker,'stop_worker',lambda:None)
    async def run():
        async with main.lifespan(main.app):
            pytest.fail('Invalid worker cannot expose a started server')
    with pytest.raises(RuntimeError,match='preflight failure'):
        asyncio.run(run())
    assert len(started)==6 and set(started)==set(stopped)


@pytest.mark.parametrize('groups, master, requested', [
    ('["documents"]', '1', True),
    ('["documents"]', '0', False),
    ('[]', '1', False),
])
def test_staged_worker_selection_starts_and_stops_only_documents(queue, monkeypatch, groups, master, requested):
    import asyncio
    from app import main
    from app.services import auto_scan
    from backend.app.services import document_job_worker

    monkeypatch.setenv('AGENT_WORKER_GROUPS', groups)
    monkeypatch.setenv('AGENT_START_WORKERS', master)
    monkeypatch.setattr(main, 'init_db', lambda: None)
    monkeypatch.setattr(main, 'mp_init_db', lambda: None)
    calls = []
    monkeypatch.setattr(auto_scan, 'start_auto_scan', lambda: pytest.fail('Le scan mail doit rester suspendu'))
    monkeypatch.setattr(document_job_worker, 'start_worker', lambda: calls.append('start'))
    monkeypatch.setattr(document_job_worker, 'stop_worker', lambda: calls.append('stop'))

    async def run():
        async with main.lifespan(main.app):
            assert calls == (['start'] if requested else [])

    asyncio.run(run())
    assert calls == (['start', 'stop'] if requested else [])
