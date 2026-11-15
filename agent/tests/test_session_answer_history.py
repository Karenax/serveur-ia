"""Durable conversations and explicit pins, isolated from hardware and LLMs."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

from app.db import get_db
from app.meeting_session_models import MeetingSessionEvent
from app.models import Project as BrainProject
from app.routers.session_assistant import router
from app.services import scoped_assistant as assistant, meeting_sessions as sessions
from app.services.settings_service import save_section
from backend.app.models import BrainLink, Project
from backend.app.services.project_operator import Operator, operator_context
from tests.test_session_assistant import enable, model, note_session, source
from tests.test_meeting_sessions import stores as stores_fixture, command, create

stores = stores_fixture


def generate(db, row, monkeypatch, query='Quelle réserve ?', **kwargs):
    model(monkeypatch, 'Réserve de 50 euros [C1].')
    return asyncio.run(assistant.answer(db, row, query=query, **kwargs))


def client_for(brain):
    app = FastAPI()
    app.include_router(router)
    def database():
        with brain() as db:
            yield db
    app.dependency_overrides[get_db] = database
    return TestClient(app)


def test_history_survives_new_connection_without_generation_and_separates_sessions(stores, monkeypatch):
    brain, _, pid, _ = stores
    with brain() as db:
        enable(db)
        first, _ = note_session(db, pid)
        second, _ = note_session(db, pid)
        one = generate(db, first, monkeypatch)
        two = generate(db, second, monkeypatch, query='Quelle réserve seconde séance ?')
        save_section(db, 'ai', {'enabled': False})
        first_id, second_id = first.id, second.id
    model(monkeypatch, lambda *args, **kwargs: pytest.fail('Reading history must not generate'))
    with client_for(brain) as client:
        assert [x['id'] for x in client.get(f'/api/v1/meeting-sessions/{first_id}/ask').json()['items']] == [one['id']]
        assert [x['id'] for x in client.get(f'/api/v1/meeting-sessions/{second_id}/ask').json()['items']] == [two['id']]
        assert client.get(f'/api/v1/meeting-sessions/{first_id}/ask?scope=unknown').status_code == 422


def test_selected_sources_are_partitioned_and_order_independent(stores, monkeypatch):
    brain, _, pid, bid = stores
    with brain() as db:
        enable(db)
        row, _ = note_session(db, pid)
        sources = [source(db, bid) for _ in range(2)]
        first = generate(db, row, monkeypatch, scope='sources', source_ids=[sources[0].id])
        both = generate(db, row, monkeypatch, scope='sources', source_ids=[s.id for s in sources])
        model(monkeypatch, lambda *args, **kwargs: pytest.fail('An identical source set must replay its answer'))
        assert asyncio.run(assistant.answer(db, row, query='Quelle réserve ?', scope='sources',
            source_ids=[sources[1].id, sources[0].id, sources[0].id]))['id'] == both['id']
        other = generate(db, row, monkeypatch, scope='sources', source_ids=[sources[1].id])
        assert [x['id'] for x in assistant.stored_answers(db, row, 'assistant.answer', scope='sources',
                source_ids=[sources[0].id])['items']] == [first['id']]
        assert [x['id'] for x in assistant.stored_answers(db, row, 'assistant.answer', scope='sources',
                source_ids=[sources[1].id, sources[0].id, sources[0].id])['items']] == [both['id']]
        assert [x['id'] for x in assistant.stored_answers(db, row, 'assistant.answer', scope='sources',
                source_ids=[sources[1].id])['items']] == [other['id']]
        assert assistant.stored_answers(db, row, 'assistant.answer', scope='project')['items'] == []


def test_history_marks_changed_note_stale_and_never_moves_old_project_context(stores, monkeypatch):
    brain, _, pid, _ = stores
    with brain() as db:
        enable(db)
        row, saved = note_session(db)
        before = generate(db, row, monkeypatch)
        command(db, row.id, 'assign-project', saved['revision'], project_id=pid)
        db.refresh(row)
        assert assistant.stored_answers(db, row, 'assistant.answer', scope='session')['items'] == []
        after = generate(db, row, monkeypatch)
        from tests.test_meeting_sessions import content
        note = sessions.serialize_session(db, row)
        command(db, row.id, 'notes', row.revision, title='Corrigée', content=content('Réserve modifiée 70 euros.'),
            expected_note_revision=note['note_revision'], expected_note_version_id=note['note_version_id'])
        history = assistant.stored_answers(db, row, 'assistant.answer', scope='session')['items']
        assert len(history) == 1 and history[0]['id'] == after['id'] and history[0]['stale']
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(
            MeetingSessionEvent.data['id'].as_string() == before['id'])) == 1


def test_live_pin_replays_persists_and_preserves_model_output(stores, monkeypatch):
    brain, _, pid, _ = stores
    with brain() as db:
        enable(db)
        row, _ = note_session(db, pid)
        answer = generate(db, row, monkeypatch, live=True)
        event = db.scalar(select(MeetingSessionEvent).where(MeetingSessionEvent.kind == 'assistant.live-answer'))
        original = deepcopy(event.data)
        for _ in range(2):
            assert assistant.pin_live_answer(db, row, answer['id'], True) == {'id': answer['id'], 'pinned': True}
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(
            MeetingSessionEvent.kind == 'assistant.live-pin')) == 1
        db.refresh(event)
        assert event.data == original
        sid = row.id
    with client_for(brain) as client:
        assert client.get(f'/api/v1/meeting-sessions/{sid}/live-answers').json()['items'][0]['pinned']
        assert client.put(f'/api/v1/meeting-sessions/{sid}/live-answers/{answer["id"]}/pin',
                          json={'pinned': False}).json() == {'id': answer['id'], 'pinned': False}
        assert not client.get(f'/api/v1/meeting-sessions/{sid}/live-answers').json()['items'][0]['pinned']
        with operator_context(Operator('local', 'reader', None)):
            assert client.put(f'/api/v1/meeting-sessions/{sid}/live-answers/{answer["id"]}/pin',
                              json={'pinned': True}).status_code == 403


def test_revoked_project_hides_entire_stored_answer_and_pin(stores, monkeypatch):
    brain, erp, pid, _ = stores
    with brain() as db, erp() as target:
        enable(db)
        other = BrainProject(code='HISTORY-SECRET', name='Secret')
        db.add(other)
        db.commit()
        project = Project(code='HISTORY-SECRET', title='Secret')
        target.add(project)
        target.flush()
        target.add(BrainLink(project_id=project.id, brain_project_id=other.id))
        target.commit()
        secret = source(db, other.id)
        row, _ = note_session(db, pid)
        answer = generate(db, row, monkeypatch, scope='sources', source_ids=[secret.id], live=True)
        assert assistant.stored_answers(db, row, 'assistant.live-answer')['items']
        with operator_context(Operator('local', 'editor', frozenset([pid]))):
            assert assistant.stored_answers(db, row, 'assistant.live-answer')['items'] == []
            with pytest.raises(HTTPException) as error:
                assistant.pin_live_answer(db, row, answer['id'], True)
            assert error.value.status_code == 404


def test_pinned_old_card_survives_recent_history_limit_and_pin_is_session_scoped(stores, monkeypatch):
    brain, _, pid, _ = stores
    with brain() as db:
        enable(db)
        row, _ = note_session(db, pid)
        answer = generate(db, row, monkeypatch, live=True)
        assistant.pin_live_answer(db, row, answer['id'], True)
        for i in range(101):
            sessions.append_event(db, row, 'assistant.live-answer', {**answer, 'id': f'later-{i}'})
        db.commit()
        history = assistant.stored_answers(db, row, 'assistant.live-answer')['items']
        assert len(history) == 101
        assert next(item for item in history if item['id'] == answer['id'])['pinned']
        other = sessions.get_session(db, create(db, project_id=pid)['id'])
        with pytest.raises(HTTPException) as error:
            assistant.pin_live_answer(db, other, answer['id'], True)
        assert error.value.status_code == 404


def test_concurrent_same_pin_is_one_audit_event(stores, monkeypatch):
    brain, _, pid, _ = stores
    with brain() as db:
        enable(db)
        row, _ = note_session(db, pid)
        answer = generate(db, row, monkeypatch, live=True)
        sid = row.id
    barrier = Barrier(2)
    def pin():
        with brain() as db:
            row = sessions.get_session(db, sid)
            barrier.wait()
            return assistant.pin_live_answer(db, row, answer['id'], True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: pin(), range(2)))
    assert results == [{'id': answer['id'], 'pinned': True}] * 2
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(
            MeetingSessionEvent.kind == 'assistant.live-pin')) == 1


def test_moved_source_never_exposes_old_project_answer_or_pin(stores, monkeypatch):
    from app.models import SourceArtifact

    brain, erp, pid, bid = stores
    with brain() as db, erp() as target:
        enable(db)
        private = BrainProject(code='HISTORY-OLD-PRIVATE', name='Ancien projet privé')
        db.add(private)
        db.commit()
        old_project = Project(code='HISTORY-OLD-PRIVATE', title='Ancien projet privé')
        target.add(old_project)
        target.flush()
        target.add(BrainLink(project_id=old_project.id, brain_project_id=private.id))
        target.commit()
        selected = source(db, private.id, text='La réserve secrète de l’ancien projet est de 1234 euros.')
        row, _ = note_session(db, pid)
        model(monkeypatch, 'La réserve secrète est de 1234 euros [C1].')
        arguments = dict(query='Quelle réserve secrète ?', scope='sources', source_ids=[selected.id])
        regular = asyncio.run(assistant.answer(db, row, **arguments))
        live = asyncio.run(assistant.answer(db, row, live=True, **arguments))
        originals = {event.id: deepcopy(event.data) for event in db.scalars(select(MeetingSessionEvent).where(
            MeetingSessionEvent.kind.in_(['assistant.answer', 'assistant.live-answer'])))}

        with operator_context(Operator('local', 'editor', frozenset([pid]))):
            assert assistant.stored_answers(db, row, 'assistant.answer', scope='sources',
                source_ids=[selected.id])['items'] == []

        # The current Source now belongs to an allowed project with new content.
        # Its old answer still contains evidence from the inaccessible origin.
        selected.project_id = bid
        artifact = db.scalar(select(SourceArtifact).where(SourceArtifact.source_id == selected.id))
        artifact.content_text = 'Le nouveau projet autorisé contient seulement une réserve publique de 50 euros.'
        db.commit()

        owner_history = assistant.stored_answers(db, row, 'assistant.answer', scope='sources',
            source_ids=[selected.id])['items']
        assert len(owner_history) == 1 and owner_history[0]['id'] == regular['id'] and owner_history[0]['stale']
        with operator_context(Operator('local', 'editor', frozenset([pid]))):
            assert assistant.stored_answers(db, row, 'assistant.answer', scope='sources',
                source_ids=[selected.id])['items'] == []
            assert assistant.stored_answers(db, row, 'assistant.live-answer')['items'] == []
            with pytest.raises(HTTPException) as caught:
                assistant.pin_live_answer(db, row, live['id'], True)
            assert caught.value.status_code == 404
        for event_id, original in originals.items():
            db.refresh(event := db.get(MeetingSessionEvent, event_id))
            assert event.data == original


def test_pin_quota_can_be_released_without_deleting_cards_or_events(stores, monkeypatch):
    brain, _, pid, _ = stores
    with brain() as db:
        enable(db)
        row, _ = note_session(db, pid)
        answer = generate(db, row, monkeypatch, live=True)
        for i in range(51):
            sessions.append_event(db, row, 'assistant.live-answer', {**answer, 'id': f'card-{i}'})
        db.commit()
        for i in range(50):
            assistant.pin_live_answer(db, row, f'card-{i}', True)
        with pytest.raises(HTTPException) as error:
            assistant.pin_live_answer(db, row, 'card-50', True)
        assert error.value.status_code == 409
        assistant.pin_live_answer(db, row, 'card-0', False)
        assistant.pin_live_answer(db, row, 'card-50', True)
        cards = assistant.stored_answers(db, row, 'assistant.live-answer')['items']
        assert len(cards) == 52 and sum(card['pinned'] for card in cards) == 50
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(
            MeetingSessionEvent.kind == 'assistant.live-pin')) == 52
