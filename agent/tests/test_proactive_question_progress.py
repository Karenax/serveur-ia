"""Durable pending/outcome projection; no inference, timeout or retry on reads."""
from datetime import timedelta
import asyncio
import json

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

from app.meeting_session_models import LiveTranscriptSegment, MeetingSession, MeetingSessionEvent
from app.services import meeting_sessions as sessions, session_proactive as worker
from app.services import scoped_assistant as assistant
from app.services.settings_service import save_section
from app.db import get_db
from app.routers.session_assistant import router
from backend.app.services.project_operator import Operator, operator_context
from tests.test_meeting_sessions import stores as stores_fixture, create, command, key

stores = stores_fixture


def test_ordinary_proactive_worker_does_not_silently_retry_an_empty_provider_reply(stores, monkeypatch):
    from app.services import ai_client
    brain, _, _, _ = stores
    worker._stop.clear()
    with brain() as db:
        save_section(db, 'ai', {'enabled': True, 'provider': 'openai_compatible',
            'base_url': 'http://fictitious-provider.invalid', 'model': 'fictitious',
            'fallback_enabled': False, 'clear_api_key': True})
        save_section(db, 'foresight', {'proactive_enabled': True, 'auto_enhancement_enabled': False})
        data = create(db)
        command(db, data['id'], 'resume', 1)
        db.add(LiveTranscriptSegment(id=key(), session_id=data['id'], track='mic',
            start_ms=0, end_ms=1000, text='Une réserve de cinquante euros reste à vérifier.'))
        db.add(LiveTranscriptSegment(id=key(), session_id=data['id'], track='mic',
            start_ms=1000, end_ms=3000, text='Quelle réserve faut-il vérifier ?'))
        db.commit()
    calls = []

    def empty_provider(url, payload, **kwargs):
        calls.append(payload['max_tokens'])
        assert len(calls) == 1, 'An uncertain automatic result must not launch a second request'
        return {'choices': [{'message': {'content': ''}}]}

    monkeypatch.setattr(ai_client, '_post_json', empty_provider)
    worker.tick()
    worker.tick()
    assert calls == [1200]
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(
            MeetingSessionEvent.kind == 'assistant.proactive-attempt')) == 1
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(
            MeetingSessionEvent.kind == 'assistant.live-answer')) == 0
        failure = db.scalar(select(MeetingSessionEvent).where(
            MeetingSessionEvent.kind == 'assistant.proactive-error'))
        assert "fourni de réponse" in failure.data['error']


def test_explicit_session_question_preserves_legacy_blank_reply_retry(stores, monkeypatch):
    from app.services import ai_client
    brain, _, _, _ = stores
    calls = []

    def provider(url, payload, **kwargs):
        calls.append(payload['max_tokens'])
        return {'choices': [{'message': {'content': '' if len(calls) == 1 else 'Réponse fictive [C1].'}}]}

    monkeypatch.setattr(ai_client, '_post_json', provider)
    with brain() as db:
        row, _, _ = pending(db)
        save_section(db, 'ai', {'enabled': True, 'provider': 'openai_compatible',
            'base_url': 'http://fictitious-provider.invalid', 'model': 'fictitious',
            'fallback_enabled': False, 'clear_api_key': True})
        result = asyncio.run(assistant.answer(db, row, query='Quelle réserve faut-il vérifier ?'))
        assert result['answer'] == 'Réponse fictive [C1].'
    assert calls == [1200, 2400]


def pending(db, pid=None, age=0, version=1):
    save_section(db, 'foresight', {'proactive_enabled': True, 'auto_enhancement_enabled': False})
    data = create(db, project_id=pid)
    command(db, data['id'], 'resume', 1)
    row = db.get(MeetingSession, data['id'])
    segment = LiveTranscriptSegment(id=key()+':0', session_id=row.id, track='mic',
        start_ms=0, end_ms=3000, text='Faut-il vérifier la réserve ?', finalized=True)
    db.add(segment)
    db.flush()
    token = f'{segment.id}:{segment.revision}'
    event = MeetingSessionEvent(session_id=row.id, kind='assistant.proactive-attempt',
        revision=row.revision, created_at=sessions.now()-timedelta(seconds=age),
        data={'question_token': token, 'query': segment.text, 'progress_version': version})
    db.add(event)
    db.commit()
    return row, segment, token


def test_idle_and_disabled_are_distinct_without_starting_work(stores):
    brain, _, _, _ = stores
    with brain() as db:
        row = db.get(MeetingSession, create(db)['id'])
        assert worker.question_progress(db, row)['state'] == 'disabled'
        save_section(db, 'foresight', {'proactive_enabled': True})
        before = db.scalar(select(func.count()).select_from(MeetingSessionEvent))
        assert worker.question_progress(db, row)['state'] == 'idle'
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent)) == before


@pytest.mark.parametrize('age,delayed', [(0, False), (11, True), (100000, True)])
def test_pending_age_only_reports_delay_and_never_abandons_work(stores, age, delayed):
    brain, _, _, _ = stores
    with brain() as db:
        row, _, _ = pending(db, age=age)
        before = db.scalar(select(func.count()).select_from(MeetingSessionEvent))
        result = worker.question_progress(db, row)
        assert result['state'] == 'pending' and result['delayed'] is delayed
        assert result['elapsed_seconds'] >= age
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent)) == before


@pytest.mark.parametrize('kind,obsolete,state', [
    ('assistant.proactive-completed', False, 'completed'),
    ('assistant.proactive-completed', True, 'obsolete'),
    ('assistant.proactive-error', False, 'failed'),
])
def test_exact_durable_outcome_ends_progress_without_exposing_internal_error(stores, kind, obsolete, state):
    brain, _, _, _ = stores
    with brain() as db:
        row, _, token = pending(db, age=15)
        sessions.append_event(db, row, kind, {'question_token': token, 'obsolete': obsolete,
            'error': 'Authorization Bearer PRIVATE-TEST-TOKEN'})
        db.commit()
        result = worker.question_progress(db, row)
        assert result['state'] == state and not result['delayed']
        assert 'PRIVATE-TEST-TOKEN' not in json.dumps(result)


def test_foreign_question_completion_cannot_end_current_attempt(stores):
    brain, _, _, _ = stores
    with brain() as db:
        row, _, _ = pending(db)
        sessions.append_event(db, row, 'assistant.proactive-completed', {'question_token': 'another:1'})
        db.commit()
        assert worker.question_progress(db, row)['state'] == 'pending'


def test_corrected_question_marks_old_progress_obsolete(stores):
    brain, _, _, _ = stores
    with brain() as db:
        row, segment, _ = pending(db)
        segment.revision += 1
        db.commit()
        assert worker.question_progress(db, row)['state'] == 'obsolete'


def test_historical_attempt_without_outcome_protocol_is_not_invented_as_pending(stores):
    brain, _, _, _ = stores
    with brain() as db:
        row, _, _ = pending(db, version=None)
        assert worker.question_progress(db, row)['state'] == 'unknown'


@pytest.mark.parametrize('token', [None, 42])
def test_malformed_historical_token_does_not_break_the_read_endpoint(stores, token):
    brain, _, _, _ = stores
    with brain() as db:
        row, _, _ = pending(db)
        event = db.scalar(select(MeetingSessionEvent).where(
            MeetingSessionEvent.kind == 'assistant.proactive-attempt'))
        event.data = {**event.data, 'question_token': token}
        db.commit()
        assert worker.question_progress(db, row)['state'] == 'unknown'


def test_interrupted_session_and_disabled_automatic_work_do_not_spin_forever(stores):
    brain, _, _, _ = stores
    with brain() as db:
        row, _, _ = pending(db)
        row.state = 'interrupted'
        db.commit()
        assert worker.question_progress(db, row)['state'] == 'interrupted'
        row.state = 'recording'
        save_section(db, 'foresight', {'proactive_enabled': False})
        db.commit()
        assert worker.question_progress(db, row)['state'] == 'unknown'


def test_progress_preserves_project_access_boundary(stores):
    brain, _, pid, _ = stores
    with brain() as db:
        row, _, _ = pending(db, pid=pid)
        with operator_context(Operator('restricted', 'reader', frozenset())):
            with pytest.raises(HTTPException) as failure:
                worker.question_progress(db, row)
        assert failure.value.status_code == 404


def test_live_answers_http_returns_readonly_progress_without_generating(stores, monkeypatch):
    brain, _, _, _ = stores
    with brain() as db:
        row, _, _ = pending(db, age=15)
        sid = row.id
        before = db.scalar(select(func.count()).select_from(MeetingSessionEvent))
    app = FastAPI()
    app.include_router(router)

    def database():
        with brain() as db:
            yield db

    app.dependency_overrides[get_db] = database
    monkeypatch.setattr(assistant, 'answer', lambda *a, **k: pytest.fail('GET must not generate'))
    with TestClient(app) as client:
        for _ in range(2):
            response = client.get(f'/api/v1/meeting-sessions/{sid}/live-answers')
            assert response.status_code == 200
            assert response.json()['items'] == []
            assert response.json()['automatic']['state'] == 'pending'
            assert response.json()['automatic']['delayed'] is True
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent)) == before


def test_actual_worker_records_pending_then_exact_completion_once(stores, monkeypatch):
    brain, _, _, _ = stores
    worker._stop.clear()
    with brain() as db:
        save_section(db, 'foresight', {'proactive_enabled': True, 'auto_enhancement_enabled': False})
        data = create(db)
        command(db, data['id'], 'resume', 1)
        db.add(LiveTranscriptSegment(id=key(), session_id=data['id'], track='mic',
            start_ms=0, end_ms=3000, text='Quelle réserve faut-il vérifier ?'))
        db.commit()
    observed = []

    async def answer(db, row, **kwargs):
        observed.append(worker.question_progress(db, row)['state'])
        return {'id': 'fictitious-answer', 'status': 'answered'}

    monkeypatch.setattr(assistant, 'answer', answer)
    worker.tick()
    worker.tick()
    with brain() as db:
        result = worker.question_progress(db, db.get(MeetingSession, data['id']))
        completions = list(db.scalars(select(MeetingSessionEvent).where(
            MeetingSessionEvent.kind == 'assistant.proactive-completed')))
        assert result['state'] == 'completed'
        assert len(completions) == 1 and observed == ['pending']
