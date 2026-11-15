"""Fictional Windows originals, retained backup, crash recovery and v1 history."""
import json
import os
from copy import deepcopy

from fastapi import HTTPException
import pytest
from sqlalchemy.exc import OperationalError

from app.services.deliverable_manifest import freeze
from app.services.document_jobs_backup import validate_job_history
from backend.app.project_document_publication_schemas import DocumentPublicationPreview, DocumentPublicationCommand
from backend.app.services import document_publication_commands as publications, document_job_history
from backend.app.services.document_publication_io import AnchoredDirectory
from tests.test_document_publication_commands import publish, records, tables
from tests.test_document_publication_preview import prepared as prepared_fixture, review, failure
from tests.test_project_document_jobs import queue as queue_fixture, command as batch_command
from tests.test_project_document_job_api import api as api_fixture, HEADERS, ROOT
from backend.app.services import document_jobs as jobs

queue = queue_fixture
prepared = prepared_fixture
api = api_fixture


@pytest.fixture
def replacement(prepared):
    if os.name!='nt':
        pytest.skip('Anchored original move requires native Windows')
    queue, aid, _ = prepared
    reviewed = review(prepared)
    target = queue[2]/reviewed['filename']
    target.write_bytes(b'Original fictional customer document to retain')
    chosen = (queue,aid,DocumentPublicationPreview(link_id='link',replace_existing=True))
    report = review(chosen)
    assert report['can_publish'] and report['occupied'] and report['existing_receipt']
    payload = DocumentPublicationCommand(command_id='replace-once',link_id='link',replace_existing=True,
        expected_revision=report['job_revision'],expected_preview_sha256=report['preview_sha256'],reviewed=True)
    return chosen,payload,target,report


def test_explicit_replacement_retains_original_identity_and_bytes_and_exact_replay(replacement):
    chosen,payload,target,preview = replacement
    original = target.read_bytes()
    result = publish(chosen,payload)
    backup = target.parent/result['backup']
    assert result['state']=='succeeded' and result['job_revision']==8
    assert result['backup_receipt']==preview['existing_receipt'] and backup.read_bytes()==original
    with AnchoredDirectory(target.parent,target.parent) as opened:
        opened.verify(backup.name,preview['existing_receipt'])
        opened.verify(target.name,result['receipt'])
    before = tables(chosen[0])
    assert publish(chosen,payload)==result and tables(chosen[0])==before
    assert validate_job_history(chosen[0][4])
    kinds = [row['kind'] for row in sorted(before['project_document_job_events'],key=lambda row:row['revision'])]
    assert kinds[-5:]==['publication_requested','publication_prepared','publication_backup_requested',
                       'publication_backup_saved','publication_succeeded']


@pytest.mark.parametrize('boundary',['backup_intent_commit','before_backup_move','after_backup_move',
                                   'backup_saved_commit','before_final_move','after_final_move','success_commit'])
def test_replacement_crash_reconciles_owned_backup_and_candidate_without_new_bytes(replacement,monkeypatch,boundary):
    chosen,payload,target,preview = replacement
    original = target.read_bytes()
    append, promote = publications._append, AnchoredDirectory.promote
    def fail_append(db,pid,jid,kind,detail,**kwargs):
        bad = {'backup_intent_commit':'publication_backup_requested','backup_saved_commit':'publication_backup_saved',
               'success_commit':'publication_succeeded'}.get(boundary)
        if kind==bad:
            raise OperationalError('COMMIT',None,OSError('Simulated crash'))
        return append(db,pid,jid,kind,detail,**kwargs)
    def fail_move(self,candidate,name,expected):
        is_backup = name.startswith('.agent-backup-')
        if boundary==('before_backup_move' if is_backup else 'before_final_move'):
            raise OSError('Simulated stop before rename')
        result = promote(self,candidate,name,expected)
        if boundary==('after_backup_move' if is_backup else 'after_final_move'):
            raise OSError('Simulated stop after rename')
        return result
    with monkeypatch.context() as scoped:
        scoped.setattr(publications,'_append',fail_append)
        scoped.setattr(AnchoredDirectory,'promote',fail_move)
        with pytest.raises((OperationalError,OSError)):
            publish(chosen,payload)
    record = records(chosen)['items'][0]
    assert record['state'] in {'prepared','backup_requested','backup_saved'}
    assert validate_job_history(chosen[0][4])
    monkeypatch.setattr(AnchoredDirectory,'create_candidate',lambda *args:pytest.fail('Recovery must use durable prepared bytes'))
    result = publish(chosen,payload)
    assert result['state']=='succeeded' and result['receipt']==record['receipt']
    assert (target.parent/result['backup']).read_bytes()==original
    assert result['backup_receipt']==preview['existing_receipt']
    assert publish(chosen,payload)==result


def test_original_changed_after_review_or_after_preparation_is_never_moved(replacement,monkeypatch):
    chosen,payload,target,_ = replacement
    target.write_bytes(b'Changed after human review')
    failure(409,lambda:publish(chosen,payload))
    assert records(chosen)['total']==0
    reviewed = review(chosen)
    payload = payload.model_copy(update={'expected_preview_sha256':reviewed['preview_sha256']})
    original_append = publications._append
    def change_after_prepare(db,pid,jid,kind,detail,**kwargs):
        result = original_append(db,pid,jid,kind,detail,**kwargs)
        if kind=='publication_prepared':
            target.write_bytes(b'New edit during generation')
        return result
    monkeypatch.setattr(publications,'_append',change_after_prepare)
    failure(409,lambda:publish(chosen,payload))
    assert target.read_bytes()==b'New edit during generation'
    assert not list(target.parent.glob('.agent-backup-*.bak'))
    assert records(chosen)['items'][0]['state']=='prepared'


def test_final_collision_after_original_backup_preserves_every_file(replacement,monkeypatch):
    chosen,payload,target,_ = replacement
    original = target.read_bytes()
    promote = AnchoredDirectory.promote
    def collide(self,candidate,name,expected):
        if candidate.startswith('.agent-publish-'):
            target.write_bytes(b'Raced-in third party original')
        return promote(self,candidate,name,expected)
    with monkeypatch.context() as scoped:
        scoped.setattr(AnchoredDirectory,'promote',collide)
        failure(409,lambda:publish(chosen,payload))
    record = records(chosen)['items'][0]
    assert record['state']=='backup_saved' and (target.parent/record['backup']).read_bytes()==original
    assert target.read_bytes()==b'Raced-in third party original'
    failure(409,lambda:publish(chosen,payload))
    retained = target.with_suffix('.third-party-retained')
    target.rename(retained)  # Fictional human resolution; no deletion.
    assert publish(chosen,payload)['state']=='succeeded'
    assert retained.read_bytes()==b'Raced-in third party original'


def test_backup_collision_is_never_adopted_or_overwritten(replacement,monkeypatch):
    chosen,payload,target,_ = replacement
    original = target.read_bytes()
    append = publications._append
    def occupy_backup(db,pid,jid,kind,detail,**kwargs):
        result = append(db,pid,jid,kind,detail,**kwargs)
        if kind=='publication_backup_requested':
            row = records(chosen)['items'][0]
            (target.parent/row['backup']).write_bytes(original)
        return result
    monkeypatch.setattr(publications,'_append',occupy_backup)
    failure(409,lambda:publish(chosen,payload))
    assert target.read_bytes()==original and records(chosen)['items'][0]['state']=='backup_requested'


@pytest.mark.parametrize('damage',['same_bytes_other_identity','missing'])
def test_historical_success_replay_requires_original_backup_still_verified(replacement,damage):
    chosen,payload,target,_ = replacement
    result = publish(chosen,payload)
    backup = target.parent/result['backup']
    saved = backup.with_suffix('.retained-original')
    backup.rename(saved)
    if damage=='same_bytes_other_identity':
        backup.write_bytes(saved.read_bytes())
    failure(409,lambda:publish(chosen,payload))
    assert saved.is_file() and target.is_file() and records(chosen)['items'][0]['state']=='succeeded'


@pytest.mark.parametrize('damage',['drop_backup_intent','drop_saved_receipt','wrong_original_receipt','unsafe_backup_name','disable_choice'])
def test_closed_replacement_history_rejects_forged_safekeeping(replacement,damage):
    chosen,payload,_,_ = replacement
    publish(chosen,payload)
    raw = tables(chosen[0])
    events = raw['project_document_job_events']
    request = next(row for row in events if row['kind']=='publication_requested')
    if damage in {'drop_backup_intent','drop_saved_receipt'}:
        wanted = 'publication_backup_requested' if damage=='drop_backup_intent' else 'publication_backup_saved'
        next(row for row in events if row['kind']==wanted)['kind']='worker_interrupted'
    elif damage=='wrong_original_receipt':
        event = next(row for row in events if row['kind']=='publication_backup_saved')
        detail = json.loads(event['detail'])
        detail['receipt']['sha256']='0'*64
        event['detail']=freeze(detail)[0]
    else:
        detail = json.loads(request['detail'])
        if damage=='unsafe_backup_name':
            detail['backup']='../business.docx'
        else:
            detail['command']['replace_existing']=False
            detail['command_sha256']=freeze(detail['command'])[1]
        request['detail']=freeze(detail)[0]
    with pytest.raises((ValueError,HTTPException)):
        document_job_history.validate(raw)


def test_v1_history_remains_closed_valid_without_new_default_fields(prepared):
    result = publish(prepared)
    raw = deepcopy(tables(prepared[0]))
    request = next(row for row in raw['project_document_job_events'] if row['kind']=='publication_requested')
    detail = json.loads(request['detail'])
    detail.pop('backup')
    detail['preview']['version']=1
    detail['preview'].pop('replace_existing')
    detail['preview'].pop('existing_receipt')
    detail['command'].pop('replace_existing')
    detail['command']['expected_preview_sha256']=freeze(detail['preview'])[1]
    detail['command_sha256']=freeze(detail['command'])[1]
    request['detail']=freeze(detail)[0]
    assert result['state']=='succeeded' and document_job_history.validate(raw)


def test_replace_choice_is_strict_and_missing_original_is_blocked(prepared):
    from pydantic import ValidationError
    for value in (1,'true',None):
        with pytest.raises(ValidationError):
            DocumentPublicationPreview(link_id='link',replace_existing=value)
    selected = (prepared[0],prepared[1],DocumentPublicationPreview(link_id='link',replace_existing=True))
    result = review(selected)
    assert not result['can_publish'] and result['blockers']==['replacement_target_missing']


def test_actual_http_replacement_requires_choice_and_keeps_original_receipt(api,monkeypatch):
    client,queue,_,_ = api
    monkeypatch.setenv('AGENT_DOCUMENT_WRITE_ROOTS',json.dumps([str(queue[2])]))
    submitted = client.post(ROOT+'/jobs',json=batch_command(queue).model_dump(),headers=HEADERS).json()
    job = jobs.run_one(queue[1],'project',submitted['id'],storage_root=queue[3])
    base = ROOT+'/artifacts/'+job['items'][0]['artifact_id']
    empty = client.post(base+'/publication-preview',json={'link_id':'link'},headers=HEADERS).json()
    target = queue[2]/empty['filename']
    target.write_bytes(b'HTTP fictional original to retain')
    ordinary = client.post(base+'/publication-preview',json={'link_id':'link'},headers=HEADERS).json()
    assert ordinary['blockers']==['destination_occupied']
    reviewed = client.post(base+'/publication-preview',json={'link_id':'link','replace_existing':True},headers=HEADERS).json()
    assert reviewed['can_publish'] and reviewed['existing_receipt']
    payload = {'command_id':'http-replace','link_id':'link','replace_existing':True,'reviewed':True,
               'expected_revision':reviewed['job_revision'],'expected_preview_sha256':reviewed['preview_sha256']}
    assert client.post(base+'/publish',json={**payload,'replace_existing':1},headers=HEADERS).status_code==422
    reply = client.post(base+'/publish',json=payload,headers=HEADERS)
    assert reply.status_code==200,reply.text
    result = reply.json()
    assert result['backup_receipt']==reviewed['existing_receipt']
    assert (queue[2]/result['backup']).read_bytes()==b'HTTP fictional original to retain'
    assert client.post(base+'/publish',json=payload,headers=HEADERS).json()==result
