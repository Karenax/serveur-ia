"""Project-scoped publication review, separate write policy and unchanged stores."""
import json

from fastapi import HTTPException
from pydantic import ValidationError
import pytest
from sqlalchemy import select

from backend.app.models import NetworkLink
from backend.app.project_document_job_models import DocumentJobArtifact, DocumentJob
from backend.app.project_document_publication_schemas import DocumentPublicationPreview, DocumentPublicationCommand
from backend.app.services import document_publications as publication, document_jobs as jobs
from backend.app.services import project_documents
from backend.app.project_document_schemas import DocumentPreview
from backend.app.project_document_job_schemas import DocumentBatchSubmit, DocumentBatchItem
from backend.app.services.document_file_access import FilePolicy
from backend.app.services.migration_guard import capture_baseline
from tests.test_project_document_jobs import queue as queue_fixture, install, enqueue
from tests.test_project_document_jobs import command
from tests.test_project_document_job_api import api as api_fixture, HEADERS, ROOT as API_ROOT

queue = queue_fixture
api = api_fixture


@pytest.fixture
def prepared(queue, monkeypatch):
    install(queue)
    job = enqueue(queue)
    jobs.run_one(queue[1], 'project', job['id'], storage_root=queue[3])
    monkeypatch.setenv('AGENT_DOCUMENT_WRITE_ROOTS', json.dumps([str(queue[2])]))
    with queue[1]() as db:
        artifact = db.scalar(select(DocumentJobArtifact))
        aid = artifact.id
    return queue, aid, DocumentPublicationPreview(link_id='link')


def review(prepared, **options):
    queue, aid, choice = prepared
    with queue[1]() as db:
        return publication.preview(db, 'project', aid, choice, storage_root=queue[3], **options)


def failure(code, action):
    with pytest.raises(HTTPException) as raised:
        action()
    assert raised.value.status_code == code


def test_actual_preview_binds_frozen_copy_directory_identity_and_link_without_write(prepared):
    queue, aid, choice = prepared
    before = capture_baseline(queue[4])
    files = {p.name:p.read_bytes() for p in queue[2].iterdir()}
    first = review(prepared)
    second = review(prepared)
    assert first == second and first['artifact_id'] == aid and first['job_revision'] == 3
    assert first['filename'] == 'AIRB26LTH0205-A-Demande de CE.docx'
    assert first['can_publish'] and not first['occupied'] and first['read_only']
    assert not first['network_published'] and first['directory_identity']
    assert first['destination'] == str(queue[2] / first['filename'])
    assert len(first['preview_sha256']) == 64 and len(first['write_policy_sha256']) == 64
    assert capture_baseline(queue[4]) == before
    assert files == {p.name:p.read_bytes() for p in queue[2].iterdir()}


def test_read_roots_do_not_enable_writes(prepared, monkeypatch):
    monkeypatch.delenv('AGENT_DOCUMENT_WRITE_ROOTS')
    assert publication.configured_write_policy().roots == ()
    failure(409, lambda:review(prepared))


def test_update_requires_the_exact_source_version_used_to_prepare_copy(queue, monkeypatch):
    from tests.test_document_publication_commands import publish
    install(queue)
    monkeypatch.setenv('AGENT_DOCUMENT_WRITE_ROOTS', json.dumps([str(queue[2])]))
    target = queue[2] / 'AIRB26LTH0205-A-Demande de CE.docx'
    original = (queue[2] / 'ce.docx').read_bytes()
    target.write_bytes(original)
    with queue[1]() as db:
        db.add(NetworkLink(project_id='project', code='demande_ce', libelle='Demande de CE'))
        db.commit()
        choice = DocumentPreview(document_id='ce_request', link_id='link', relative_path=target.name)
        report = project_documents.preview(db, 'project', choice)
        item = DocumentBatchItem(**choice.model_dump(), expected_source_sha256=report['source_sha256'],
            expected_link_sha256=report['link_sha256'], expected_values_sha256=report['values_sha256'],
            expected_identity_revision=report['field_values']['identity_revision'],
            expected_planning_revision=report['field_values']['planning_revision'])
        job = jobs.submit(db, 'project', DocumentBatchSubmit(command_id='refresh-ce', items=[item]))
        db.commit()
    jobs.run_one(queue[1], 'project', job['id'], storage_root=queue[3])
    with queue[1]() as db:
        generated = jobs.detail(db, 'project', job['id'])['items'][0]
        suggestion = generated['publication_suggestion']
        assert suggestion == {'link_id': 'link', 'relative_directory': '', 'replace_existing': True}
    chosen = queue, generated['artifact_id'], DocumentPublicationPreview(**suggestion)
    target.write_bytes(b'Edited after copy was prepared')
    blocked = review(chosen)
    assert not blocked['can_publish'] and 'source_changed' in blocked['blockers']
    target.write_bytes(original)
    reviewed = review(chosen)
    if not reviewed['can_publish']:  # Non-Windows cannot replace an existing original.
        assert reviewed['blockers'] == ['replacement_not_supported']
        return
    result = publish(chosen, DocumentPublicationCommand(**suggestion, command_id='publish-ce',
        expected_revision=reviewed['job_revision'], expected_preview_sha256=reviewed['preview_sha256'],
        reviewed=True, link_to_project=True))
    assert (target.parent / result['backup']).read_bytes() == original
    with queue[1]() as db:
        links = list(db.scalars(select(NetworkLink).filter_by(project_id='project', code='demande_ce')))
        assert len(links) == 1 and links[0].chemin == str(target)


def test_scope_precedes_write_configuration_and_every_filesystem_probe(prepared, monkeypatch):
    queue, aid, choice = prepared
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', '["foreign"]')
    monkeypatch.setattr(publication, 'configured_write_policy', lambda:pytest.fail('No policy before scope'))
    monkeypatch.setattr(publication, 'AnchoredDirectory', lambda *args:pytest.fail('No IO before scope'))
    with queue[1]() as db:
        failure(404, lambda:publication.preview(db, 'project', aid, choice, storage_root=queue[3]))


def test_foreign_link_or_artifact_is_not_resolved(prepared, monkeypatch):
    queue, aid, choice = prepared
    monkeypatch.setattr(publication, 'AnchoredDirectory', lambda *args:pytest.fail('Foreign link must not probe IO'))
    with queue[1]() as db:
        failure(404, lambda:publication.preview(db, 'project', aid, DocumentPublicationPreview(link_id='foreign-link'), storage_root=queue[3]))
        failure(404, lambda:publication.preview(db, 'foreign', aid, choice, storage_root=queue[3]))


def test_reader_and_imported_history_can_review_but_cannot_publish(prepared, monkeypatch):
    queue, aid, choice = prepared
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    value = review(prepared)
    assert not value['can_publish'] and value['blockers'] == ['read_only']
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'owner')
    with queue[1]() as db:
        db.scalar(select(DocumentJob)).execution_blocked = True
        db.commit()
    value = review(prepared)
    assert not value['can_publish'] and value['blockers'] == ['execution_blocked']


def test_collision_and_missing_folder_preserve_every_existing_byte(prepared):
    queue, aid, choice = prepared
    target = queue[2] / 'AIRB26LTH0205-A-Demande de CE.docx'
    target.write_bytes(b'Original business file')
    value = review(prepared)
    assert value['occupied'] and not value['can_publish'] and value['blockers'] == ['destination_occupied']
    assert target.read_bytes() == b'Original business file'
    with queue[1]() as db:
        failure(409, lambda:publication.preview(db, 'project', aid,
            DocumentPublicationPreview(link_id='link',relative_directory='missing'), storage_root=queue[3]))
    assert not (queue[2] / 'missing').exists()


def test_changed_directory_link_and_write_policy_change_review_fingerprint(prepared):
    queue, aid, choice = prepared
    original = review(prepared)
    second = queue[2] / 'second'
    second.mkdir()
    with queue[1]() as db:
        db.get(NetworkLink, 'link').chemin = str(second)
        db.commit()
    changed = review(prepared)
    assert changed['link_sha256'] != original['link_sha256']
    assert changed['directory_identity'] != original['directory_identity']
    assert changed['preview_sha256'] != original['preview_sha256']
    broader = review(prepared, policy=FilePolicy((str(queue[2].parent),)))
    assert broader['preview_sha256'] != changed['preview_sha256']


@pytest.mark.parametrize('relative', ['../foreign',r'..\foreign',r'C:\other','/other', 'dir:stream'])
def test_unsafe_relative_directory_is_rejected_before_open(prepared, relative, monkeypatch):
    queue, aid, _ = prepared
    monkeypatch.setattr(publication,'AnchoredDirectory',lambda *args:pytest.fail('Unsafe destination must not open'))
    with queue[1]() as db:
        failure(422,lambda:publication.preview(db,'project',aid,
            DocumentPublicationPreview(link_id='link',relative_directory=relative),storage_root=queue[3]))


@pytest.mark.parametrize('roots', ['{}','["relative"]','invalid'])
def test_invalid_write_configuration_is_reported(prepared, monkeypatch, roots):
    monkeypatch.setenv('AGENT_DOCUMENT_WRITE_ROOTS', roots)
    failure(409,lambda:review(prepared))


def test_outside_write_root_is_rejected_without_probe(prepared, tmp_path, monkeypatch):
    monkeypatch.setattr(publication,'AnchoredDirectory',lambda *args:pytest.fail('Outside root must not probe'))
    failure(403,lambda:review(prepared,policy=FilePolicy((str(tmp_path/'other'),))))


def test_tampered_managed_copy_cannot_get_a_destination_review(prepared):
    queue, _, _ = prepared
    next(queue[3].iterdir()).write_bytes(b'corrupt')
    failure(409,lambda:review(prepared))


def test_strict_publication_commands_have_no_output_name_root_actor_or_finance():
    valid = {'command_id':'publish-1','link_id':'link','expected_revision':3,
             'expected_preview_sha256':'a'*64,'reviewed':True}
    assert DocumentPublicationCommand.model_validate(valid).relative_directory == ''
    for key,value in [('filename','other.docx'),('root','V:/'),('actor_id','forged'),('price',42),
                      ('reviewed',False),('reviewed',1),('reviewed','true'),('expected_revision',True)]:
        with pytest.raises(ValidationError):
            DocumentPublicationCommand.model_validate({**valid,key:value})


def test_http_destination_preview_reader_scope_and_strict_body(api, monkeypatch):
    client, queue, _, _ = api
    reply = client.post(API_ROOT+'/jobs',json=command(queue).model_dump(),headers=HEADERS)
    assert reply.status_code == 200
    done = jobs.run_one(queue[1],'project',reply.json()['id'],storage_root=queue[3])
    aid = done['items'][0]['artifact_id']
    monkeypatch.setenv('AGENT_DOCUMENT_WRITE_ROOTS',json.dumps([str(queue[2])]))
    path = API_ROOT+'/artifacts/'+aid+'/publication-preview'
    before = capture_baseline(queue[4])
    owner = client.post(path,json={'link_id':'link'},headers=HEADERS)
    assert owner.status_code == 200 and owner.json()['can_publish']
    assert owner.json()['publication_command_available']
    assert client.post(path,json={'link_id':'link','filename':'forged.docx'},headers=HEADERS).status_code == 422
    assert client.post(path,json={'link_id':'link'}).status_code == 403
    assert client.post(path,json={'link_id':'link'},headers={**HEADERS,'Origin':'http://foreign.invalid'}).status_code == 403
    monkeypatch.setenv('AGENT_OPERATOR_ROLE','reader')
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS','["project"]')
    reader = client.post(path,json={'link_id':'link'},headers=HEADERS)
    assert reader.status_code == 200 and reader.json()['blockers'] == ['read_only']
    assert client.post(path.replace('/project/','/foreign/'),json={'link_id':'link'},headers=HEADERS).status_code == 404
    assert capture_baseline(queue[4]) == before


def test_http_preview_requires_explicit_write_roots_even_with_running_worker(api, monkeypatch):
    client, queue, _, _ = api
    reply = client.post(API_ROOT+'/jobs',json=command(queue).model_dump(),headers=HEADERS)
    done = jobs.run_one(queue[1],'project',reply.json()['id'],storage_root=queue[3])
    monkeypatch.delenv('AGENT_DOCUMENT_WRITE_ROOTS',raising=False)
    path = API_ROOT+'/artifacts/'+done['items'][0]['artifact_id']+'/publication-preview'
    response = client.post(path,json={'link_id':'link'},headers=HEADERS)
    assert response.status_code == 409 and 'racines d’écriture' in response.json()['detail']
