"""Real leased worker, abrupt process death and bounded scoped queue queries."""
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest
from sqlalchemy import select

from backend.app.project_document_job_models import DocumentJobAttempt, DocumentJobReceipt
from backend.app.services import document_jobs as jobs, document_job_queries as queries, project_documents
from backend.app.services.document_job_worker import DocumentCoordinator
from backend.app.services.document_worker_lease import WorkerLease
from backend.app.services.project_operator import Operator
from tests.test_project_document_jobs import queue as queue_fixture
from tests.test_project_document_jobs import install, enqueue

queue=queue_fixture


def wait_for(predicate, *, timeout=10):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        value=predicate()
        if value:
            return value
        threading.Event().wait(.02)
    pytest.fail('Document worker did not reach expected state')


def current(queue,job_id):
    with queue[1]() as db:
        return jobs.detail(db,'project',job_id)


def completed_state(queue,job_id):
    state=current(queue,job_id)
    return state if state['status']=='completed' else None


def manager(queue,operator=None):
    return DocumentCoordinator(queue[1],storage_root=queue[3],operator=operator or Operator('worker','owner'))


def test_disabled_uninstalled_reader_do_not_start_or_create_lock(queue):
    first=manager(queue)
    assert first.start(enabled=False)['state']=='disabled'
    assert first.start(enabled=True)['state']=='not_installed'
    install(queue)
    reader=manager(queue,Operator('reader','reader',frozenset({'project'})))
    assert reader.start(enabled=True)['state']=='read_only'
    assert not queue[4].with_name(queue[4].name+'.document-worker.lock').exists()


def test_os_lease_is_exclusive_across_processes_and_released(queue):
    lease=WorkerLease(queue[4])
    assert lease.acquire()
    script='from backend.app.services.document_worker_lease import WorkerLease; import sys; x=WorkerLease(sys.argv[1]); print(x.acquire(),flush=True); x.close()'
    def child():
        return subprocess.run([sys.executable,'-c',script,str(queue[4])],cwd=Path(__file__).resolve().parents[1],
            capture_output=True,text=True,timeout=10)
    try:
        locked=child()
        assert locked.returncode==0 and locked.stdout.strip()=='False', locked.stderr
    finally:
        lease.close()
    free=child()
    assert free.returncode==0 and free.stdout.strip()=='True', free.stderr


def test_hard_link_alias_of_database_cannot_create_a_second_worker_lease(queue):
    alias=queue[4].with_name('alias.db')
    os.link(queue[4],alias)
    with pytest.raises(ValueError,match='sans alias'):
        WorkerLease(alias)
    with pytest.raises(ValueError,match='sans alias'):
        WorkerLease(queue[4])


def test_real_worker_prepares_queue_and_second_coordinator_cannot_run(queue):
    install(queue)
    job=enqueue(queue,both=True)
    first,second=manager(queue),manager(queue)
    try:
        assert first.start(enabled=True)['can_submit']
        assert second.start(enabled=True)['state']=='lease_busy'
        end=wait_for(lambda:completed_state(queue,job['id']))
        assert end['processed']==end['total']==2
        with queue[1]() as db:
            assert len(list(db.scalars(select(DocumentJobAttempt))))==2
            assert len(list(db.scalars(select(DocumentJobReceipt))))==2
            assert queries.list_jobs(db,'project')['items'][0]['processed']==2
    finally:
        assert first.stop(timeout=5)
        second.stop()


def test_shutdown_timeout_retains_lease_until_io_finishes(queue,monkeypatch):
    install(queue)
    job=enqueue(queue,both=True)
    entered,released=threading.Event(),threading.Event()
    original=project_documents.prepare_copy
    def blocked(*args,**kwargs):
        entered.set()
        assert released.wait(10)
        return original(*args,**kwargs)
    monkeypatch.setattr(project_documents,'prepare_copy',blocked)
    first,second=manager(queue),manager(queue)
    try:
        first.start(enabled=True)
        assert entered.wait(5)
        assert not first.stop(timeout=.02)
        assert first.status()['state']=='stopping' and not first.status()['can_submit']
        assert second.start(enabled=True)['state']=='lease_busy'
        released.set()
        wait_for(lambda:not first.status()['running'])
        assert first.stop()
        assert second.start(enabled=True)['can_submit']
        end=current(queue,job['id'])
        assert end['status']=='interrupted' and end['items'][0]['status']=='succeeded' and end['items'][1]['status']=='interrupted'
    finally:
        released.set()
        first.stop(timeout=5)
        second.stop(timeout=5)


def test_actual_process_death_recovered_once_then_requires_explicit_retry(queue):
    install(queue)
    job=enqueue(queue)
    script='''
import os,sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db_support import configure_sqlite
from backend.app.services.document_worker_lease import WorkerLease
from backend.app.services import document_jobs as jobs
engine=create_engine('sqlite:///'+sys.argv[1]); configure_sqlite(engine)
lease=WorkerLease(sys.argv[1]); assert lease.acquire()
with sessionmaker(bind=engine)() as db:
    jobs.claim(db,'project',sys.argv[2],1); db.commit()
os._exit(7)
'''
    env={**os.environ,'MINIPILOT_HOME':str(queue[4].parent/'child-home')}
    child=subprocess.run([sys.executable,'-c',script,str(queue[4]),job['id']],env=env,
        cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=10)
    assert child.returncode==7, child.stderr
    assert current(queue,job['id'])['status']=='running'
    worker=manager(queue)
    try:
        assert worker.start(enabled=True)['can_submit']
        interrupted=current(queue,job['id'])
        assert interrupted['status']=='interrupted' and interrupted['processed']==1
        with queue[1]() as db:
            assert db.scalar(select(DocumentJobReceipt)).outcome=='interrupted'
            jobs.retry(db,'project',job['id'],interrupted['revision'])
            db.commit()
        worker.wake()
        completed=wait_for(lambda:completed_state(queue,job['id']))
        assert completed['processed']==1
        with queue[1]() as db:
            assert len(list(db.scalars(select(DocumentJobAttempt))))==2
            assert queries.attempts(db,'project',job['id'],limit=1)['total']==2
    finally:
        worker.stop(timeout=5)
    again=manager(queue)
    try:
        again.start(enabled=True)
        with queue[1]() as db:
            assert len(list(db.scalars(select(DocumentJobReceipt))))==2
    finally:
        again.stop(timeout=5)


def test_scoped_worker_ignores_other_project_jobs(queue):
    install(queue)
    job=enqueue(queue)
    worker=manager(queue,Operator('foreign-worker','editor',frozenset({'foreign'})))
    try:
        assert worker.start(enabled=True)['can_submit']
        assert worker._next() is None
        assert current(queue,job['id'])['status']=='queued'
    finally:
        worker.stop(timeout=5)


def test_bounded_queue_journals_stable_pages_and_dormant_no_ddl(queue,monkeypatch):
    with queue[1]() as db:
        assert queries.list_jobs(db,'project')['available'] is False
    install(queue)
    first=enqueue(queue,command_id='first')
    second=enqueue(queue,command_id='second')
    jobs.run_one(queue[1],'project',first['id'],storage_root=queue[3])
    monkeypatch.setattr(project_documents,'acquire_file',lambda *a,**k:pytest.fail('queries read shares'))
    with queue[1]() as db:
        page=queries.list_jobs(db,'project',limit=1)
        assert page['total']==2 and page['items'][0]['id']==second['id']
        assert queries.list_jobs(db,'project',limit=1,offset=1)['items'][0]['id']==first['id']
        journal=queries.events(db,'project',first['id'],limit=1)
        assert journal['total']==3 and journal['items'][0]['revision']==3
        assert queries.events(db,'project',first['id'],limit=1,offset=1)['items'][0]['revision']==2
        attempts=queries.attempts(db,'project',first['id'])
        assert attempts['total']==1 and attempts['items'][0]['outcome']=='succeeded'
        assert attempts['items'][0]['finished_at'].endswith('+00:00')
