"""Bounded admission with isolated stores; no microphone, model or canonical data."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
import pytest
from sqlalchemy import func, select

from app.meeting_session_models import (LiveTranscriptSegment, MeetingAudioChunk,
                                       MeetingSession, MeetingSessionCommand, MeetingSessionEvent)
from app.meeting_session_schemas import Command
from app.services import live_speech, meeting_sessions as sessions, native_audio, speech_admission as admission
from app.services.settings_service import save_section
from backend.app.services.project_operator import Operator, operator_context
from tests.test_meeting_sessions import stores, create, chunk, wav

__all__ = ['stores']


@pytest.fixture(autouse=True)
def no_hardware_or_engine(monkeypatch, request, tmp_path):
    # Exercise boundary behavior cheaply, independently of production capacity.
    monkeypatch.setattr(admission, "MAX_CHUNKS", 24)
    monkeypatch.setattr(admission, "RETRY_LIMIT", 8)
    monkeypatch.setattr(admission, "MAX_BUDGET_MS", 120_000)
    monkeypatch.setattr(admission, "UNKNOWN_COST_MS", 120_001)
    monkeypatch.setattr(native_audio, 'status', lambda sid=None: {'session': None})
    monkeypatch.setattr(native_audio, '_captures', {})
    monkeypatch.setattr(live_speech, 'wake_worker', lambda: None)
    if 'stores' in request.fixturenames:
        request.getfixturevalue('stores')
        from app.config import settings
        # Stage's extra source path must not push immutable hash filenames
        # past the Windows limit. All audio stays in this new test directory.
        monkeypatch.setattr(settings, 'storage_dir', str(tmp_path.parent / ('s-' + uuid4().hex[:8])))


def enabled(db, value=True):
    save_section(db, 'foresight', {'enabled': True, 'live_transcription_enabled': value})


def audio(db, sid, seq=0, *, duration=10, track='mic', command_id=None):
    return chunk(db, sid, seq, raw=wav(max(160, duration * 16)), track=track,
                 duration_ms=duration, command_id=command_id)


def items(db, sid):
    return list(db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == sid)
                          .order_by(MeetingAudioChunk.sequence)))


@pytest.mark.parametrize('duration,eligible', [(0, False), (-1, False), (True, False),
                                              (1, True), (10000, True), (10001, False)])
def test_pure_direct_eligibility_never_accepts_unknown_duration(duration, eligible):
    assert admission.eligible_direct(SimpleNamespace(duration_ms=duration, track='mic')) is eligible


def test_disabled_audio_is_retained_acknowledged_and_replay_never_admits(stores):
    brain = stores[0]
    with brain() as db:
        enabled(db, False)
        sid = create(db, kind='note')['id']
        command_id = str(uuid4())
        received = audio(db, sid, command_id=command_id)
        saved = items(db, sid)[0]
        original = Path(saved.storage_path).read_bytes()
        assert received['acknowledged'] and received['speech_admission']['reason'] == 'direct_disabled'
        assert saved.speech_status == 'retained'
        assert hashlib.sha256(original).hexdigest() == saved.sha256
        enabled(db)
        assert audio(db, sid, command_id=command_id) == received
        assert items(db, sid)[0].speech_status == 'retained'
        result = sessions.retry_transcription(db, sid, Command(command_id=str(uuid4()), expected_revision=1))
        assert result['retried_chunks'] == 1
        assert items(db, sid)[0].speech_status == 'pending'
        assert Path(saved.storage_path).read_bytes() == original


def test_global_count_limit_suspends_without_rejecting_audio_and_requires_explicit_resume(stores):
    brain = stores[0]
    with brain() as db:
        enabled(db)
        other, own = create(db)['id'], create(db, kind='note')['id']
        for seq in range(24):
            audio(db, other, seq)
        overflow = audio(db, own)
        assert overflow['acknowledged'] and overflow['speech_admission']['reason'] == 'capacity'
        own_chunk = items(db, own)[0]
        original = Path(own_chunk.storage_path).read_bytes()
        items(db, other)[0].speech_status = 'completed'
        db.commit()
        assert audio(db, own, 1)['speech_admission']['reason'] == 'suspended'
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(
            MeetingSessionEvent.session_id == own, MeetingSessionEvent.kind == 'transcript.admission.suspended')) == 1
        for saved in items(db, other):
            saved.speech_status = 'completed'
        db.commit()
        result = sessions.retry_transcription(db, own, Command(command_id=str(uuid4()), expected_revision=1))
        assert result['retried_chunks'] == 2 and result['admission_resumed']
        assert audio(db, own, 2)['speech_admission']['status'] == 'pending'
        assert Path(own_chunk.storage_path).read_bytes() == original
        assert not sessions.serialize_session(db, sessions.get_session(db, own))['transcript_processing_complete']


def test_duration_budget_is_global_and_running_reservations_stay_counted(stores):
    brain = stores[0]
    with brain() as db:
        enabled(db)
        left, right = create(db)['id'], create(db)['id']
        audio(db, left, duration=10000)
        for seq in range(11):
            audio(db, right, seq, duration=10000, track='system')
        items(db, left)[0].speech_status = 'running'
        db.get(MeetingSession, left).state = 'cancelled'
        db.commit()
        response = audio(db, right, 11, track='system')
        assert response['acknowledged'] and response['speech_admission']['reason'] == 'capacity'
        assert items(db, left)[0].speech_status == 'running'
        assert admission._usage(db) == (12, 120000)


@pytest.mark.parametrize('kind,duration,reason', [('note', 0, 'duration_unknown'),
    ('note', 20000, 'chunk_too_long'), ('import', 0, 'import_manual'), ('import', 20000, 'import_manual')])
def test_unknown_long_and_imported_audio_keep_originals_outside_direct(stores, kind, duration, reason):
    brain = stores[0]
    with brain() as db:
        enabled(db)
        sid = create(db, kind=kind)['id']
        response = audio(db, sid, duration=duration)
        row = sessions.get_session(db, sid)
        saved = items(db, sid)[0]
        original = Path(saved.storage_path).read_bytes()
        assert response['acknowledged'] and response['speech_admission']['reason'] == reason
        assert saved.speech_status == 'retained' and admission._usage(db) == (0, 0)
        retry = sessions.retry_transcription(db, sid, Command(command_id=str(uuid4()), expected_revision=1))
        assert retry['retried_chunks'] == 0 and retry['retained_batch_only_chunks'] == 1
        assert Path(saved.storage_path).read_bytes() == original
        assert sessions.consolidated_audio(db, row)[0] == original
        assert sessions.serialize_session(db, row)['transcription_admission']['retained_batch_only_chunks'] == 1


def test_native_wav_frames_guard_declared_duration_without_discarding_audio(stores):
    brain = stores[0]
    with brain() as db:
        enabled(db)
        sid = create(db)['id']
        response = chunk(db, sid, raw=wav(), duration_ms=5000)
        assert response['acknowledged'] and response['speech_admission']['reason'] == 'invalid_pcm'
        saved = items(db, sid)[0]
        assert saved.speech_status == 'retained' and admission._usage(db) == (0, 0)
        assert Path(saved.storage_path).read_bytes() == wav()
        result = sessions.retry_transcription(db, sid, Command(command_id=str(uuid4()), expected_revision=1))
        assert result['retried_chunks'] == 0 and result['retained_batch_only_chunks'] == 1


def test_partial_retry_receipt_preserves_human_text_and_replays_original_selection(stores):
    brain = stores[0]
    with brain() as db:
        enabled(db, False)
        sid = create(db, kind='note')['id']
        for seq in range(30):
            audio(db, sid, seq)
        original = [(c.id, c.sha256, c.storage_path, c.size_bytes) for c in items(db, sid)]
        db.add(LiveTranscriptSegment(id='human', session_id=sid, chunk_id=original[0][0], track='mic',
            start_ms=0, end_ms=10, speaker='Human', text='Ne pas engager les travaux.', revision=7, finalized=True))
        db.commit()
        enabled(db)
        body = Command(command_id=str(uuid4()), expected_revision=1)
        result = sessions.retry_transcription(db, sid, body)
        assert result['retried_chunks'] == 8 and result['chunk_ids'] == [row[0] for row in original[:8]]
        assert result['remaining_recoverable_chunks'] == 22
        assert admission._usage(db) == (8, 40000)
        db.get(MeetingAudioChunk, result['chunk_ids'][0]).speech_status = 'failed'
        db.commit()
        enabled(db, False)
        assert sessions.retry_transcription(db, sid, body) == result
        assert db.get(MeetingAudioChunk, result['chunk_ids'][0]).speech_status == 'failed'
        assert [(c.id, c.sha256, c.storage_path, c.size_bytes) for c in items(db, sid)] == original
        human = db.get(LiveTranscriptSegment, 'human')
        assert (human.text, human.revision, human.finalized) == ('Ne pas engager les travaux.', 7, True)


def test_retry_uses_only_global_free_capacity_without_exposing_other_session_ids(stores):
    brain = stores[0]
    with brain() as db:
        enabled(db)
        other = create(db)['id']
        for seq in range(23):
            audio(db, other, seq)
        enabled(db, False)
        own = create(db)['id']
        for seq in range(4):
            audio(db, own, seq)
        enabled(db)
        result = sessions.retry_transcription(db, own, Command(command_id=str(uuid4()), expected_revision=1))
        assert result['retried_chunks'] == 1 and result['remaining_recoverable_chunks'] == 3
        assert result['admission_blocked_reason'] == 'capacity'
        assert all(db.get(MeetingAudioChunk, cid).session_id == own for cid in result['chunk_ids'])
        snapshot = result['session']['transcription_admission']
        assert snapshot['admitted_chunks'] == 1 and snapshot['retained_chunks'] == 3
        assert set(snapshot) == {'policy', 'suspended', 'reason', 'admitted_chunks', 'retained_chunks',
                                 'recoverable_direct_chunks', 'retained_batch_only_chunks', 'last_transition_at_utc'}


def test_prepared_secondary_retry_does_not_block_native_audio_persistence(stores, monkeypatch):
    brain = stores[0]
    with brain() as db:
        enabled(db, False)
        sid = create(db)['id']
        audio(db, sid)
        enabled(db)
    def fail_finish(*args, **kwargs):
        raise RuntimeError('Fixture failure after durable preparation')
    monkeypatch.setattr(sessions, '_finish', fail_finish)
    body = Command(command_id=str(uuid4()), expected_revision=1)
    with pytest.raises(RuntimeError):
        with brain() as db:
            sessions.retry_transcription(db, sid, body)
    owner = SimpleNamespace(state='recording')
    monkeypatch.setattr(native_audio, '_captures', {sid: owner})
    raw = wav()
    with brain() as db:
        assert db.get(MeetingSessionCommand, body.command_id).status == 'prepared'
        response = sessions.store_chunk(db, sid, 'mic', 1, raw=raw, filename='native.wav', mime_type='audio/wav',
            command_id=str(uuid4()), sha256=hashlib.sha256(raw).hexdigest(), start_ms=10, duration_ms=10,
            internal_capture_owner=owner)
        assert response['acknowledged'] and len(items(db, sid)) == 2
        assert db.get(MeetingSession, sid).pending_command_id == body.command_id


def test_prepared_finalization_still_refuses_new_fragments(stores):
    brain = stores[0]
    with brain() as db:
        enabled(db)
        sid = create(db)['id']
        row = sessions.get_session(db, sid)
        sessions._begin(db, row, 'finalize', {'command_id': str(uuid4()), 'expected_revision': 1})
        with pytest.raises(HTTPException) as blocked:
            audio(db, sid)
        assert blocked.value.status_code == 409
        assert items(db, sid) == []


def test_concurrent_connections_cannot_both_reserve_last_slot(stores):
    brain = stores[0]
    with brain() as db:
        enabled(db)
        full = create(db)['id']
        for seq in range(23):
            audio(db, full, seq)
        left, right = create(db)['id'], create(db)['id']
    barrier = Barrier(2)
    def upload(sid):
        with brain() as db:
            barrier.wait(timeout=5)
            return audio(db, sid)
    with ThreadPoolExecutor(max_workers=2) as executor:
        answers = list(executor.map(upload, [left, right]))
    assert all(answer['acknowledged'] for answer in answers)
    assert sorted(answer['speech_admission']['status'] for answer in answers) == ['pending', 'retained']
    with brain() as db:
        assert admission._usage(db) == (24, 120000)


def test_historical_reconciliation_is_dated_bounded_and_does_not_commit_for_caller(stores):
    brain = stores[0]
    with brain() as db:
        enabled(db, False)
        sid = create(db)['id']
        for seq in range(30):
            audio(db, sid, seq)
        for saved in items(db, sid):
            saved.speech_status = 'pending'
        db.commit()
        enabled(db)
        proof = admission.reconcile_queue(db)
        assert proof['bounded'] and proof['retained_chunks'] == 6 and len(proof['admitted_chunk_ids']) == 24
        event = db.scalar(select(MeetingSessionEvent).where(MeetingSessionEvent.session_id == sid,
            MeetingSessionEvent.kind == 'transcript.admission.reconciled'))
        assert datetime.fromisoformat(event.data['at_utc'].replace('Z', '+00:00')).tzinfo == timezone.utc
        assert event.data['retained_chunks'] == 6 and len(event.data['admitted_chunk_ids']) == 24
        db.rollback()
        assert all(saved.speech_status == 'pending' for saved in items(db, sid))
        assert db.scalar(select(MeetingSessionEvent.id).where(
            MeetingSessionEvent.kind == 'transcript.admission.reconciled')) is None
    with brain() as fresh:
        proof = admission.reconcile_queue(fresh)
        fresh.commit()
        assert proof['bounded'] and admission._usage(fresh) == (24, 120000)


def test_opt_in_off_never_repairs_legacy_running_or_pending(stores):
    brain = stores[0]
    with brain() as db:
        enabled(db, False)
        sid = create(db)['id']
        audio(db, sid)
        saved = items(db, sid)[0]
        saved.speech_status = 'running'
        db.commit()
        proof = admission.reconcile_queue(db, recover_running=True)
        assert proof['enabled'] is False and proof['reconciled'] is False
        assert saved.speech_status == 'running'
        assert db.scalar(select(MeetingSessionEvent.id).where(
            MeetingSessionEvent.kind == 'transcript.admission.reconciled')) is None


@pytest.mark.parametrize('duration,frames', [(0, 160), (20000, 320000), (10, 320000)])
def test_invalid_historical_running_reservation_blocks_new_admission_until_real_completion(stores, duration, frames):
    brain = stores[0]
    with brain() as db:
        enabled(db, False)
        old, own = create(db)['id'], create(db, kind='note')['id']
        chunk(db, old, raw=wav(frames), duration_ms=duration)
        running = items(db, old)[0]
        original = Path(running.storage_path).read_bytes()
        running.speech_status = 'running'
        db.commit()
        enabled(db)
        proof = admission.reconcile_queue(db)
        assert proof['bounded'] is False and running.speech_status == 'running'
        response = audio(db, own)
        assert response['acknowledged'] and response['speech_admission']['reason'] == 'capacity'
        assert admission._usage(db)[1] > admission.MAX_BUDGET_MS
        assert running.speech_status == 'running' and Path(running.storage_path).read_bytes() == original
        running.speech_status = 'completed'
        db.commit()
        assert admission._usage(db) == (0, 0)
        retry = sessions.retry_transcription(db, own, Command(command_id=str(uuid4()), expected_revision=1))
        assert retry['retried_chunks'] == 1 and retry['admission_resumed']


def test_batch_states_never_enter_direct_pool_and_failed_retry_requires_rights(stores):
    brain, _, pid, _ = stores
    with brain() as db:
        enabled(db)
        sid = create(db, project_id=pid)['id']
        audio(db, sid)
        saved = items(db, sid)[0]
        saved.speech_status = 'batch_running'
        db.commit()
        admission.reconcile_queue(db, recover_running=True)
        assert saved.speech_status == 'batch_running' and admission._usage(db) == (0, 0)
        saved.speech_status = 'failed'
        db.commit()
        with operator_context(Operator(id='restricted', role='editor', project_ids=frozenset())):
            with pytest.raises(HTTPException) as denied:
                sessions.retry_transcription(db, sid, Command(command_id=str(uuid4()), expected_revision=1))
        assert denied.value.status_code == 404 and saved.speech_status == 'failed'
