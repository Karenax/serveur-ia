"""Real SQL replay/follow isolation; no application startup, audio or model."""
import asyncio
from datetime import datetime, timedelta
import json

import pytest

from app.meeting_session_models import MeetingSession, MeetingSessionEvent
from app.routers import meeting_sessions as api
from backend.app.services.project_operator import Operator, operator_context
from tests.test_meeting_sessions import create, stores as stores_fixture

stores = stores_fixture


@pytest.fixture(autouse=True)
def no_device_probe(monkeypatch):
    monkeypatch.setattr('app.services.native_audio.status', lambda *_: {'session': None})


class Request:
    def __init__(self, headers=None):
        self.headers = headers or {}
        self.disconnected = False

    async def is_disconnected(self):
        return self.disconnected


def seed_events(factory, count=1):
    with factory() as db:
        session = create(db)
        sid = session['id']
        # Begin beyond create's event to exercise only the chosen replay.
        after = session['event_cursor']
        rows = [MeetingSessionEvent(session_id=sid, kind='transcript.updated',
                revision=1, data={'ordinal': n}) for n in range(count)]
        db.add_all(rows)
        db.commit()
        ids = [row.id for row in rows]
    return sid, after, ids


async def finite_frames(response):
    return [value async for value in response.body_iterator]


def frame_data(frame):
    return json.loads(next(line[6:] for line in frame.splitlines() if line.startswith('data: ')))


def test_finite_default_keeps_replay_limit_and_releases_initial_transaction(stores):
    factory = stores[0]
    sid, after, ids = seed_events(factory, 205)
    with factory() as db:
        response = api.events(sid, Request(), after=after, follow=False, db=db)
        assert not db.in_transaction()
        frames = asyncio.run(finite_frames(response))
    assert len(frames) == 200
    assert f'id: {ids[0]}\n' in frames[0]
    assert f'id: {ids[199]}\n' in frames[-1]
    assert datetime.fromisoformat(frame_data(frames[0])['created_at']).utcoffset() == timedelta()


def test_last_event_header_advances_finite_replay(stores):
    factory = stores[0]
    sid, after, ids = seed_events(factory, 3)
    with factory() as db:
        response = api.events(sid, Request({'last-event-id': str(ids[1])}),
                              after=after, follow=False, db=db)
        frames = asyncio.run(finite_frames(response))
    assert len(frames) == 1
    assert f'id: {ids[2]}\n' in frames[0]


def test_follow_gets_late_commit_without_retaining_initial_transaction(stores, monkeypatch):
    factory = stores[0]
    sid, after, ids = seed_events(factory)
    request = Request()
    monkeypatch.setattr(api, 'EVENT_POLL_SECONDS', 0.001)

    async def exercise():
        with factory() as db:
            response = api.events(sid, request, after=after, follow=True, db=db)
            assert not db.in_transaction()
        stream = response.body_iterator
        assert await anext(stream) == 'retry: 500\n\n'
        first = await anext(stream)
        with factory() as db:
            late = MeetingSessionEvent(session_id=sid, kind='transcript.corrected',
                                       revision=2, data={'text': 'Fictif : devis refusé.'})
            db.add(late)
            db.commit()
            late_id = late.id
        second = await asyncio.wait_for(anext(stream), 2)
        request.disconnected = True
        with pytest.raises(StopAsyncIteration):
            await anext(stream)
        return first, second, late_id

    first, second, late_id = asyncio.run(exercise())
    assert f'id: {ids[0]}\n' in first
    assert f'id: {late_id}\n' in second
    assert frame_data(second)['data'] == {}
    assert 'Fictif : devis refusé.' not in second


def test_follow_drains_more_than_one_batch_with_monotone_ids(stores):
    factory = stores[0]
    sid, after, expected = seed_events(factory, 205)
    request = Request()

    async def exercise():
        with factory() as db:
            response = api.events(sid, request, after=after, follow=True, db=db)
        stream = response.body_iterator
        await anext(stream)
        frames = [await asyncio.wait_for(anext(stream), 2) for _ in expected]
        request.disconnected = True
        with pytest.raises(StopAsyncIteration):
            await anext(stream)
        return frames

    frames = asyncio.run(exercise())
    assert [int(frame.splitlines()[0][4:]) for frame in frames] == expected


def test_follow_keeps_captured_operator_and_stops_after_project_moves(stores, monkeypatch):
    factory = stores[0]
    sid, after, _ = seed_events(factory)
    with factory() as db:
        row = db.get(MeetingSession, sid)
        row.project_id = 'allowed'
        db.commit()
    request = Request()
    actor = Operator('reader-test', 'reader', frozenset({'allowed'}))
    monkeypatch.setattr(api, 'EVENT_POLL_SECONDS', 0.001)
    with operator_context(actor), factory() as db:
        response = api.events(sid, request, after=after, follow=True, db=db)
    # The configured owner fallback is now in scope; the stream must retain reader-test.
    async def exercise():
        stream = response.body_iterator
        await anext(stream)
        await anext(stream)
        with factory() as db:
            db.get(MeetingSession, sid).project_id = 'forbidden'
            db.add(MeetingSessionEvent(session_id=sid, kind='transcript.updated',
                revision=2, data={'text': 'Contenu qui ne doit pas être envoyé'}))
            db.commit()
        denied = await asyncio.wait_for(anext(stream), 2)
        with pytest.raises(StopAsyncIteration):
            await anext(stream)
        return denied
    denied = asyncio.run(exercise())
    assert denied == 'event: stream.denied\ndata: {"status": 404}\n\n'
    assert 'Contenu' not in denied


def test_follow_deadline_finishes_even_without_events(stores, monkeypatch):
    factory = stores[0]
    sid, _, ids = seed_events(factory)
    monkeypatch.setattr(api, 'EVENT_FOLLOW_SECONDS', 0.02)
    monkeypatch.setattr(api, 'EVENT_POLL_SECONDS', 0.002)
    with factory() as db:
        response = api.events(sid, Request(), after=ids[-1], follow=True, db=db)
    frames = asyncio.run(asyncio.wait_for(finite_frames(response), 2))
    assert frames == ['retry: 500\n\n']


@pytest.mark.parametrize('follow', [False, True])
def test_event_notifications_do_not_expose_answer_from_another_project(stores, follow):
    from app.services.scoped_assistant import answer_visible, stored_answers

    factory = stores[0]
    sid, after, _ = seed_events(factory)
    private = {'conversation': {'erp_project_id': 'forbidden'},
               'answer': 'EXTRAIT FICTIF HORS PERIMETRE', 'citations': []}
    with factory() as db:
        row = db.get(MeetingSession, sid)
        row.project_id = 'allowed'
        db.add_all([MeetingSessionEvent(session_id=sid, kind='assistant.answer', revision=2, data=private),
                    MeetingSessionEvent(session_id=sid, kind='future.business-event', revision=2, data=private)])
        db.commit()
    request = Request()
    actor = Operator('reader-test', 'reader', frozenset({'allowed'}))
    with operator_context(actor), factory() as db:
        assert not answer_visible(db, private)
        assert stored_answers(db, db.get(MeetingSession, sid), 'assistant.answer')['items'] == []
        response = api.events(sid, request, after=after, follow=follow, db=db)

    async def exercise():
        stream = response.body_iterator
        if follow:
            await anext(stream)
            frames = [await anext(stream) for _ in range(3)]
            request.disconnected = True
            with pytest.raises(StopAsyncIteration):
                await anext(stream)
            return frames
        return await finite_frames(response)

    frames = asyncio.run(exercise())
    assert len(frames) == 3
    assert all(frame_data(frame)['data'] == {} for frame in frames)
    assert all('EXTRAIT' not in frame and 'forbidden' not in frame for frame in frames)


def test_transcript_event_only_correlates_a_chunk_of_its_own_session(stores):
    from app.meeting_session_models import MeetingAudioChunk
    from tests.test_meeting_sessions import key

    factory = stores[0]
    sid, after, _ = seed_events(factory)
    with factory() as db:
        other = create(db)['id']
        owned_id, other_id = key(), key()
        for identity, session_id in [(owned_id, sid), (other_id, other)]:
            db.add(MeetingAudioChunk(id=identity, session_id=session_id, track='mic', sequence=0,
                filename='fictif.wav', mime_type='audio/wav', storage_path='not-read.wav',
                sha256='0' * 64, size_bytes=1, start_ms=0, duration_ms=5))
        db.add_all([MeetingSessionEvent(session_id=sid, kind='transcript.updated', revision=2,
                    data={'chunk_id': owned_id, 'text': 'TEXTE FICTIF A NE PAS ENVOYER'}),
                    MeetingSessionEvent(session_id=sid, kind='transcript.updated', revision=2,
                    data={'chunk_id': other_id, 'error': 'ERREUR FICTIVE PRIVEE'})])
        db.commit()
        response = api.events(sid, Request(), after=after, follow=False, db=db)
    frames = asyncio.run(finite_frames(response))
    assert frame_data(frames[-2])['data'] == {'chunk_id': owned_id}
    assert frame_data(frames[-1])['data'] == {}
    assert all('FICTIF' not in frame for frame in frames)
