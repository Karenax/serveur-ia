"""L01 exit criteria through the real registered HTTP handlers and private SQL."""
import hashlib

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import get_db
from app.meeting_session_models import MeetingSession
from app.models import MeetingRecording, Source
from app.routers.meeting_sessions import router as session_router
from app.routers.workspace import router as workspace_router, get_erp_db
from backend.app.models import BrainLink, Meeting, Project
from backend.app.project_note_models import NoteVersion
from tests.test_meeting_sessions import stores as stores_fixture, key, content, wav

stores = stores_fixture


def test_global_and_project_identity_staging_assignment_and_finalization_replay(stores):
    brain, erp, pid, bid = stores
    app = FastAPI()
    app.include_router(session_router)
    app.include_router(workspace_router)
    def brain_db():
        with brain() as db:
            yield db
    def erp_db():
        with erp() as db:
            yield db
    app.dependency_overrides[get_db] = brain_db
    app.dependency_overrides[get_erp_db] = erp_db
    with erp() as db:
        other = Project(code='OTHER-ACCEPTANCE', title='Autre projet autorisé')
        db.add(other)
        db.flush()
        db.add(BrainLink(project_id=other.id, brain_project_id=bid))
        historical = Meeting(project_id=pid, title='CR historique conservé', date='2026-10-01')
        db.add(historical)
        db.commit()
        historical_id = historical.id
        other_id = other.id
    with TestClient(app) as client:
        created = client.post('/api/v1/meeting-sessions', json={'command_id':key(), 'title':'Séance à attribuer'})
        assert created.status_code == 201, created.text
        sid = created.json()['id']
        base = '/api/v1/meeting-sessions/' + sid
        save = client.put(base+'/notes', json={'command_id':key(), 'expected_revision':1,
            'title':'Notes avant attribution', 'content':content('Réserve conservée').model_dump(mode='json')})
        assert save.status_code == 200, save.text
        raw = wav()
        uploaded = client.put(base+'/chunks/mic/0', data={'command_id':key(),
            'sha256':hashlib.sha256(raw).hexdigest(), 'start_ms':'0', 'duration_ms':'10'},
            files={'file':('capture.wav', raw, 'audio/wav')})
        assert uploaded.status_code == 200, uploaded.text
        finish = {'command_id':key(), 'expected_revision':save.json()['revision']}
        completed = client.post(base+'/finalize', json=finish)
        assert completed.status_code == 200 and completed.json()['recording_id'] is None
        with brain() as db:
            assert db.scalar(select(func.count()).select_from(Source)) == 0
            assert db.scalar(select(func.count()).select_from(MeetingRecording)) == 0
        assert [r['id'] for r in client.get('/api/v1/meeting-sessions').json()['items']] == [sid]
        assert client.get('/api/v1/meeting-sessions', params={'project_id':pid}).json()['items'] == []
        assign = {'command_id':key(), 'expected_revision':completed.json()['revision'], 'project_id':pid}
        bound = client.post(base+'/assign-project', json=assign)
        assert bound.status_code == 200, bound.text
        assert client.post(base+'/assign-project', json=assign).json() == bound.json()
        assert client.post(base+'/finalize', json=finish).json() == completed.json()
        # A valid, authorised different target isolates command-key collision
        # from the separate 404 privacy check on an unknown project.
        assert client.post(base+'/assign-project', json={**assign, 'project_id':other_id}).status_code == 409
        canonical = client.get(base).json()
        assert canonical['recording_id'] == bound.json()['recording_id']
        assert canonical['note']['content'] == content('Réserve conservée').model_dump(mode='json')
        global_list = client.get('/api/v1/meeting-sessions').json()['items']
        project_list = client.get('/api/v1/meeting-sessions', params={'project_id':pid}).json()['items']
        assert global_list == project_list and global_list[0]['id'] == sid
        for params in ({}, {'project_id':pid}):
            rows = client.get('/api/v1/workspace/meetings', params=params).json()['items']
            assert len(rows) == 2
            assert next(row for row in rows if row['recording_id'])['session_id'] == sid
            assert next(row for row in rows if row['meeting_id'])['meeting_id'] == historical_id
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(MeetingSession)) == 1
        assert db.scalar(select(func.count()).select_from(MeetingRecording)) == 1
        assert db.scalar(select(func.count()).select_from(Source)) == 1
    with erp() as db:
        assert db.scalar(select(func.count()).select_from(NoteVersion)) == 1
        assert db.scalar(select(func.count()).select_from(Meeting)) == 1
