"""Direct admission/lifecycle on isolated SQLite and fictitious WAVs only."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
from threading import Event, Thread
from pathlib import Path
from uuid import uuid4
import wave

import pytest
from sqlalchemy import select

from app.meeting_session_models import (LiveTranscriptSegment, MeetingAudioChunk, MeetingSession,
                                       MeetingSessionCommand, MeetingSessionEvent)
from app.services import audio_cpu_coordinator as cpu, live_speech as live
from app.services.audio_capture import PreparedAudio
from app.services.settings_service import save_section
from tests.test_meeting_sessions import stores as stores_fixture, create, chunk, wav

stores = stores_fixture


@pytest.fixture(autouse=True)
def isolated_worker(stores, monkeypatch):
    from app.config import settings
    fixture_root = Path(stores[0].kw['bind'].url.database).parent.parent / ('s-' + uuid4().hex[:8])
    monkeypatch.setattr(settings, 'storage_dir', str(fixture_root))
    monkeypatch.setattr(live, '_stop', Event())
    monkeypatch.setattr(live, '_wake', Event())
    monkeypatch.setattr(live, '_thread', None)
    monkeypatch.setattr(live, '_resident', None)
    monkeypatch.setattr(live, '_desired_running', False)
    monkeypatch.setattr(live, '_closing', 0)
    monkeypatch.setattr(live, '_stop_generation', 0)
    monkeypatch.setattr(live, '_lifecycle_generation', 0)
    monkeypatch.setattr(live, '_metrics', {'processed_chunks': 0, 'failed_chunks': 0, 'last_compute_s': None})
    monkeypatch.setattr(cpu, '_batch_owner', None)
    monkeypatch.setattr(cpu, '_direct_jobs', 0)
    monkeypatch.setattr('app.services.native_audio._captures', {})
    monkeypatch.setattr(live, 'ResidentWhisper', lambda *_args, **_kwargs: pytest.fail('No real speech model'))
    monkeypatch.setattr(live.subprocess, 'Popen', lambda *_args, **_kwargs: pytest.fail('No real child process'))
    yield
    live.stop_worker()
    assert live._thread is None or not live._thread.is_alive()


def enable(db, enabled=True):
    save_section(db, 'foresight', {'enabled': True, 'live_transcription_enabled': enabled})


def seed(db, statuses, *, kind='note', duration=5000, session_state='created'):
    """A historical archive, never an implicit admission through upload."""
    enable(db, False)
    sid = create(db, kind=kind)['id']
    raw = wav(samples=80000)
    ids = []
    for sequence, status in enumerate(statuses):
        chunk(db, sid, sequence, raw=raw, duration_ms=duration, start_ms=sequence * duration)
        row = db.scalar(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == sid,
                                                        MeetingAudioChunk.sequence == sequence))
        row.speech_status, row.speech_error = status, 'Original fixture state'
        ids.append(row.id)
    db.get(MeetingSession, sid).state = session_state
    db.commit()
    return sid, ids


def fake_engine(monkeypatch, *, transcribe=None):
    calls = []

    class Engine:
        def transcribe(self, prepared, **kwargs):
            calls.append(kwargs['track'])
            if transcribe is not None:
                return transcribe(prepared, **kwargs)
            return {'segments': [{'start_ms': 0, 'end_ms': 1000, 'speaker': 'mic', 'text': 'Texte fictif'}],
                    'duration_ms': 5000, 'compute_s': .001}

        def close(self):
            pass

    monkeypatch.setattr(live, '_resident', Engine())
    monkeypatch.setattr(live.audio_capture, 'prepare_chunk', lambda row, *_args, **_kwargs:
                        PreparedAudio(Path(row.storage_path), row.start_ms, 0, row.duration_ms, False))
    return calls


@pytest.mark.parametrize('state', ['retained', 'failed', 'running', 'completed', 'batch_pending', 'batch_running'])
def test_only_pending_can_enter_direct_cpu_or_be_claimed(stores, monkeypatch, state):
    brain = stores[0]
    with brain() as db:
        _, ids = seed(db, [state])
        enable(db)
    monkeypatch.setattr(cpu, 'direct_speech', lambda: pytest.fail('No CPU reservation for non-pending audio'))
    assert live.process_chunk(ids[0]) is False
    assert live._process_chunk(ids[0]) is False
    with brain() as db:
        item = db.get(MeetingAudioChunk, ids[0])
        assert item.speech_status == state and item.speech_error == 'Original fixture state'
        assert live.pending_candidate(db) is None


@pytest.mark.parametrize('state', ['pending', 'failed', 'retained', 'batch_pending'])
def test_cpu_busy_preserves_existing_admission_without_retrying_failed_or_archived(stores, monkeypatch, state):
    brain = stores[0]
    with brain() as db:
        _, ids = seed(db, [state])
        enable(db)
    monkeypatch.setattr(cpu, '_batch_owner', ('fictitious-batch', object()))
    assert live.process_chunk(ids[0]) is False
    with brain() as db:
        item = db.get(MeetingAudioChunk, ids[0])
        assert item.speech_status == state
        assert ('en attente' in item.speech_error) if state == 'pending' else item.speech_error == 'Original fixture state'


def test_busy_handler_rechecks_opt_in_before_writing_waiting_error(stores, monkeypatch):
    brain = stores[0]
    with brain() as db:
        _, ids = seed(db, ['pending'])
        enable(db)

    @contextmanager
    def busy_after_opt_out():
        with brain() as db:
            enable(db, False)
        raise cpu.AudioCpuBusy('Simulated batch admission')
        yield  # pragma: no cover - generator context protocol.

    monkeypatch.setattr(cpu, 'direct_speech', busy_after_opt_out)
    assert live.process_chunk(ids[0]) is False
    with brain() as db:
        item = db.get(MeetingAudioChunk, ids[0])
        assert item.speech_status == 'pending' and item.speech_error == 'Original fixture state'


def test_durable_batch_reservation_blocks_direct_without_memory_owner(stores):
    brain = stores[0]
    with brain() as db:
        sid, ids = seed(db, ['pending'], session_state='completed')
        enable(db)
        db.add(MeetingSessionCommand(id=str(uuid4()), session_id=sid, operator_id='local',
            kind='transcription-batch', digest='f' * 64, body={'_batch': {'state': 'admitted'}},
            status='completed', result={}))
        db.commit()
        assert cpu._batch_owner is None and cpu._running_batch(db)
    assert live.process_chunk(ids[0]) is False
    assert cpu.status()['direct_speech_jobs'] == 0 and live._resident is None
    with brain() as db:
        item = db.get(MeetingAudioChunk, ids[0])
        assert item.speech_status == 'pending' and item.speech_error == 'Original fixture state'


def test_legacy_queued_stock_keeps_priority_for_direct_capture(stores, monkeypatch, tmp_path):
    from app.models import MeetingRecording
    from tests.test_audio_cpu_arbitration import recording
    brain, _, pid, bid = stores
    with brain() as db:
        legacy = recording(db, bid, pid, tmp_path)
        legacy.job_kind, legacy.job_status = 'transcription', 'queued'
        db.commit()
        legacy_id = legacy.id
        _, ids = seed(db, ['pending'])
        enable(db)
        assert cpu._running_batch(db) is False
    calls = fake_engine(monkeypatch)
    live.process_chunk(ids[0])
    assert calls == ['mic']
    with brain() as db:
        assert db.get(MeetingAudioChunk, ids[0]).speech_status == 'completed'
        assert db.get(MeetingRecording, legacy_id).job_status == 'queued'


def test_startup_reconciles_old_backlog_under_budget_with_durable_events(stores, monkeypatch):
    from app.services import speech_admission
    monkeypatch.setattr(speech_admission, "MAX_CHUNKS", 24)
    monkeypatch.setattr(speech_admission, "MAX_BUDGET_MS", 120000)
    monkeypatch.setattr(speech_admission, "UNKNOWN_COST_MS", 120001)
    from app.services.speech_admission import MAX_CHUNKS, MAX_BUDGET_MS, MIN_COST_MS
    brain = stores[0]
    states = ['running', 'running'] + ['pending'] * 28 + ['failed', 'retained', 'batch_pending', 'batch_running']
    with brain() as db:
        _, ids = seed(db, states)
        before = {item.id: (item.sha256, item.storage_path, item.size_bytes)
                  for item in db.scalars(select(MeetingAudioChunk))}
        enable(db)
        assert live.startup_recovery(db)
        rows = list(db.scalars(select(MeetingAudioChunk)))
        admitted = [item for item in rows if item.speech_status in {'pending', 'running'}]
        assert len(admitted) == MAX_CHUNKS
        assert sum(max(MIN_COST_MS, item.duration_ms) for item in admitted) <= MAX_BUDGET_MS
        assert not any(item.speech_status == 'running' for item in rows)
        assert [db.get(MeetingAudioChunk, cid).speech_status for cid in ids[-4:]] == states[-4:]
        assert {item.id: (item.sha256, item.storage_path, item.size_bytes) for item in rows} == before
        events = list(db.scalars(select(MeetingSessionEvent).where(
            MeetingSessionEvent.kind == 'transcript.admission.reconciled')))
        assert events and all(event.data for event in events)
        # No automatic consumption, even though recovery admitted pending audio.
        assert live._resident is None


@pytest.mark.parametrize('opt_in', [{}, {'live_transcription_enabled': False}, {'live_transcription_enabled': 'true'}])
def test_no_opt_in_means_no_recovery_no_model_and_no_worker(stores, monkeypatch, opt_in):
    from app.services import speech_admission
    brain = stores[0]
    with brain() as db:
        _, ids = seed(db, ['running', 'pending', 'failed', 'retained'])
        save_section(db, 'foresight', {'enabled': True, **opt_in})
        before = [(db.get(MeetingAudioChunk, cid).speech_status, db.get(MeetingAudioChunk, cid).speech_error) for cid in ids]
        monkeypatch.setattr(speech_admission, 'reconcile_queue', lambda *_args, **_kwargs:
                            pytest.fail('No job repair without direct opt-in'))
        assert live.startup_recovery(db) is False
    assert live.start_worker() is False and live._thread is None
    assert live.process_chunk(ids[1]) is False
    with brain() as db:
        assert [(db.get(MeetingAudioChunk, cid).speech_status, db.get(MeetingAudioChunk, cid).speech_error) for cid in ids] == before


@pytest.mark.parametrize('owner', ['direct', 'batch'])
def test_startup_does_not_steal_an_existing_cpu_reservation(stores, monkeypatch, owner):
    brain = stores[0]
    with brain() as db:
        _, ids = seed(db, ['running'])
        enable(db)
        monkeypatch.setattr(cpu, '_direct_jobs', 1 if owner == 'direct' else 0)
        monkeypatch.setattr(cpu, '_batch_owner', ('fictitious', object()) if owner == 'batch' else None)
        assert live.startup_recovery(db) is False
        assert db.get(MeetingAudioChunk, ids[0]).speech_status == 'running'
        monkeypatch.setattr(cpu, '_direct_jobs', 0)
        monkeypatch.setattr(cpu, '_batch_owner', None)
        assert live.startup_recovery(db)
        db.expire_all()
        assert db.get(MeetingAudioChunk, ids[0]).speech_status == 'pending'


def test_stop_during_reconciliation_rolls_back_and_remains_responsive(stores, monkeypatch):
    from app.services import speech_admission
    brain = stores[0]
    with brain() as db:
        _, ids = seed(db, ['running'] + ['pending'] * 26)
        enable(db)
        reconcile = speech_admission.reconcile_queue

        def stop_after_reconciliation(*args, **kwargs):
            proof = reconcile(*args, **kwargs)
            stopper = Thread(target=lambda: live.stop_worker(wait=False))
            stopper.start()
            stopper.join(1)
            assert not stopper.is_alive(), 'STOP blocked behind the historical reconciliation'
            return proof

        monkeypatch.setattr(speech_admission, 'reconcile_queue', stop_after_reconciliation)
        assert live.startup_recovery(db) is False
        db.expire_all()
        assert [db.get(MeetingAudioChunk, cid).speech_status for cid in ids] == ['running'] + ['pending'] * 26
        assert not list(db.scalars(select(MeetingSessionEvent).where(
            MeetingSessionEvent.kind == 'transcript.admission.reconciled')))


def test_claim_rechecks_current_pending_state_after_cpu_admission(stores, monkeypatch):
    brain = stores[0]
    with brain() as db:
        _, ids = seed(db, ['pending'])
        enable(db)

    @contextmanager
    def archive_at_admission():
        with brain() as db:
            db.get(MeetingAudioChunk, ids[0]).speech_status = 'retained'
            db.commit()
        yield

    monkeypatch.setattr(cpu, 'direct_speech', archive_at_admission)
    assert live.process_chunk(ids[0]) is False
    with brain() as db:
        assert db.get(MeetingAudioChunk, ids[0]).speech_status == 'retained'


def test_invalid_historical_pending_is_retained_without_inference(stores):
    brain = stores[0]
    with brain() as db:
        _, ids = seed(db, ['pending'], duration=20000)
        enable(db)
    assert live.process_chunk(ids[0]) is False
    with brain() as db:
        assert db.get(MeetingAudioChunk, ids[0]).speech_status == 'retained'
        assert live.pending_candidate(db) is None


def test_personal_note_direct_audio_preserves_original_and_human_segment(stores, monkeypatch):
    brain = stores[0]
    with brain() as db:
        sid, ids = seed(db, ['pending'], kind='note')
        enable(db)
        item = db.get(MeetingAudioChunk, ids[0])
        original = (item.sha256, item.storage_path, item.size_bytes)
        identity = 'live-' + hashlib.sha256(f'{item.id}:0'.encode()).hexdigest()
        db.add(LiveTranscriptSegment(id=identity, session_id=sid, chunk_id=item.id,
            track='mic', start_ms=0, end_ms=1000, speaker='Voix relue', text='Correction humaine',
            revision=7, finalized=True))
        db.commit()
    calls = fake_engine(monkeypatch)
    live.process_chunk(ids[0])
    assert calls == ['mic']
    with brain() as db:
        item = db.get(MeetingAudioChunk, ids[0])
        assert item.speech_status == 'completed'
        assert (item.sha256, item.storage_path, item.size_bytes) == original
        human = db.get(LiveTranscriptSegment, identity)
        assert (human.text, human.revision, human.finalized) == ('Correction humaine', 7, True)
        assert db.get(MeetingSession, sid).project_id is None


def test_cancelled_inflight_job_keeps_running_reservation_until_fake_engine_finishes(stores, monkeypatch):
    brain = stores[0]
    with brain() as db:
        sid, ids = seed(db, ['pending'])
        enable(db)
    entered, release = Event(), Event()

    def transcribe(*_args, **_kwargs):
        entered.set()
        assert release.wait(3)
        return {'segments': [{'start_ms': 0, 'end_ms': 1000, 'speaker': 'mic', 'text': 'Must not publish'}],
                'duration_ms': 5000, 'compute_s': .001}

    fake_engine(monkeypatch, transcribe=transcribe)
    with ThreadPoolExecutor(max_workers=1) as executor:
        task = executor.submit(live.process_chunk, ids[0])
        try:
            assert entered.wait(2)
            with brain() as db:
                db.get(MeetingSession, sid).state = 'cancelled'
                db.commit()
                assert cpu.status()['direct_speech_jobs'] == 1
                assert live.startup_recovery(db) is False
                assert db.get(MeetingAudioChunk, ids[0]).speech_status == 'running'
        finally:
            release.set()
        task.result(timeout=2)
    assert cpu.status()['direct_speech_jobs'] == 0
    with brain() as db:
        assert db.get(MeetingAudioChunk, ids[0]).speech_status == 'retained'
        assert not list(db.scalars(select(LiveTranscriptSegment).where(LiveTranscriptSegment.session_id == sid)))


def test_failed_attempt_stays_failed_on_later_worker_candidates(stores, monkeypatch):
    brain = stores[0]
    with brain() as db:
        _, ids = seed(db, ['pending'])
        enable(db)

    def fail(*_args, **_kwargs):
        raise ValueError('Fictitious ASR failure')

    calls = fake_engine(monkeypatch, transcribe=fail)
    live.process_chunk(ids[0])
    assert calls == ['mic']
    assert live.process_chunk(ids[0]) is False
    with brain() as db:
        assert live.pending_candidate(db) is None
        assert live.startup_recovery(db)
        assert db.get(MeetingAudioChunk, ids[0]).speech_status == 'failed'
        assert db.get(MeetingAudioChunk, ids[0]).speech_error == 'Fictitious ASR failure'
    assert calls == ['mic']


@pytest.mark.parametrize('previous_status,context', [
    ('pending', True), ('running', True), ('completed', True),
    ('retained', False), ('failed', False), ('batch_pending', False), ('batch_running', False),
])
def test_pcm_context_never_reads_archived_or_batch_audio(tmp_path, previous_status, context):
    rows = []
    for sequence, sample in enumerate([8, 7]):
        raw = wav(samples=80000, sample=sample)
        path = tmp_path / f'fiction-{sequence}.wav'
        path.write_bytes(raw)
        rows.append({'id': str(sequence), 'session_id': 'fictitious', 'track': 'mic', 'sequence': sequence,
            'storage_path': str(path), 'size_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'start_ms': sequence * 5000, 'duration_ms': 5000, 'mime_type': 'audio/wav',
            'speech_status': previous_status if sequence == 0 else 'running'})
    prepared = live.prepare_direct_chunk(rows[1], rows, storage_root=tmp_path, derived_root=tmp_path / 'derived')
    with wave.open(str(prepared.path), 'rb') as audio:
        samples = audio.readframes(audio.getnframes())
    assert prepared.assembled is context
    if context:
        assert prepared.offset_ms + prepared.clip_start_ms == 4500
        assert samples == bytes([8, 0]) * 8000 + bytes([7, 0]) * 80000
    else:
        assert prepared.path == Path(rows[1]['storage_path'])
        assert prepared.offset_ms + prepared.clip_start_ms == 5000
        assert samples == bytes([7, 0]) * 80000


@pytest.mark.parametrize('previous_status,contiguous,expected_start', [
    ('retained', True, 5000), ('failed', True, 5000), ('batch_running', True, 5000),
    ('completed', False, 5000), ('completed', True, 4500),
])
def test_webm_keeps_bootstrap_headers_but_crops_archived_context(tmp_path, previous_status, contiguous, expected_start):
    rows = []
    for sequence, raw in enumerate([b'\x1aE\xdf\xa3FICTIVE-WEBM-HEADER', b'FICTIVE-HEADERLESS-CLUSTER']):
        path = tmp_path / f'fiction-{sequence}.webm'
        path.write_bytes(raw)
        rows.append({'id': str(sequence), 'session_id': 'fictitious', 'track': 'system', 'sequence': sequence,
            'storage_path': str(path), 'size_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'start_ms': sequence * 5000, 'duration_ms': 5000 if contiguous or sequence else 4000,
            'mime_type': 'audio/webm', 'speech_status': previous_status if sequence == 0 else 'running'})
    prepared = live.prepare_direct_chunk(rows[1], rows, storage_root=tmp_path, derived_root=tmp_path / 'derived')
    assert prepared.assembled and prepared.offset_ms == 0
    assert prepared.path.read_bytes() == b'\x1aE\xdf\xa3FICTIVE-WEBM-HEADERFICTIVE-HEADERLESS-CLUSTER'
    assert prepared.clip_start_ms == expected_start and prepared.clip_end_ms == 10000
    # Pure inference adapter receives only the permitted PCM interval, without
    # importing a decoder or model, and preserves the original time origin.
    from scripts.transcribe_live import transcribe
    received = []
    class Model:
        def transcribe(self, samples, **kwargs):
            received.extend(samples)
            return [], None
    archive = [1] * 80000
    current = [2] * 80000
    transcribe(Model(), archive + current, {'offset_ms': prepared.offset_ms,
        'clip_start_ms': prepared.clip_start_ms, 'clip_end_ms': prepared.clip_end_ms, 'keep_from_ms': 5000})
    assert received == ([1] * 8000 if expected_start == 4500 else []) + current


def test_short_completed_pcm_context_does_not_extend_into_earlier_retained_audio(tmp_path):
    rows = [{'id': '0', 'session_id': 'fictitious', 'track': 'mic', 'sequence': 0,
             'storage_path': str(tmp_path / 'retained-not-opened.wav'), 'size_bytes': 0,
             'sha256': 'f' * 64, 'start_ms': 0, 'duration_ms': 4900,
             'mime_type': 'audio/wav', 'speech_status': 'retained'}]
    for sequence, samples, start, duration, status, sample in [
            (1, 1600, 4900, 100, 'completed', 8), (2, 80000, 5000, 5000, 'running', 7)]:
        raw = wav(samples=samples, sample=sample)
        path = tmp_path / f'fiction-{sequence}.wav'
        path.write_bytes(raw)
        rows.append({'id': str(sequence), 'session_id': 'fictitious', 'track': 'mic', 'sequence': sequence,
            'storage_path': str(path), 'size_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'start_ms': start, 'duration_ms': duration, 'mime_type': 'audio/wav', 'speech_status': status})
    prepared = live.prepare_direct_chunk(rows[2], rows, storage_root=tmp_path, derived_root=tmp_path / 'derived')
    assert prepared.offset_ms + prepared.clip_start_ms == 4900
    with wave.open(str(prepared.path), 'rb') as audio:
        assert audio.readframes(audio.getnframes()) == bytes([8, 0]) * 1600 + bytes([7, 0]) * 80000
