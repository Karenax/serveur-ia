"""Exercise the real Notes routes on disposable projects and private notebooks."""
from io import BytesIO
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app.security import local_guard
from backend.app.db import Base, get_db
from backend.app.models import Project
from backend.app.personal_note_models import PersonalNote, PersonalNoteImage, PersonalNoteVersion
from backend.app.routers import project_note_files, project_notes, workspace_notes
from tests import test_project_notes_core as core

store = core.store


@pytest.fixture
def client(store, tmp_path, monkeypatch):
    engine, factory, ids, _ = store
    core.install(store)
    Base.metadata.create_all(engine, tables=[PersonalNote.__table__, PersonalNoteImage.__table__, PersonalNoteVersion.__table__])
    monkeypatch.setattr('backend.app.services.project_note_files.APP_DIR', tmp_path)
    app = FastAPI()
    app.middleware('http')(local_guard)
    for router in (project_note_files.router, project_note_files.clipboard_router, project_notes.router, workspace_notes.router):
        app.include_router(router)

    def dependency():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = dependency
    with TestClient(app, base_url='http://127.0.0.1:8001') as session:
        yield session, ids


def paste(session, url, command, data):
    return session.post(url + '/paste-image', files={'command': ('note.json', json.dumps(command), 'application/json'),
                                                    'file': ('capture.png', data, 'image/png')})


def screenshot():
    stream = BytesIO()
    Image.new('RGB', (6, 4), 'blue').save(stream, format='PNG')
    return stream.getvalue()


@pytest.mark.parametrize('personal', [True, False])
def test_first_paste_is_replayable_and_preserves_note_format(client, personal):
    session, (first, _) = client
    root = '/api/v1/notes/personal' if personal else f'/api/v1/projects/{first}/notes'
    command = {'command_id': core.command(), 'title': 'Première capture', 'expected_revision': 0,
               'content': core.rich().model_dump(mode='json'), 'insert_at': 2}
    data = screenshot()
    assert paste(session, root, command, b'not a PNG').status_code == 422
    assert session.get(root).json()['total'] == 0
    result = paste(session, root, command, data)
    assert result.status_code == 201, result.text
    note = result.json()['note']
    attachment = note['attachment_ids'][0]
    blocks = note['content']['blocks']
    assert [block['type'] for block in blocks] == ['heading', 'paragraph', 'image', 'list', 'table']
    assert blocks[1]['runs'][0]['color'] == '#112233' and blocks[3]['items'][0]['checked'] is True
    detail = root + '/' + note['id']
    image = session.get(detail + '/attachments/' + attachment + '/image')
    assert image.status_code == 200 and image.content == data
    assert paste(session, root, command, data).json()['replayed']
    assert session.get(root + '?query=premiere').json()['total'] == 1
    assert session.get(detail + '/history').status_code == 200
    before = session.get(detail).json()
    assert paste(session, detail, {**command, 'command_id': core.command()}, data).status_code == 409
    assert session.get(detail).json() == before


def test_private_boundaries_and_copy_with_image(client, store, monkeypatch):
    session, (first, second) = client
    root = '/api/v1/notes/personal'
    catalogue = '/api/v1/notes/projects'
    result = paste(session, root, {'command_id': core.command(), 'title': 'Privée', 'expected_revision': 0,
                                  'content': {'blocks': []}, 'insert_at': 0}, screenshot())
    assert result.status_code == 201, result.text
    note = result.json()['note']
    url = f'{root}/{note["id"]}'
    attachment = note['attachment_ids'][0]
    target = {'project_id': first, 'version_id': note['version_id']}

    monkeypatch.setenv('AGENT_OPERATOR_ID', 'autre-compte')
    assert session.get(root).json()['total'] == 0
    assert session.get(url).status_code == 404
    assert session.get(url + '/history').status_code == 404
    assert session.get(url + '/attachments/' + attachment + '/image').status_code == 404
    assert session.post(url + '/copy-to-project', json=target).status_code == 404

    monkeypatch.setenv('AGENT_OPERATOR_ID', 'local')
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'editor')
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', json.dumps([first]))
    assert session.get(catalogue).json()['projects'] == [{'id': first, 'code': 'FIRST', 'title': 'Premier', 'has_notes': False}]
    assert session.post(url + '/copy-to-project', json={**target, 'project_id': second}).status_code == 404
    copied = session.post(url + '/copy-to-project', json=target)
    assert copied.status_code == 201, copied.text
    project_note = copied.json()
    assert session.post(url + '/copy-to-project', json=target).json()['id'] == project_note['id']
    assert session.get(url).json() == note
    assert session.get(catalogue).json()['projects'][0]['has_notes'] is True
    project_url = f'/api/v1/projects/{first}/notes/{project_note["id"]}'
    asset = project_note['attachment_ids'][0]
    assert asset != attachment
    assert session.get(f'{project_url}/attachments/{asset}/image').content == screenshot()

    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    assert session.get(root).json()['can_edit'] is False
    assert session.post(root, json={'command_id': core.command(), 'title': 'Privée'}).status_code == 403
    with store[1]() as db:
        project = db.get(Project, first)
        project.status = 'archived'
        db.commit()
    assert session.get(catalogue).json()['projects'] == []


def test_all_notes_colours_permissions_and_replayable_deletion(client, monkeypatch):
    session, (first, second) = client
    roots = ['/api/v1/notes/personal', f'/api/v1/projects/{first}/notes', f'/api/v1/projects/{second}/notes']
    notes = []
    for root, title, background in zip(roots, ['Privée', 'Premier projet', 'Autre projet'], ['pink', 'blue', 'green']):
        result = session.post(root, json={'command_id': core.command(), 'title': title,
                                         'content': {'blocks': [], 'background': background}})
        assert result.status_code == 201, result.text
        notes.append(result.json()['note'])
    all_url = '/api/v1/notes/all'
    params = [('projects', first), ('projects', second)]
    assert {row['background'] for row in session.get(all_url, params=params).json()['items']} == {'pink', 'blue', 'green'}
    assert session.get(all_url, params={'query': 'privee'}).json()['items'][0]['title'] == 'Privée'
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'editor')
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', json.dumps([first]))
    assert session.get(all_url, params=params).json()['total'] == 2
    foreign = f"{roots[2]}/{notes[2]['id']}"
    assert session.request('DELETE', foreign, json={'command_id': core.command(), 'expected_revision': 1}).status_code == 404
    for root, note in zip(roots[:2], notes[:2]):
        path = f"{root}/{note['id']}"
        delete = {'command_id': core.command(), 'expected_revision': 1}
        assert session.request('DELETE', path, json={**delete, 'expected_revision': 2}).status_code == 409
        assert session.request('DELETE', path, json=delete).json() == {'deleted': True}
        assert session.request('DELETE', path, json=delete).json() == {'deleted': True}
        assert session.get(path).status_code == 404
        assert session.get(root).json()['total'] == 0
    assert session.get(all_url, params=params).json()['total'] == 0
    assert session.get('/api/v1/notes/projects').json()['projects'][0]['has_notes'] is False


def test_private_clipboard_image_over_five_mib_keeps_background(client):
    session, _ = client
    stream = BytesIO()
    Image.new('RGB', (1500, 1500), 'blue').save(stream, format='PNG', compress_level=0)
    data = stream.getvalue()
    assert len(data) > 5 * 1024 * 1024
    root = '/api/v1/notes/personal'
    result = paste(session, root, {'command_id': core.command(), 'title': 'Grande image', 'expected_revision': 0,
                                   'content': {'blocks': [], 'background': 'yellow'}, 'insert_at': 0}, data)
    assert result.status_code == 201, result.text
    note = result.json()['note']
    assert note['content']['background'] == 'yellow'
    attachment = note['attachment_ids'][0]
    assert session.get(f"{root}/{note['id']}/attachments/{attachment}/image").content == data
