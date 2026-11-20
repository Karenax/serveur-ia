"""Guarded saved forms/settings, real transactions and effective file discovery."""
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event

from app.security import local_guard, SESSION_TOKEN
from backend.app.db import get_db
from backend.app.models import NetworkLink
from backend.app.personal_document_models import PersonalDocumentSearchVersion
from backend.app.routers import project_documents as http
from backend.app.services.migration_guard import capture_baseline
from backend.app.services import document_forms as forms
from tests.test_project_document_forms import store, install
from tests.test_project_document_packages import package, parts_for

__all__ = ['store']


@pytest.fixture
def api(store, monkeypatch):
    _, factory, ids, path = store
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'owner')
    monkeypatch.delenv('AGENT_OPERATOR_PROJECT_IDS', raising=False)
    app = FastAPI()
    app.middleware('http')(local_guard)
    app.include_router(http.router)
    app.include_router(http.settings_router)
    def dependency():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = dependency
    with TestClient(app, base_url='http://127.0.0.1', raise_server_exceptions=False) as client:
        yield client, '/api/v1/projects/' + ids[0] + '/documents', ids, path


def test_dormant_reads_do_not_install_or_seed_and_writes_refused(api):
    client, root, _, path = api
    before = capture_baseline(path)
    for url in (root + '/forms/tdao', '/api/v1/document-settings'):
        result = client.get(url)
        assert result.status_code == 200 and result.json()['available'] is False
        assert result.json()['revision'] == 0
        assert client.get(url + '/history').json()['total'] == 0
    assert client.put(root + '/forms/tdao', json={'expected_revision': 0}).status_code == 409
    assert capture_baseline(path) == before


def test_saved_form_pagination_restore_and_stale_write_rollback(api, store):
    install(store)
    client, root, ids, path = api
    url = root + '/forms/tdao'
    versions = []
    for revision in range(3):
        response = client.put(url, json={'expected_revision': revision, 'link_id': ids[3],
                            'relative_path': 'Etudes/TDAO.xlsx', 'overrides': {'description': str(revision)}})
        assert response.status_code == 200, response.text
        versions.append(response.json()['version_id'])
    saved = client.get(url).json()
    assert saved['revision'] == 3 and saved['selected_link']['id'] == ids[3]
    assert saved['selected_link']['code'] == 'same'
    pages = [client.get(url + f'/history?offset={offset}&limit=1').json() for offset in range(4)]
    assert all(page['total'] == 3 for page in pages)
    assert [p['items'][0]['revision'] for p in pages[:3]] == [3, 2, 1] and pages[3]['items'] == []
    assert pages[0]['items'][0]['created_at'].endswith('+00:00')
    before = capture_baseline(path)
    assert client.put(url, json={'expected_revision': 2, 'overrides': {'description': 'lost'}}).status_code == 409
    assert client.post(url + '/restore', json={'expected_revision': 3, 'version_id': 'foreign'}).status_code == 404
    assert capture_baseline(path) == before
    restored = client.post(url + '/restore', json={'expected_revision': 3, 'version_id': versions[0]})
    assert restored.status_code == 200 and restored.json()['revision'] == 4
    assert restored.json()['overrides'] == {'description': '0'}
    assert client.get(url + '/history').json()['items'][0]['value']['restored_from'] == versions[0]


@pytest.mark.parametrize('role,scope,write_code', [('reader', True, 403), ('editor', True, 200), ('owner', True, 200), ('editor', False, 200)])
def test_project_policy_and_global_settings_administration(api, store, monkeypatch, role, scope, write_code):
    install(store)
    client, root, ids, _ = api
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', role)
    if scope:
        monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', json.dumps([ids[0]]))
    assert client.get(root + '/forms/tdao').status_code == 200
    assert client.put(root + '/forms/tdao', json={'expected_revision': 0}, headers={'X-Operator-Role': 'owner'}).status_code == write_code
    if scope:
        assert client.get(root.replace(ids[0], ids[1]) + '/forms/tdao').status_code == 404
    preferences = client.get('/api/v1/document-settings')
    assert preferences.status_code == 200 and preferences.json()['can_edit'] is False
    assert len(preferences.json()['items']) == 8
    for method, url, body in (('get', '/api/v1/document-settings/history', None),
                            ('put', '/api/v1/document-settings', {}),
                            ('post', '/api/v1/document-settings/restore', {})):
        assert getattr(client, method)(url, **({'json': body} if body is not None else {})).status_code == 403


@pytest.mark.parametrize('changes', [{'expected_revision': True}, {'actor_id': 'forged'}, {'roots': ['V:/']},
                                   {'role': 'owner'}, {'overrides': {'hourly_rate': '12'}}, {'relative_path': '../elsewhere.xlsx'}])
def test_invalid_saved_commands_cannot_change_database(api, store, changes):
    install(store)
    client, root, ids, path = api
    before = capture_baseline(path)
    response = client.put(root + '/forms/tdao', json={'expected_revision': 0, 'link_id': ids[2], **changes})
    assert response.status_code == 422
    assert capture_baseline(path) == before


def test_settings_have_independent_versions_pagination_and_restore(api, store):
    install(store)
    client, root, _, path = api
    url = '/api/v1/document-settings'
    initial = client.get(url).json()
    first = client.put(url, json={'expected_revision': 0, 'items': initial['items']}).json()
    changed = initial['items']
    changed[0]['label'] = 'Libellé commun personnalisé'
    second = client.put(url, json={'expected_revision': 1, 'items': changed})
    assert second.status_code == 200 and second.json()['revision'] == 2
    page = client.get(url + '/history?offset=1&limit=1').json()
    assert page['total'] == 2 and page['items'][0]['id'] == first['version_id']
    before = capture_baseline(path)
    assert client.put(url, json={'expected_revision': 0, 'items': changed}).status_code == 409
    assert capture_baseline(path) == before
    restored = client.post(url + '/restore', json={'expected_revision': 2, 'version_id': first['version_id']})
    assert restored.status_code == 200 and restored.json()['revision'] == 3
    assert restored.json()['items'][0]['label'] == first['items'][0]['label']
    assert client.get(root + '/forms/tdao').json()['revision'] == 0


def test_effective_rules_labels_order_and_inactive_search_use_saved_preferences(api, store, monkeypatch, tmp_path):
    install(store)
    client, root, ids, _ = api
    folder = tmp_path / 'authorized'
    folder.mkdir()
    source = folder / 'Custom template.docx'
    source.write_bytes(package(parts_for('ce_request')))
    original = source.read_bytes()
    with store[1]() as db:
        db.get(NetworkLink, ids[2]).chemin = str(folder)
        db.commit()
    monkeypatch.setenv('AGENT_DOCUMENT_ROOTS', json.dumps([str(folder)]))
    items = forms.default_preferences()
    ce = next(row for row in items if row['document_id'] == 'ce_request')
    ce.update(label='Ma demande', order=0, relative_paths=['.'], filename_patterns=['Custom template'])
    saved = client.put('/api/v1/document-settings', json={'expected_revision': 0, 'items': items}).json()
    workspace = client.get(root).json()
    assert workspace['templates'][0]['id'] == 'ce_request' and workspace['templates'][0]['label'] == 'Ma demande'
    assert workspace['search_preferences']['revision'] == 1
    result = client.post(root + '/discover', json={'document_id': 'ce_request', 'link_id': ids[2]})
    assert result.status_code == 200, result.text
    assert result.json()['preferences_version_id'] == saved['version_id']
    assert [row['filename'] for row in result.json()['candidates']] == ['Custom template.docx']
    ce['active'] = False
    assert client.put('/api/v1/document-settings', json={'expected_revision': 1, 'items': items}).status_code == 200
    assert client.post(root + '/discover', json={'document_id': 'ce_request', 'link_id': ids[2]}).status_code == 409
    assert client.get(root + '/forms/ce_request').status_code == 200 and source.read_bytes() == original


def test_personal_rules_drive_discovery_and_isolate_versions(api, store, monkeypatch, tmp_path):
    install(store)
    PersonalDocumentSearchVersion.__table__.create(store[0])
    client, root, ids, _ = api
    folder = tmp_path / 'authorized'
    folder.mkdir()
    raw = package(parts_for('ce_request'))
    for name in ('Alpha.docx', 'Beta.docx'):
        (folder / name).write_bytes(raw)
    with store[1]() as db:
        db.get(NetworkLink, ids[2]).chemin = str(folder)
        db.commit()
    monkeypatch.setenv('AGENT_DOCUMENT_ROOTS', json.dumps([str(folder)]))
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', json.dumps([ids[0]]))
    url = '/api/v1/document-settings/personal'
    results = {}
    for actor, name in [('alpha', 'Alpha'), ('beta', 'Beta')]:
        monkeypatch.setenv('AGENT_OPERATOR_ID', actor)
        state = client.get(url).json()
        assert state['revision'] == 0 and state['can_edit'] is True
        rule = next(row for row in state['items'] if row['document_id'] == 'ce_request')
        rule.update(relative_paths=['.'], filename_patterns=[name], active=True)
        saved = client.put(url, json={'expected_revision': 0, 'items': state['items']})
        assert saved.status_code == 200, saved.text
        results[actor] = saved.json()['version_id']
        assert client.put(url, json={'expected_revision': 0, 'items': state['items']}).status_code == 409
    for actor, name, other in [('alpha', 'Alpha', 'beta'), ('beta', 'Beta', 'alpha')]:
        monkeypatch.setenv('AGENT_OPERATOR_ID', actor)
        search = client.post(root + '/discover', json={'document_id': 'ce_request', 'link_id': ids[2]})
        assert search.status_code == 200, search.text
        assert search.json()['preferences_version_id'] == results[actor]
        assert [item['filename'] for item in search.json()['candidates']] == [name + '.docx']
        history = client.get(url + '/history').json()
        assert [row['id'] for row in history['items']] == [results[actor]]
        assert client.post(url + '/restore', json={'expected_revision': 1, 'version_id': results[other]}).status_code == 404
        assert client.get('/api/v1/document-settings').json()['revision'] == 0


def test_personal_criteria_can_be_saved_without_the_shared_document_editor(api, store):
    PersonalDocumentSearchVersion.__table__.create(store[0])
    client, _, _, _ = api
    url = '/api/v1/document-settings/personal'
    assert client.get('/api/v1/document-settings').json()['available'] is False
    state = client.get(url).json()
    assert state['available'] is True
    saved = client.put(url, json={'expected_revision': 0, 'items': state['items']})
    assert saved.status_code == 200 and saved.json()['revision'] == 1


def test_origin_csrf_foreign_link_and_write_failure_rollback(api, store, monkeypatch):
    install(store)
    client, root, ids, path = api
    monkeypatch.setenv('AGENT_TESTING', '0')
    url = root + '/forms/tdao'
    command = {'expected_revision': 0, 'link_id': ids[2]}
    assert client.put(url, json=command).status_code == 403
    assert client.put(url, json=command, headers={'X-Agent-Token': SESSION_TOKEN, 'Origin': 'https://foreign.invalid'}).status_code == 403
    headers = {'X-Agent-Token': SESSION_TOKEN}
    before = capture_baseline(path)
    assert client.put(url, json={**command, 'link_id': ids[4]}, headers=headers).status_code == 404
    assert capture_baseline(path) == before
    def failure(connection, cursor, statement, parameters, context, many):
        if statement.lstrip().upper().startswith('INSERT INTO PROJECT_DOCUMENT_DRAFT_VERSIONS'):
            raise RuntimeError('Fictitious disk failure')
    engine = store[0]
    event.listen(engine, 'before_cursor_execute', failure)
    try:
        assert client.put(url, json=command, headers=headers).status_code == 500
    finally:
        event.remove(engine, 'before_cursor_execute', failure)
    assert capture_baseline(path) == before
    assert client.put(url, json=command, headers=headers).status_code == 200


@pytest.mark.parametrize('suffix', ['?offset=-1', '?limit=201', '?limit=0'])
def test_history_pagination_is_bounded(api, store, suffix):
    install(store)
    client, root, *_ = api
    for url in (root + '/forms/tdao/history', '/api/v1/document-settings/history'):
        assert client.get(url + suffix).status_code == 422


def test_native_mono_server_serves_both_document_form_routers(store, monkeypatch):
    from app.main import app
    install(store)
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'owner')
    monkeypatch.delenv('AGENT_OPERATOR_PROJECT_IDS', raising=False)
    def dependency():
        with store[1]() as db:
            yield db
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = dependency
    try:
        # No lifespan: production workers and engines are not initialized.
        client = TestClient(app, base_url='http://127.0.0.1')
        response = client.put('/api/v1/document-settings', json={'expected_revision': 0, 'items': forms.default_preferences()})
        assert response.status_code == 200, response.text
        assert client.get('/api/v1/document-settings/history').json()['total'] == 1
        assert client.get('/api/v1/projects/' + store[2][0] + '/documents/forms/tdao').status_code == 200
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
