"""Publication/history reads on genuinely transported fictional paired stores."""
import base64
from copy import deepcopy
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.db import get_db as get_brain
from backend.app.db import get_db
from backend.app.project_review_models import ProjectReview, ReviewEvent, ReviewPublication
from backend.app.routers import project_reviews as http
from backend.app.services import project_archive
from backend.app.services.migration_guard import capture_baseline
from backend.app.services.project_operator import Operator, operator_context
from tests import test_project_review_archive as fixtures

store = fixtures.store
audio = fixtures.audio
envelope = fixtures.envelope
l3_store = fixtures.l3_store
typed_document = fixtures.typed_document
transport = fixtures.transport


@pytest.mark.parametrize('rounds', [1, 2])
def test_restored_publication_history_bindings_are_separate_scoped_and_readonly(transport, rounds):
    data, target, brain, erp_path, brain_path, _ = transport
    original = deepcopy(data)
    first = fixtures.restore(target, data)
    current = first
    if rounds == 2:
        with target() as db:
            exported = project_archive.export_archive(db, first['id'])
        current = fixtures.restore(target, exported, 'COPIE-0306')
    with target() as db:
        publication = db.query(ReviewPublication).filter_by(project_id=current['id']).one()
        review_id = publication.review_id
        expected_bindings = deepcopy(publication.bindings)
        events = db.query(ReviewEvent).filter_by(review_id=review_id).all()
        expected_events = {row.id: {'previous': deepcopy(row.previous), 'value': deepcopy(row.value),
                                  'bindings': deepcopy(row.bindings)} for row in events}
        other_review = db.query(ProjectReview).filter(ProjectReview.project_id == current['id'],
                                                     ProjectReview.id != review_id).one()
        foreign_review_id = other_review.id
    app = FastAPI()
    app.include_router(http.router)

    def erp_db():
        with target() as db:
            yield db

    def brain_db():
        with brain() as db:
            yield db

    app.dependency_overrides[get_db] = erp_db
    app.dependency_overrides[get_brain] = brain_db
    before = capture_baseline(erp_path), capture_baseline(brain_path)
    url = f"/api/v1/projects/{current['id']}/reviews/{review_id}"
    with TestClient(app) as client, operator_context(Operator('reader', 'reader', frozenset([current['id']]))):
        published = client.get(url + '/publication')
        assert published.status_code == 200, published.text
        response = published.json()
        captured = original['tables']['project_review_publications'][0]
        assert response['snapshot'] == json.loads(captured['snapshot'])
        assert response['sha256'] == captured['sha256']
        assert response['pdf_sha256'] == captured['pdf_sha256']
        assert response['bindings'] == expected_bindings
        assert response['snapshot']['project']['id'] == original['project']['id']
        assert response['bindings']['erp'][original['project']['id']] == current['id']
        assert response['bindings']['erp'][response['snapshot']['deliverables'][0]['id']] != response['snapshot']['deliverables'][0]['id']
        live = client.get(url).json()
        assert not live['can_edit']
        proof = next(iter(live['provenance'].values()))
        captured_proof = next(iter(response['snapshot']['review']['provenance'].values()))
        assert response['bindings']['brain'][captured_proof['recording_id']] == proof['recording_id']
        pdf = client.get(url + '/pdf')
        assert pdf.status_code == 200 and pdf.content == base64.b64decode(captured['pdf_base64'])
        assert pdf.headers['etag'] == f'"{captured["pdf_sha256"]}"'
        for event_id, expected in expected_events.items():
            detail = client.get(url + '/history/' + event_id)
            assert detail.status_code == 200, detail.text
            assert {key: detail.json()[key] for key in expected} == expected
            foreign_url = f"/api/v1/projects/{current['id']}/reviews/{foreign_review_id}/history/{event_id}"
            assert client.get(foreign_url).status_code == 404
        with operator_context(Operator('foreign', 'reader', frozenset(['other-project']))):
            assert client.get(url + '/publication').status_code == 404
            assert client.get(url + '/pdf').status_code == 404
            assert client.get(url + '/history/' + next(iter(expected_events))).status_code == 404
    assert (capture_baseline(erp_path), capture_baseline(brain_path)) == before
    assert data == original
