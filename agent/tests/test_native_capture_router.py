"""Native command durability with simulated hardware and real isolated stores."""
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
import hashlib
import io
from threading import Barrier, Thread
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

from app.db import get_db
from app.meeting_session_models import MeetingAudioChunk, MeetingSessionCommand
from app.meeting_session_schemas import Command
from app.routers import native_capture as routes
from app.services import meeting_sessions as sessions, native_audio as native
from backend.app.services.project_operator import Operator, operator_context
from tests.test_meeting_sessions import stores as stores_fixture, create, key, wav

stores = stores_fixture
native_stop_impl = native.stop_capture


@pytest.fixture
def hardware(stores, monkeypatch):
    brain, _, _, _ = stores
    captures = {}
    calls = []
    monkeypatch.setattr(native, '_captures', captures)

    def status(sid=None):
        return {'ready': True, 'active': [{'session_id': identity, 'state': item.state, 'tracks': item.tracks}
                for identity, item in captures.items()], 'session': None}

    def start(db, sid, *, tracks, devices):
        calls.append('start')
        captures[sid] = SimpleNamespace(state='recording', tracks=tracks, process=None)
        sessions.append_event(db, sessions.get_session(db, sid), 'native.capture.owner', {'tracks': tracks})
        db.commit()

    def simple(sid, operation, state):
        calls.append(operation)
        captures[sid].state = state
        return {'session_id': sid, 'state': state}

    def stop(sid):
        calls.append('stop')
        owner = captures[sid]
        errors = []
        context = copy_context()
        def drain():
            try:
                with brain() as db:
                    raw = wav()
                    sessions.store_chunk(db, sid, 'mic', 0, raw=raw, filename='native.wav', mime_type='audio/wav',
                        command_id=key(), sha256=hashlib.sha256(raw).hexdigest(), start_ms=0, duration_ms=10,
                        internal_capture_owner=owner)
            except Exception as exc:
                errors.append(exc)
        thread = Thread(target=lambda: context.run(drain), daemon=True)
        thread.start()
        thread.join(3)
        if thread.is_alive():
            raise RuntimeError('Native drain deadlocked on the session lock')
        if errors:
            raise errors[0]
        owner.state = 'stopped'
        captures.pop(sid, None)
        return {'session_id': sid, 'state': 'stopped'}

    monkeypatch.setattr(native, 'status', status)
    monkeypatch.setattr(native, 'start_capture', start)
    monkeypatch.setattr(native, 'pause_capture', lambda sid: simple(sid, 'pause', 'paused'))
    monkeypatch.setattr(native, 'resume_capture', lambda sid: simple(sid, 'resume', 'recording'))
    monkeypatch.setattr(native, 'stop_capture', stop)
    return captures, calls


def client(brain):
    app = FastAPI()
    app.include_router(routes.router)
    def dependency():
        with brain() as db:
            yield db
    app.dependency_overrides[get_db] = dependency
    return TestClient(app)


def test_native_lifecycle_drain_and_stop_receipt_replay(stores, hardware):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
    http = client(brain)
    prefix = f"/api/v1/meeting-sessions/{row['id']}/native-capture"
    start = {'command_id': key(), 'expected_revision': 1, 'tracks': ['mic']}
    assert http.post(prefix + '/start', json=start).json()['state'] == 'recording'
    assert http.post(prefix + '/start', json=start).status_code == 200
    assert http.post(prefix + '/pause', json={'command_id': key(), 'expected_revision': 2}).json()['state'] == 'paused'
    assert http.post(prefix + '/resume', json={'command_id': key(), 'expected_revision': 3}).json()['state'] == 'recording'
    stop = {'command_id': key(), 'expected_revision': 4}
    ended = http.post(prefix + '/stop', json=stop)
    assert ended.status_code == 200, ended.text
    assert ended.json()['state'] == 'completed'
    assert http.post(prefix + '/stop', json=stop).json() == ended.json()
    assert hardware[1] == ['start', 'pause', 'resume', 'stop']
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(MeetingAudioChunk)) == 1
        receipt = db.get(MeetingSessionCommand, stop['command_id'])
        assert receipt.status == 'completed' and receipt.result['state'] == 'completed'


def test_registered_stopped_helper_is_drained_before_finalize(stores, hardware):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        routes.perform(db, row['id'], 'start', routes.Start(command_id=key(), expected_revision=1, tracks=['mic']))
        hardware[0][row['id']].state = 'stopped'
        assert not native.owns_session(row['id'])
        assert native.has_registered_capture(row['id'])
        result = routes.perform(db, row['id'], 'stop', Command(command_id=key(), expected_revision=2))
        assert result['state'] == 'completed'
        assert hardware[1] == ['start', 'stop']
        assert db.scalar(select(func.count()).select_from(MeetingAudioChunk)) == 1
        assert not native.has_registered_capture(row['id'])


@pytest.mark.parametrize('exit_code', [0, 1])
def test_registered_auto_stop_requires_real_exit_barrier_before_route_receipt(
        stores, hardware, monkeypatch, tmp_path, exit_code):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        routes.perform(db, row['id'], 'start', routes.Start(command_id=key(), expected_revision=1, tracks=['mic']))
        owner = native.NativeCapture(row['id'], tmp_path / 'native-private', ['mic'], {}, {'mic': 0}, 0)
        owner.request['qualification'] = {'token': 'simulated-private-handshake'}
        owner.process = SimpleNamespace(poll=lambda: exit_code, wait=lambda timeout: exit_code,
                                        stdin=io.StringIO(), stdout=io.StringIO())
        owner._reader_done.set()  # Simulated EOF; no child or microphone exists.
        owner.state = 'stopped'
        hardware[0][row['id']] = owner
        raw = wav()
        sessions.store_chunk(db, row['id'], 'mic', 0, raw=raw, filename='durable.wav', mime_type='audio/wav',
            command_id=key(), sha256=hashlib.sha256(raw).hexdigest(), start_ms=0, duration_ms=10,
            internal_capture_owner=owner)
        interrupted = []
        monkeypatch.setattr(owner, '_record_interruption', lambda: interrupted.append(True))
        monkeypatch.setattr(native, 'stop_capture', native_stop_impl)
        finalize = routes.finalize_stop
        finalized = []
        def track_finalize(*args):
            finalized.append(True)
            return finalize(*args)
        monkeypatch.setattr(routes, 'finalize_stop', track_finalize)
        body = Command(command_id=key(), expected_revision=2)
        if exit_code:
            with pytest.raises(HTTPException, match='terminée en erreur') as failure:
                routes.perform(db, row['id'], 'stop', body)
            assert failure.value.status_code == 409
            receipt = db.get(MeetingSessionCommand, body.command_id)
            assert receipt.status == 'rejected' and receipt.error
            assert not finalized and interrupted == [True]
            assert owner.state == 'interrupted' and owner.error
            with pytest.raises(HTTPException) as repeated:
                routes.perform(db, row['id'], 'stop', body)
            assert repeated.value.status_code == 409 and not finalized
            db.expire_all()
            assert db.get(MeetingSessionCommand, body.command_id).status == 'rejected'
            interrupted_row = sessions.get_session(db, row['id'])
            preserved = sessions.execute_command(db, row['id'], 'finalize',
                Command(command_id=key(), expected_revision=interrupted_row.revision))
            assert preserved['state'] == 'completed'
            assert any('arrêt Windows non confirmé' in issue for issue in preserved['issues'])
        else:
            result = routes.perform(db, row['id'], 'stop', body)
            assert result['state'] == 'completed' and finalized == [True] and not interrupted
        assert db.scalar(select(func.count()).select_from(MeetingAudioChunk)) == 1
        assert not native.has_registered_capture(row['id'])


@pytest.mark.parametrize('helper_state', ['recording', 'stopped', 'interrupted'])
def test_generic_finalize_cannot_bypass_registered_native_owner(stores, hardware, helper_state):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        routes.perform(db, row['id'], 'start', routes.Start(command_id=key(), expected_revision=1, tracks=['mic']))
        hardware[0][row['id']].state = helper_state
        command = Command(command_id=key(), expected_revision=2)
        with pytest.raises(HTTPException) as rejected:
            sessions.execute_command(db, row['id'], 'finalize', command)
        assert rejected.value.status_code == 409
        assert db.get(MeetingSessionCommand, command.command_id) is None
        assert native.has_registered_capture(row['id']) and hardware[1] == ['start']


def test_confirmed_drain_marker_survives_loss_before_parent_finish(stores, hardware, monkeypatch):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        routes.perform(db, row['id'], 'start', routes.Start(command_id=key(), expected_revision=1, tracks=['mic']))
        body = Command(command_id=key(), expected_revision=2)
        finish = sessions._finish
        monkeypatch.setattr(sessions, '_finish', lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('lost parent write')))
        with pytest.raises(RuntimeError, match='lost parent write'):
            routes.perform(db, row['id'], 'stop', body)
        db.expire_all()
        receipt = db.get(MeetingSessionCommand, body.command_id)
        assert receipt.status == 'prepared' and receipt.body['_native_drain_confirmed'] is True
        assert not native.has_registered_capture(row['id'])
        monkeypatch.setattr(sessions, '_finish', finish)
        restored = routes.perform(db, row['id'], 'stop', body)
        assert restored['state'] == 'completed' and hardware[1] == ['start', 'stop']
        assert routes.perform(db, row['id'], 'stop', body) == restored


def test_uncommitted_drain_marker_cannot_be_inferred_on_retry(stores, hardware, monkeypatch):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        routes.perform(db, row['id'], 'start', routes.Start(command_id=key(), expected_revision=1, tracks=['mic']))
        body = Command(command_id=key(), expected_revision=2)
        commit = db.commit
        failed = False
        def commit_once():
            nonlocal failed
            receipt = db.get(MeetingSessionCommand, body.command_id)
            if not failed and receipt and receipt.body.get('_native_drain_confirmed') is True and receipt.status == 'prepared':
                failed = True
                raise RuntimeError('drain marker not committed')
            return commit()
        monkeypatch.setattr(db, 'commit', commit_once)
        with pytest.raises(RuntimeError, match='drain marker not committed'):
            routes.perform(db, row['id'], 'stop', body)
        db.expire_all()
        receipt = db.get(MeetingSessionCommand, body.command_id)
        assert receipt.status == 'prepared' and receipt.body['_native_drain_confirmed'] is False
        with pytest.raises(HTTPException) as rejected:
            routes.perform(db, row['id'], 'stop', body)
        assert rejected.value.status_code == 409
        assert db.get(MeetingSessionCommand, body.command_id).status == 'rejected'
        assert hardware[1] == ['start', 'stop']
        assert db.scalar(select(func.count()).select_from(MeetingAudioChunk)) == 1


def test_native_stop_recovers_between_parent_and_finalization(stores, hardware, monkeypatch):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        routes.perform(db, row['id'], 'start', routes.Start(command_id=key(), expected_revision=1, tracks=['mic']))
        body = Command(command_id=key(), expected_revision=2)
        finish = routes.finalize_stop
        monkeypatch.setattr(routes, 'finalize_stop', lambda *args: (_ for _ in ()).throw(RuntimeError('lost parent response')))
        with pytest.raises(RuntimeError):
            routes.perform(db, row['id'], 'stop', body)
        db.rollback()
        assert db.get(MeetingSessionCommand, body.command_id).status == 'completed'
        monkeypatch.setattr(routes, 'finalize_stop', finish)
        result = routes.perform(db, row['id'], 'stop', body)
        assert result['state'] == 'completed'
        assert routes.perform(db, row['id'], 'stop', body) == result
        assert hardware[1] == ['start', 'stop']
        assert db.scalar(select(func.count()).select_from(MeetingAudioChunk)) == 1


def test_native_stop_child_commit_lost_response_reuses_exact_child(stores, hardware, monkeypatch):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        routes.perform(db, row['id'], 'start', routes.Start(command_id=key(), expected_revision=1, tracks=['mic']))
        body = Command(command_id=key(), expected_revision=2)
        execute = sessions.execute_command
        def committed(*args, **kwargs):
            execute(*args, **kwargs)
            raise RuntimeError('lost child response')
        monkeypatch.setattr(sessions, 'execute_command', committed)
        with pytest.raises(RuntimeError):
            routes.perform(db, row['id'], 'stop', body)
        monkeypatch.setattr(sessions, 'execute_command', execute)
        result = routes.perform(db, row['id'], 'stop', body)
        assert result['state'] == 'completed'
        assert hardware[1] == ['start', 'stop']
        assert db.scalar(select(func.count()).select_from(MeetingSessionCommand).where(MeetingSessionCommand.kind == 'finalize')) == 1


def test_native_uuid_revision_tracks_validation(stores, hardware):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
    http = client(brain)
    url = f"/api/v1/meeting-sessions/{row['id']}/native-capture/start"
    valid = {'command_id': key(), 'expected_revision': 1, 'tracks': ['mic']}
    for changes in [{'command_id': 'wrong'}, {'tracks': ['mic', 'mic']}, {'devices': {'mic': -1}}, {'extra': True}]:
        assert http.post(url, json={**valid, **changes}).status_code == 422
    assert http.post(url, json={**valid, 'expected_revision': 2}).status_code == 409
    assert hardware[1] == []


def test_native_scopes_readers_and_status_do_not_leak(stores, hardware):
    brain, _, pid, _ = stores
    with brain() as db:
        row = create(db, project_id=pid)
        body = routes.Start(command_id=key(), expected_revision=1, tracks=['mic'])
        with operator_context(Operator('restricted', 'editor', frozenset())):
            with pytest.raises(HTTPException) as caught:
                routes.perform(db, row['id'], 'start', body)
            assert caught.value.status_code == 404
            hardware[0][row['id']] = SimpleNamespace(state='recording', tracks=['mic'], process=None)
            assert routes.status(db)['active'] == []
            hardware[0].clear()
        with operator_context(Operator('reader', 'reader', frozenset([pid]))):
            with pytest.raises(HTTPException) as caught:
                routes.perform(db, row['id'], 'start', body)
            assert caught.value.status_code == 403
    assert hardware[1] == []


def test_native_failed_start_is_interrupted_and_exact_retry(stores, hardware, monkeypatch):
    brain, _, _, _ = stores
    start = native.start_capture
    monkeypatch.setattr(native, 'start_capture', lambda *args, **kwargs: (_ for _ in ()).throw(HTTPException(409, 'hardware unavailable')))
    with brain() as db:
        row = create(db)
        body = routes.Start(command_id=key(), expected_revision=1, tracks=['mic'])
        with pytest.raises(HTTPException):
            routes.perform(db, row['id'], 'start', body)
        saved = sessions.serialize_session(db, sessions.get_session(db, row['id']))
        assert saved['state'] == 'interrupted' and saved['pending_command']['id'] == body.command_id
        monkeypatch.setattr(native, 'start_capture', start)
        assert routes.perform(db, row['id'], 'start', body)['state'] == 'recording'
        assert hardware[1] == ['start']


def test_concurrent_native_stop_same_command_drains_once(stores, hardware):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        routes.perform(db, row['id'], 'start', routes.Start(command_id=key(), expected_revision=1, tracks=['mic']))
    body = Command(command_id=key(), expected_revision=2)
    barrier = Barrier(2)
    def stop():
        with brain() as db:
            barrier.wait(timeout=5)
            return routes.perform(db, row['id'], 'stop', body)
    with ThreadPoolExecutor(max_workers=2) as executor:
        jobs = [executor.submit(stop) for _ in range(2)]
        results = [job.result(timeout=10) for job in jobs]
    assert results[0] == results[1] and results[0]['state'] == 'completed'
    assert hardware[1] == ['start', 'stop']


def test_disabled_feature_allows_native_pause_stop_and_buffer_drain(stores, hardware, monkeypatch):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        begin = routes.Start(command_id=key(), expected_revision=1, tracks=['mic'])
        started = routes.perform(db, row['id'], 'start', begin)
        monkeypatch.setenv('AGENT_MEETING_SESSIONS_ENABLED', '0')
        assert routes.perform(db, row['id'], 'start', begin) == started
        paused = routes.perform(db, row['id'], 'pause', Command(command_id=key(), expected_revision=2))
        with pytest.raises(HTTPException) as caught:
            routes.perform(db, row['id'], 'resume', Command(command_id=key(), expected_revision=paused['revision']))
        assert caught.value.status_code == 409
        ended = routes.perform(db, row['id'], 'stop', Command(command_id=key(), expected_revision=paused['revision']))
        assert ended['state'] == 'completed' and hardware[1] == ['start', 'pause', 'stop']
        assert db.scalar(select(func.count()).select_from(MeetingAudioChunk)) == 1
