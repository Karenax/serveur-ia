"""Explicit opinions on private answers; no model, microphone or business writes."""
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

from app.db import get_db
from app.meeting_session_models import MeetingSessionEvent
from app.models import KnowledgeItem
from app.routers.session_assistant import router
from app.services import assistant_feedback as feedback, meeting_sessions as sessions, scoped_assistant
from app.services import fusion_insights, fusion_index_metrics
from backend.app.services.project_operator import Operator, operator_context
from tests.test_meeting_sessions import stores as stores_fixture, create
from tests.test_session_assistant import enable, source
from tests.test_insights_completeness import no_runtime

stores = stores_fixture


def retained(db, pid, *, identity='a1', kind='ask'):
    row = sessions.get_session(db, create(db, project_id=pid, kind='note')['id'])
    conversation = scoped_assistant.conversation_context(row, 'session')
    event = sessions.append_event(db, row, feedback.KINDS[kind], {'id': identity, 'query': 'Quelle réserve ?',
        'answer': 'La réserve reste ouverte.', 'scope': 'session', 'citations': [],
        'conversation': conversation, 'conversation_key': scoped_assistant.conversation_key(conversation)})
    db.commit()
    return row, event


def test_opinion_changes_are_idempotent_and_preserve_answer_and_business(stores):
    brain, _, pid, _ = stores
    with brain() as db:
        row, event = retained(db, pid)
        original, revision = dict(event.data), row.revision
        for value in (True, True, False, False, None, None):
            assert feedback.set_feedback(db, row, 'ask', 'a1', value)['useful'] is value
        opinions = db.scalars(select(MeetingSessionEvent).where(MeetingSessionEvent.kind == feedback.EVENT)
                              .order_by(MeetingSessionEvent.id)).all()
        assert [item.data['useful'] for item in opinions] == [True, False, None]
        assert all(item.data['operator_id'] == 'local' and item.data['answer_event_id'] == event.id for item in opinions)
        db.refresh(event)
        db.refresh(row)
        assert event.data == original and row.revision == revision
        assert db.scalar(select(func.count()).select_from(KnowledgeItem)) == 0
        assert row.recording_id is None and row.note_id is None


def test_same_identity_in_two_answer_kinds_and_another_session_stays_separate(stores):
    brain, _, pid, _ = stores
    with brain() as db:
        row, event = retained(db, pid)
        sessions.append_event(db, row, feedback.KINDS['live'], dict(event.data))
        other, other_event = retained(db, pid)
        db.commit()
        feedback.set_feedback(db, row, 'ask', 'a1', True)
        feedback.set_feedback(db, row, 'live', 'a1', False)
        assert feedback.annotate(db, row.id, 'ask', [event.data])[0]['useful'] is True
        assert feedback.annotate(db, row.id, 'live', [event.data])[0]['useful'] is False
        assert feedback.annotate(db, other.id, 'ask', [other_event.data])[0]['useful'] is None


def test_unknown_answer_and_read_only_operator_cannot_write_an_opinion(stores):
    brain, _, pid, _ = stores
    with brain() as db:
        row, _ = retained(db, pid)
        with pytest.raises(HTTPException) as unknown:
            feedback.set_feedback(db, row, 'ask', 'absent', True)
        assert unknown.value.status_code == 404
        db.rollback()
        with operator_context(Operator('local', 'reader', frozenset([pid]))):
            with pytest.raises(HTTPException) as readonly:
                feedback.set_feedback(db, row, 'ask', 'a1', True)
        assert readonly.value.status_code == 403
        db.rollback()
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(MeetingSessionEvent.kind == feedback.EVENT)) == 0


def test_revoked_citation_blocks_opinion_and_does_not_leak_into_stats(stores, monkeypatch):
    from app.models import Project
    brain, _, pid, _ = stores
    no_runtime(monkeypatch)
    monkeypatch.setattr(fusion_index_metrics, 'measured_indexes', lambda *args: {'indexed_sources': 0})
    monkeypatch.setattr(scoped_assistant, 'context_current', lambda *args: True)
    with brain() as db:
        row, event = retained(db, pid)
        foreign = Project(code='HIDDEN', name='Projet inaccessible')
        db.add(foreign)
        db.flush()
        hidden = source(db, foreign.id)
        event.data = {**event.data, 'citations': [{'source_id': hidden.id, 'source_project_id': foreign.id}]}
        db.commit()
        feedback.set_feedback(db, row, 'ask', 'a1', True)
        with operator_context(Operator('local', 'editor', frozenset([pid]))):
            with pytest.raises(HTTPException) as denied:
                feedback.set_feedback(db, row, 'ask', 'a1', False)
            assert denied.value.status_code == 404
            db.rollback()
            assert fusion_insights.stats(db)['assistant']['evaluated_answers'] == 0


def test_http_opinion_is_strict_and_history_restores_it_without_generation(stores, monkeypatch):
    brain, _, pid, _ = stores
    monkeypatch.setattr(scoped_assistant, 'context_current', lambda *args: True)
    monkeypatch.setattr('app.services.ai_client.chat_text', lambda *args, **kwargs: pytest.fail('unexpected model'))
    with brain() as db:
        enable(db)
        row, _ = retained(db, pid)
        sid = row.id
    app = FastAPI()
    app.include_router(router)
    def private_db():
        with brain() as db:
            yield db
    app.dependency_overrides[get_db] = private_db
    url = f'/api/v1/meeting-sessions/{sid}/answers/ask/a1/feedback'
    with TestClient(app) as client:
        assert client.put(url, json={'useful': True}).json() == {'id': 'a1', 'kind': 'ask', 'useful': True}
        assert client.get(f'/api/v1/meeting-sessions/{sid}/ask').json()['items'][0]['useful'] is True
        for body in ({'useful': 1}, {'useful': 'true'}, {}, {'useful': True, 'operator_id': 'spoofed'}):
            assert client.put(url, json=body).status_code == 422
        assert client.put(url.replace('/ask/', '/invalid/'), json={'useful': True}).status_code == 422
        assert client.put(url, json={'useful': None}).json()['useful'] is None
        assert client.get(f'/api/v1/meeting-sessions/{sid}/ask').json()['items'][0]['useful'] is None


def test_statistics_count_latest_explicit_opinion_once_and_allow_withdrawal(stores, monkeypatch):
    brain, _, pid, _ = stores
    no_runtime(monkeypatch)
    monkeypatch.setattr(fusion_index_metrics, 'measured_indexes', lambda *args: {'indexed_sources': 0})
    monkeypatch.setattr(scoped_assistant, 'context_current', lambda *args: True)
    with brain() as db:
        row, first = retained(db, pid)
        sessions.append_event(db, row, feedback.KINDS['live'], {**first.data, 'id': 'a2'})
        db.commit()
        assert fusion_insights.stats(db)['assistant']['evaluated_answers'] == 0
        feedback.set_feedback(db, row, 'ask', 'a1', False)
        feedback.set_feedback(db, row, 'ask', 'a1', True)
        feedback.set_feedback(db, row, 'live', 'a2', False)
        measured = fusion_insights.stats(db)['assistant']
        assert (measured['useful_answers'], measured['unhelpful_answers'], measured['evaluated_answers']) == (1, 1, 2)
        feedback.set_feedback(db, row, 'ask', 'a1', None)
        measured = fusion_insights.stats(db)['assistant']
        assert (measured['useful_answers'], measured['unhelpful_answers'], measured['evaluated_answers']) == (0, 1, 1)
        sessions.append_event(db, row, feedback.EVENT, {'answer_kind': 'ask', 'answer_id': 'absent', 'useful': True})
        db.commit()
        assert fusion_insights.stats(db)['assistant']['useful_answers'] == 0
