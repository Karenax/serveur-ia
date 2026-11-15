"""Real SQLite queue, OOXML preparation, durable claim and owned artifact bytes."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import sqlite3
from threading import Barrier
import zipfile

from fastapi import HTTPException
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db_support import backup_sqlite, configure_sqlite
from backend.app.db import Base
from backend.app.models import NetworkLink, Project
from backend.app.project_identity_models import IDENTITY_TABLES
from backend.app.project_planning_models import ProjectPlanningState
from backend.app.project_document_job_models import DOCUMENT_JOB_TABLES, DocumentJob, DocumentJobItem, DocumentJobAttempt, DocumentJobArtifact, DocumentJobReceipt, DocumentJobEvent
from backend.app.project_document_job_schemas import DocumentBatchSubmit
from backend.app.project_document_schemas import DocumentPreview
from backend.app.services import document_jobs as jobs, project_documents
from backend.app.services.document_job_schema import install_job_schema, validate_job_schema
from backend.app.services.migration_guard import capture_baseline, compare_baseline
from backend.app.services.project_operator import Operator, operator_context
from tests.test_project_document_packages import package, parts_for


@pytest.fixture
def queue(tmp_path, monkeypatch):
    path = tmp_path / 'erp.db'
    engine = create_engine(f'sqlite:///{path}', connect_args={'check_same_thread':False})
    configure_sqlite(engine)
    Base.metadata.create_all(engine, tables=[Project.__table__, NetworkLink.__table__, *IDENTITY_TABLES,
                                            ProjectPlanningState.__table__])
    factory = sessionmaker(bind=engine)
    source = tmp_path / 'sources'
    source.mkdir()
    for doc_id, name in [('ce_request','ce.docx'),('user_manual','notice.docm')]:
        (source/name).write_bytes(package(parts_for(doc_id)))
    with factory() as db:
        db.add_all([Project(id='project',code='AIRB26LTH0205-A',title='LED',hourly_rate=99,margin_pct=12),
                    Project(id='foreign',code='OTHER',title='Hors périmètre')])
        db.flush()
        db.add_all([NetworkLink(id='link',project_id='project',code='affaire',libelle='Modèles',chemin=str(source)),
                    NetworkLink(id='foreign-link',project_id='foreign',code='affaire',libelle='Autre',chemin=str(source))])
        db.commit()
    monkeypatch.setenv('AGENT_DOCUMENT_ROOTS',json.dumps([str(source)]))
    monkeypatch.delenv('AGENT_DOCUMENT_DRIVE_MAPPINGS',raising=False)
    monkeypatch.setenv('AGENT_OPERATOR_ROLE','owner')
    monkeypatch.delenv('AGENT_OPERATOR_PROJECT_IDS',raising=False)
    yield engine, factory, source, tmp_path / 'artifacts', path
    engine.dispose()


def install(queue):
    return install_job_schema(queue[0],backup=lambda:backup_sqlite(queue[4],queue[4].with_suffix('.before.db')))


def command(queue, *, both=False, command_id='once'):
    choices = [('ce_request','ce.docx',{})]
    if both:
        choices.append(('user_manual','notice.docm',{'description':'Notice fictive'}))
    items=[]
    with queue[1]() as db:
        for doc_id,name,overrides in choices:
            payload=DocumentPreview(document_id=doc_id,link_id='link',relative_path=name,overrides=overrides)
            report=project_documents.preview(db,'project',payload)
            assert report['can_prepare'], report['blockers']
            items.append({**payload.model_dump(),'expected_source_sha256':report['source_sha256'],
                'expected_link_sha256':report['link_sha256'],'expected_values_sha256':report['values_sha256'],
                'expected_identity_revision':report['field_values']['identity_revision'],
                'expected_planning_revision':report['field_values']['planning_revision']})
    return DocumentBatchSubmit(command_id=command_id,items=items)


def enqueue(queue, **options):
    with queue[1]() as db:
        result=jobs.submit(db,'project',command(queue,**options))
        db.commit()
        return result


def error(code, action):
    with pytest.raises(HTTPException) as exc:
        action()
    assert exc.value.status_code == code


def test_dormant_guard_and_backup_first_conservation(queue):
    before=capture_baseline(queue[4])
    with queue[1]() as db:
        error(409,lambda:jobs.submit(db,'project',command(queue)))
    assert not set(table.name for table in DOCUMENT_JOB_TABLES)&set(inspect(queue[0]).get_table_names())
    def failed():
        raise OSError('backup failed')
    with pytest.raises(OSError):
        install_job_schema(queue[0],backup=failed)
    assert capture_baseline(queue[4])==before
    assert len(install(queue)['created_tables'])==6
    assert compare_baseline(before,capture_baseline(queue[4]))['preserved']
    assert validate_job_schema(queue[0])=={'created_tables':[],'created_triggers':[]}
    assert install_job_schema(queue[0],backup=lambda:pytest.fail('must be idempotent'))=={'created_tables':[],'created_triggers':[]}


def test_submit_freezes_review_and_replay_does_not_probe_files(queue,monkeypatch):
    install(queue)
    cmd=command(queue)
    with queue[1]() as db:
        first=jobs.submit(db,'project',cmd)
        db.commit()
    monkeypatch.setattr(project_documents,'acquire_file',lambda *a,**k:pytest.fail('Replay must not reread share'))
    with queue[1]() as db:
        same=jobs.submit(db,'project',cmd)
        assert same['id']==first['id'] and same['revision']==1 and same['total']==1 and same['processed']==0
        changed=cmd.model_copy(update={'items':[cmd.items[0].model_copy(update={'relative_path':'other.docx'})]})
        error(409,lambda:jobs.submit(db,'project',changed))
        assert len(list(db.scalars(select(DocumentJob))))==1
        assert len(list(db.scalars(select(DocumentJobEvent))))==1
        item=db.scalar(select(DocumentJobItem))
        assert item.link_id=='link' and item.draft_version_id is None
        assert json.loads(item.snapshot)['command']['relative_path']=='ce.docx'
        assert json.loads(item.snapshot)['preview']['field_values']['values']['project_code']=='AIRB26LTH0205-A'


def test_actual_prepare_owned_artifact_receipt_reopen_and_source_preserved(queue):
    install(queue)
    before=capture_baseline(queue[4])
    original=(queue[2]/'ce.docx').read_bytes()
    job=enqueue(queue)
    result=jobs.run_one(queue[1],'project',job['id'],storage_root=queue[3])
    assert result['status']=='completed' and result['processed']==result['total']==1 and result['progress']==100
    with queue[1]() as db:
        content,name=jobs.artifact_content(db,'project',result['items'][0]['artifact_id'],storage_root=queue[3])
        assert name=='AIRB26LTH0205-A-Demande de CE.docx' and content!=original
        artifact=db.scalar(select(DocumentJobArtifact))
        assert artifact.sha256==hashlib.sha256(content).hexdigest()
        assert len(list(db.scalars(select(DocumentJobAttempt))))==1
        assert db.scalar(select(DocumentJobReceipt)).outcome=='succeeded'
        assert jobs.detail(db,'project',job['id'])['status']=='completed'
    assert (queue[2]/'ce.docx').read_bytes()==original
    assert compare_baseline(before,capture_baseline(queue[4]))['preserved']
    assert len(list(queue[3].iterdir()))==1
    backup_sqlite(queue[4],queue[4].with_suffix('.completed.db'))
    with sqlite3.connect(queue[4].with_suffix('.completed.db')) as copied:
        assert copied.execute('SELECT status FROM project_document_jobs').fetchone()[0]=='completed'
        assert copied.execute('SELECT count(*) FROM project_document_job_receipts').fetchone()[0]==1


def test_failure_retry_preserves_prior_success_and_counts_items_once(queue):
    install(queue)
    job=enqueue(queue,both=True)
    first=jobs.run_one(queue[1],'project',job['id'],storage_root=queue[3])
    assert first['status']=='running' and first['processed']==1 and first['total']==2
    original=(queue[2]/'notice.docm').read_bytes()
    (queue[2]/'notice.docm').write_bytes(b'changed')
    failed=jobs.run_one(queue[1],'project',job['id'],storage_root=queue[3])
    assert failed['status']=='failed' and failed['processed']==2 and failed['items'][0]['artifact_id']==first['items'][0]['artifact_id']
    (queue[2]/'notice.docm').write_bytes(original)
    with queue[1]() as db:
        error(409,lambda:jobs.retry(db,'project',job['id'],1))
        db.rollback()
        retried=jobs.retry(db,'project',job['id'],failed['revision'])
        db.commit()
    assert retried['processed']==1 and retried['items'][0]['status']=='succeeded'
    completed=jobs.run_one(queue[1],'project',job['id'],storage_root=queue[3])
    assert completed['status']=='completed' and completed['processed']==2
    with queue[1]() as db:
        assert len(list(db.scalars(select(DocumentJobAttempt))))==3
        assert len(list(db.scalars(select(DocumentJobArtifact))))==2
        assert len(list(db.scalars(select(DocumentJobReceipt))))==3
        assert completed['items'][0]['artifact_id']==first['items'][0]['artifact_id']


def test_cancel_queued_then_explicit_retry(queue):
    install(queue)
    job=enqueue(queue,both=True)
    with queue[1]() as db:
        stopped=jobs.cancel(db,'project',job['id'],job['revision'])
        db.commit()
    assert stopped['status']=='cancelled' and stopped['processed']==2
    with queue[1]() as db:
        error(409,lambda:jobs.claim(db,'project',job['id'],stopped['revision']))
        resumed=jobs.retry(db,'project',job['id'],stopped['revision'])
        db.commit()
    assert resumed['status']=='queued' and resumed['processed']==0


def test_active_cancel_accepts_finished_file_without_starting_another(queue):
    install(queue)
    job=enqueue(queue,both=True)
    with queue[1]() as db:
        taken=jobs.claim(db,'project',job['id'],1)
        db.commit()
    with queue[1]() as db:
        stopped=jobs.cancel(db,'project',job['id'],taken['revision'])
        db.commit()
    assert stopped['status']=='running' and stopped['cancel_requested'] and stopped['processed']==1
    with queue[1]() as db:
        end=jobs.finish(db,'project',job['id'],taken['attempt_id'],error='cancelled during file read')
        db.commit()
    assert end['status']=='cancelled' and end['processed']==2
    with queue[1]() as db:
        error(409,lambda:jobs.claim(db,'project',job['id'],end['revision']))


def test_recovery_appends_interrupted_receipt_then_new_attempt(queue):
    install(queue)
    job=enqueue(queue)
    with queue[1]() as db:
        taken=jobs.claim(db,'project',job['id'],1)
        db.commit()
    # Close original session; explicit trusted coordinator recovery only.
    with queue[1]() as db:
        recovered=jobs.recover_interrupted(db,'project',job['id'],taken['revision'])
        db.commit()
    assert recovered['status']=='interrupted' and recovered['processed']==1
    with queue[1]() as db:
        assert db.scalar(select(DocumentJobReceipt)).outcome=='interrupted'
        error(409,lambda:jobs.finish(db,'project',job['id'],taken['attempt_id'],error='late'))
        resumed=jobs.retry(db,'project',job['id'],recovered['revision'])
        db.commit()
    assert resumed['processed']==0
    result=jobs.run_one(queue[1],'project',job['id'],storage_root=queue[3])
    assert result['status']=='completed'
    with queue[1]() as db:
        assert [a.number for a in db.scalars(select(DocumentJobAttempt).order_by(DocumentJobAttempt.number))]==[1,2]


def test_two_connections_cannot_claim_same_file(queue):
    install(queue)
    job=enqueue(queue)
    barrier=Barrier(2)
    def take():
        with queue[1]() as db:
            barrier.wait()
            try:
                claim=jobs.claim(db,'project',job['id'],1)
                db.commit()
                return claim['attempt_id']
            except HTTPException as exc:
                db.rollback()
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:take(),range(2)))
    assert sum(isinstance(value,str) for value in results)==1 and results.count(409)==1
    with queue[1]() as db:
        assert len(list(db.scalars(select(DocumentJobAttempt))))==1


@pytest.mark.parametrize('table',['project_document_job_attempts','project_document_job_artifacts','project_document_job_receipts','project_document_job_events'])
def test_historical_rows_cannot_be_rewritten_or_deleted(queue,table):
    install(queue)
    job=enqueue(queue)
    jobs.run_one(queue[1],'project',job['id'],storage_root=queue[3])
    with queue[0].connect() as db:
        with pytest.raises(IntegrityError):
            db.execute(text(f"UPDATE {table} SET id = 'forged'"))
        db.rollback()
        with pytest.raises(IntegrityError):
            db.execute(text(f'DELETE FROM {table}'))
        db.rollback()


def test_snapshot_and_head_identities_immutable(queue):
    install(queue)
    job=enqueue(queue)
    with queue[0].connect() as db:
        for sql in ["UPDATE project_document_jobs SET snapshot='{}'", "UPDATE project_document_job_items SET document_id='tdao'",
                    "DELETE FROM project_document_jobs", "DELETE FROM project_document_job_items"]:
            with pytest.raises(IntegrityError):
                db.execute(text(sql))
            db.rollback()
    with queue[1]() as db:
        assert jobs.detail(db,'project',job['id'])['revision']==1


def test_parent_permissions_precede_storage_and_schema(queue,monkeypatch):
    monkeypatch.setattr(jobs,'_ready',lambda *a,**k:pytest.fail('permission must precede schema'))
    with operator_context(Operator('reader','reader',frozenset({'project'}))),queue[1]() as db:
        error(403,lambda:jobs.submit(db,'project',DocumentBatchSubmit(command_id='x',items=[{
            'document_id':'ce_request','link_id':'link','expected_source_sha256':'a'*64,
            'expected_link_sha256':'b'*64,'expected_values_sha256':'c'*64,
            'expected_identity_revision':0,'expected_planning_revision':0}])))
        error(404,lambda:jobs.detail(db,'foreign','fake'))


def test_artifact_tampering_and_missing_receipt_refused(queue):
    install(queue)
    job=enqueue(queue)
    result=jobs.run_one(queue[1],'project',job['id'],storage_root=queue[3])
    with queue[1]() as db:
        artifact=db.scalar(select(DocumentJobArtifact))
        path=queue[3]/artifact.storage_key
        original=path.read_bytes()
        path.write_bytes(b'x'*len(original))
        error(409,lambda:jobs.artifact_content(db,'project',artifact.id,storage_root=queue[3]))
        error(404,lambda:jobs.artifact_content(db,'foreign',result['items'][0]['artifact_id'],storage_root=queue[3]))
        path.write_bytes(original)
        with operator_context(Operator('reader','reader',frozenset({'project'}))):
            assert jobs.artifact_content(db,'project',artifact.id,storage_root=queue[3])[0]==original


@pytest.mark.parametrize('extra', [{'actor_id':'forged'},{'root':'V:/any'},{'price':42},{'output_path':'V:/out'}])
def test_batch_commands_forbid_client_policy_actor_and_finance(queue,extra):
    raw=command(queue).model_dump()
    with pytest.raises(ValidationError):
        DocumentBatchSubmit.model_validate({**raw,**extra})


def test_incompatible_schema_refused_before_backup(queue):
    with queue[0].begin() as db:
        db.exec_driver_sql('CREATE TABLE project_document_jobs (id TEXT PRIMARY KEY)')
    with pytest.raises(ValueError,match='incompatible'):
        install_job_schema(queue[0],backup=lambda:pytest.fail('must preflight'))


def test_queue_captures_bounded_before_any_row_is_written(queue,monkeypatch):
    install(queue)
    cmd=command(queue)
    preview=project_documents.preview
    def excessive(*args,**kwargs):
        report=preview(*args,**kwargs)
        report['targets'][0]['existing_value']='x'*(4*1024*1024)
        return report
    monkeypatch.setattr(project_documents,'preview',excessive)
    with queue[1]() as db:
        error(422,lambda:jobs.submit(db,'project',cmd))
        assert db.scalar(select(DocumentJob)) is None


def test_batch_submission_stale_preview_and_foreign_link_create_no_job(queue):
    install(queue)
    cmd=command(queue)
    with zipfile.ZipFile(queue[2]/'ce.docx','a') as archive:
        archive.comment=b'Changed after review'
    with queue[1]() as db:
        error(409,lambda:jobs.submit(db,'project',cmd))
        db.rollback()
        foreign=cmd.model_copy(update={'items':[cmd.items[0].model_copy(update={'link_id':'foreign-link'})]})
        error(404,lambda:jobs.submit(db,'project',foreign))
        db.rollback()
        assert db.scalar(select(DocumentJob)) is None and db.scalar(select(DocumentJobItem)) is None


def test_artifact_storage_failure_records_failure_without_touching_source(queue,monkeypatch):
    install(queue)
    original=(queue[2]/'ce.docx').read_bytes()
    job=enqueue(queue)
    monkeypatch.setattr(jobs,'write_artifact',lambda *a,**k:(_ for _ in ()).throw(OSError('disk full')))
    failed=jobs.run_one(queue[1],'project',job['id'],storage_root=queue[3])
    assert failed['status']=='failed' and failed['processed']==1
    with queue[1]() as db:
        assert db.scalar(select(DocumentJobArtifact)) is None
        assert db.scalar(select(DocumentJobReceipt)).outcome=='failed'
    assert (queue[2]/'ce.docx').read_bytes()==original


def test_receipt_transaction_failure_retains_owned_candidate_for_recovery(queue):
    install(queue)
    job=enqueue(queue)
    with queue[0].begin() as db:
        db.exec_driver_sql("CREATE TRIGGER test_receipt_failure BEFORE INSERT ON project_document_job_receipts BEGIN SELECT RAISE(ABORT, 'disk failure'); END")
    with pytest.raises(IntegrityError):
        jobs.run_one(queue[1],'project',job['id'],storage_root=queue[3])
    assert len(list(queue[3].iterdir()))==1  # Retained, never purged on rollback.
    with queue[1]() as db:
        state=jobs.detail(db,'project',job['id'])
        assert state['status']=='running' and state['processed']==0
        assert db.scalar(select(DocumentJobArtifact)) is None
        assert db.scalar(select(DocumentJobReceipt)) is None
    with queue[0].begin() as db:
        db.exec_driver_sql('DROP TRIGGER test_receipt_failure')
    with queue[1]() as db:
        recovered=jobs.recover_interrupted(db,'project',job['id'],state['revision'])
        db.commit()
    assert recovered['status']=='interrupted' and len(list(queue[3].iterdir()))==1


def test_active_cancel_during_real_prepare_keeps_success_and_stops_remaining(queue,monkeypatch):
    install(queue)
    job=enqueue(queue,both=True)
    prepare=project_documents.prepare_copy
    def cancelling(db,*args,**kwargs):
        result=prepare(db,*args,**kwargs)
        with queue[1]() as concurrent:
            state=jobs.detail(concurrent,'project',job['id'])
            jobs.cancel(concurrent,'project',job['id'],state['revision'])
            concurrent.commit()
        return result
    monkeypatch.setattr(project_documents,'prepare_copy',cancelling)
    stopped=jobs.run_one(queue[1],'project',job['id'],storage_root=queue[3])
    assert stopped['status']=='cancelled' and stopped['processed']==2
    assert stopped['items'][0]['status']=='succeeded' and stopped['items'][0]['artifact_id']
    assert stopped['items'][1]['status']=='cancelled'
    with queue[1]() as db:
        assert len(list(db.scalars(select(DocumentJobAttempt))))==1


def test_read_detail_and_download_cannot_mutate_or_probe_shares(queue,monkeypatch):
    install(queue)
    job=enqueue(queue)
    with operator_context(Operator('reader','reader',frozenset({'project'}))),queue[1]() as db:
        assert not jobs.detail(db,'project',job['id'])['can_cancel']
    completed=jobs.run_one(queue[1],'project',job['id'],storage_root=queue[3])
    before=capture_baseline(queue[4])
    monkeypatch.setattr(project_documents,'acquire_file',lambda *a,**k:pytest.fail('read query probes share'))
    with operator_context(Operator('reader','reader',frozenset({'project'}))),queue[1]() as db:
        assert jobs.detail(db,'project',job['id'])['status']=='completed'
        assert jobs.artifact_content(db,'project',completed['items'][0]['artifact_id'],storage_root=queue[3])[0]
        error(403,lambda:jobs.retry(db,'project',job['id'],completed['revision']))
        error(404,lambda:jobs.detail(db,'foreign',job['id']))
    assert capture_baseline(queue[4])==before
