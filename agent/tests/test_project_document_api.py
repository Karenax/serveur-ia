"""Real guarded HTTP, temporary files and metadata changes during Office copy."""
import hashlib
from io import BytesIO
import json
import zipfile

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.security import local_guard
from backend.app.db import Base, get_db
from backend.app.models import NetworkLink, Project
from backend.app.project_identity_models import IDENTITY_TABLES, ProjectPerson, ProjectProfile, ProjectReference
from backend.app.project_planning_models import ProjectPlanningState
from backend.app.routers import project_documents as http
from backend.app.services import project_documents as service
from backend.app.services.document_package_preview import preview_package
from backend.app.services.migration_guard import capture_baseline
from tests.test_project_document_packages import package, parts_for


@pytest.fixture
def api(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "documents.db"}')
    Base.metadata.create_all(engine, tables=[Project.__table__, NetworkLink.__table__,
                                           *IDENTITY_TABLES, ProjectPlanningState.__table__])
    factory = sessionmaker(bind=engine)
    folder = tmp_path / 'authorized'
    folder.mkdir()
    source = folder / 'demande.docx'
    source.write_bytes(package(parts_for('ce_request')))
    with factory() as db:
        project, other = Project(code='AIRB26LTH0205-A', title='LED 2026'), Project(code='OTHER', title='Autre')
        person = ProjectPerson(first_name='Élodie', last_name='Durand', email='test@example.invalid')
        client = ProjectReference(kind='client', code='CLIENT', normalized_code='client', label='Client actuel')
        db.add_all([project, other, person, client])
        db.flush()
        links = [NetworkLink(project_id=p.id, code='affaire', libelle='Dossier', chemin=str(folder), ordre=i)
                 for i, p in enumerate((project, other))]
        db.add_all([*links, ProjectProfile(project_id=project.id, responsible_id=person.id, client_id=client.id, revision=2),
                    ProjectPlanningState(project_id=project.id, revision=4, excluded_dates=[])])
        db.commit()
        ids = {'project': project.id, 'other': other.id, 'link': links[0].id, 'other_link': links[1].id,
               'person': person.id, 'client': client.id}
    monkeypatch.setenv('AGENT_DOCUMENT_ROOTS', json.dumps([str(folder)]))
    monkeypatch.delenv('AGENT_DOCUMENT_DRIVE_MAPPINGS', raising=False)
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'editor')
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', json.dumps([ids['project']]))
    application = FastAPI()
    application.middleware('http')(local_guard)
    application.include_router(http.router)
    def dependency():
        with factory() as db:
            yield db
    application.dependency_overrides[get_db] = dependency
    with TestClient(application, base_url='http://127.0.0.1') as client:
        yield client, f'/api/v1/projects/{ids["project"]}/documents', factory, ids, source
    engine.dispose()


def choice(api, **changes):
    return {'document_id': 'ce_request', 'link_id': api[3]['link'], 'relative_path': 'demande.docx', **changes}


def approved(api, **changes):
    selected = choice(api, **changes)
    response = api[0].post(api[1] + '/preview', json=selected)
    assert response.status_code == 200, response.text
    report = response.json()
    return {**selected, 'expected_source_sha256': report['source_sha256'], 'expected_link_sha256': report['link_sha256'],
            'expected_values_sha256': report['values_sha256'],
            'expected_identity_revision': report['field_values']['identity_revision'],
            'expected_planning_revision': report['field_values']['planning_revision']}, report


def test_workspace_pagination_sourcing_configuration_and_no_implicit_rows(api, monkeypatch):
    client, root, factory, ids, source = api
    baseline = capture_baseline(factory.kw['bind'].url.database)
    original = source.read_bytes()
    monkeypatch.setattr(service, 'acquire_file', lambda *a, **k: pytest.fail('Workspace probes files'))
    result = client.get(root + '?limit=1').json()
    assert result['links']['total'] == 1 and result['links']['items'][0]['id'] == ids['link']
    assert len(result['templates']) == 8 and result['values']['project_code'] == 'AIRB26LTH0205-A'
    assert result['origins']['client_name']['record_id'] == ids['client']
    assert result['identity_revision'] == 2 and result['planning_revision'] == 4
    assert result['file_access']['status'] == 'configured' and result['can_prepare_copy']
    assert result['publication'] == 'explicit_separate_command' and not result['batch_available']
    assert client.get(root + '?offset=1&limit=1').json()['links']['items'] == []
    for query in ('?limit=201', '?limit=0', '?offset=-1'):
        assert client.get(root + query).status_code == 422
    monkeypatch.setenv('AGENT_DOCUMENT_ROOTS', '[]')
    assert client.get(root).json()['file_access']['status'] == 'disabled'
    monkeypatch.setenv('AGENT_DOCUMENT_ROOTS', 'invalid JSON')
    assert client.get(root).json()['file_access']['status'] == 'invalid'
    assert capture_baseline(factory.kw['bind'].url.database) == baseline and source.read_bytes() == original


def test_guarded_preview_and_copy_download_preserve_source_and_database(api):
    client, root, factory, _, source = api
    baseline, original = capture_baseline(factory.kw['bind'].url.database), source.read_bytes()
    command, preview = approved(api)
    assert preview['can_prepare'] and preview['output_filename'] == 'AIRB26LTH0205-A-Demande de CE.docx'
    response = client.post(root + '/prepare-copy', json=command)
    assert response.status_code == 200, response.text
    assert response.headers['content-type'] == 'application/octet-stream'
    assert response.headers['content-disposition'].startswith("attachment; filename*=UTF-8''AIRB26LTH0205-A-")
    assert response.headers['etag'] == '"' + hashlib.sha256(response.content).hexdigest() + '"'
    assert response.headers['x-agent-source-sha256'] == command['expected_source_sha256']
    assert response.headers['x-agent-values-sha256'] == command['expected_values_sha256']
    assert response.headers['x-agent-network-published'] == 'false'
    assert response.headers['cache-control'] == 'private, no-store'
    result = preview_package(response.content, 'ce_request', preview['field_values']['values'])
    assert all(t['existing_value'] == 'AIRB26LTH0205-A' for t in result['targets'])
    with zipfile.ZipFile(BytesIO(original)) as before, zipfile.ZipFile(BytesIO(response.content)) as after:
        for name in before.namelist():
            if name != 'word/document.xml':
                assert before.read(name) == after.read(name)
    assert capture_baseline(factory.kw['bind'].url.database) == baseline and source.read_bytes() == original
    assert list(source.parent.iterdir()) == [source]


def test_reader_preview_allowed_but_copy_denied_even_with_forged_role(api, monkeypatch):
    client, root, *_ = api
    command, _ = approved(api)
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    assert not client.get(root).json()['can_prepare_copy']
    preview = client.post(root + '/preview', json=choice(api))
    assert preview.status_code == 200 and not preview.json()['can_prepare_copy']
    denied = client.post(root + '/prepare-copy', json={**command, 'role': 'owner'}, headers={'X-Operator-Role': 'owner'})
    assert denied.status_code == 403
    assert client.post(root + '/preview/extra', json=choice(api)).status_code == 403


def test_foreign_scope_and_link_are_checked_before_any_file_probe(api, monkeypatch):
    client, root, _, ids, _ = api
    from backend.app.services import document_file_access as files
    def forbidden(*args, **kwargs):
        pytest.fail('File configuration/probe before authorization')
    monkeypatch.setattr(files, 'configured_policy', forbidden)
    foreign = root.replace(ids['project'], ids['other'])
    assert client.post(foreign + '/preview', json=choice(api, link_id=ids['other_link'])).status_code == 404
    assert client.get(foreign).status_code == 404
    assert client.post(root + '/preview', json=choice(api, link_id=ids['other_link'])).status_code == 404


@pytest.mark.parametrize('changes', [{'document_id': 'unknown'}, {'actor_id': 'forged'}, {'roots': ['C:\\']},
    {'overrides': {'hourly_rate': '42'}}, {'overrides': {'project_code': 'FORGED'}}, {'overrides': {'today': '2020'}},
    {'overrides': {'client_name': 123}}, {'overrides': {'description': '\x01'}}, {'relative_path': '../outside.docx'}])
def test_invalid_or_financial_commands_refused(api, changes):
    client, root, factory, _, source = api
    before, original = capture_baseline(factory.kw['bind'].url.database), source.read_bytes()
    assert client.post(root + '/preview', json=choice(api, **changes)).status_code == 422
    assert capture_baseline(factory.kw['bind'].url.database) == before and source.read_bytes() == original


@pytest.mark.parametrize('field', ['source', 'person', 'client', 'project', 'identity', 'planning', 'overrides', 'link'])
def test_stale_preview_cannot_prepare_even_if_project_revision_unchanged(api, field):
    client, root, factory, ids, source = api
    command, _ = approved(api)
    if field == 'source':
        source.write_bytes(package(parts_for('ce_request', extra={'new.xml': '<added/>'})))
    elif field == 'overrides':
        command['overrides'] = {'client_name': 'Correction tardive'}
    else:
        with factory() as db:
            if field == 'person':
                db.get(ProjectPerson, ids['person']).email = 'changed@example.invalid'
            elif field == 'client':
                db.get(ProjectReference, ids['client']).label = 'Client modifié'
            elif field == 'project':
                db.get(Project, ids['project']).code = 'NEW-0205'
            elif field == 'identity':
                db.get(ProjectProfile, ids['project']).revision += 1
            elif field == 'link':
                db.get(NetworkLink, ids['link']).chemin = str(source)
            else:
                db.get(ProjectPlanningState, ids['project']).revision += 1
            db.commit()
    baseline, original = capture_baseline(factory.kw['bind'].url.database), source.read_bytes()
    response = client.post(root + '/prepare-copy', json=command)
    assert response.status_code == 409, response.text
    assert capture_baseline(factory.kw['bind'].url.database) == baseline and source.read_bytes() == original


@pytest.mark.parametrize('operation', ['preview', 'prepare'])
@pytest.mark.parametrize('change', ['person', 'link', 'removed_link'])
def test_fresh_connection_detects_contact_or_link_change_during_acquisition_or_preparation(api, monkeypatch, operation, change):
    client, root, factory, ids, _ = api
    command, _ = approved(api)
    function = 'acquire_file' if operation == 'preview' else 'prepare_package'
    original = getattr(service, function)
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        with factory() as db:
            if change == 'person':
                db.get(ProjectPerson, ids['person']).email = 'changed-during-copy@example.invalid'
            elif change == 'link':
                db.get(NetworkLink, ids['link']).chemin = 'V:\\modified'
            else:
                db.delete(db.get(NetworkLink, ids['link']))  # Fictional temporary fixture only.
            db.commit()
        return result
    monkeypatch.setattr(service, function, changed)
    response = client.post(root + ('/preview' if operation == 'preview' else '/prepare-copy'),
                           json=choice(api) if operation == 'preview' else command)
    assert response.status_code == 409, response.text


def test_corrected_copy_is_document_only_and_literal_macros_preserved(api):
    client, root, factory, ids, source = api
    macro = source.with_name('notice.docm')
    macro.write_bytes(package(parts_for('user_manual')))
    baseline = capture_baseline(factory.kw['bind'].url.database)
    command, report = approved(api, document_id='user_manual', relative_path='notice.docm',
                               overrides={'description': '=HYPERLINK("literal") Élodie'})
    assert report['field_values']['origins']['description']['kind'] == 'document_override'
    result = client.post(root + '/prepare-copy', json=command)
    assert result.status_code == 200
    report = preview_package(result.content, 'user_manual', report['field_values']['values'])
    assert report['targets'][0]['existing_value'] == '=HYPERLINK("literal") Élodie'
    with zipfile.ZipFile(BytesIO(macro.read_bytes())) as original, zipfile.ZipFile(BytesIO(result.content)) as copy:
        assert original.read('word/vbaProject.bin') == copy.read('word/vbaProject.bin')
    assert capture_baseline(factory.kw['bind'].url.database) == baseline
    with factory() as db:
        assert db.get(Project, ids['project']).title == 'LED 2026'


def test_blocked_or_incompatible_template_and_invalid_output_filename(api):
    client, root, factory, ids, source = api
    assert client.post(root + '/preview', json=choice(api, document_id='tdao')).status_code == 422
    source.write_bytes(package(parts_for('ce_request', extra={'word/settings.xml':
        '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:documentProtection/></w:settings>'})))
    command, report = approved(api)
    assert not report['can_prepare'] and 'document_protected' in report['blockers']
    assert client.post(root + '/prepare-copy', json=command).status_code == 422
    source.write_bytes(package(parts_for('ce_request')))
    with factory() as db:
        db.get(Project, ids['project']).code = 'C:/unsafe'
        db.commit()
    command, report = approved(api)
    assert not report['can_prepare'] and 'output_filename_invalid' in report['blockers']
    assert client.post(root + '/prepare-copy', json=command).status_code == 422


def test_mutating_commands_still_require_local_session_token(api, monkeypatch):
    from app.security import SESSION_TOKEN
    client, root, *_ = api
    monkeypatch.delenv('AGENT_TESTING')
    assert client.post(root + '/preview', json=choice(api)).status_code == 403
    assert client.post(root + '/preview', json=choice(api), headers={'X-Agent-Token': SESSION_TOKEN}).status_code == 200
    assert client.post(root + '/preview', json=choice(api), headers={'X-Agent-Token': SESSION_TOKEN,
                       'Origin': 'https://foreign.invalid'}).status_code == 403


def test_document_routes_registered_before_html_fallback():
    from app.main import app
    paths = app.openapi()['paths']
    root = '/api/v1/projects/{project_id}/documents'
    assert 'get' in paths[root] and 'post' in paths[root + '/preview'] and 'post' in paths[root + '/prepare-copy']
