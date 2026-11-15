"""Atomic immediate admission; legacy audio and all originals stay intact."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import queue
from threading import Barrier, Event
from uuid import uuid4

from fastapi import HTTPException
import pytest

from app.meeting_session_schemas import Command
from app.models import MeetingRecording, Source
from app.routers import native_capture
from app.services import audio_cpu_coordinator as cpu, meeting_audio as batch, meeting_sessions as sessions
from tests.test_meeting_sessions import stores as stores_fixture, create, command, key, wav

stores = stores_fixture


@pytest.fixture(autouse=True)
def coordinator(monkeypatch):
    monkeypatch.setattr(cpu, '_batch_owner', None)
    monkeypatch.setattr(cpu, '_direct_jobs', 0)
    monkeypatch.setattr('app.services.native_audio._captures', {})


def recording(db, bid, pid, tmp_path):
    path = tmp_path / ('fictif-' + uuid4().hex + '.wav')
    raw = wav()
    path.write_bytes(raw)
    source = Source(project_id=bid, source_type='audio', status='resolved', original_uri=str(path),
        sha256=hashlib.sha256(raw + uuid4().bytes).hexdigest())
    db.add(source)
    db.flush()
    row = MeetingRecording(project_id=bid, erp_project_id=pid, source_id=source.id, title='Enregistrement fictif', filename=path.name)
    db.add(row)
    db.commit()
    return row


def ready_batch(monkeypatch, brain):
    monkeypatch.setattr(batch, 'SessionLocal', brain)
    monkeypatch.setattr(batch, 'runtime_status', lambda: {'ready': True, 'detail': 'Fixture'})
    monkeypatch.setattr(batch, '_stop', Event())


def result():
    return {'segments': [{'id': 's1', 'start': 0., 'end': .01, 'speaker': 'FICTIF', 'text': 'Audio fictif conservé'}]}


def test_new_batch_is_busy_during_declared_capture_and_paused(stores, monkeypatch, tmp_path):
    brain, _, pid, bid = stores
    ready_batch(monkeypatch, brain)
    with brain() as db:
        legacy = recording(db, bid, pid, tmp_path)
        studio = create(db)
        command(db, studio['id'], 'resume', 1)
        with pytest.raises(cpu.AudioCpuBusy, match='Capture'):
            batch.queue_job(db, legacy, 'transcription')
        assert legacy.job_status == 'idle' and legacy.segments == []
        command(db, studio['id'], 'pause', 2)
        with pytest.raises(cpu.AudioCpuBusy):
            batch.queue_job(db, legacy, 'transcription')
        assert cpu.status()['batch_active'] is False


def test_running_batch_refuses_browser_and_native_start_immediately_then_releases(stores, monkeypatch, tmp_path):
    brain, _, pid, bid = stores
    ready_batch(monkeypatch, brain)
    entered, release = Event(), Event()
    def transcribe(*args):
        entered.set()
        assert release.wait(5)
        return result()
    monkeypatch.setattr(batch, '_transcribe', transcribe)
    with brain() as db:
        legacy = recording(db, bid, pid, tmp_path)
        batch.queue_job(db, legacy, 'transcription')
        rid = legacy.id
        browser = create(db)
        native = create(db)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(batch.run_job, rid)
        assert entered.wait(3)
        assert cpu.status()['batch_active']
        with brain() as db:
            with pytest.raises(HTTPException) as caught:
                command(db, browser['id'], 'resume', 1)
            assert caught.value.status_code == 409 and 'Transcription complète' in caught.value.detail
            assert sessions.get_session(db, browser['id']).pending_command_id is None
            with pytest.raises(HTTPException) as caught:
                native_capture.perform(db, native['id'], 'start', native_capture.Start(command_id=key(), expected_revision=1, tracks=['mic']))
            assert caught.value.status_code == 409
        release.set()
        assert future.result(timeout=5)
    assert not cpu.status()['batch_active']
    with brain() as db:
        assert db.get(MeetingRecording, rid).job_status == 'completed'
        assert command(db, browser['id'], 'resume', 1)['state'] == 'recording'


def test_preexisting_queued_batch_waits_without_computation_then_resumes(stores, monkeypatch, tmp_path):
    brain, _, pid, bid = stores
    ready_batch(monkeypatch, brain)
    calls = []
    monkeypatch.setattr(batch, '_transcribe', lambda *args: calls.append(True) or result())
    with brain() as db:
        legacy = recording(db, bid, pid, tmp_path)
        batch.queue_job(db, legacy, 'transcription')
        rid = legacy.id
        studio = create(db)
        command(db, studio['id'], 'resume', 1)
    assert batch.run_job(rid) is False and calls == []
    with brain() as db:
        legacy = db.get(MeetingRecording, rid)
        assert legacy.job_status == 'queued' and 'file d’attente' in legacy.error
        command(db, studio['id'], 'finalize', 2)
    assert batch.run_job(rid) is True and calls == [True]
    with brain() as db:
        assert db.get(MeetingRecording, rid).job_status == 'completed'


def test_batch_capture_admission_race_has_one_winner(stores):
    brain, _, _, _ = stores
    with brain() as db:
        studio = create(db)
    barrier, release, admissions = Barrier(2), Event(), queue.Queue()
    def browser():
        with brain() as db:
            barrier.wait(3)
            try:
                sessions.execute_command(db, studio['id'], 'resume', Command(command_id=key(), expected_revision=1))
                admissions.put('capture')
            except HTTPException as exc:
                assert exc.status_code == 409
                admissions.put('busy')
    def complete():
        with brain() as db:
            barrier.wait(3)
            try:
                with cpu.batch_slot(db, 'fictitious-batch'):
                    admissions.put('batch')
                    assert release.wait(5)
            except cpu.AudioCpuBusy:
                admissions.put('busy')
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(browser), executor.submit(complete)]
        first, second = admissions.get(timeout=5), admissions.get(timeout=5)
        release.set()
        for future in futures:
            future.result(timeout=5)
    assert {first, second} in [{'batch', 'busy'}, {'capture', 'busy'}]
    assert not cpu.status()['batch_active']


@pytest.mark.parametrize('failure,expected', [(ValueError('fixture failed'), 'failed'), (batch.Cancelled(), 'cancelled')])
def test_batch_exception_or_cancel_releases_token_and_keeps_audio(stores, monkeypatch, tmp_path, failure, expected):
    brain, _, pid, bid = stores
    ready_batch(monkeypatch, brain)
    monkeypatch.setattr(batch, '_transcribe', lambda *args: (_ for _ in ()).throw(failure))
    with brain() as db:
        legacy = recording(db, bid, pid, tmp_path)
        path = db.get(Source, legacy.source_id).original_uri
        batch.queue_job(db, legacy, 'transcription')
        rid = legacy.id
    assert batch.run_job(rid)
    assert not cpu.status()['batch_active']
    from pathlib import Path
    assert Path(path).read_bytes() == wav()
    with brain() as db:
        assert db.get(MeetingRecording, rid).job_status == expected
        studio = create(db)
        assert command(db, studio['id'], 'resume', 1)['state'] == 'recording'


def test_direct_speech_activity_blocks_batch_and_releases_after_error(stores):
    brain, _, _, _ = stores
    with brain() as db:
        with pytest.raises(RuntimeError, match='fixture'):
            with cpu.direct_speech():
                assert cpu.status()['direct_speech_jobs'] == 1
                with pytest.raises(cpu.AudioCpuBusy):
                    cpu.ensure_batch_available(db)
                raise RuntimeError('fixture')
        assert cpu.status()['direct_speech_jobs'] == 0
        with cpu.batch_slot(db, 'fictif'):
            with pytest.raises(cpu.AudioCpuBusy, match='fragment direct'):
                with cpu.direct_speech():
                    pytest.fail('direct overlaps batch')


def test_capabilities_distinguish_operational_trial_from_qualified_live(stores, monkeypatch):
    brain, _, _, _ = stores
    monkeypatch.setattr('app.services.meeting_audio.runtime_status', lambda **kwargs: {'ready': True, 'detail': 'Batch'})
    monkeypatch.setattr('app.services.native_audio.status', lambda *args: {})
    monkeypatch.setattr('app.services.live_speech.runtime_status', lambda: {'ready': True, 'detail': 'Une voix fictive'})
    with brain() as db:
        capability = sessions.capabilities(db)
        assert capability['transcription']['live_operational'] and not capability['transcription']['live_ready']
        assert 'relecture nécessaire' in capability['transcription']['detail']
        assert capability['audio_arbitration']['admission_wait_seconds'] == 0
        assert capability['proactive_limits']['queue_wait_seconds'] == 900
        monkeypatch.setattr('app.services.live_speech.runtime_status', lambda: {'ready': True,
            'qualified_live_latency': True, 'industrial_quality_qualified': True, 'detail': 'Qualifié'})
        assert sessions.capabilities(db)['transcription']['live_ready']
