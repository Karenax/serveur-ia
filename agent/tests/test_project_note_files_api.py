"""Guarded real multipart commands and verified frozen attachment responses."""
from io import BytesIO

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app.security import local_guard, session
from backend.app.db import get_db
from backend.app.routers.project_note_files import router
from backend.app.services.migration_guard import capture_baseline
from tests import test_project_note_files as attachment_tests
from tests import test_project_notes_core as core

store = core.store
attachments = attachment_tests.attachments


@pytest.fixture
def api(attachments):
    store, note_id, _ = attachments
    _, factory, ids, _ = store
    app = FastAPI()
    app.middleware('http')(local_guard)
    app.get('/api/v1/session')(session)
    app.include_router(router)
    def dependency():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = dependency
    with TestClient(app, base_url='http://127.0.0.1:8001') as client:
        yield client, f'/api/v1/projects/{ids[0]}/notes/{note_id}/attachments', ids


def upload(client, url, command_id=None, *, filename='réunion.txt', data=b'Saisie'):
    return client.post(url, data={'command_id': command_id or core.command()},
                       files={'file': (filename, data, 'image/png')})


def test_multipart_retry_download_headers_and_dangerous_preview(api, attachments):
    client, url, _ = api
    command = core.command()
    first = upload(client, url, command)
    assert first.status_code == 201, first.text
    item = first.json()['attachment']
    assert item['content_type'] == 'text/plain'  # Ignore a forged upload MIME.
    assert upload(client, url, command).json()['replayed']
    assert len(client.get(url).json()['items']) == 1
    result = client.get(url + '/' + item['id'] + '/download')
    assert result.status_code == 200 and result.content == b'Saisie'
    assert result.headers['content-disposition'].startswith("attachment; filename*=UTF-8''")
    assert result.headers['content-type'] == 'application/octet-stream'
    assert result.headers['x-content-type-options'] == 'nosniff'
    assert result.headers['cache-control'] == 'private, no-store'
    assert client.get(url + '/' + item['id'] + '/image').status_code == 422
    assert upload(client, url, command, data=b'Other').status_code == 409
    assert len(list(attachments[2].glob('note-files/*/blob'))) == 1


def test_valid_image_frozen_response_and_missing_file_no_new_metadata(api, attachments):
    client, url, _ = api
    data = BytesIO()
    Image.new('RGB', (5, 5), 'blue').save(data, format='PNG')
    result = upload(client, url, filename='image.png', data=data.getvalue())
    assert result.status_code == 201
    image = client.get(url + '/' + result.json()['attachment']['id'] + '/image')
    assert image.status_code == 200 and image.content == data.getvalue()
    assert image.headers['content-type'] == 'image/png'
    assert image.headers['content-disposition'].startswith('inline;')
    before = capture_baseline(attachments[0][3])
    assert upload(client, url, filename='bad.png', data=b'<html/>').status_code == 422
    assert capture_baseline(attachments[0][3]) == before


def test_foreign_scope_reader_and_actual_csrf_guard(api, attachments, monkeypatch):
    client, url, ids = api
    before = capture_baseline(attachments[0][3])
    assert upload(client, url.replace(ids[0], ids[1])).status_code == 404
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    assert upload(client, url).status_code == 403
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'editor')
    monkeypatch.setenv('AGENT_TESTING', '0')
    assert upload(client, url).status_code == 403
    token = client.get('/api/v1/session').json()['token']
    result = client.post(url, data={'command_id': core.command()}, files={'file': ('note.txt', b'Allowed')},
                         headers={'x-agent-token': token, 'origin': 'https://foreign.example'})
    assert result.status_code == 403
    assert capture_baseline(attachments[0][3]) == before
    assert not (attachments[2] / 'note-files').exists()
