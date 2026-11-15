"""Explicit STT opt-in/retry/lifecycle on isolated DBs and fake residents only."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import threading
import time
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
import pytest
from sqlalchemy import func, select

from app.meeting_session_models import (LiveTranscriptSegment, MeetingAudioChunk,
                                       MeetingSession, MeetingSessionCommand, MeetingSessionEvent)
from app.meeting_session_schemas import Command
from app.services import live_speech as live, meeting_sessions as sessions
from app.services.settings_service import save_section
from backend.app.services.project_operator import Operator, current_operator, operator_context
from tests.test_meeting_sessions import stores, create, chunk

__all__ = ['stores']


@pytest.fixture(autouse=True)
def fake_lifecycle(monkeypatch, request, tmp_path):
    if 'stores' in request.fixturenames:
        request.getfixturevalue('stores')
        from app.config import settings
        monkeypatch.setattr(settings, 'storage_dir', str(tmp_path.parent / ('s-' + uuid4().hex[:8])))
    monkeypatch.setattr(live, '_stop', threading.Event())
    monkeypatch.setattr(live, '_wake', threading.Event())
    monkeypatch.setattr(live, '_thread', None)
    monkeypatch.setattr(live, '_resident', None)
    monkeypatch.setattr(live, '_desired_running', False)
    monkeypatch.setattr(live, '_closing', 0)
    monkeypatch.setattr(live, '_stop_generation', 0)
    monkeypatch.setattr(live, '_lifecycle_generation', 0)
    monkeypatch.setattr(live, '_metrics', {'processed_chunks': 0, 'failed_chunks': 0, 'last_compute_s': None})
    yield
    live.stop_worker()
    assert live._thread is None or not live._thread.is_alive()


def enabled(db, **changes):
    save_section(db, 'foresight', {'enabled': True, 'live_transcription_enabled': True, **changes})


def setup_chunk(db, status='pending'):
    row = create(db)
    chunk(db, row['id'])
    item = db.scalar(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == row['id']))
    item.speech_status = status
    db.commit()
    return row['id'], item.id


@pytest.mark.parametrize('legacy', [{}, {'live_transcription_enabled': False},
                                  {'live_transcription_enabled': 'true'}, {'live_transcription_enabled': 1}])
def test_general_enabled_and_legacy_values_do_not_opt_in(stores, legacy, monkeypatch):
    from app.routers.fusion_insights import Controls, configure
    monkeypatch.setattr(sessions, 'capabilities', lambda db: {})
    brain = stores[0]
    with brain() as db:
        stored = Controls(enabled=True).model_dump()
        stored.pop('live_transcription_enabled')
        save_section(db, 'foresight', {**stored, **legacy})
        assert sessions.feature_enabled(db)
        assert sessions.live_transcription_enabled(db) is False
        configure(Controls(enabled=True, live_transcription_enabled=True), db)
        assert sessions.live_transcription_enabled(db) is True
        with brain() as fresh:
            assert sessions.live_transcription_enabled(fresh) is True
        enabled(db, enabled=False)
        assert sessions.live_transcription_enabled(db) is False


def test_disabled_start_does_not_repair_running_or_instantiate_resident(stores, monkeypatch):
    brain = stores[0]
    with brain() as db:
        _, cid = setup_chunk(db, 'running')
        save_section(db, 'foresight', {'enabled': True})
    monkeypatch.setattr(live, 'ResidentWhisper', lambda *args: pytest.fail('No model while direct disabled'))
    assert live.start_worker() is False
    assert live._thread is None
    with brain() as db:
        assert db.get(MeetingAudioChunk, cid).speech_status == 'running'
        assert live.process_chunk(cid) is False
        assert db.get(MeetingAudioChunk, cid).speech_status == 'running'
    with pytest.raises(HTTPException) as refused:
        live.warm_up()
    assert refused.value.status_code == 409


def test_admission_rechecks_opt_in_after_outer_check_before_claim(stores, monkeypatch):
    brain = stores[0]
    with brain() as db:
        enabled(db)
        _, cid = setup_chunk(db)
    @contextmanager
    def revoke_at_admission():
        with brain() as db:
            enabled(db, live_transcription_enabled=False)
        yield
    monkeypatch.setattr('app.services.audio_cpu_coordinator.direct_speech', revoke_at_admission)
    monkeypatch.setattr(live.audio_capture, 'prepare_chunk', lambda *args, **kwargs: pytest.fail('No decode after opt-out'))
    assert live.process_chunk(cid) is False
    with brain() as db:
        assert db.get(MeetingAudioChunk, cid).speech_status == 'pending'


def test_retry_admits_failed_and_retained_and_replays_exact_immutable_receipt(stores, monkeypatch):
    brain = stores[0]
    wakes = []
    monkeypatch.setattr(live, 'wake_worker', lambda: wakes.append('after-commit'))
    with brain() as db:
        enabled(db)
        sid, _ = setup_chunk(db, 'failed')
        for index, state in enumerate(('pending', 'running', 'completed', 'failed', 'retained'), 1):
            chunk(db, sid, index, start_ms=index * 10)
            item = db.scalar(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == sid,
                                                            MeetingAudioChunk.sequence == index))
            item.speech_status = state
        db.flush()
        original = list(db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == sid)
                                  .order_by(MeetingAudioChunk.sequence)))
        saved = [(item.id, item.sha256, item.storage_path, item.size_bytes, item.speech_status) for item in original]
        segment = LiveTranscriptSegment(id='human-preserved', session_id=sid, chunk_id=original[0].id,
            track='mic', start_ms=0, end_ms=8, speaker='Human', text='Correction humaine', revision=7, finalized=True)
        db.add(segment)
        db.commit()
        wakes.clear()  # Upload ACKs legitimately wake the worker before this command.
        body = Command(command_id=str(uuid4()), expected_revision=1)
        result = sessions.retry_transcription(db, sid, body)
        assert result['retried_chunks'] == 3
        assert result['chunk_ids'] == [saved[0][0], saved[4][0], saved[5][0]]
        assert result['remaining_recoverable_chunks'] == 0
        assert result['session']['revision'] == 2
        assert all(datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')).utcoffset() == timedelta(0)
                   for row in result['session']['chunks'])
        for cid, digest, path, size, state in saved:
            item = db.get(MeetingAudioChunk, cid)
            assert (item.sha256, item.storage_path, item.size_bytes) == (digest, path, size)
            assert item.speech_status == ('pending' if state in {'failed', 'retained'} else state)
        db.refresh(segment)
        assert (segment.text, segment.revision, segment.finalized) == ('Correction humaine', 7, True)
        event = db.scalar(select(MeetingSessionEvent).where(MeetingSessionEvent.kind == 'transcript.retry_requested'))
        assert event.data['retried_chunks'] == 3
        assert datetime.fromisoformat(event.data['requested_at_utc'].replace('Z', '+00:00')).utcoffset() == timedelta(0)
        db.get(MeetingAudioChunk, saved[0][0]).speech_status = 'completed'
        db.commit()
        assert sessions.retry_transcription(db, sid, body.model_dump()) == result
        assert db.get(MeetingAudioChunk, saved[0][0]).speech_status == 'completed'
        assert db.scalar(select(func.count()).select_from(MeetingSessionCommand).where(
            MeetingSessionCommand.kind == 'retry-transcription')) == 1
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(
            MeetingSessionEvent.kind == 'transcript.retry_requested')) == 1
        assert wakes == ['after-commit']
        # A completed receipt stays recoverable while the direct is off. It
        # must not requeue a new failure produced after the original retry.
        db.get(MeetingAudioChunk, saved[0][0]).speech_status = 'failed'
        db.commit()
        enabled(db, live_transcription_enabled=False)
        assert sessions.retry_transcription(db, sid, body) == result
        assert db.get(MeetingAudioChunk, saved[0][0]).speech_status == 'failed'
        assert wakes == ['after-commit']
        other = create(db)
        with pytest.raises(HTTPException) as wrong_session:
            sessions.retry_transcription(db, other['id'], body)
        assert wrong_session.value.status_code == 409
        enabled(db, enabled=False, live_transcription_enabled=False)
        assert sessions.retry_transcription(db, sid, body) == result
        assert db.get(MeetingAudioChunk, saved[0][0]).speech_status == 'failed'
        with pytest.raises(HTTPException) as conflict:
            sessions.retry_transcription(db, sid, Command(command_id=body.command_id, expected_revision=2))
        assert conflict.value.status_code == 409
        with operator_context(Operator(id=current_operator().id, role='reader')):
            with pytest.raises(HTTPException) as denied:
                sessions.retry_transcription(db, sid, body)
        assert denied.value.status_code == 403


@pytest.mark.parametrize('guard', ['general-off', 'direct-off', 'cancelled', 'other-operator'])
def test_retry_preconditions_leave_no_receipt_or_status_change(stores, guard):
    brain = stores[0]
    with brain() as db:
        enabled(db)
        sid, cid = setup_chunk(db, 'failed')
        if guard == 'general-off':
            enabled(db, enabled=False)
        elif guard == 'direct-off':
            enabled(db, live_transcription_enabled=False)
        elif guard == 'cancelled':
            db.get(MeetingSession, sid).state = 'cancelled'
            db.commit()
        body = Command(command_id=str(uuid4()), expected_revision=1)
        with operator_context(Operator(id='not-owner' if guard == 'other-operator' else current_operator().id, role='owner')):
            with pytest.raises(HTTPException) as refused:
                sessions.retry_transcription(db, sid, body)
        assert refused.value.status_code == (404 if guard == 'other-operator' else 409)
        assert db.get(MeetingAudioChunk, cid).speech_status == 'failed'
        assert db.get(MeetingSessionCommand, body.command_id) is None
        db.rollback()


def test_sql_failure_after_preparation_remains_recoverable(stores, monkeypatch):
    brain = stores[0]
    original_finish = sessions._finish
    with brain() as db:
        enabled(db)
        sid, cid = setup_chunk(db, 'failed')
    body = Command(command_id=str(uuid4()), expected_revision=1)
    def failed_commit(*args, **kwargs):
        raise RuntimeError('Fictitious storage failure before final commit')
    monkeypatch.setattr(sessions, '_finish', failed_commit)
    with pytest.raises(RuntimeError):
        with brain() as db:
            sessions.retry_transcription(db, sid, body)
    with brain() as db:
        assert db.get(MeetingSessionCommand, body.command_id).status == 'prepared'
        assert db.get(MeetingSession, sid).pending_command_id == body.command_id
        assert db.get(MeetingAudioChunk, cid).speech_status == 'failed'
    monkeypatch.setattr(sessions, '_finish', original_finish)
    with brain() as db:
        assert sessions.retry_transcription(db, sid, body)['retried_chunks'] == 1


def test_revoked_project_write_after_preparation_cannot_write_rejection(stores, monkeypatch):
    brain, _, pid, bid = stores
    with brain() as db:
        enabled(db)
        sid, cid = setup_chunk(db, 'failed')
        db.get(MeetingSession, sid).project_id = pid
        db.get(MeetingSession, sid).brain_project_id = bid
        db.commit()
    original_begin = sessions._begin
    blocked_project = str(uuid4())
    def prepare_then_move(*args, **kwargs):
        result = original_begin(*args, **kwargs)
        with brain() as changed:
            changed.get(MeetingSession, sid).project_id = blocked_project
            changed.commit()
        return result
    monkeypatch.setattr(sessions, '_begin', prepare_then_move)
    body = Command(command_id=str(uuid4()), expected_revision=1)
    with operator_context(Operator(id=current_operator().id, role='editor', project_ids=frozenset({pid}))):
        with pytest.raises(HTTPException) as denied:
            with brain() as db:
                sessions.retry_transcription(db, sid, body)
    assert denied.value.status_code == 404
    with brain() as db:
        assert db.get(MeetingSessionCommand, body.command_id).status == 'prepared'
        assert db.get(MeetingSession, sid).pending_command_id == body.command_id
        assert db.get(MeetingAudioChunk, cid).speech_status == 'failed'


def test_priority_recording_oldest_tracks_then_historical(stores):
    brain = stores[0]
    with brain() as db:
        enabled(db)
        old_sid, old_cid = setup_chunk(db)
        db.get(MeetingSession, old_sid).state = 'completed'
        active_sid, mic = setup_chunk(db)
        db.get(MeetingSession, active_sid).state = 'recording'
        chunk(db, active_sid, 0, track='system')
        system = db.scalar(select(MeetingAudioChunk.id).where(MeetingAudioChunk.session_id == active_sid,
                                                             MeetingAudioChunk.track == 'system'))
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        db.get(MeetingAudioChunk, old_cid).created_at = base
        db.get(MeetingAudioChunk, mic).created_at = base + timedelta(seconds=10)
        db.get(MeetingAudioChunk, system).created_at = base + timedelta(seconds=11)
        db.commit()
        assert live.pending_candidate(db) == mic
        db.get(MeetingAudioChunk, mic).speech_status = 'running'
        db.commit()
        assert live.pending_candidate(db) == system
        db.get(MeetingAudioChunk, system).speech_status = 'completed'
        db.commit()
        assert live.pending_candidate(db) == old_cid
        assert live.select_candidate('active', 'historical') == 'active'
        assert live.select_candidate(None, 'historical') == 'historical'


def test_opt_out_during_fake_compute_preserves_audio_and_suppresses_result(stores, monkeypatch):
    brain = stores[0]
    with brain() as db:
        enabled(db)
        _, cid = setup_chunk(db)
    class FakeResident:
        def transcribe(self, *args, **kwargs):
            with brain() as db:
                enabled(db, live_transcription_enabled=False)
            return {'segments': [{'start_ms': 0, 'end_ms': 8, 'speaker': 'mic', 'text': 'Obsolete'}],
                    'duration_ms': 10, 'compute_s': .01}
        def close(self):
            pass
    monkeypatch.setattr(live, '_resident', FakeResident())
    live.process_chunk(cid)
    with brain() as db:
        assert db.get(MeetingAudioChunk, cid).speech_status == 'pending'
        assert db.scalar(select(func.count()).select_from(LiveTranscriptSegment)) == 0


def test_stop_and_reenable_during_close_keep_single_consumer(stores, monkeypatch):
    brain = stores[0]
    with brain() as db:
        enabled(db)
        _, cid = setup_chunk(db)
    entered, close_entered, release_close, interrupted, completed = [threading.Event() for _ in range(5)]
    threads = []
    class OldResident:
        def transcribe(self, *args, **kwargs):
            threads.append(threading.get_ident())
            entered.set()
            assert interrupted.wait(3)
            raise InterruptedError('Deliberate fake shutdown')
        def close(self):
            close_entered.set()
            assert release_close.wait(3)
            interrupted.set()
    class NewResident:
        def transcribe(self, *args, **kwargs):
            threads.append(threading.get_ident())
            completed.set()
            return {'segments': [], 'duration_ms': 10, 'compute_s': .01}
        def close(self):
            pass
    monkeypatch.setattr(live, '_resident', OldResident())
    monkeypatch.setattr(live, 'ResidentWhisper', lambda *args, **kwargs: NewResident())
    monkeypatch.setattr(live, 'runtime_status', lambda: {'installed': True})
    assert live.start_worker() is True
    assert entered.wait(3)
    consumer = live._thread
    stopper = threading.Thread(target=live.stop_worker)
    stopper.start()
    assert close_entered.wait(3)
    assert live.start_worker() is True
    assert live._thread is consumer and live._stop.is_set()
    release_close.set()
    stopper.join(3)
    assert not stopper.is_alive() and completed.wait(3)
    limit = time.monotonic() + 3
    while time.monotonic() < limit:
        with brain() as db:
            if db.get(MeetingAudioChunk, cid).speech_status == 'completed':
                break
        time.sleep(.01)
    else:
        pytest.fail('Reenabled single consumer did not complete durable pending chunk')
    assert threads == [consumer.ident, consumer.ident]
    live.stop_worker()
    live.stop_worker()
    assert live._thread is None


def test_stale_disabled_tick_cannot_override_newer_enable(stores, monkeypatch):
    brain = stores[0]
    with brain() as db:
        enabled(db)
    actual_enabled = sessions.live_transcription_enabled
    first = True
    nested_activation = False
    fresh_tick = threading.Event()
    def old_snapshot_then_new_enable(db=None):
        nonlocal first, nested_activation
        if threading.current_thread().name == 'live-speech' and first:
            first = False
            with brain() as changed:
                enabled(changed, live_transcription_enabled=False)
            observed = actual_enabled(db)
            assert observed is False
            with brain() as changed:
                enabled(changed)
            nested_activation = True
            assert live.start_worker() is True  # Newer explicit enable, same consumer.
            nested_activation = False
            return observed  # The previous tick still holds its off observation.
        if threading.current_thread().name == 'live-speech' and not nested_activation:
            fresh_tick.set()
        return actual_enabled(db)
    monkeypatch.setattr(sessions, 'live_transcription_enabled', old_snapshot_then_new_enable)
    monkeypatch.setattr(live, 'runtime_status', lambda: {'installed': False})
    assert live.start_worker() is True
    assert fresh_tick.wait(3), 'Old off observation incorrectly stopped the newer activation'
    assert live._desired_running and live._thread.is_alive()


def test_configuration_direct_off_keeps_capture_and_secondary_flags(stores, monkeypatch):
    from app.routers import fusion_insights as route
    brain = stores[0]
    calls = []
    monkeypatch.setattr(route, 'require_reference_write', lambda: None)
    monkeypatch.setattr(sessions, 'capabilities', lambda db: {})
    monkeypatch.setattr('app.services.native_audio.status', lambda sid=None: {'active': []})
    monkeypatch.setattr('app.routers.native_capture.perform', lambda *args: pytest.fail('Direct off must not stop capture'))
    monkeypatch.setattr(live, 'start_worker', lambda: calls.append('start-STT'))
    monkeypatch.setattr(live, 'stop_worker', lambda: calls.append('stop-STT'))
    monkeypatch.setenv('AGENT_TESTING', '1')
    with brain() as db:
        value = route.configure(route.Controls(enabled=True, live_transcription_enabled=False,
                                               proactive_enabled=True, auto_enhancement_enabled=True), db)
        assert value['enabled'] and value['live_transcription_enabled'] is False
        assert value['proactive_enabled'] and value['auto_enhancement_enabled']
        assert calls == ['stop-STT']


def test_resident_close_is_idempotent_and_closes_only_its_job(monkeypatch, tmp_path):
    calls = []
    resident = live.ResidentWhisper(tmp_path)
    resident.process = SimpleNamespace(poll=lambda: 0,
        stdin=SimpleNamespace(close=lambda: calls.append('stdin')),
        stdout=SimpleNamespace(close=lambda: calls.append('stdout')))
    resident._job = (SimpleNamespace(CloseHandle=lambda handle: calls.append(handle) or True), 'owned-job')
    resident.close()
    resident.close()
    assert calls == ['stdin', 'stdout', 'owned-job']
    monkeypatch.setattr(live.subprocess, 'Popen', lambda *args, **kwargs: pytest.fail('No load after stop'))
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(InterruptedError):
        resident.start(cancel=cancel)
