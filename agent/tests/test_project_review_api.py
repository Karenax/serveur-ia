"""RLP HTTP adapter on fictional stores, not registered on production yet."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.db import get_db as get_brain
from backend.app.db import Base, get_db
from backend.app.routers import project_reviews as http
from backend.app.services.migration_guard import capture_baseline
from backend.app.services.project_operator import Operator, operator_context
from tests.test_project_reviews import audio as audio_store, content, fake_pdf, store as review_store

store = review_store
audio = audio_store


@pytest.fixture
def api(store, audio):
    app = FastAPI()
    app.include_router(http.router)
    app.include_router(http.catalogue_router)
    def erp_db():
        with store[0]() as db:
            yield db
    def brain_db():
        with audio[0]() as db:
            yield db
    app.dependency_overrides[get_db] = erp_db
    app.dependency_overrides[get_brain] = brain_db
    with TestClient(app) as client:
        yield client, f"/api/v1/projects/{store[1]['project']}/reviews"


def create(api, store):
    client, root = api
    response = client.post(root, json={'expected_revision': 0, 'content': content(store[1]).model_dump()})
    assert response.status_code == 201, response.text
    return response.json(), f"{root}/{response.json()['id']}"


def payload(row, **values):
    return {'expected_revision': row['revision'], 'expected_review_revision': row['review_revision'], **values}


def test_http_read_create_update_publish_download_revision(api, store, monkeypatch):
    from backend.app.services import project_review_pdf
    monkeypatch.setattr(project_review_pdf, 'build_pdf', fake_pdf)
    client, root = api
    assert client.get('/api/v1/review-types').json()[0]['code'] == 'rlp'
    assert client.get(root).json()['total'] == 0
    row, url = create(api, store)
    edit = row['content']
    edit['notes'] = 'Décision explicite et humaine'
    saved = client.put(url, json=payload(row, content=edit))
    assert saved.status_code == 200 and saved.json()['content']['notes'] == edit['notes']
    row = saved.json()
    published = client.post(f'{url}/publish', json=payload(row, confirmed=True))
    assert published.status_code == 200, published.text
    snapshot = client.get(f'{url}/publication')
    assert snapshot.status_code == 200 and snapshot.json()['snapshot']['review']['content']['notes'] == edit['notes']
    assert snapshot.json()['bindings'] == {}
    pdf = client.get(f'{url}/pdf')
    assert pdf.status_code == 200 and pdf.content == fake_pdf(None)
    assert pdf.headers['content-type'] == 'application/pdf'
    assert pdf.headers['etag'] == f'"{published.json()["publication"]["pdf_sha256"]}"'
    assert pdf.headers['content-disposition'].startswith('attachment;')
    created = client.post(f'{url}/revision', json=payload(published.json()))
    assert created.status_code == 201 and created.json()['status'] == 'draft'
    assert client.get(root).json()['total'] == 2
    assert client.get(f'{url}/history').json()['total'] == 3
    assert client.get(url).json()['status'] == 'published'
    assert not client.get(url).json()['can_create_revision']
    event = client.get(f'{url}/history').json()['items'][0]
    evidence = client.get(f'{url}/history/{event["id"]}')
    assert evidence.status_code == 200
    assert evidence.json()['previous']['content']['notes'] == edit['notes']
    assert evidence.json()['value']['status'] == 'published'
    assert evidence.json()['bindings'] == {}


def test_http_stale_and_invalid_command_rolls_back(api, store):
    client, _ = api
    row, url = create(api, store)
    before = capture_baseline(store[2])
    for data in [payload(row, content={'notes': 'x', 'actor_id': 'forged'}),
                 payload(row, content={'meeting_date': 'demain'}),
                 payload(row, content={'participants': [{'name': 'Alice', 'person_id': 'absent'}]})]:
        response = client.put(url, json=data)
        assert response.status_code == 422, response.text
        assert capture_baseline(store[2]) == before
    stale = client.put(url, json={**payload(row, content=row['content']), 'expected_revision': 0})
    assert stale.status_code == 409 and capture_baseline(store[2]) == before
    invalid = client.post(f'{url}/publish', json=payload(row, confirmed=False))
    assert invalid.status_code == 422 and capture_baseline(store[2]) == before
    assert client.post('/api/v1/projects/' + store[1]['foreign'] + '/reviews',
                       json={'expected_revision': 0, 'type_code': 'rlc'}).status_code == 422


def test_http_recording_import_keeps_original_transcript_and_pdf_requires_publication(api, store, audio):
    client, _ = api
    row, url = create(api, store)
    before = capture_baseline(audio[2])
    assert client.get(f'{url}/pdf').status_code == 404
    imported = client.post(f'{url}/recordings', json=payload(row, recording_id=audio[1], expected_recording_revision=3))
    assert imported.status_code == 200, imported.text
    assert imported.json()['status'] == 'draft' and not imported.json()['publication']
    assert list(imported.json()['provenance'].values())[0]['speaker'] == 'Alice'
    assert capture_baseline(audio[2]) == before
    assert client.post(f'{url}/publish', json=payload(imported.json(), confirmed=True)).status_code == 409


def test_reader_foreign_scope_and_pagination(api, store):
    client, root = api
    row, url = create(api, store)
    with operator_context(Operator('reader', 'reader', frozenset([store[1]['project']]))):
        assert client.get(url).status_code == 200
        assert not client.get(url).json()['can_edit']
        assert client.put(url, json=payload(row, content=row['content'])).status_code == 403
    with operator_context(Operator('foreign', 'editor', frozenset([store[1]['foreign']]))):
        assert client.get(url).status_code == 404
        assert client.get(f'{url}/pdf').status_code == 404
    for query in ('?limit=201', '?limit=0', '?offset=-1'):
        assert client.get(root + query).status_code == 422
        assert client.get(f'{url}/history' + query).status_code == 422


def test_partial_migration_models_do_not_leak_into_generic_archives(store):
    from backend.app.services import project_archive
    from fastapi import HTTPException
    from tests.test_project_reviews import create as create_review
    initial = create_review(store)
    with store[0]() as db:
        assert project_archive._rows(db, Base.metadata, store[1]['project'])['project_reviews']
    # A real incomplete protected schema is still refused, while a qualified
    # schema can now be read by the typed v6 exporter.
    with store[0].kw['bind'].begin() as connection:
        connection.exec_driver_sql('DROP TRIGGER trg_project_review_events_update_immutable')
    with store[0]() as db, pytest.raises(HTTPException, match='409'):
        project_archive._rows(db, Base.metadata, store[1]['project'])
    with store[0]() as db, pytest.raises(HTTPException, match='400'):
        project_archive.import_archive(db, {'format': 'agent-project-archive', 'version': 5,
            'tables': {'project_reviews': [initial]}})


def test_recording_choices_are_paged_scoped_current_and_read_only(api, store, audio):
    from copy import deepcopy
    from app.models import MeetingRecording, Project as BrainProject
    from backend.app.models import BrainLink
    from tests.test_project_reviews import transaction
    client, root = api
    before_erp, before_brain = capture_baseline(store[2]), capture_baseline(audio[2])
    page = client.get(root + '/recording-choices?limit=1')
    assert page.status_code == 200, page.text
    assert page.json()['total'] == 1 and page.json()['items'][0]['id'] == audio[1]
    assert 'summary' not in page.json()['items'][0] and 'segments' not in page.json()['items'][0]
    assert capture_baseline(store[2]) == before_erp and capture_baseline(audio[2]) == before_brain
    with transaction(audio[0]) as db:
        db.add(BrainProject(id='foreign-brain', code='OTHER-0001', name='Autre projet fictif'))
        db.flush()
        original = db.get(MeetingRecording, audio[1])
        fields = {column.name: deepcopy(getattr(original, column.name)) for column in MeetingRecording.__table__.columns
                  if column.name != 'id'}
        for key, change in [('stale-summary', {'summary_revision': 2}), ('stale-review', {'reviewed_revision': 2}),
                            ('busy', {'job_status': 'running'}), ('foreign-erp', {'erp_project_id': store[1]['foreign']}),
                            ('foreign-brain', {'project_id': 'foreign-brain'}), ('no-summary', {'summary': {}}),
                            ('null-summary', {'summary': None})]:
            db.add(MeetingRecording(id=key, **{**fields, **change}))
    assert client.get(root + '/recording-choices').json()['total'] == 1
    assert client.get(root + '/recording-choices?offset=1&limit=1').json()['items'] == []
    for query in ('?limit=101', '?offset=-1', '?limit=0'):
        assert client.get(root + '/recording-choices' + query).status_code == 422
    with operator_context(Operator('foreign', 'reader', frozenset([store[1]['foreign']]))):
        assert client.get(root + '/recording-choices').status_code == 404
    with transaction(store[0]) as db:
        db.delete(db.get(BrainLink, store[1]['project']))
    assert client.get(root + '/recording-choices').json()['total'] == 0


def test_history_detail_checks_both_project_and_review_and_reader_revision_capability(api, store, monkeypatch):
    from backend.app.services import project_review_pdf
    monkeypatch.setattr(project_review_pdf, 'build_pdf', fake_pdf)
    client, _ = api
    row, url = create(api, store)
    published = client.post(f'{url}/publish', json=payload(row, confirmed=True)).json()
    assert published['can_create_revision'] and not published['can_edit']
    event_id = client.get(f'{url}/history').json()['items'][0]['id']
    assert client.get(f'{url}/history/{event_id}').status_code == 200
    created = client.post(f'{url}/revision', json=payload(published)).json()
    other = url.rsplit('/', 1)[0] + '/' + created['id']
    assert client.get(f'{other}/history/{event_id}').status_code == 404
    assert client.get(f'{url}/history/missing').status_code == 404
    with operator_context(Operator('reader', 'reader', frozenset([store[1]['project']]))):
        assert not client.get(other).json()['can_create_revision']
        assert client.get(f'{url}/history/{event_id}').status_code == 200
    with operator_context(Operator('foreign', 'editor', frozenset([store[1]['foreign']]))):
        assert client.get(f'{url}/history/{event_id}').status_code == 404
