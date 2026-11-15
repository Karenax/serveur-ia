"""Historical staging citations resolve exactly, without generation or mutation."""
import asyncio
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import get_db
from app.meeting_session_models import MeetingSessionEvent, StagedSessionNoteVersion
from app.routers.meeting_sessions import router
from app.services import meeting_sessions as sessions, scoped_assistant as assistant
from backend.app.services.project_operator import Operator, operator_context
from tests.test_meeting_sessions import stores as stores_fixture, create, command, content

stores = stores_fixture


def client_for(brain):
    app = FastAPI()
    app.include_router(router)
    def database():
        with brain() as db:
            yield db
    app.dependency_overrides[get_db] = database
    return TestClient(app)


def staged(db, text='Ancienne décision : 50 euros.'):
    row = create(db, kind='note')
    saved = command(db, row['id'], 'notes', row['revision'], title='Version initiale', content=content(text))
    return row['id'], saved['staged_note']['version_id'], saved['revision']


def test_exact_historical_snapshot_survives_new_head_and_assignment(stores):
    brain, _, project_id, _ = stores
    with brain() as db:
        sid, first_id, revision = staged(db)
        first = db.get(StagedSessionNoteVersion, first_id)
        original = {key: getattr(first, key) for key in ('content', 'plain_text', 'sha256', 'revision')}
        created_at = first.created_at.replace(tzinfo=timezone.utc)
        saved = command(db, sid, 'notes', revision, title='Version corrigée', content=content('Décision corrigée : 70 euros.'))
        second_id = saved['staged_note']['version_id']
        command(db, sid, 'assign-project', saved['revision'], project_id=project_id)
        events_before = db.scalar(select(func.count()).select_from(MeetingSessionEvent))
    with client_for(brain) as client:
        first_response = client.get(f'/api/v1/meeting-sessions/{sid}/note-versions/{first_id}')
        assert first_response.status_code == 200
        value = first_response.json()
        assert value['id'] == first_id and value['session_id'] == sid and value['created_at']
        assert datetime.fromisoformat(value['created_at']) == created_at
        assert datetime.fromisoformat(value['created_at']).utcoffset().total_seconds() == 0
        assert {key: value[key] for key in original} == original
        second = client.get(f'/api/v1/meeting-sessions/{sid}/note-versions/{second_id}').json()
        assert second['revision'] == 2 and second['content'] != value['content']
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent)) == events_before
        assert sessions.session_note(db, sessions.get_session(db, sid))['title'] == 'Version corrigée'


def test_staging_version_cannot_be_read_through_another_session(stores):
    brain, _, _, _ = stores
    with brain() as db:
        sid, first_id, _ = staged(db)
        other_sid, other_id, _ = staged(db, 'Autre séance.')
    with client_for(brain) as client:
        for path in (f'{sid}/note-versions/{other_id}', f'{other_sid}/note-versions/{first_id}',
                     f'{sid}/note-versions/missing', f'missing/note-versions/{first_id}'):
            assert client.get(f'/api/v1/meeting-sessions/{path}').status_code == 404


def test_version_read_respects_staging_owner_and_current_project_rights(stores):
    brain, _, project_id, _ = stores
    with brain() as db:
        sid, version_id, revision = staged(db)
    path = f'/api/v1/meeting-sessions/{sid}/note-versions/{version_id}'
    with client_for(brain) as client:
        with operator_context(Operator('other', 'reader', None)):
            assert client.get(path).status_code == 404
        with operator_context(Operator('local', 'reader', None)):
            assert client.get(path).status_code == 200
        with operator_context(Operator('local', 'reader', frozenset([project_id]))):
            assert client.get(path).status_code == 404
        with brain() as db:
            command(db, sid, 'assign-project', revision, project_id=project_id)
        with operator_context(Operator('reader', 'reader', frozenset([project_id]))):
            assert client.get(path).status_code == 200
        with operator_context(Operator('local', 'editor', frozenset())):
            assert client.get(path).status_code == 404


def test_existing_snapshot_read_remains_available_when_creation_is_disabled(stores, monkeypatch):
    brain, _, _, _ = stores
    with brain() as db:
        sid, version_id, _ = staged(db)
    monkeypatch.setenv('AGENT_MEETING_SESSIONS_ENABLED', '0')
    with client_for(brain) as client:
        assert client.get(f'/api/v1/meeting-sessions/{sid}/note-versions/{version_id}').status_code == 200


def test_staging_citation_contains_session_and_exact_version_url(stores):
    brain, _, _, _ = stores
    with brain() as db:
        sid, version_id, _ = staged(db)
        from app.services.settings_service import save_section
        save_section(db, 'ai', {'enabled': True})
        _, _, prepared = asyncio.run(assistant.prepare(db, sessions.get_session(db, sid), query='Quelle décision ?', scope='session'))
        note = next(c for c in prepared['citations'] if c['locator'].get('staged_note_version_id'))
        assert note['locator']['session_id'] == sid
        assert note['locator']['note_version_id'] == version_id
        assert note['source_url'] == f'/api/v1/meeting-sessions/{sid}/note-versions/{version_id}'
