"""Actual guarded note HTTP commands, persistence, scope and lost responses."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.security import local_guard, session
from backend.app.db import get_db
from backend.app.routers.project_notes import router
from backend.app.services.migration_guard import capture_baseline
from tests import test_project_notes_core as core

store = core.store
install = core.install
command = core.command


@pytest.fixture
def api(store):
    _, factory, ids, path = store
    app = FastAPI()
    app.middleware('http')(local_guard)
    app.get('/api/v1/session')(session)
    app.include_router(router)
    def dependency():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = dependency
    with TestClient(app, base_url='http://127.0.0.1:8001') as client:
        yield client, '/api/v1/projects/' + ids[0] + '/notes', ids, path


def create(client, root):
    body = {'command_id': command(), 'title': 'Compte rendu', 'content': {'blocks': [
        {'type': 'paragraph', 'runs': [{'text': 'Texte vérifié', 'marks': ['bold']}]}]}}
    response = client.post(root, json=body)
    assert response.status_code == 201, response.text
    return response.json(), body


def test_dormant_reads_and_rejected_write_have_no_side_effect(api):
    client, root, _, path = api
    before = capture_baseline(path)
    assert client.get(root).json()['available'] is False
    assert client.post(root, json={'command_id': command(), 'title': 'Brouillon'}).status_code == 409
    assert capture_baseline(path) == before


def test_http_create_retry_history_selected_version_restore_and_stale_rollback(api, store):
    install(store)
    client, root, _, path = api
    first, body = create(client, root)
    url = root + '/' + first['note']['id']
    retry = client.post(root, json=body)
    assert retry.status_code == 201 and retry.json()['replayed']
    assert client.get(root).json()['total'] == 1
    assert client.get(root).json()['can_edit'] is True
    assert client.get(root).json()['operator_id'] == 'local'
    saved = {'command_id': command(), 'expected_revision': 1, 'title': 'Révisée', 'content': {'blocks': []}}
    assert client.put(url, json=saved).json()['note']['revision'] == 2
    before = capture_baseline(path)
    for _ in range(2):
        replay = client.put(url, json=saved)
        assert replay.status_code == 200 and replay.json()['command_revision'] == 2 and replay.json()['replayed']
    assert client.put(url, json={**saved, 'command_id': command(), 'title': 'Saisie locale conservée'}).status_code == 409
    assert capture_baseline(path) == before
    history = client.get(url + '/history?limit=1').json()
    assert history['total'] == 2 and history['items'][0]['revision'] == 2 and 'value' not in history['items'][0]
    version = client.get(url + '/versions/' + first['command_version_id'])
    assert version.status_code == 200 and version.json()['value']['plain_text'] == 'Texte vérifié'
    restored = client.post(url + '/restore', json={'command_id': command(), 'expected_revision': 2,
                                                  'version_id': first['command_version_id']})
    assert restored.status_code == 200 and restored.json()['note']['revision'] == 3
    assert client.get(url).json()['plain_text'] == 'Texte vérifié'
    assert client.get(url + '/history?limit=1&offset=3').json()['items'] == []


def test_foreign_project_and_reader_cannot_edit_or_reveal_notes(api, store, monkeypatch):
    install(store)
    client, root, ids, path = api
    first, body = create(client, root)
    before = capture_baseline(path)
    foreign = root.replace(ids[0], ids[1]) + '/' + first['note']['id']
    assert client.get(foreign).status_code == 404
    assert client.get(foreign + '/versions/' + first['command_version_id']).status_code == 404
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    assert client.get(root).status_code == 200
    assert client.get(root).json()['can_edit'] is False
    assert client.post(root, json=body).status_code == 403
    assert client.put(root + '/' + first['note']['id'], json={'command_id': command(), 'expected_revision': 1, 'title': 'Tentative'}).status_code == 403
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'editor')
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', '["' + ids[1] + '"]')
    assert client.get(root).status_code == 404
    assert capture_baseline(path) == before


@pytest.mark.parametrize('extra', [{'actor_id': 'forged'}, {'role': 'owner'}, {'content_html': '<script/>'}, {'expected_revision': True}])
def test_http_closed_commands_reject_identity_html_and_boolean_revision(api, store, extra):
    install(store)
    client, root, _, path = api
    first, _ = create(client, root)
    before = capture_baseline(path)
    assert client.put(root + '/' + first['note']['id'], json={
        'command_id': command(), 'expected_revision': 1, 'title': 'Texte', **extra}).status_code == 422
    assert capture_baseline(path) == before


def test_actual_host_origin_and_session_protection(api, store, monkeypatch):
    install(store)
    client, root, _, path = api
    monkeypatch.setenv('AGENT_TESTING', '0')
    before = capture_baseline(path)
    body = {'command_id': command(), 'title': 'Protégée'}
    assert client.post(root, json=body).status_code == 403
    token = client.get('/api/v1/session').json()['token']
    assert client.post(root, json=body, headers={'x-agent-token': token, 'origin': 'https://foreign.example'}).status_code == 403
    assert client.get(root, headers={'host': 'foreign.example'}).status_code == 400
    assert capture_baseline(path) == before
    allowed = client.post(root, json=body, headers={'x-agent-token': token, 'origin': 'http://127.0.0.1:8001'})
    assert allowed.status_code == 201
