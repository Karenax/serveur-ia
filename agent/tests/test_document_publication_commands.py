"""Real file publication, crash boundaries, immutable receipts and scoped HTTP."""
from copy import deepcopy
import hashlib
import json
import sqlite3
import subprocess
import sys
from uuid import uuid4

from fastapi import HTTPException
import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.db_support import backup_sqlite
from app.services.document_jobs_backup import validate_job_history, suspend_restored_jobs
from app.services.deliverable_manifest import freeze
from backend.app.models import NetworkLink
from backend.app.project_document_job_models import DocumentJob, DocumentJobArtifact, DocumentJobEvent
from backend.app.project_document_publication_schemas import DocumentPublicationCommand
from backend.app.services import document_jobs as jobs, document_publication_commands as publications
from backend.app.services import document_job_history, document_publication_history
from backend.app.services.project_document_job_archive import import_rows, section_for
from backend.app.services.document_publication_io import AnchoredDirectory
from backend.app.services.document_worker_lease import WorkerLease
from backend.app.services.migration_guard import capture_baseline
from tests.test_document_publication_preview import prepared as prepared_fixture, review, failure
from tests.test_project_document_jobs import queue as queue_fixture, command as batch_command
from tests.test_project_document_job_api import api as api_fixture, HEADERS, ROOT

queue = queue_fixture
prepared = prepared_fixture
api = api_fixture


def command(prepared, *, cid='publish-once'):
    report = review(prepared)
    return DocumentPublicationCommand(command_id=cid, link_id=prepared[2].link_id,
        expected_revision=report['job_revision'], expected_preview_sha256=report['preview_sha256'], reviewed=True)


def publish(prepared, payload=None):
    queue, aid, _ = prepared
    payload = command(prepared) if payload is None else payload
    with queue[1]() as db:
        return publications.publish(db, 'project', aid, payload, storage_root=queue[3])


def records(prepared):
    queue, aid, _ = prepared
    with queue[1]() as db:
        job_id = db.get(DocumentJobArtifact, aid).job_id
        return publications.list_publications(db, 'project', job_id)


def tables(queue):
    with sqlite3.connect(queue[4]) as db:
        db.row_factory = sqlite3.Row
        return {'projects':[dict(db.execute("SELECT * FROM projects WHERE id='project'").fetchone())],
                'network_links':[dict(row) for row in db.execute("SELECT * FROM network_links WHERE project_id='project'")],
                **{name:[dict(row) for row in db.execute(f'SELECT * FROM {name}')] for name in document_job_history.JOB_TABLES}}


def test_real_publish_same_command_replay_keeps_file_identity_bytes_events_and_legacy_data(prepared):
    queue = prepared[0]
    payload = command(prepared)
    before = capture_baseline(queue[4])
    existing = {p.name:p.read_bytes() for p in queue[2].iterdir()}
    result = publish(prepared, payload)
    assert result['state'] == 'succeeded' and result['network_published'] and result['job_revision'] == 6
    output = queue[2] / 'AIRB26LTH0205-A-Demande de CE.docx'
    assert hashlib.sha256(output.read_bytes()).hexdigest() == result['receipt']['sha256']
    committed = capture_baseline(queue[4])
    again = publish(prepared, payload)
    assert again == result and capture_baseline(queue[4]) == committed
    assert records(prepared)['total'] == 1
    assert records(prepared)['items'][0]['command'] == payload.model_dump()
    with queue[1]() as db:
        events = list(db.scalars(select(DocumentJobEvent).where(DocumentJobEvent.kind.like('publication_%'))))
        assert [e.kind for e in sorted(events, key=lambda e:e.revision)] == [
            'publication_requested','publication_prepared','publication_succeeded']
        assert {e.actor_id for e in events} == {'local'}
    assert {name:(queue[2]/name).read_bytes() for name in existing} == existing
    # All pre-existing non-queue rows, including historical financial values,
    # are preserved. Only the parent queue revision and its new events change.
    for table, snapshot in before['tables'].items():
        if not table.startswith('project_document_'):
            assert committed['tables'][table] == snapshot
    assert validate_job_history(queue[4])[0]['sha256'] == result['receipt']['sha256']


@pytest.mark.parametrize('boundary', ['before_create', 'before_prepared_commit', 'before_promote', 'after_promote', 'before_success_commit'])
def test_crash_boundaries_never_regenerate_and_reconcile_only_durable_identity(prepared, monkeypatch, boundary):
    payload = command(prepared)
    original_append = publications._append
    original_create = AnchoredDirectory.create_candidate
    original_promote = AnchoredDirectory.promote
    creations = []

    def create(self, name, content):
        creations.append(name)
        if boundary == 'before_create':
            raise OSError('Simulated process stop before IO')
        return original_create(self, name, content)

    def append(db, pid, jid, kind, detail, **kwargs):
        if (boundary == 'before_prepared_commit' and kind == 'publication_prepared'
                or boundary == 'before_success_commit' and kind == 'publication_succeeded'):
            raise OperationalError('COMMIT', None, OSError('Simulated lost commit'))
        return original_append(db, pid, jid, kind, detail, **kwargs)

    def promote(self, *args):
        if boundary == 'before_promote':
            raise OSError('Simulated stop before promotion')
        value = original_promote(self, *args)
        if boundary == 'after_promote':
            raise OSError('Simulated lost reply after rename')
        return value

    with monkeypatch.context() as scoped:
        scoped.setattr(AnchoredDirectory, 'create_candidate', create)
        scoped.setattr(AnchoredDirectory, 'promote', promote)
        scoped.setattr(publications, '_append', append)
        with pytest.raises((OSError, OperationalError)):
            publish(prepared, payload)
    state = records(prepared)['items'][0]
    assert state['state'] == ('requested' if boundary in {'before_create','before_prepared_commit'} else 'prepared')
    assert len(creations) == 1 and validate_job_history(prepared[0][4])
    monkeypatch.setattr(AnchoredDirectory, 'create_candidate', lambda *args:pytest.fail('Replay must never recreate bytes'))
    if state['state'] == 'requested':
        with pytest.raises(HTTPException) as raised:
            publish(prepared, payload)
        assert raised.value.status_code == 409 and raised.value.detail['code'] == 'publication_uncertain'
        failure(409, lambda:publish(prepared, command(prepared,cid='unsafe-new-nonce')))
    else:
        result = publish(prepared, payload)
        assert result['state'] == 'succeeded' and result['receipt'] == state['receipt']
        assert publish(prepared, payload) == result
    assert len(creations) == 1


def test_sql_prepared_commit_failure_preserves_candidate_but_refuses_adoption(prepared, monkeypatch):
    payload = command(prepared)
    queue, aid, _ = prepared
    with queue[1]() as db:
        commit = db.commit
        calls = []
        def fail_second_commit():
            calls.append(1)
            if len(calls) == 2:
                raise OperationalError('COMMIT', None, OSError('Disk database full'))
            commit()
        monkeypatch.setattr(db,'commit',fail_second_commit)
        with pytest.raises(OperationalError):
            publications.publish(db,'project',aid,payload,storage_root=queue[3])
    assert len(calls) == 2
    assert records(prepared)['items'][0]['state'] == 'requested'
    assert len(list(queue[2].glob('.agent-publish-*.pending'))) == 1
    failure(409, lambda:publish(prepared,payload))
    assert validate_job_history(queue[4])


def test_collision_created_after_receipt_never_overwrites_and_can_resume_after_human_resolution(prepared, monkeypatch):
    payload = command(prepared)
    original = AnchoredDirectory.promote
    target = prepared[0][2] / review(prepared)['filename']
    def collide(self, *args):
        target.write_bytes(b'Another operator original file')
        return original(self, *args)
    with monkeypatch.context() as scoped:
        scoped.setattr(AnchoredDirectory,'promote',collide)
        failure(409,lambda:publish(prepared,payload))
    state = records(prepared)['items'][0]
    assert state['state'] == 'prepared' and target.read_bytes() == b'Another operator original file'
    failure(409,lambda:publish(prepared,payload))
    target.rename(target.with_suffix('.retained-original'))  # Fictional human resolution; no deletion.
    assert publish(prepared,payload)['receipt'] == state['receipt']
    assert target.with_suffix('.retained-original').read_bytes() == b'Another operator original file'


@pytest.mark.parametrize('damage', ['same_bytes_new_file','changed_bytes','missing'])
def test_success_replay_refuses_changed_or_missing_final_and_never_recreates(prepared, monkeypatch, damage):
    payload = command(prepared)
    publish(prepared,payload)
    target = prepared[0][2] / review(prepared)['filename']
    saved = target.with_suffix('.original')
    target.rename(saved)
    if damage == 'same_bytes_new_file':
        target.write_bytes(saved.read_bytes())
    elif damage == 'changed_bytes':
        target.write_bytes(b'Externally changed')
    monkeypatch.setattr(AnchoredDirectory,'create_candidate',lambda *args:pytest.fail('Never recreate a historical success'))
    failure(409,lambda:publish(prepared,payload))
    assert records(prepared)['items'][0]['state'] == 'succeeded'


def test_command_nonce_destination_revision_and_policy_changes_are_refused_before_candidate_io(prepared, monkeypatch):
    payload = command(prepared)
    queue, _, _ = prepared
    second = queue[2] / 'second'
    second.mkdir()
    with queue[1]() as db:
        db.get(NetworkLink,'link').chemin = str(second)
        db.commit()
    monkeypatch.setattr(AnchoredDirectory,'create_candidate',lambda *args:pytest.fail('No candidate on stale review'))
    failure(409,lambda:publish(prepared,payload))
    assert records(prepared)['total'] == 0
    with queue[1]() as db:
        db.get(NetworkLink,'link').chemin = str(queue[2])
        db.commit()
    monkeypatch.setenv('AGENT_DOCUMENT_WRITE_ROOTS',json.dumps([str(queue[2].parent)]))
    failure(409,lambda:publish(prepared,payload))
    assert records(prepared)['total'] == 0


def test_scope_reader_and_blocked_history_precede_lock_and_filesystem(prepared, monkeypatch):
    payload = command(prepared)
    monkeypatch.setattr(publications,'_lease',lambda *args:pytest.fail('Forbidden before any lock IO'))
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS','["foreign"]')
    failure(404,lambda:publish(prepared,payload))
    monkeypatch.delenv('AGENT_OPERATOR_PROJECT_IDS')
    monkeypatch.setenv('AGENT_OPERATOR_ROLE','reader')
    failure(403,lambda:publish(prepared,payload))
    monkeypatch.setenv('AGENT_OPERATOR_ROLE','owner')
    with prepared[0][1]() as db:
        db.scalar(select(DocumentJob)).execution_blocked = True
        db.commit()
    failure(409,lambda:publish(prepared,payload))


def test_publication_lease_is_separate_exclusive_across_processes_and_released(prepared):
    queue = prepared[0]
    worker, lease = WorkerLease(queue[4]), WorkerLease(queue[4],namespace='publication')
    assert worker.acquire() and lease.acquire()
    script = 'import sys; from backend.app.services.document_worker_lease import WorkerLease; x=WorkerLease(sys.argv[1],namespace="publication"); print(x.acquire()); x.close()'
    try:
        child = subprocess.run([sys.executable,'-c',script,str(queue[4])],capture_output=True,text=True,timeout=10)
        assert child.returncode == 0 and child.stdout.strip() == 'False', child.stderr
        failure(409,lambda:publish(prepared,command(prepared)))
        assert records(prepared)['total'] == 0
    finally:
        lease.close()
        worker.close()
    assert publish(prepared)['state'] == 'succeeded'
    with pytest.raises(ValueError):
        WorkerLease(queue[4],namespace='../unsafe')


def test_completed_command_cannot_be_rebound_to_other_payload(prepared):
    payload = command(prepared)
    publish(prepared,payload)
    failure(409,lambda:publish(prepared,payload.model_copy(update={'relative_directory':'second'})))
    failure(409,lambda:publish(prepared,payload.model_copy(update={'expected_revision':1})))
    assert records(prepared)['total'] == 1


def test_history_read_has_no_network_probes_and_reader_can_consult(prepared, monkeypatch):
    publish(prepared)
    monkeypatch.setenv('AGENT_OPERATOR_ROLE','reader')
    monkeypatch.setattr(publications,'AnchoredDirectory',lambda *args:pytest.fail('Read history is offline'))
    monkeypatch.setattr(publications,'_lease',lambda *args:pytest.fail('Read history has no lease'))
    record = records(prepared)['items'][0]
    assert record['state'] == 'succeeded' and not record['can_resume']


def test_offline_restore_suspends_publication_replay_without_touching_destination(prepared, tmp_path, monkeypatch):
    payload = command(prepared)
    publish(prepared,payload)
    queue = prepared[0]
    restored = tmp_path / 'restored.db'
    backup_sqlite(queue[4],restored)
    files = {p.name:p.read_bytes() for p in queue[2].iterdir()}
    suspend_restored_jobs(restored)
    assert validate_job_history(restored)
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(f'sqlite:///{restored}')
    try:
        with sessionmaker(bind=engine)() as db:
            monkeypatch.setattr(publications,'_lease',lambda *args:pytest.fail('Restore must never replay IO'))
            failure(409,lambda:publications.publish(db,'project',prepared[1],payload,storage_root=queue[3]))
            history = publications.list_publications(db,'project',db.get(DocumentJobArtifact,prepared[1]).job_id)
            assert history['execution_blocked'] and history['items'][0]['state'] == 'succeeded'
            assert not history['items'][0]['can_resume']
    finally:
        engine.dispose()
    assert files == {p.name:p.read_bytes() for p in queue[2].iterdir()}


def test_typed_remap_twice_retains_raw_intent_receipts_and_maps_artifact_and_destination_link(prepared):
    publish(prepared)
    raw = tables(prepared[0])
    original = deepcopy(raw)
    section_for(raw)
    original_details = [e['detail'] for e in raw['project_document_job_events']]
    for _ in range(2):
        ledger = document_job_history.validate(raw)
        mapping = {row['id']:str(uuid4()) for rows in raw.values() for row in rows}
        mapped = import_rows(raw,mapping,actor='trusted-import')
        raw = {'projects':[{'id':mapping[raw['projects'][0]['id']]}],
               'network_links':[{**r,'id':mapping[r['id']],'project_id':mapping[r['project_id']]} for r in raw['network_links']],**mapped}
        ledger = document_job_history.validate(raw)
        job = next(iter(ledger['jobs'].values()))
        row = document_publication_history.for_job(ledger,job)['publish-once']
        assert job['execution_blocked'] and row['state'] == 'succeeded'
        assert row['binding']['artifact_id'] in ledger['job_artifacts']
        assert row['binding']['link_id'] in {link['id'] for link in raw['network_links']}
        assert [e['detail'] for e in raw['project_document_job_events'][:len(original_details)]] == original_details
        section_for(raw)
    assert tables(prepared[0]) == original


@pytest.mark.parametrize('damage', ['receipt_identity','receipt_size','receipt_hash','receipt_extra','success_without_prepare',
    'duplicate_request','preview_extra','preview_foreign_artifact','preview_hash','candidate_path','command_extra','import_binding'])
def test_closed_offline_publication_history_rejects_forgery(prepared, damage):
    publish(prepared)
    raw = tables(prepared[0])
    events = raw['project_document_job_events']
    request = next(e for e in events if e['kind'] == 'publication_requested')
    prepared_event = next(e for e in events if e['kind'] == 'publication_prepared')
    detail = json.loads(request['detail'])
    receipt = json.loads(prepared_event['detail'])
    if damage == 'receipt_identity':
        receipt['receipt']['identity'] = 'forged'
    elif damage == 'receipt_size':
        receipt['receipt']['size_bytes'] = True
    elif damage == 'receipt_hash':
        receipt['receipt']['sha256'] = '0'*64
    elif damage == 'receipt_extra':
        receipt['receipt']['root'] = 'V:/'
    elif damage == 'success_without_prepare':
        prepared_event['kind'] = 'publication_succeeded'
    elif damage == 'duplicate_request':
        prepared_event['kind'], prepared_event['detail'] = 'publication_requested', request['detail']
    elif damage == 'preview_extra':
        detail['preview']['rate'] = 99
    elif damage == 'preview_foreign_artifact':
        detail['preview']['artifact_id'] = 'foreign-artifact'
        detail['command']['expected_preview_sha256'] = freeze(detail['preview'])[1]
        detail['command_sha256'] = freeze(detail['command'])[1]
    elif damage == 'preview_hash':
        detail['preview']['filename'] = 'forged.docx'
    elif damage == 'candidate_path':
        detail['candidate'] = '../foreign.pending'
    elif damage == 'command_extra':
        detail['command']['actor_id'] = 'forged'
    else:
        mapping = {row['id']:str(uuid4()) for rows in raw.values() for row in rows}
        mapped = import_rows(raw,mapping,actor='trusted-import')
        raw = {'projects':[{'id':mapping['project']}],**mapped}
        last = mapped['project_document_job_events'][-1]
        binding = json.loads(last['detail'])
        binding['publication_bindings']['publish-once']['artifact_id'] = 'foreign-artifact'
        last['detail'] = freeze(binding)[0]
    if damage.startswith('receipt_'):
        prepared_event['detail'] = freeze(receipt)[0]
    elif damage in {'preview_extra','preview_foreign_artifact','preview_hash','candidate_path','command_extra'}:
        request['detail'] = freeze(detail)[0]
    with pytest.raises((ValueError,HTTPException)):
        document_job_history.validate(raw)


def test_actual_http_publish_review_csrf_reader_history_and_same_command(api, monkeypatch):
    client, queue, _, _ = api
    batch = client.post(ROOT+'/jobs',json=batch_command(queue).model_dump(),headers=HEADERS)
    assert batch.status_code == 200
    job = jobs.run_one(queue[1],'project',batch.json()['id'],storage_root=queue[3])
    aid = job['items'][0]['artifact_id']
    monkeypatch.setenv('AGENT_DOCUMENT_WRITE_ROOTS',json.dumps([str(queue[2])]))
    path = ROOT+'/artifacts/'+aid
    preview = client.post(path+'/publication-preview',json={'link_id':'link'},headers=HEADERS).json()
    payload = {'command_id':'actual-http-once','link_id':'link','expected_revision':preview['job_revision'],
               'expected_preview_sha256':preview['preview_sha256'],'reviewed':True}
    assert client.post(path+'/publish',json=payload).status_code == 403
    assert client.post(path+'/publish',json={**payload,'reviewed':1},headers=HEADERS).status_code == 422
    response = client.post(path+'/publish',json=payload,headers=HEADERS)
    assert response.status_code == 200, response.text
    assert response.json()['state'] == 'succeeded'
    assert client.post(path+'/publish',json=payload,headers=HEADERS).json() == response.json()
    monkeypatch.setenv('AGENT_OPERATOR_ROLE','reader')
    assert client.post(path+'/publish',json=payload,headers=HEADERS).status_code == 403
    journal = client.get(ROOT+'/jobs/'+job['id']+'/publications').json()
    assert journal['total'] == 1 and not journal['items'][0]['can_resume']
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS','["foreign"]')
    assert client.get(ROOT+'/jobs/'+job['id']+'/publications').status_code == 404
    monkeypatch.setenv('AGENT_OPERATOR_ROLE','owner')
    assert client.post(path+'/publish',json=payload,headers=HEADERS).status_code == 404


def test_publication_refuses_session_with_unrelated_pending_changes_without_committing(prepared):
    payload = command(prepared)
    queue, aid, _ = prepared
    before = capture_baseline(queue[4])
    with queue[1]() as db:
        db.get(NetworkLink,'link').libelle = 'Unrelated pending edit'
        failure(409,lambda:publications.publish(db,'project',aid,payload,storage_root=queue[3]))
    assert capture_baseline(queue[4]) == before
    assert records(prepared)['total'] == 0


def test_windows_relative_directory_normalized_before_review_and_command_capture(prepared):
    from backend.app.project_document_publication_schemas import DocumentPublicationPreview
    queue, aid, _ = prepared
    (queue[2]/'nested'/'leaf').mkdir(parents=True)
    selected = (queue,aid,DocumentPublicationPreview(link_id='link',relative_directory=r'nested\leaf'))
    reviewed = review(selected)
    payload = DocumentPublicationCommand(command_id='nested',link_id='link',relative_directory=r'nested\leaf',
        expected_revision=reviewed['job_revision'],expected_preview_sha256=reviewed['preview_sha256'],reviewed=True)
    assert payload.relative_directory == 'nested/leaf'
    result = publish(selected,payload)
    assert result['state'] == 'succeeded'
    assert (queue[2]/'nested'/'leaf'/reviewed['filename']).is_file()
    assert validate_job_history(queue[4])


def test_closed_history_refuses_new_publication_after_restore_even_with_valid_hashes(prepared):
    publish(prepared)
    raw = tables(prepared[0])
    job = raw['project_document_jobs'][0]
    original = next(row for row in raw['project_document_job_events'] if row['kind']=='publication_requested')
    restored = {**original,'id':str(uuid4()),'revision':job['revision']+1,'kind':'store_restored',
                'detail':freeze({'execution_blocked':True,'previous_status':job['status']})[0]}
    detail = json.loads(original['detail'])
    detail['command']['command_id'] = 'forged-after-restore'
    detail['command']['expected_revision'] = restored['revision']
    detail['preview']['job_revision'] = restored['revision']
    detail['command']['expected_preview_sha256'] = freeze(detail['preview'])[1]
    detail['command_sha256'] = freeze(detail['command'])[1]
    detail['candidate'] = '.agent-publish-'+uuid4().hex+'.pending'
    forged = {**original,'id':str(uuid4()),'revision':restored['revision']+1,'detail':freeze(detail)[0]}
    raw['project_document_job_events'].extend([restored,forged])
    job['revision'] = forged['revision']
    job['execution_blocked'] = True
    with pytest.raises(ValueError,match='postérieure'):
        document_job_history.validate(raw)
