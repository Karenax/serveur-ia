"""Real SQLite ownership/HTTP/concurrency, with all media/native work forbidden."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.db import get_db
from app.meeting_session_models import MeetingSession, MeetingSessionCommand, MeetingSessionEvent
from app.meeting_session_schemas import BrowserCaptureReservation, CaptureControl, SessionNoteSave
from app.routers import native_capture
from app.routers.meeting_sessions import router
from app.security import local_guard
from app.services import browser_capture as capture, meeting_sessions as sessions, native_audio
from backend.app.services.project_operator import Operator, operator_context
from tests.test_meeting_sessions import stores as stores_fixture, create, key, chunk, content
from tests.test_native_capture_router import hardware as hardware_fixture

stores = stores_fixture
hardware = hardware_fixture


@pytest.fixture(autouse=True)
def forbid_hardware(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('No real native media/runtime is permitted')
    monkeypatch.setattr(native_audio, '_captures', {})
    monkeypatch.setattr(native_audio, 'inventory', forbidden)
    monkeypatch.setattr(native_audio.NativeCapture, 'start', forbidden)


def reserve(db, sid, revision, owner=None, command=None):
    body = BrowserCaptureReservation(command_id=command or key(), expected_revision=revision, owner_id=owner or key())
    return capture.perform(db, sid, 'reserve', body), body


def release(db, row, owner, command=None):
    return capture.perform(db, row['id'], 'release', BrowserCaptureReservation(
        command_id=command or key(), expected_revision=row['revision'], owner_id=owner))


def control(db, row, action, token=None):
    return sessions.execute_command(db, row['id'], action, CaptureControl(command_id=key(),
        expected_revision=row['revision'], browser_capture_owner_id=token))


def http_client(brain):
    app = FastAPI()
    app.middleware('http')(local_guard)
    app.include_router(router)
    app.include_router(native_capture.router)
    def dependency():
        with brain() as db:
            yield db
    app.dependency_overrides[get_db] = dependency
    return TestClient(app)


def test_reservation_and_receipt_are_atomic_and_replay_does_not_create_owner(stores):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        first, body = reserve(db, row['id'], 1)
        assert first['state'] == 'created'
        assert first['browser_capture'] == {'session_id': row['id'], 'owner_id': body.owner_id,
            'can_control': True, 'state': 'reserved'}
        assert capture.perform(db, row['id'], 'reserve', body) == first
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(
            MeetingSessionEvent.kind == capture.OWNER)) == 1
        receipt = db.get(MeetingSessionCommand, body.command_id)
        assert receipt.status == 'completed' and receipt.result == first


def test_owner_survives_pause_restart_and_generic_finalize_cancel(stores):
    brain, _, _, _ = stores
    with brain() as db:
        row, body = reserve(db, create(db)['id'], 1)
        row = control(db, row, 'resume', body.owner_id)
        row = control(db, row, 'pause', body.owner_id)
        assert row['state'] == 'paused' and row['browser_capture']['owner_id'] == body.owner_id
        sessions.recover_interrupted(db)
        assert capture.active_owners(db)[row['id']].data['owner_id'] == body.owner_id
        for action in ['resume', 'pause', 'finalize', 'cancel']:
            with pytest.raises(HTTPException) as error:
                control(db, row, action)
            assert error.value.status_code == 409
        assert db.get(MeetingSession, row['id']).pending_command_id is None
    with brain() as db:
        assert capture.active_owners(db)[row['id']].data['owner_id'] == body.owner_id


@pytest.mark.parametrize('initial', ['created', 'recording', 'paused'])
def test_release_after_closed_media_keeps_originals_and_no_implicit_finalize(stores, initial):
    brain, _, _, _ = stores
    with brain() as db:
        row, body = reserve(db, create(db)['id'], 1)
        if initial in {'recording', 'paused'}:
            row = control(db, row, 'resume', body.owner_id)
            chunk(db, row['id'])
            row = sessions.serialize_session(db, sessions.get_session(db, row['id']))
        if initial == 'paused':
            row = control(db, row, 'pause', body.owner_id)
        before = row['chunks']
        ended = release(db, row, body.owner_id)
        assert ended['browser_capture'] is None
        assert ended['state'] == ('created' if initial == 'created' else 'interrupted')
        assert ended['chunks'] == before and ended['recording_id'] is None
        assert not capture.active_owners(db)


def test_wrong_owner_neither_releases_nor_controls_and_used_nonce_cannot_reopen(stores):
    brain, _, _, _ = stores
    with brain() as db:
        row, body = reserve(db, create(db)['id'], 1)
        for attempt in [lambda: release(db, row, key()), lambda: control(db, row, 'resume', key())]:
            with pytest.raises(HTTPException) as error:
                attempt()
            assert error.value.status_code == 409
        ended = release(db, row, body.owner_id)
        with pytest.raises(HTTPException):
            capture.perform(db, row['id'], 'reserve', body)
        with pytest.raises(HTTPException):
            reserve(db, row['id'], ended['revision'], body.owner_id)
        assert not capture.active_owners(db)


def test_release_replay_does_not_release_new_owner_or_mutate_its_revision(stores):
    brain, _, _, _ = stores
    with brain() as db:
        row, body = reserve(db, create(db)['id'], 1)
        release_body = BrowserCaptureReservation(command_id=key(), expected_revision=row['revision'], owner_id=body.owner_id)
        ended = capture.perform(db, row['id'], 'release', release_body)
        other, new_body = reserve(db, row['id'], ended['revision'])
        assert capture.perform(db, row['id'], 'release', release_body) == ended
        assert capture.active_owners(db)[row['id']].data['owner_id'] == new_body.owner_id
        assert db.get(MeetingSession, row['id']).revision == other['revision']


def test_lost_reserve_response_is_recovered_with_same_uuid_before_release(stores, monkeypatch):
    brain, _, _, _ = stores
    original = sessions._finish
    def response_lost(*args, **kwargs):
        original(*args, **kwargs)
        raise ConnectionError('Response lost after the real SQL commit')
    with brain() as db:
        sid = create(db)['id']
        body = BrowserCaptureReservation(command_id=key(), expected_revision=1, owner_id=key())
        with monkeypatch.context() as patch:
            patch.setattr(sessions, '_finish', response_lost)
            with pytest.raises(ConnectionError):
                capture.perform(db, sid, 'reserve', body)
    with brain() as db:
        recovered = capture.perform(db, sid, 'reserve', body)
        assert recovered['browser_capture']['owner_id'] == body.owner_id
        assert release(db, recovered, body.owner_id)['browser_capture'] is None


@pytest.mark.parametrize('same_command', [False, True])
def test_two_sqlite_threads_reserve_once_same_session(stores, same_command):
    brain, _, _, _ = stores
    with brain() as db:
        sid = create(db)['id']
    bodies = [BrowserCaptureReservation(command_id=key(), expected_revision=1, owner_id=key()) for _ in range(2)]
    if same_command:
        bodies[1] = bodies[0]
    barrier = Barrier(2)
    def run(body):
        with brain() as db:
            barrier.wait(timeout=5)
            try:
                return capture.perform(db, sid, 'reserve', body)
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, bodies))
    assert sum(isinstance(result, dict) for result in results) == (2 if same_command else 1)
    with brain() as db:
        assert len(capture.active_owners(db)) == 1
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(
            MeetingSessionEvent.kind == capture.OWNER)) == 1


def test_two_sqlite_threads_different_sessions_cannot_both_reserve(stores):
    brain, _, _, _ = stores
    with brain() as db:
        ids = [create(db)['id'], create(db)['id']]
    barrier = Barrier(2)
    def run(sid):
        with brain() as db:
            # Deliberately load both rows before either thread owns the writer.
            sessions.get_session(db, sid)
            barrier.wait(timeout=5)
            try:
                return reserve(db, sid, 1)[0]
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, ids))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert 409 in results


@pytest.mark.parametrize('paused', [False, True])
def test_explicit_browser_owner_blocks_native_other_or_same_sid(stores, hardware, paused):
    brain, _, _, _ = stores
    with brain() as db:
        row, body = reserve(db, create(db)['id'], 1)
        if paused:
            row = control(db, row, 'resume', body.owner_id)
            row = control(db, row, 'pause', body.owner_id)
        other = create(db)
        for target in [row, other]:
            with pytest.raises(HTTPException) as error:
                native_capture.perform(db, target['id'], 'start', native_capture.Start(
                    command_id=key(), expected_revision=target['revision'], tracks=['mic']))
            assert error.value.status_code == 409
        assert hardware[1] == []


@pytest.mark.parametrize('same_session', [False, True])
def test_native_recording_commit_blocks_browser_before_helper_registry(stores, hardware, monkeypatch, same_session):
    brain, _, _, _ = stores
    ready, finish = Event(), Event()
    original = native_audio.start_capture
    def held(db, sid, **kwargs):
        assert not native_audio.has_capture_owner()
        ready.set()
        assert finish.wait(5)
        return original(db, sid, **kwargs)
    monkeypatch.setattr(native_audio, 'start_capture', held)
    with brain() as db:
        target, browser = create(db), create(db)
        if same_session:
            browser = target
    def start():
        with brain() as db:
            return native_capture.perform(db, target['id'], 'start', native_capture.Start(
                command_id=key(), expected_revision=1, tracks=['mic']))
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(start)
        assert ready.wait(5)
        try:
            with brain() as db:
                assert db.get(MeetingSession, target['id']).state == 'recording'
                assert not native_audio.has_capture_owner()
                with pytest.raises(HTTPException) as error:
                    reserve(db, browser['id'], 1)
                assert error.value.status_code == 409
                with pytest.raises(HTTPException) as error:
                    control(db, browser, 'resume')
                assert error.value.status_code == 409
        finally:
            finish.set()
        assert future.result(timeout=5)['state'] == 'recording'


def test_old_drafts_do_not_block_but_legacy_recording_cannot_coexist(stores, hardware):
    brain, _, _, _ = stores
    with brain() as db:
        draft = create(db)
        saved = db.get(MeetingSession, draft['id'])
        saved.state = 'paused'
        db.commit()
        row, body = reserve(db, create(db)['id'], 1)
        assert row['browser_capture']['owner_id'] == body.owner_id
        ended = release(db, row, body.owner_id)
        control(db, ended, 'resume')  # Legacy import/API contract still exists.
        other = create(db)
        with pytest.raises(HTTPException):
            control(db, other, 'resume')
        with pytest.raises(HTTPException):
            native_capture.perform(db, other['id'], 'start', native_capture.Start(command_id=key(), expected_revision=1, tracks=['mic']))
        assert hardware[1] == []


def test_fresh_operator_rights_scope_and_origin_apply_to_reserve_release(stores):
    brain, _, pid, _ = stores
    with operator_context(Operator('owner', 'owner')), brain() as db:
        row = create(db, project_id=pid)
        row, body = reserve(db, row['id'], 1)
    for operator in [Operator('owner', 'reader'), Operator('owner', 'editor', frozenset()), Operator('other', 'owner')]:
        with operator_context(operator), brain() as db:
            with pytest.raises(HTTPException):
                release(db, row, body.owner_id)
            snapshot = sessions.serialize_session(db, sessions.get_session(db, row['id'])) if operator.project_ids is None else None
            if snapshot:
                assert snapshot['browser_capture']['owner_id'] is None
    http = http_client(brain)
    invalid = http.post(f"/api/v1/meeting-sessions/{row['id']}/browser-capture/release",
        json={'command_id': key(), 'expected_revision': row['revision'], 'owner_id': body.owner_id},
        headers={'Origin': 'https://untrusted.example'})
    assert invalid.status_code == 403


def test_browser_reservation_blocks_batch_and_release_is_available_when_flag_off(stores, monkeypatch):
    from app.services.audio_cpu_coordinator import AudioCpuBusy, ensure_batch_available
    brain, _, _, _ = stores
    with brain() as db:
        row, body = reserve(db, create(db)['id'], 1)
        with pytest.raises(AudioCpuBusy):
            ensure_batch_available(db)
        monkeypatch.setenv('AGENT_MEETING_SESSIONS_ENABLED', '0')
        assert release(db, row, body.owner_id)['browser_capture'] is None


@pytest.mark.parametrize('operation', ['start', 'pause', 'resume', 'stop'])
def test_native_control_cannot_trap_browser_release_with_pending_command(stores, hardware, operation):
    brain, _, _, _ = stores
    with brain() as db:
        row, body = reserve(db, create(db)['id'], 1)
        model = native_capture.Start if operation == 'start' else CaptureControl
        args = {'tracks': ['mic']} if operation == 'start' else {}
        with pytest.raises(HTTPException) as error:
            native_capture.perform(db, row['id'], operation,
                model(command_id=key(), expected_revision=row['revision'], **args))
        assert error.value.status_code == 409
        assert db.get(MeetingSession, row['id']).pending_command_id is None
        assert release(db, row, body.owner_id)['browser_capture'] is None
        assert hardware[1] == []


def test_reserve_during_real_batch_admission_returns_409_before_any_owner(stores, monkeypatch):
    from app.services import audio_cpu_coordinator
    brain, _, _, _ = stores
    monkeypatch.setattr(audio_cpu_coordinator, '_batch_owner', ('fictitious-batch', object()))
    with brain() as db:
        row = create(db)
        with pytest.raises(HTTPException) as error:
            reserve(db, row['id'], 1)
        assert error.value.status_code == 409
        assert not capture.active_owners(db)


@pytest.mark.parametrize('paused', [False, True])
def test_offline_copy_freezes_owner_without_releasing_original_or_replaying_receipts(stores, tmp_path, paused):
    from app.db_support import backup_sqlite, configure_sqlite
    from app.services.meeting_session_backup import relocate
    brain, _, _, _ = stores
    with brain() as db:
        row, body = reserve(db, create(db)['id'], 1)
        if paused:
            row = control(db, row, 'resume', body.owner_id)
            chunk(db, row['id'])
            row = sessions.serialize_session(db, sessions.get_session(db, row['id']))
            row = control(db, row, 'pause', body.owner_id)
        source = db.get_bind().url.database
        original_receipt = db.get(MeetingSessionCommand, body.command_id).result
    copied = tmp_path / 'restored-brain.db'
    backup_sqlite(source, copied)
    relocate(copied, tmp_path / 'restored', {})
    engine = create_engine('sqlite:///' + copied.as_posix())
    configure_sqlite(engine)
    restored = sessionmaker(bind=engine)
    try:
        with restored() as db:
            assert not capture.active_owners(db)
            assert db.get(MeetingSession, row['id']).state == ('interrupted' if paused else 'created')
            assert db.get(MeetingSessionCommand, body.command_id).result == original_receipt
            assert db.scalar(select(MeetingSessionEvent).where(MeetingSessionEvent.kind == capture.OWNER))
            frozen = db.scalar(select(MeetingSessionEvent).where(MeetingSessionEvent.kind == capture.FROZEN_ON_COPY))
            assert frozen.data['owner_id'] == body.owner_id
            assert 'physical streams not observed' in frozen.data['reason']
    finally:
        engine.dispose()
    with brain() as db:
        assert capture.active_owners(db)[row['id']].data['owner_id'] == body.owner_id
        assert not db.scalar(select(MeetingSessionEvent).where(MeetingSessionEvent.kind == capture.FROZEN_ON_COPY))


@pytest.mark.parametrize('operation', ['pause', 'cancel', 'resume', 'finalize'])
def test_generic_controls_cannot_modify_windows_owner_or_stop_its_acknowledgments(stores, hardware, operation):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        started = native_capture.perform(db, row['id'], 'start', native_capture.Start(
            command_id=key(), expected_revision=1, tracks=['mic']))
        with pytest.raises(HTTPException) as error:
            control(db, started, operation)
        assert error.value.status_code == 409
        assert db.get(MeetingSession, row['id']).state == 'recording'
        assert db.get(MeetingSession, row['id']).pending_command_id is None
        assert hardware[1] == ['start']


def test_old_tokenized_resume_receipt_cannot_acknowledge_reopening_after_release(stores):
    brain, _, _, _ = stores
    with brain() as db:
        row, body = reserve(db, create(db)['id'], 1)
        resume = CaptureControl(command_id=key(), expected_revision=row['revision'], browser_capture_owner_id=body.owner_id)
        active = sessions.execute_command(db, row['id'], 'resume', resume)
        ended = release(db, active, body.owner_id)
        new, new_body = reserve(db, row['id'], ended['revision'])
        with pytest.raises(HTTPException) as error:
            sessions.execute_command(db, row['id'], 'resume', resume)
        assert error.value.status_code == 409
        assert db.get(MeetingSessionCommand, resume.command_id).result == active
        assert capture.active_owners(db)[row['id']].data['owner_id'] == new_body.owner_id
        assert db.get(MeetingSession, row['id']).revision == new['revision']


def test_native_and_browser_threads_compete_on_same_admission_and_sql_writer(stores, hardware):
    brain, _, _, _ = stores
    with brain() as db:
        a, b = create(db), create(db)
    barrier = Barrier(2)
    def run(browser):
        with brain() as db:
            barrier.wait(timeout=5)
            try:
                if browser:
                    return reserve(db, b['id'], 1)[0]
                return native_capture.perform(db, a['id'], 'start', native_capture.Start(
                    command_id=key(), expected_revision=1, tracks=['mic']))
            except HTTPException as error:
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, [False, True]))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert 409 in results
    with brain() as db:
        assert bool(capture.active_owners(db)) != bool(hardware[1])


def test_reservation_revision_uuid_and_cross_session_receipt_are_closed_contracts(stores):
    brain, _, _, _ = stores
    with brain() as db:
        a, b = create(db), create(db)
        row, body = reserve(db, a['id'], 1)
        with pytest.raises(HTTPException) as error:
            capture.perform(db, b['id'], 'reserve', body)
        assert error.value.status_code == 409
        with pytest.raises(HTTPException):
            release(db, {**row, 'revision': 1}, body.owner_id)
        assert capture.active_owners(db)[a['id']].data['owner_id'] == body.owner_id
    http = http_client(brain)
    invalid = http.post(f"/api/v1/meeting-sessions/{a['id']}/browser-capture/release",
        json={'command_id': key(), 'expected_revision': row['revision'], 'owner_id': 'invalid'})
    assert invalid.status_code == 422


def test_legacy_pause_before_first_chunk_blocks_same_or_other_sid_until_conservation(stores, hardware):
    brain, _, _, _ = stores
    with brain() as db:
        legacy = control(db, create(db), 'resume')
        legacy = control(db, legacy, 'pause')
        assert legacy['chunks'] == [] and legacy['browser_capture'] is None
        other = create(db)
        for row in [legacy, other]:
            with pytest.raises(HTTPException) as error:
                reserve(db, row['id'], row['revision'])
            assert error.value.status_code == 409
            with pytest.raises(HTTPException) as error:
                native_capture.perform(db, row['id'], 'start', native_capture.Start(
                    command_id=key(), expected_revision=row['revision'], tracks=['mic']))
            assert error.value.status_code == 409
        assert hardware[1] == []
        # Existing legacy capture may resume/pause/finalize, without a new mic.
        legacy = control(db, legacy, 'resume')
        legacy = control(db, legacy, 'pause')
        control(db, legacy, 'finalize')
        assert reserve(db, other['id'], 1)[0]['browser_capture']


def test_refused_reserve_is_durable_without_changing_business_data_or_pending(stores):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        body = BrowserCaptureReservation(command_id=key(), expected_revision=2, owner_id=key())
        with pytest.raises(HTTPException) as error:
            capture.perform(db, row['id'], 'reserve', body)
        assert error.value.detail['rejected_command_id'] == body.command_id
        receipt = db.get(MeetingSessionCommand, body.command_id)
        assert receipt.kind == 'browser.reserve' and receipt.status == 'rejected'
        assert receipt.body == body.model_dump() and receipt.digest == sessions._digest('browser.reserve', body.model_dump())
        fresh = db.get(MeetingSession, row['id'])
        assert (fresh.state, fresh.revision, fresh.pending_command_id) == ('created', 1, None)
        assert not capture.active_owners(db)
        # Even after the formerly stale revision becomes current, the old
        # rejected command and owner UUID cannot become media authority.
        changed = sessions.execute_command(db, row['id'], 'notes', SessionNoteSave(command_id=key(),
            expected_revision=1, title='Human note retained', content=content('Original human text')))
        assert changed['revision'] == 2
        with pytest.raises(HTTPException) as replay:
            capture.perform(db, row['id'], 'reserve', body)
        assert replay.value.detail == error.value.detail
        with pytest.raises(HTTPException) as reused:
            reserve(db, row['id'], 2, owner=body.owner_id)
        assert reused.value.detail['rejected_command_id'] != body.command_id
        assert db.get(MeetingSession, row['id']).staged_note == changed['staged_note']
        assert reserve(db, row['id'], 2)[0]['browser_capture']


def test_refused_reserve_receipt_is_available_over_http_and_auth_refusals_reveal_none(stores):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
    http = http_client(brain)
    body = {'command_id': key(), 'expected_revision': 2, 'owner_id': key()}
    response = http.post(f"/api/v1/meeting-sessions/{row['id']}/browser-capture/reserve", json=body)
    assert response.status_code == 409
    assert response.json()['detail']['rejected_command_id'] == body['command_id']
    receipt = http.get(f"/api/v1/meeting-sessions/{row['id']}/commands/{body['command_id']}")
    assert receipt.status_code == 200
    assert {name: receipt.json()[name] for name in ['id', 'kind', 'status']} == {
        'id': body['command_id'], 'kind': 'browser.reserve', 'status': 'rejected'}
    with operator_context(Operator('local', 'reader')), brain() as db:
        forbidden = BrowserCaptureReservation(command_id=key(), expected_revision=1, owner_id=key())
        with pytest.raises(HTTPException) as error:
            capture.perform(db, row['id'], 'reserve', forbidden)
        assert error.value.status_code == 403
        assert db.get(MeetingSessionCommand, forbidden.command_id) is None


def test_lost_refusal_response_replays_same_refused_nonce_without_opening(stores, monkeypatch):
    brain, _, _, _ = stores
    original = capture.durable_reserve_refusal
    def lost(*args, **kwargs):
        original(*args, **kwargs)
        raise ConnectionError('Refusal response lost after its SQL commit')
    with brain() as db:
        row = create(db)
        body = BrowserCaptureReservation(command_id=key(), expected_revision=2, owner_id=key())
        with monkeypatch.context() as patch:
            patch.setattr(capture, 'durable_reserve_refusal', lost)
            with pytest.raises(ConnectionError):
                capture.perform(db, row['id'], 'reserve', body)
    with brain() as db:
        with pytest.raises(HTTPException) as replay:
            capture.perform(db, row['id'], 'reserve', body)
        assert replay.value.detail['rejected_command_id'] == body.command_id
        assert db.get(MeetingSessionCommand, body.command_id).status == 'rejected'
        assert not capture.active_owners(db)


def test_collision_cannot_claim_rejected_ack_of_another_payload_or_session(stores):
    brain, _, _, _ = stores
    with brain() as db:
        a, b = create(db), create(db)
        body = BrowserCaptureReservation(command_id=key(), expected_revision=2, owner_id=key())
        with pytest.raises(HTTPException):
            capture.perform(db, a['id'], 'reserve', body)
        for sid, wrong in [(a['id'], BrowserCaptureReservation(command_id=body.command_id,
                expected_revision=1, owner_id=key())), (b['id'], body)]:
            with pytest.raises(HTTPException) as error:
                capture.perform(db, sid, 'reserve', wrong)
            assert isinstance(error.value.detail, str)
        assert db.get(MeetingSessionCommand, body.command_id).body == body.model_dump()
        assert not capture.active_owners(db)


def test_native_busy_rejection_cannot_become_reserve_after_native_stop(stores, hardware):
    brain, _, _, _ = stores
    with brain() as db:
        win, browser = create(db), create(db)
        active = native_capture.perform(db, win['id'], 'start', native_capture.Start(
            command_id=key(), expected_revision=1, tracks=['mic']))
        body = BrowserCaptureReservation(command_id=key(), expected_revision=1, owner_id=key())
        with pytest.raises(HTTPException) as error:
            capture.perform(db, browser['id'], 'reserve', body)
        assert error.value.detail['rejected_command_id'] == body.command_id
        native_capture.perform(db, win['id'], 'stop', CaptureControl(command_id=key(), expected_revision=active['revision']))
        with pytest.raises(HTTPException) as replay:
            capture.perform(db, browser['id'], 'reserve', body)
        assert replay.value.detail == error.value.detail
        assert reserve(db, browser['id'], 1)[0]['browser_capture']


def test_refusal_keeps_sqlite_writer_until_rejected_nonce_is_durable(stores, monkeypatch):
    brain, _, _, _ = stores
    original = capture.durable_reserve_refusal
    checked = []
    def check_writer(db, *args):
        # This connection has no Python admission/session locks. A rollback
        # that released the writer before storing rejected would let it enter.
        with sqlite3.connect(db.get_bind().url.database, timeout=0) as independent:
            with pytest.raises(sqlite3.OperationalError, match='locked'):
                independent.execute('BEGIN IMMEDIATE')
        checked.append(True)
        return original(db, *args)
    monkeypatch.setattr(capture, 'durable_reserve_refusal', check_writer)
    with brain() as db:
        row = create(db)
        body = BrowserCaptureReservation(command_id=key(), expected_revision=2, owner_id=key())
        with pytest.raises(HTTPException) as error:
            capture.perform(db, row['id'], 'reserve', body)
        assert checked == [True]
        assert error.value.detail['rejected_command_id'] == body.command_id


def test_durable_cpu_refusal_holds_admission_against_same_owner_competitor(stores, monkeypatch):
    from app.services import audio_cpu_coordinator as coordinator
    brain, _, _, _ = stores
    original = capture.durable_reserve_refusal
    entered, release_refusal, competitor_started = Event(), Event(), Event()
    with brain() as db:
        sid = create(db)['id']
    owner = key()
    bodies = [BrowserCaptureReservation(command_id=key(), expected_revision=1, owner_id=owner) for _ in range(2)]
    def held(db, identity, body, error):
        if body.command_id == bodies[0].command_id:
            assert coordinator._guard._is_owned()
            entered.set()
            assert release_refusal.wait(5)
        return original(db, identity, body, error)
    monkeypatch.setattr(capture, 'durable_reserve_refusal', held)
    monkeypatch.setattr(coordinator, '_batch_owner', ('fictitious-batch', object()))
    def attempt(index):
        with brain() as db:
            if index:
                competitor_started.set()
            try:
                return capture.perform(db, sid, 'reserve', bodies[index])
            except HTTPException as error:
                return error
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(attempt, 0)
        assert entered.wait(5)
        # Simulate completion of the formerly blocking resource while its
        # refused capture still must commit its nonce under the admission lock.
        monkeypatch.setattr(coordinator, '_batch_owner', None)
        second = pool.submit(attempt, 1)
        assert competitor_started.wait(5)
        try:
            assert not second.done()
        finally:
            release_refusal.set()
        results = [first.result(timeout=5), second.result(timeout=5)]
    assert all(isinstance(value, HTTPException) and value.status_code == 409 for value in results)
    with brain() as db:
        assert not capture.active_owners(db)
        assert all(db.get(MeetingSessionCommand, body.command_id).status == 'rejected' for body in bodies)
