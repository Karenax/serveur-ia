"""HTTP multipart preview/apply/originals, bounded selection and closed identity."""
from io import BytesIO
import json
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from backend.app.db import get_db
from backend.app.project_note_models import ProjectNote
from backend.app.routers.project_note_imports import router
from backend.app.services import project_note_files as storage
from backend.app.services.project_note_upload_selection import acquire_uploads
from tests import test_project_notes_core as core
from tests.test_project_note_source_preview import sources

store = core.store


@pytest.fixture
def http(store, tmp_path, monkeypatch):
    core.install(store)
    root = tmp_path / 'managed-http'
    root.mkdir()
    monkeypatch.setattr(storage, 'APP_DIR', root)
    app = FastAPI()
    app.include_router(router)
    def database():
        with store[1]() as db:
            yield db
    app.dependency_overrides[get_db] = database
    with TestClient(app) as client:
        yield client, store, root


def multipart(source_files):
    return [('files', (name, data, 'application/octet-stream')) for name, data in source_files.items()]


def prepared(http, source_files=None):
    client, store, _ = http
    source_files = sources() if source_files is None else source_files
    base = '/api/v1/projects/' + store[2][0] + '/notes'
    paths = json.dumps(list(source_files))
    note_id = core.command()
    preview = client.post(base + '/imports/preview', data={'planned_note_id': note_id, 'paths': paths},
                          files=multipart(source_files))
    assert preview.status_code == 200 and preview.json()['can_apply']
    command = {'command_id': core.command(), 'planned_note_id': note_id,
               'expected_preview_sha256': preview.json()['preview_sha256']}
    return base, source_files, paths, command


def test_http_preview_import_replay_and_original_html_download_only(http):
    client, store, _ = http
    base, source_files, paths, command = prepared(http)
    first = client.post(base + '/imports', data={'command': json.dumps(command), 'paths': paths}, files=multipart(source_files))
    assert first.status_code == 201 and first.json()['note']['revision'] == 2
    # Commit receipt takes precedence; a lost response needs no source bytes.
    replay = client.post(base + '/imports', data={'command': json.dumps(command), 'paths': 'not needed'},
                         files=[('files', ('placeholder', b'', 'application/octet-stream'))])
    assert replay.status_code == 201 and replay.json()['replayed'] and replay.json()['import_id'] == first.json()['import_id']
    note = base + '/' + command['planned_note_id']
    source = client.get(note + '/source')
    assert source.status_code == 200 and len(source.json()['source_versions']) == 2
    assert {f['relative_path'] for f in source.json()['source_files']} == set(source_files)
    assert source.json()['source_descriptor'] == {'kind': 'upload', 'link_id': None, 'relative_path': ''}
    original = client.get(note + '/originals/download', params={'relative_path': 'content.html'})
    assert original.status_code == 200 and original.content == source_files['content.html']
    assert original.headers['content-type'] == 'application/octet-stream'
    assert original.headers['content-disposition'].startswith('attachment;')
    assert original.headers['x-content-type-options'] == 'nosniff'
    assert "sandbox" in original.headers['content-security-policy']
    assert client.get(note + '/originals/download', params={'relative_path': '../../secret'}).status_code == 404
    foreign = note.replace(store[2][0], store[2][1])
    assert client.get(foreign + '/source').status_code == 404


def test_replay_json_never_acquires_sources_and_preserves_command_identity(http, monkeypatch):
    client, _, root = http
    base, source_files, paths, command = prepared(http)
    first = client.post(base + '/imports', data={'command': json.dumps(command), 'paths': paths}, files=multipart(source_files))
    assert first.status_code == 201
    before = sorted((str(p.relative_to(root)), p.read_bytes()) for p in root.rglob('*') if p.is_file())
    monkeypatch.setattr('backend.app.routers.project_note_imports.acquire_uploads', lambda *_: pytest.fail('No reacquisition'))
    replay = client.post(base + '/imports/replay', json=command)
    assert replay.status_code == 200 and replay.json()['replayed']
    assert replay.json()['command_id'] == command['command_id']
    assert replay.json()['import_id'] == first.json()['import_id']
    assert sorted((str(p.relative_to(root)), p.read_bytes()) for p in root.rglob('*') if p.is_file()) == before
    wrong = client.post(base + '/imports/replay', json={**command, 'expected_preview_sha256': 'b' * 64})
    assert wrong.status_code == 409


def test_replay_missing_import_has_no_files_or_note_and_obeys_scope_and_reader(http, monkeypatch):
    client, store, root = http
    base, _, _, command = prepared(http)
    response = client.post(base + '/imports/replay', json=command)
    assert response.status_code == 404 and not list(root.iterdir())
    with store[1]() as db:
        assert db.scalar(select(ProjectNote.id)) is None
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    assert client.post(base + '/imports/replay', json=command).status_code == 403
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'editor')
    monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', json.dumps([store[2][1]]))
    assert client.post(base + '/imports/replay', json=command).status_code == 404


def test_replay_does_not_unfreeze_a_restored_import_command(http):
    from backend.app.project_note_models import NoteSourceImport
    client, store, _ = http
    base, source_files, paths, command = prepared(http)
    first = client.post(base + '/imports', data={'command': json.dumps(command), 'paths': paths}, files=multipart(source_files))
    assert first.status_code == 201
    with store[1]() as db:
        row = db.get(NoteSourceImport, first.json()['import_id'])
        row.execution_blocked = True
        db.commit()
    assert client.post(base + '/imports/replay', json=command).status_code == 409
    assert client.get(base + '/' + command['planned_note_id'] + '/source').status_code == 200


@pytest.mark.parametrize('extra', [{'actor_id': 'forged'}, {'role': 'owner'}, {'absolute_path': 'V:/data'}])
def test_http_import_does_not_accept_caller_authority_or_server_paths(http, extra):
    client, store, root = http
    base, source_files, paths, command = prepared(http)
    response = client.post(base + '/imports', data={'command': json.dumps({**command, **extra}), 'paths': paths},
                           files=multipart(source_files))
    assert response.status_code == 422 and not list(root.iterdir())
    with store[1]() as db:
        assert db.scalar(select(ProjectNote.id)) is None


def test_http_reader_cannot_preview_or_apply_import(http, monkeypatch):
    client, _, root = http
    base, source_files, paths, command = prepared(http)
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    assert client.post(base + '/imports/preview', data={'planned_note_id': command['planned_note_id'], 'paths': paths},
                       files=multipart(source_files)).status_code == 403
    assert client.post(base + '/imports', data={'command': json.dumps(command), 'paths': paths},
                       files=multipart(source_files)).status_code == 403
    assert not list(root.iterdir())


def test_duplicate_json_and_source_names_rejected_without_copy(http):
    client, _, root = http
    base, source_files, paths, command = prepared(http)
    doubled = json.dumps(command)[:-1] + ', "command_id": "' + core.command() + '"}'
    assert client.post(base + '/imports', data={'command': doubled, 'paths': paths}, files=multipart(source_files)).status_code == 422
    assert client.post(base + '/imports/preview', data={'planned_note_id': command['planned_note_id'], 'paths': '["content.html","CONTENT.html"]'},
                       files=[('files', ('a', b'<p>A</p>')), ('files', ('b', b'<p>B</p>'))]).status_code == 422
    assert not list(root.iterdir())


@pytest.mark.parametrize('paths', [['../../secret'], ['C:/secret'], ['attachments/a.txt', 'ATTACHMENTS/A.TXT'], ['manifest.json'] * 201])
def test_upload_names_validated_before_reading_any_stream(paths):
    class NeverRead:
        def read(self, *args):
            pytest.fail('Names must be checked before acquisition')
    with pytest.raises(HTTPException) as caught:
        acquire_uploads([SimpleNamespace(file=NeverRead()) for _ in paths], paths)
    assert caught.value.status_code == 422


def test_upload_stream_is_bounded_and_no_empty_or_changed_source_silently_omitted():
    stream = BytesIO(b'a' * 2_000_001)
    with pytest.raises(HTTPException) as caught:
        acquire_uploads([SimpleNamespace(file=stream)], ['content.txt'])
    assert caught.value.status_code == 413
    assert stream.tell() == 2_000_001
    files = acquire_uploads([SimpleNamespace(file=BytesIO(b''))], ['content.html'])
    assert files == {'content.html': b''}
