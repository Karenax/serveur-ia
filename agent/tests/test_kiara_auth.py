"""Kiara signatures bind each Agent request to a server-selected operator."""

from fastapi.testclient import TestClient
import uuid

from app.main import app
from kiara_shared.agent_auth import issue


def test_transcription_events_follow_the_current_erp_brain_link(monkeypatch):
    from app.db import SessionLocal as BrainSession
    from app.models import AuditLog, MeetingRecording, Project as BrainProject, Source
    from backend.app.db import SessionLocal as ErpSession
    from backend.app.models import BrainLink, Project

    project_id, brain_id, obsolete_id, source_id, recording_id, obsolete_recording = [str(uuid.uuid4()) for _ in range(6)]
    with ErpSession.begin() as db:
        db.add(Project(id=project_id, title='Recette'))
        db.flush()
        db.add(BrainLink(project_id=project_id, brain_project_id=brain_id))
    with BrainSession.begin() as db:
        db.add_all([BrainProject(id=i, name='Recette', code=i) for i in (brain_id, obsolete_id)])
        db.flush()
        db.add(Source(id=source_id, project_id=brain_id, source_type='meeting', original_uri='fixture', sha256=uuid.uuid4().hex))
        db.flush()
        for pid, rid in ((brain_id, recording_id), (obsolete_id, obsolete_recording)):
            db.add(MeetingRecording(id=rid, project_id=pid, source_id=source_id,
                                    erp_project_id=project_id, title='Privé', filename='fixture.wav'))
            db.add(AuditLog(id=rid, project_id=pid, event_type='meeting.transcription.completed.v1',
                            actor='audio-worker', payload={'recording_id': rid, 'revision': 1}))
    key = b't' * 32
    monkeypatch.setenv('AGENT_KIARA_KEY', key.hex())
    client = TestClient(app)
    path = '/internal/kiara/transcriptions'
    for projects, expected in (([project_id], [recording_id]), ([], [])):
        actor = {'id': 'device-a', 'role': 'reader', 'project_ids': projects, 'person_id': None}
        response = client.get(path, headers={'X-Kiara-Agent-Context': issue(key, 'GET', path, actor)})
        assert response.status_code == 200
        assert [event['id'] for event in response.json()['events']] == expected


def test_signed_context_and_replay(monkeypatch):
    key = bytes.fromhex('ab' * 32)
    monkeypatch.setenv('AGENT_KIARA_KEY', key.hex())
    client = TestClient(app)
    operator = {'id': 'client-a', 'role': 'reader', 'project_ids': [], 'person_id': None}
    target = '/api/v1/session'
    assert client.get(target).status_code == 403
    token = issue(key, 'GET', target, operator)
    response = client.get(target, headers={'X-Kiara-Agent-Context': token})
    assert response.status_code == 200
    assert response.json()['operator']['id'] == 'client-a'
    assert response.json()['operator']['role'] == 'reader'
    assert client.get(target, headers={'X-Kiara-Agent-Context': token}).status_code == 403
    token = issue(key, 'GET', target, operator)
    assert client.get(target + '?x=1', headers={'X-Kiara-Agent-Context': token}).status_code == 403
    token = issue(key, 'POST', '/api/v1/projects', operator)
    response = client.post('/api/v1/projects', json={'code': 'TEST', 'title': 'Test'},
                           headers={'X-Kiara-Agent-Context': token})
    assert response.status_code == 403


def test_invalid_and_expired_context(monkeypatch):
    key = bytes.fromhex('cd' * 32)
    monkeypatch.setenv('AGENT_KIARA_KEY', key.hex())
    client = TestClient(app)
    operator = {'id': 'client-a', 'role': 'owner', 'project_ids': None, 'person_id': None}
    target = '/api/v1/session'
    for token in (issue(key, 'GET', target, operator, now=1),
                  issue(b'x' * 32, 'GET', target, operator), 'malformed'):
        assert client.get(target, headers={'X-Kiara-Agent-Context': token}).status_code == 403


def test_private_session_inventory_requires_the_managed_service_identity(monkeypatch):
    client = TestClient(app)
    path = '/internal/kiara/personal-sessions'
    monkeypatch.delenv('AGENT_KIARA_KEY', raising=False)
    assert client.get(path).status_code == 404
    key = b'i' * 32
    monkeypatch.setenv('AGENT_KIARA_KEY', key.hex())
    owner = {'id': 'client-a', 'role': 'owner', 'project_ids': None, 'person_id': None}
    service = {**owner, 'id': 'kiara-service'}
    assert client.get(path, headers={'X-Kiara-Agent-Context': issue(key, 'GET', path, owner)}).status_code == 404
    response = client.get(path, headers={'X-Kiara-Agent-Context': issue(key, 'GET', path, service)})
    assert response.status_code == 200 and isinstance(response.json()['sessions'], list)


def test_project_scope_is_applied_to_portfolio_and_direct_access(monkeypatch):
    client = TestClient(app)
    monkeypatch.delenv('AGENT_KIARA_KEY', raising=False)
    code = uuid.uuid4().hex[:10]
    projects = [client.post('/api/v1/projects', json={'code': code + str(index), 'title': 'Test'}).json()['id']
                for index in range(2)]
    key = b'z' * 32
    monkeypatch.setenv('AGENT_KIARA_KEY', key.hex())
    operator = {'id': 'client-a', 'role': 'reader', 'project_ids': [projects[0]], 'person_id': None}

    def get(target):
        return client.get(target, headers={'X-Kiara-Agent-Context': issue(key, 'GET', target, operator)})

    response = get('/api/v1/portfolio')
    assert response.status_code == 200
    assert [item['id'] for item in response.json()] == [projects[0]]
    catalogue = get('/api/v1/project-catalogue')
    assert catalogue.status_code == 200
    assert catalogue.json() == [{'id': projects[0], 'code': code + '0', 'title': 'Test',
                                  'status': 'active', 'brain_project_id': None}]
    assert get('/api/v1/projects/' + projects[0]).status_code == 200
    assert get('/api/v1/projects/' + projects[1]).status_code == 404

    project_path = '/api/v1/projects/' + projects[0]
    payload = {'status': 'archived'}
    token = issue(key, 'PATCH', project_path, operator)
    assert client.patch(project_path, json=payload, headers={'X-Kiara-Agent-Context': token}).status_code == 403
    editor = {**operator, 'role': 'editor'}
    token = issue(key, 'PATCH', project_path, editor)
    assert client.patch(project_path, json=payload, headers={'X-Kiara-Agent-Context': token}).status_code == 200
    assert get('/api/v1/project-catalogue').json()[0]['status'] == 'archived'

    create_path = '/api/v1/projects'
    new_project = {'title': 'Nouveau projet Kiara'}
    token = issue(key, 'POST', create_path, editor)
    assert client.post(create_path, json=new_project, headers={'X-Kiara-Agent-Context': token}).status_code == 403
    owner = {**operator, 'role': 'owner', 'project_ids': None}
    token = issue(key, 'POST', create_path, owner)
    created = client.post(create_path, json=new_project, headers={'X-Kiara-Agent-Context': token})
    assert created.status_code == 201
    token = issue(key, 'GET', '/api/v1/project-catalogue', owner)
    visible = client.get('/api/v1/project-catalogue', headers={'X-Kiara-Agent-Context': token}).json()
    assert any(row['id'] == created.json()['id'] and row['title'] == new_project['title'] for row in visible)


def test_managed_capture_status_does_not_claim_server_devices(monkeypatch):
    from app.services import native_audio

    key = b'n' * 32
    monkeypatch.setenv('AGENT_KIARA_KEY', key.hex())
    monkeypatch.setattr(native_audio, '_inventory', {'installed': True})
    operator = {'id': 'client-a', 'role': 'owner', 'project_ids': None, 'person_id': None}
    path = '/api/v1/workspace/native-capture'
    response = TestClient(app).get(path, headers={'X-Kiara-Agent-Context': issue(key, 'GET', path, operator)})
    assert response.status_code == 200
    value = response.json()
    assert value['installed'] is False and value['ready'] is False and value['devices'] == []
    assert isinstance(value['owners'], list) and isinstance(value['recovery'], list)


def test_kiara_chat_context_resolves_only_the_authorized_erp_project(monkeypatch):
    from app.routers import kiara_admin
    from backend.app.db import SessionLocal
    from backend.app.models import BrainLink, Project

    brain_id = str(uuid.uuid4())
    with SessionLocal.begin() as db:
        project = Project(title='Recette Agent')
        other = Project(title='Autre projet')
        db.add_all([project, other])
        db.flush()
        project_id, other_id = project.id, other.id
        db.add(BrainLink(project_id=project_id, brain_project_id=brain_id))

    calls = []

    async def search(db, **query):
        calls.append(query)
        return {'items': [{'title': 'Note', 'excerpt': 'Extrait', 'level': 'validated'}]}

    monkeypatch.setattr(kiara_admin, 'search', search)
    key = b'c' * 32
    monkeypatch.setenv('AGENT_KIARA_KEY', key.hex())
    operator = {'id': 'client-a', 'role': 'reader', 'project_ids': [project_id], 'person_id': None}
    client = TestClient(app)

    def request(project):
        path = f'/internal/kiara/projects/{project}/context?q=essai'
        return client.get(path, headers={'X-Kiara-Agent-Context': issue(key, 'GET', path, operator)})

    assert request(other_id).status_code == 404
    response = request(project_id)
    assert response.status_code == 200
    assert response.json()['items'][0]['level'] == 'validated'
    assert calls == [{'query': 'essai', 'project_id': brain_id, 'limit': 6}]
    with SessionLocal.begin() as db:
        db.get(Project, project_id).status = 'archived'
    assert request(project_id).status_code == 409
    assert len(calls) == 1


def test_kiara_publication_keeps_erp_scope_and_private_history(monkeypatch):
    from backend.app.db import SessionLocal
    from backend.app.models import Project

    with SessionLocal.begin() as db:
        projects = [Project(title='Publication Kiara') for _ in range(2)]
        db.add_all(projects)
        db.flush()
        source, destination = (project.id for project in projects)
    key = b'p' * 32
    monkeypatch.setenv('AGENT_KIARA_KEY', key.hex())
    operator = {'id': 'device-a', 'role': 'editor', 'project_ids': [source, destination], 'person_id': None}
    client = TestClient(app)
    identity = uuid.uuid4().hex

    def request(method, path, body=None, actor=operator):
        token = issue(key, method, path, actor)
        return client.request(method, path, json=body, headers={'X-Kiara-Agent-Context': token})

    path = f'/internal/kiara/projects/{source}/conversations'
    new_path = f'/internal/kiara/projects/{destination}/conversations'
    save = {'action': 'conversation_save', 'id': identity, 'title': 'Discussion',
            'messages': [{'role': 'user', 'content': 'Texte privé'}]}
    assert request('POST', path, save, {**operator, 'role': 'reader'}).status_code == 403
    assert request('POST', path, save).json() == {'revision': 1}
    assert request('POST', path, save).status_code == 409
    other = {**operator, 'id': 'device-b'}
    assert request('GET', path + '?id=' + identity, actor=other).status_code == 404
    assert request('GET', '/internal/kiara/conversations', actor=other).json() == []
    move = {'action': 'conversation_move', 'id': identity, 'destination': destination, 'revision': 1}
    assert request('POST', path, move, {**operator, 'project_ids': [source]}).status_code == 404
    assert request('POST', path, move).json() == {'revision': 2}
    assert request('GET', new_path + '?id=' + identity).json()['messages'] == save['messages']
    assert request('GET', '/internal/kiara/conversations', actor={**operator, 'project_ids': [source]}).json() == []
    archive = {'action': 'conversation_archive', 'id': identity, 'archived': True, 'revision': 2}
    assert request('POST', new_path, archive).json() == {'revision': 3}
    assert request('GET', '/internal/kiara/conversations').json()[0]['archived'] is True
    remove = {'action': 'conversation_delete', 'id': identity, 'revision': 3}
    assert request('POST', new_path, remove).json() == {'deleted': True}
    assert request('GET', '/internal/kiara/conversations').json() == []


def test_kiara_project_memories_require_scope_device_and_current_revision(monkeypatch):
    from backend.app.db import SessionLocal
    from backend.app.models import Project

    with SessionLocal.begin() as db:
        project = Project(title='Mémoires Kiara')
        db.add(project)
        db.flush()
        project_id = project.id
    key = b'm' * 32
    monkeypatch.setenv('AGENT_KIARA_KEY', key.hex())
    device = {'id': 'device-a', 'role': 'editor', 'project_ids': [project_id], 'person_id': None}
    client = TestClient(app)
    path = f'/internal/kiara/projects/{project_id}/memories'
    index = f'/internal/kiara/memories?project={project_id}'

    def request(method, route, body=None, actor=device):
        return client.request(method, route, json=body,
                              headers={'X-Kiara-Agent-Context': issue(key, method, route, actor)})

    create = {'action': 'memory_create', 'text': 'Préférence privée'}
    assert request('POST', path, create, {**device, 'role': 'reader'}).status_code == 403
    added = request('POST', path, create)
    assert added.status_code == 200
    record = added.json()
    assert request('GET', index, actor={**device, 'id': 'device-b'}).json() == []
    assert request('GET', index, actor={**device, 'project_ids': []}).status_code == 404
    change = {'action': 'memory_save', **record, 'text': 'Préférence corrigée'}
    assert request('POST', path, change).json() == {'revision': '2'}
    assert request('POST', path, change).status_code == 409
    assert request('GET', index).json()[0]['text'] == 'Préférence corrigée'
    remove = {'action': 'memory_delete', 'id': record['id'], 'revision': '2'}
    assert request('POST', path, remove).json() == {'deleted': True}
    assert request('GET', index).json() == []
