"""Personal/long/unknown batch audio, simulated inference and isolated stores only."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import threading
from uuid import uuid4
import zipfile

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.db import get_db
from app.meeting_session_models import LiveTranscriptSegment, MeetingAudioChunk, MeetingSessionCommand
from app.meeting_session_schemas import Command
from app.models import MeetingRecording, Source
from app.routers.meeting_sessions import router
from app.services import audio_cpu_coordinator as cpu, meeting_sessions as sessions
from app.services import session_batch_transcription as batch
from app.services.settings_service import save_section
from backend.app.services.project_operator import Operator, operator_context
from tests.test_meeting_sessions import stores as stores_fixture, create, chunk, command, content, wav

stores = stores_fixture


def action(revision):
    return Command(command_id=str(uuid4()), expected_revision=revision)


def personal(db, *, raw=None, unknown=False, kind=None):
    save_section(db, 'foresight', {'enabled': True, 'live_transcription_enabled': False})
    row = create(db, kind=kind or ('import' if unknown else 'note'))
    sid = row['id']
    if unknown:
        raw = raw or b'ID3-personal-fictitious-audio'
        sessions.store_chunk(db, sid, 'mic', 0, raw=raw, filename='personal.mp3', mime_type='audio/mpeg',
            command_id=str(uuid4()), sha256=hashlib.sha256(raw).hexdigest(), start_ms=0, duration_ms=0)
    else:
        chunk(db, sid, raw=raw or wav(samples=320000), duration_ms=20000)
    row = command(db, sid, 'notes', sessions.get_session(db, sid).revision,
                  title='Note personnelle', content=content('Texte humain à conserver.'))
    row = command(db, sid, 'finalize', row['revision'])
    return row


class FakeResident:
    process = None

    def __init__(self, callback=None):
        self.calls = []
        self.closed = False
        self.callback = callback

    def transcribe(self, prepared, **kwargs):
        self.calls.append((prepared, kwargs))
        if self.callback:
            self.callback()
        return {'duration_ms': 20000, 'segments': [{'start_ms': prepared.offset_ms, 'end_ms': prepared.offset_ms + 19000,
            'speaker': 'mic', 'text': 'Le devis sera vérifié jeudi.'}]}

    def close(self):
        self.closed = True


@pytest.fixture
def harness(monkeypatch):
    captured = []
    resident = FakeResident()
    monkeypatch.setattr(batch, '_active', None)
    monkeypatch.setattr(batch, '_shutdown', threading.Event())
    monkeypatch.setattr(cpu, '_batch_owner', None)
    monkeypatch.setattr(cpu, '_direct_jobs', 0)
    monkeypatch.setattr(batch, 'available', lambda: True)
    monkeypatch.setattr(batch, '_new_resident', lambda root: resident)
    monkeypatch.setattr(batch, '_launch', lambda active: captured.append(active))
    yield captured, resident
    active = batch._active
    if active:
        active.cancel.set()
        if active.thread and active.thread.is_alive():
            resident.close()
            active.thread.join(3)
        if batch._active:
            assert not active.thread or not active.thread.is_alive(), 'Mock worker leaked from test'
            batch._terminal(active, 'interrupted')
            batch._release(active)


@pytest.mark.parametrize('unknown', [False, True])
def test_personal_long_or_unknown_audio_gets_explicit_batch_without_project(stores, harness, unknown):
    brain, _, _, _ = stores
    captured, resident = harness
    with brain() as db:
        row = personal(db, unknown=unknown)
        sid = row['id']
        original = db.scalar(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == sid))
        original_bytes = Path(original.storage_path).read_bytes()
        original_identity = (original.id, original.sha256, original.created_at)
        assert original.speech_status == 'retained' and row['project_id'] is None
        assert row['recording_id'] is None
        body = action(row['revision'])
        accepted = batch.request(db, sid, body)
        assert accepted['batch']['state'] == 'admitted' and accepted['batch']['selected_chunks'] == 1
        assert accepted['session']['transcription_batch'] == accepted['batch']
        assert db.get(MeetingAudioChunk, original.id).speech_status == 'batch_pending'
        assert not sessions.get_session(db, sid).pending_command_id
        assert not resident.calls  # Admission never loads/invokes a model itself.
        saved = command(db, sid, 'notes', accepted['session']['revision'],
                        title='Note corrigée', content=content('Correction humaine pendant le calcul.'))
        assert saved['staged_note']['plain_text'] == 'Correction humaine pendant le calcul.'
    batch._run(captured[0])
    assert resident.closed and len(resident.calls) == 1
    with brain() as db:
        final = sessions.serialize_session(db, sessions.get_session(db, sid))
        original = db.get(MeetingAudioChunk, original_identity[0])
        assert final['project_id'] is None and final['recording_id'] is None
        assert final['staged_note']['plain_text'] == 'Correction humaine pendant le calcul.'
        assert final['segments'][0]['text'] == 'Le devis sera vérifié jeudi.'
        assert final['transcription_batch']['state'] == 'completed'
        assert final['transcript_processing_complete'] is True
        assert (original.id, original.sha256, original.created_at) == original_identity
        assert Path(original.storage_path).read_bytes() == original_bytes
        assert not db.scalar(select(MeetingRecording.id)) and not db.scalar(select(Source.id))
        assert batch.request(db, sid, body) == accepted  # Immutable replay, no new inference.
        assert len(captured) == 1


def test_one_global_batch_admission_has_no_hidden_queue_or_cross_session_ids(stores, harness):
    brain, _, _, _ = stores
    with brain() as db:
        first = personal(db)
        second = personal(db)
        accepted = batch.request(db, first['id'], action(first['revision']))
        before = db.query(MeetingSessionCommand).count()
        with pytest.raises(HTTPException) as busy:
            batch.request(db, second['id'], action(second['revision']))
        assert busy.value.status_code == 409 and first['id'] not in str(busy.value.detail)
        assert db.query(MeetingSessionCommand).count() == before
        assert batch.status(db, second['id'])['state'] == 'idle'
        assert accepted['batch']['command_id'] not in json.dumps(batch.status(db, second['id']))
        with pytest.raises(cpu.AudioCpuBusy):
            with cpu.capture_start(db, second['id']):
                pytest.fail('Capture admission must remain unavailable')


@pytest.mark.parametrize('guard', ['capture', 'direct', 'missing-runtime', 'stale', 'reader'])
def test_admission_preconditions_preserve_audio_and_create_no_batch_receipt(stores, harness, monkeypatch, guard):
    brain, _, _, _ = stores
    with brain() as db:
        row = personal(db)
        body = action(row['revision'] - 1 if guard == 'stale' else row['revision'])
        if guard == 'capture':
            monkeypatch.setattr(cpu, '_capture_declared', lambda db: True)
        elif guard == 'direct':
            monkeypatch.setattr(cpu, '_direct_jobs', 1)
        elif guard == 'missing-runtime':
            monkeypatch.setattr(batch, 'available', lambda: False)
        original = db.scalar(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == row['id']))
        raw = Path(original.storage_path).read_bytes()
        context = Operator('local', 'reader') if guard == 'reader' else Operator('local', 'owner')
        with operator_context(context), pytest.raises(HTTPException):
            batch.request(db, row['id'], body)
        assert not db.get(MeetingSessionCommand, body.command_id)
        db.expire_all()
        assert original.speech_status == 'retained' and Path(original.storage_path).read_bytes() == raw
        assert cpu._batch_owner is None


def test_failed_prepared_admission_is_settled_without_loading_or_trapping_notes(stores, harness, monkeypatch):
    brain, _, _, _ = stores
    with brain() as db:
        row = personal(db)
        body = action(row['revision'])
        def fail(*args, **kwargs):
            raise RuntimeError('simulated commit interruption')
        with monkeypatch.context() as patch:
            patch.setattr(sessions, '_finish', fail)
            with pytest.raises(RuntimeError):
                batch.request(db, row['id'], body)
        command_row = db.get(MeetingSessionCommand, body.command_id)
        assert command_row.status == 'rejected'
        assert batch.status(db, row['id'])['state'] == 'interrupted'
        assert not sessions.get_session(db, row['id']).pending_command_id
        assert cpu._batch_owner is None and not harness[1].calls
        with pytest.raises(HTTPException):
            batch.request(db, row['id'], body)
        current = sessions.get_session(db, row['id'])
        assert command(db, row['id'], 'notes', current.revision, title='Après panne', content=content())['staged_note']


def test_durable_orphan_blocks_capture_until_explicit_or_startup_settlement(stores, harness, monkeypatch):
    brain, _, _, _ = stores
    with brain() as db:
        row = personal(db)
        body = action(row['revision'])
        accepted = batch.request(db, row['id'], body)
        packet_before = deepcopy(batch._packet(db.get(MeetingSessionCommand, body.command_id)))
        active = batch._active
        batch._release(active)  # Simulate lost in-memory ownership, no process ever started.
        with pytest.raises(cpu.AudioCpuBusy):
            with cpu.capture_start(db, row['id']):
                pytest.fail('Durable reservation must block capture after a crash')
        monkeypatch.setattr(batch, '_new_resident', lambda root: pytest.fail('Recovery must not load a model'))
        assert batch.recover_orphans(db, startup=True) == 1
        assert batch.recover_orphans(db, startup=True) == 0
        receipt = db.get(MeetingSessionCommand, body.command_id)
        assert receipt.result == accepted
        assert batch._packet(receipt)['chunks'] == packet_before['chunks']
        assert batch._packet(receipt)['admitted_at'] == packet_before['admitted_at']
        assert batch.status(db, row['id'])['state'] == 'interrupted'
        assert db.scalar(select(MeetingAudioChunk.speech_status).where(MeetingAudioChunk.session_id == row['id'])) == 'retained'
        with cpu.capture_start(db, row['id']):
            pass
        assert batch.request(db, row['id'], body) == accepted


@pytest.mark.parametrize('change', ['human', 'rights', 'binding', 'audio'])
def test_publication_rechecks_current_authority_original_and_human_revision(stores, harness, monkeypatch, change):
    brain, _, pid, bid = stores
    captured, resident = harness
    with brain() as db:
        row = personal(db)
        cid = db.scalar(select(MeetingAudioChunk.id).where(MeetingAudioChunk.session_id == row['id']))
        identity = 'live-' + hashlib.sha256(f'{cid}:0'.encode()).hexdigest()
        db.add(LiveTranscriptSegment(id=identity, session_id=row['id'], chunk_id=cid, track='mic',
            start_ms=0, end_ms=19000, speaker='Human', text='Correction déjà validée.', revision=2, finalized=False))
        db.commit()
        batch.request(db, row['id'], action(row['revision']))
    def mutate():
        if change == 'rights':
            monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
            return
        with brain() as db:
            if change == 'human':
                segment = db.get(LiveTranscriptSegment, identity)
                segment.text, segment.revision = 'Nouvelle correction humaine.', 3
            elif change == 'binding':
                current = sessions.get_session(db, row['id'])
                current.project_id, current.brain_project_id = pid, bid
            else:
                path = Path(db.get(MeetingAudioChunk, cid).storage_path)
                raw = bytearray(path.read_bytes())
                raw[-1] ^= 1
                path.write_bytes(raw)
            db.commit()
    resident.callback = mutate
    batch._run(captured[0])
    with brain() as db:
        assert db.get(MeetingAudioChunk, cid).speech_status == ('failed' if change == 'audio' else 'retained')
        assert db.get(LiveTranscriptSegment, identity).text == (
            'Nouvelle correction humaine.' if change == 'human' else 'Correction déjà validée.')
        assert db.query(LiveTranscriptSegment).count() == 1
        assert batch._packet(db.get(MeetingSessionCommand, captured[0].command_id))['state'] == ('failed' if change == 'audio' else 'interrupted')
    assert resident.closed and cpu._batch_owner is None


def test_existing_human_live_segment_is_never_overwritten_on_success(stores, harness):
    brain, _, _, _ = stores
    captured, _ = harness
    with brain() as db:
        row = personal(db)
        cid = db.scalar(select(MeetingAudioChunk.id).where(MeetingAudioChunk.session_id == row['id']))
        identity = 'live-' + hashlib.sha256(f'{cid}:0'.encode()).hexdigest()
        db.add(LiveTranscriptSegment(id=identity, session_id=row['id'], chunk_id=cid, track='mic',
            start_ms=0, end_ms=19000, speaker='Marie', text='Texte corrigé par Marie.', revision=3, finalized=False))
        db.commit()
        batch.request(db, row['id'], action(row['revision']))
    batch._run(captured[0])
    with brain() as db:
        segment = db.get(LiveTranscriptSegment, identity)
        assert (segment.text, segment.revision, segment.speaker) == ('Texte corrigé par Marie.', 3, 'Marie')
        assert batch.status(db, row['id'])['state'] == 'completed'


def test_cancel_keeps_cpu_until_worker_and_resident_close_then_replays_without_restart(stores, harness, monkeypatch):
    brain, _, _, _ = stores
    captured, resident = harness
    entered, close_entered, allow_close = threading.Event(), threading.Event(), threading.Event()
    class Process:
        ended = False
        def poll(self):
            return 0 if self.ended else None
    process = Process()
    resident.process = process
    def transcribe(prepared, **kwargs):
        entered.set()
        assert kwargs['cancel'].wait(3)
        raise InterruptedError()
    def close():
        close_entered.set()
        assert allow_close.wait(3)
        process.ended = True
        resident.closed = True
    monkeypatch.setattr(resident, 'transcribe', transcribe)
    monkeypatch.setattr(resident, 'close', close)
    with brain() as db:
        row = personal(db)
        batch.request(db, row['id'], action(row['revision']))
    active = captured[0]
    active.thread = threading.Thread(target=batch._run, args=(active,))
    active.thread.start()
    assert entered.wait(3)
    result = []
    def cancel_request():
        with brain() as db:
            current = sessions.get_session(db, row['id'])
            body = action(current.revision)
            result.append((body, batch.cancel(db, row['id'], body)))
    canceller = threading.Thread(target=cancel_request)
    canceller.start()
    assert close_entered.wait(3)
    with brain() as db:
        assert batch.status(db, row['id'])['state'] == 'cancelling'
        with pytest.raises(cpu.AudioCpuBusy):
            with cpu.capture_start(db, row['id']):
                pytest.fail('CPU released before close')
    allow_close.set()
    active.thread.join(3)
    canceller.join(3)
    assert not active.thread.is_alive() and not canceller.is_alive()
    assert process.ended and active.finished.is_set() and cpu._batch_owner is None
    with brain() as db:
        assert batch.status(db, row['id'])['state'] == 'cancelled'
        assert db.scalar(select(MeetingAudioChunk.speech_status).where(MeetingAudioChunk.session_id == row['id'])) == 'retained'
        assert batch.cancel(db, row['id'], result[0][0]) == result[0][1]
        assert len(captured) == 1


def test_get_and_api_post_are_scoped_and_projectless(stores, harness):
    brain, _, _, _ = stores
    app = FastAPI()
    app.include_router(router)
    def database():
        with brain() as db:
            yield db
    app.dependency_overrides[get_db] = database
    with brain() as db:
        row = personal(db, unknown=True)
    client = TestClient(app)
    path = f'/api/v1/meeting-sessions/{row["id"]}/transcription/batch'
    assert client.get(path).json()['state'] == 'idle'
    result = client.post(path, json=action(row['revision']).model_dump())
    assert result.status_code == 202 and result.json()['batch']['state'] == 'admitted'
    with operator_context(Operator('other', 'owner')):
        assert client.get(path).status_code == 404
    with operator_context(Operator('local', 'reader')):
        assert client.post(path, json=action(result.json()['session']['revision']).model_dump()).status_code == 403


def test_export_preserves_batch_state_and_audio_without_running_inference(stores, harness):
    from app.services.session_export import export
    brain, _, _, _ = stores
    with brain() as db:
        row = personal(db, unknown=True)
        batch.request(db, row['id'], action(row['revision']))
        target = export(db, row['id'])
    with zipfile.ZipFile(target) as archive:
        metadata = json.loads(archive.read('session.json'))
        assert metadata['session']['transcription_batch']['state'] == 'admitted'
        assert metadata['session']['chunks'][0]['speech_status'] == 'batch_pending'
        assert any(event['kind'] == 'transcript.batch.admitted' for event in metadata['events'])
        for path, binding in metadata['files'].items():
            assert hashlib.sha256(archive.read(path)).hexdigest() == binding['sha256']
    assert not harness[1].calls


def test_legacy_queued_keeps_capture_priority_but_new_personal_batch_cannot_cut_ahead(stores, harness):
    brain, _, pid, bid = stores
    with brain() as db:
        row = personal(db)
        source = Source(project_id=bid, source_type='meeting', status='resolved', original_uri='', sha256=uuid4().hex)
        db.add(source)
        db.flush()
        legacy = MeetingRecording(project_id=bid, source_id=source.id, erp_project_id=pid,
            title='Ancien batch fictif', filename='old.wav', job_kind='transcription', job_status='queued')
        db.add(legacy)
        db.commit()
        with pytest.raises(HTTPException) as busy:
            batch.request(db, row['id'], action(row['revision']))
        assert busy.value.status_code == 409
        with cpu.capture_start(db, row['id']):
            pass  # Preserve the existing priority over a merely queued job.
        with cpu.batch_slot(db, legacy.id):
            pass  # The legacy worker can still claim its own queue.
        legacy.job_status = 'running'
        db.commit()
        with pytest.raises(cpu.AudioCpuBusy):
            with cpu.capture_start(db, row['id']):
                pytest.fail('Actually running legacy batch must remain exclusive')


def test_explicit_cancel_of_prepared_orphan_does_not_change_its_snapshot_or_load(stores, harness):
    brain, _, _, _ = stores
    with brain() as db:
        row = personal(db)
        accepted = batch.request(db, row['id'], action(row['revision']))
        active = batch._active
        batch._release(active)
        old = db.get(MeetingSessionCommand, accepted['batch']['command_id'])
        snapshot = deepcopy(batch._packet(old)['chunks'])
        old.status, old.result = 'prepared', {}
        current = sessions.get_session(db, row['id'])
        current.pending_command_id = old.id
        db.commit()
        body = action(current.revision)
        cancelled = batch.cancel(db, row['id'], body)
        assert cancelled['batch']['state'] == 'cancelling'
        assert batch.status(db, row['id'])['state'] == 'cancelled'
        assert batch._packet(old)['chunks'] == snapshot and old.status == 'rejected'
        assert not sessions.get_session(db, row['id']).pending_command_id
        assert not batch.has_reserved_job(db) and not harness[1].calls
        assert batch.cancel(db, row['id'], body) == cancelled


def test_shutdown_interruption_closes_mock_worker_before_freeing_slot(stores, harness, monkeypatch):
    brain, _, _, _ = stores
    captured, resident = harness
    entered = threading.Event()
    def transcribe(prepared, **kwargs):
        entered.set()
        assert kwargs['cancel'].wait(3)
        raise InterruptedError()
    monkeypatch.setattr(resident, 'transcribe', transcribe)
    with brain() as db:
        row = personal(db)
        batch.request(db, row['id'], action(row['revision']))
    active = captured[0]
    active.thread = threading.Thread(target=batch._run, args=(active,))
    active.thread.start()
    assert entered.wait(3)
    batch.stop_all()
    active.thread.join(3)
    assert active.finished.is_set() and resident.closed and cpu._batch_owner is None
    with brain() as db:
        assert batch.status(db, row['id'])['state'] == 'interrupted'
        current = sessions.get_session(db, row['id'])
        with pytest.raises(HTTPException) as stopped:
            batch.request(db, row['id'], action(current.revision))
        assert stopped.value.status_code == 409
        assert batch._shutdown.is_set()


def test_partial_cancel_keeps_completed_chunks_and_preserves_remaining_audio(stores, harness, monkeypatch):
    brain, _, _, _ = stores
    captured, resident = harness
    with brain() as db:
        save_section(db, 'foresight', {'enabled': True, 'live_transcription_enabled': False})
        row = create(db, kind='note')
        chunk(db, row['id'], sequence=0, raw=wav(samples=320000), start_ms=0, duration_ms=20000)
        chunk(db, row['id'], sequence=1, raw=wav(samples=320000, sample=8), start_ms=20000, duration_ms=20000)
        row = command(db, row['id'], 'finalize', sessions.get_session(db, row['id']).revision)
        originals = {r.id: Path(r.storage_path).read_bytes() for r in db.scalars(select(MeetingAudioChunk))}
        batch.request(db, row['id'], action(row['revision']))
    calls = 0
    def transcribe(prepared, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            captured[0].cancel.set()
            raise InterruptedError()
        return {'duration_ms': 20000, 'segments': [{'start_ms': 0, 'end_ms': 19000,
            'speaker': 'mic', 'text': 'Première partie disponible.'}]}
    monkeypatch.setattr(resident, 'transcribe', transcribe)
    batch._run(captured[0])
    with brain() as db:
        result = batch.status(db, row['id'])
        assert result['state'] == 'cancelled' and result['selected_chunks'] == 2 and result['completed_chunks'] == 1
        rows = list(db.scalars(select(MeetingAudioChunk).order_by(MeetingAudioChunk.sequence)))
        assert [r.speech_status for r in rows] == ['completed', 'retained']
        assert all(Path(r.storage_path).read_bytes() == originals[r.id] for r in rows)
        assert db.query(LiveTranscriptSegment).count() == 1


def test_restored_batch_authority_is_interrupted_without_replaying_receipts(stores, harness, tmp_path):
    from app.db_support import backup_sqlite
    from app.services.meeting_session_backup import relocate
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    brain, _, _, _ = stores
    with brain() as db:
        row = personal(db, unknown=True)
        accepted = batch.request(db, row['id'], action(row['revision']))
        source_database = Path(db.get_bind().engine.url.database)
        original = db.scalar(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == row['id']))
        identifier, name = original.id, Path(original.storage_path).name
    batch._release(batch._active)  # Simulate an offline restored copy, no child existed.
    output = tmp_path / 'restored'
    output.mkdir()
    database = output / 'brain.db'
    backup_sqlite(source_database, database)
    relative = f'storage/meeting-sessions/{row["id"]}/mic/{name}'
    relocate(database, output, {identifier: {'path': relative}})
    engine = create_engine('sqlite:///' + database.as_posix())
    restored = sessionmaker(bind=engine)
    with restored() as db:
        assert db.get(MeetingAudioChunk, identifier).speech_status == 'batch_pending'
        assert batch.recover_orphans(db, startup=True) == 1
        assert db.get(MeetingAudioChunk, identifier).speech_status == 'retained'
        assert batch.status(db, row['id'])['state'] == 'interrupted'
        receipt = db.get(MeetingSessionCommand, accepted['batch']['command_id'])
        assert receipt.result == accepted
        assert not batch.has_reserved_job(db)
        assert not sessions.live_transcription_enabled(db)
    engine.dispose()
    assert not harness[1].calls


@pytest.mark.parametrize('kind', ['note', 'import'])
def test_old_personal_pending_unknown_is_explicitly_admitted_even_with_direct_off(stores, harness, kind):
    brain, _, _, _ = stores
    captured, _ = harness
    with brain() as db:
        row = personal(db, unknown=True, kind=kind)
        original = db.scalar(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == row['id']))
        original.speech_status = 'pending'  # Historical pre-admission-policy database.
        db.commit()
        old_receipt = db.scalar(select(MeetingSessionCommand).where(
            MeetingSessionCommand.session_id == row['id'], MeetingSessionCommand.kind == 'chunk'))
        saved_body, saved_result = deepcopy(old_receipt.body), deepcopy(old_receipt.result)
        original_id, receipt_id = original.id, old_receipt.id
        assert not sessions.live_transcription_enabled(db)
        assert batch.status(db, row['id'])['state'] == 'idle'
        assert original.speech_status == 'pending'  # GET never reconciles or processes it.
        result = batch.request(db, row['id'], action(row['revision']))
        assert result['batch']['selected_chunks'] == 1 and original.speech_status == 'batch_pending'
    batch._run(captured[0])
    with brain() as db:
        assert db.get(MeetingAudioChunk, original_id).speech_status == 'completed'
        assert db.get(MeetingSessionCommand, receipt_id).body == saved_body
        assert db.get(MeetingSessionCommand, receipt_id).result == saved_result
        assert not sessions.get_session(db, row['id']).project_id


def test_batch_decodes_all_standalone_bytes_and_keeps_original_declared_duration_receipt(stores, harness, monkeypatch):
    brain, _, _, _ = stores
    captured, resident = harness
    with brain() as db:
        save_section(db, 'foresight', {'enabled': True, 'live_transcription_enabled': True})
        row = create(db, kind='note')
        raw = wav(samples=320000)
        cid = str(uuid4())
        kwargs = {'raw': raw, 'filename': 'capture.wav', 'mime_type': 'audio/wav', 'command_id': cid,
                  'sha256': hashlib.sha256(raw).hexdigest(), 'start_ms': 0, 'duration_ms': 5000}
        original_receipt = sessions.store_chunk(db, row['id'], 'mic', 0, **kwargs)
        original = db.scalar(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == row['id']))
        assert original.speech_status == 'retained' and original.duration_ms == 5000
        original_id = original.id
        row = command(db, row['id'], 'finalize', sessions.get_session(db, row['id']).revision)
        batch.request(db, row['id'], action(row['revision']))
    def transcribe(prepared, **kwargs):
        assert prepared.clip_end_ms is None and not prepared.assembled
        return {'duration_ms': 20000, 'segments': [{'start_ms': 0, 'end_ms': 20000,
            'speaker': 'mic', 'text': 'Toute la durée du fichier a été considérée.'}]}
    monkeypatch.setattr(resident, 'transcribe', transcribe)
    batch._run(captured[0])
    with brain() as db:
        current = sessions.serialize_session(db, sessions.get_session(db, row['id']))
        assert current['duration_seconds'] == 20 and current['tracks'][0]['duration_seconds'] == 20
        assert current['chunks'][0]['duration_ms'] == 20000
        assert current['segments'][0]['end_ms'] == 20000
        assert db.get(MeetingSessionCommand, cid).body['duration_ms'] == 5000
        assert sessions.store_chunk(db, row['id'], 'mic', 0, **kwargs) == original_receipt
        assert Path(db.get(MeetingAudioChunk, original_id).storage_path).read_bytes() == raw


@pytest.mark.parametrize('change', ['cancel', 'rights'])
def test_cancel_or_lost_authority_before_first_tick_never_constructs_resident(stores, harness, monkeypatch, change):
    brain, _, _, _ = stores
    captured, _ = harness
    with brain() as db:
        row = personal(db)
        batch.request(db, row['id'], action(row['revision']))
    if change == 'cancel':
        captured[0].cancel.set()
    else:
        monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    monkeypatch.setattr(batch, '_new_resident', lambda root: pytest.fail('No resident may be constructed'))
    batch._run(captured[0])
    with brain() as db:
        command_row = db.get(MeetingSessionCommand, captured[0].command_id)
        assert batch._packet(command_row)['state'] == ('cancelled' if change == 'cancel' else 'interrupted')
        assert db.scalar(select(MeetingAudioChunk.speech_status).where(MeetingAudioChunk.session_id == row['id'])) == 'retained'
    assert cpu._batch_owner is None


def test_failed_close_keeps_detached_child_handle_and_cpu_reservation_until_real_exit(stores, harness, monkeypatch):
    brain, _, _, _ = stores
    captured, resident = harness
    class Process:
        ended = False
        def poll(self):
            return 0 if self.ended else None
    process = Process()
    resident.process = process
    def uncertain_close():
        resident.process = None  # Match ResidentWhisper's detach-before-wait behavior.
        raise TimeoutError('simulated close timeout')
    monkeypatch.setattr(resident, 'close', uncertain_close)
    with brain() as db:
        row = personal(db)
        batch.request(db, row['id'], action(row['revision']))
    active = captured[0]
    active.thread = threading.Thread(target=batch._run, args=(active,))
    active.thread.start()
    active.thread.join(5)
    assert not active.thread.is_alive() and not active.finished.is_set()
    assert active.processes == [process] and cpu._batch_owner is not None
    with brain() as db:
        with pytest.raises(cpu.AudioCpuBusy):
            with cpu.capture_start(db, row['id']):
                pytest.fail('An uncertain child close must retain CPU ownership')
        assert batch.status(db, row['id'])['state'] == 'running'
        process.ended = True
        current = sessions.get_session(db, row['id'])
        batch.cancel(db, row['id'], action(current.revision))
        assert batch.status(db, row['id'])['state'] == 'cancelled'
    assert active.finished.is_set() and cpu._batch_owner is None


def test_one_watchdog_deadline_covers_loading_and_inference_without_early_cpu_release(stores, harness, monkeypatch):
    brain, _, _, _ = stores
    captured, resident = harness
    def wait_for_timeout(prepared, **kwargs):
        assert kwargs['cancel'].wait(2)
        raise InterruptedError()
    monkeypatch.setattr(resident, 'transcribe', wait_for_timeout)
    monkeypatch.setattr(batch, 'MAX_JOB_SECONDS', 1)
    with brain() as db:
        row = personal(db)
        batch.request(db, row['id'], action(row['revision']))
    active = captured[0]
    batch._run(active)
    assert active.deadline_exceeded.is_set() and active.finished.is_set()
    assert resident.closed and cpu._batch_owner is None
    with brain() as db:
        result = batch.status(db, row['id'])
        assert result['state'] == 'failed' and 'Durée limite' in result['error']
        assert db.scalar(select(MeetingAudioChunk.speech_status).where(MeetingAudioChunk.session_id == row['id'])) == 'failed'
        assert not db.scalar(select(LiveTranscriptSegment.id))


def test_cancel_snapshots_child_created_under_start_lock_even_after_detach_timeout(stores, harness, monkeypatch):
    brain, _, _, _ = stores
    captured, resident = harness
    starting, create_child, close_attempted, detached = (threading.Event() for _ in range(4))
    class ObservedRLock:
        def __init__(self):
            self.lock = threading.RLock()
        def __enter__(self):
            if threading.current_thread().name == 'cancel-batch-lock-probe':
                close_attempted.set()  # Signal before blocking behind start().
            self.lock.acquire()
            return self
        def __exit__(self, *args):
            self.lock.release()
    close_lock = ObservedRLock()
    class Process:
        ended = False
        def poll(self):
            return 0 if self.ended else None
    process = Process()
    monkeypatch.setattr(resident, '_close_lock', close_lock, raising=False)
    resident.process = None
    def transcribe(prepared, **kwargs):
        with close_lock:
            starting.set()
            assert create_child.wait(3)
            resident.process = process
        assert kwargs['cancel'].is_set()
        assert detached.wait(3)  # Worker cannot rescue the old wrapper's missed handle.
        raise InterruptedError()
    def close():
        with close_lock:
            if resident.process is not None:
                resident.process = None
                detached.set()
                raise TimeoutError('Detach succeeded, wait for child failed')
            resident.closed = True  # A second apparent close is not exit proof.
    monkeypatch.setattr(resident, 'transcribe', transcribe)
    monkeypatch.setattr(resident, 'close', close)
    with brain() as db:
        row = personal(db)
        batch.request(db, row['id'], action(row['revision']))
    active = captured[0]
    active.thread = threading.Thread(target=batch._run, args=(active,))
    active.thread.start()
    assert starting.wait(3)
    cancellations = []
    def cancel_request():
        with brain() as db:
            current = sessions.get_session(db, row['id'])
            cancellations.append(batch.cancel(db, row['id'], action(current.revision)))
    canceller = threading.Thread(target=cancel_request, name='cancel-batch-lock-probe')
    canceller.start()
    assert active.cancel.wait(3)
    assert close_attempted.wait(3)
    create_child.set()
    active.thread.join(3)
    canceller.join(8)
    assert not active.thread.is_alive() and not canceller.is_alive()
    assert active.processes == [process] and not active.finished.is_set()
    assert resident.closed and cpu._batch_owner is not None
    with brain() as db:
        assert batch.status(db, row['id'])['state'] == 'cancelling'
        with pytest.raises(cpu.AudioCpuBusy):
            with cpu.capture_start(db, row['id']):
                pytest.fail('Detached child is still running')
        process.ended = True
        current = sessions.get_session(db, row['id'])
        batch.cancel(db, row['id'], action(current.revision))
        assert batch.status(db, row['id'])['state'] == 'cancelled'
    assert active.finished.is_set() and cpu._batch_owner is None

@pytest.fixture
def fusion_controls_without_other_workers(monkeypatch):
    from app.routers import fusion_insights as route
    monkeypatch.setattr('app.services.native_audio.status', lambda *args: {'active': []})
    monkeypatch.setattr('app.services.live_speech.stop_worker', lambda: None)
    monkeypatch.setattr('app.services.session_proactive.stop_worker', lambda: None)
    monkeypatch.setattr(route, 'controls', lambda db: {
        'enabled': sessions.feature_enabled(db), 'live_transcription_enabled': sessions.live_transcription_enabled(db)})
    return route


def test_direct_off_preserves_manual_batch(stores, harness, fusion_controls_without_other_workers):
    brain, _, _, _ = stores
    route = fusion_controls_without_other_workers
    with brain() as db:
        row = personal(db)
        admitted = batch.request(db, row['id'], action(row['revision']))
        route.configure(route.Controls(enabled=True, live_transcription_enabled=False), db)
        assert batch.status(db, row['id'])['state'] == 'admitted'
        assert not harness[0][0].cancel.is_set() and not batch._shutdown.is_set()
    batch._run(harness[0][0])
    with brain() as db:
        assert batch.status(db, row['id'])['state'] == 'completed'
        assert db.get(MeetingSessionCommand, admitted['batch']['command_id']).result == admitted


def test_general_off_before_tick_stops_without_constructing_resident_and_keeps_recovery(stores, harness, monkeypatch,
                                                                                       fusion_controls_without_other_workers):
    brain, _, _, _ = stores
    route = fusion_controls_without_other_workers
    with brain() as db:
        row = personal(db, unknown=True)
        original = db.scalar(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == row['id']))
        original_id, original_hash = original.id, original.sha256
        body = action(row['revision'])
        admitted = batch.request(db, row['id'], body)
        route.configure(route.Controls(enabled=False, live_transcription_enabled=False), db)
    monkeypatch.setattr(batch, '_new_resident', lambda root: pytest.fail('Global off must not construct a resident'))
    batch._run(harness[0][0])
    with brain() as db:
        assert batch.status(db, row['id'])['state'] == 'interrupted'
        assert not batch._shutdown.is_set() and cpu._batch_owner is None
        assert db.get(MeetingAudioChunk, original_id).sha256 == original_hash
        assert db.get(MeetingAudioChunk, original_id).speech_status == 'retained'
        assert batch.request(db, row['id'], body) == admitted  # Exact receipt, no new compute.
        current = sessions.get_session(db, row['id'])
        cancelled = batch.cancel(db, row['id'], action(current.revision))
        assert cancelled['batch']['state'] == 'interrupted'
        assert batch.status(db, row['id'])['state'] == 'interrupted'
        assert not harness[1].calls


def test_general_off_blocks_new_admission_without_reserving_cpu(stores, harness):
    brain, _, _, _ = stores
    with brain() as db:
        row = personal(db)
        save_section(db, 'foresight', {'enabled': False, 'live_transcription_enabled': False})
        body = action(row['revision'])
        with pytest.raises(HTTPException) as disabled:
            batch.request(db, row['id'], body)
        assert disabled.value.status_code == 409
        assert not db.get(MeetingSessionCommand, body.command_id)
        assert batch.status(db, row['id'])['state'] == 'idle'
        assert cpu._batch_owner is None and not harness[1].calls


def test_general_off_after_prepare_is_rechecked_under_fresh_writer(stores, harness, monkeypatch):
    brain, _, _, _ = stores
    original_begin = sessions._begin
    with brain() as db:
        row = personal(db)
        body = action(row['revision'])
    def prepare_then_disable(*args, **kwargs):
        receipt = original_begin(*args, **kwargs)
        with brain() as changed:
            save_section(changed, 'foresight', {'enabled': False, 'live_transcription_enabled': False})
        return receipt
    monkeypatch.setattr(sessions, '_begin', prepare_then_disable)
    with brain() as db, pytest.raises(HTTPException) as disabled:
        batch.request(db, row['id'], body)
    assert disabled.value.status_code == 409 and not harness[0]
    with brain() as db:
        assert db.get(MeetingSessionCommand, body.command_id).status == 'rejected'
        assert not sessions.get_session(db, row['id']).pending_command_id
        assert db.scalar(select(MeetingAudioChunk.speech_status).where(MeetingAudioChunk.session_id == row['id'])) == 'retained'
        assert cpu._batch_owner is None


def test_worker_rechecks_general_off_before_publication_even_without_route_callback(stores, harness):
    brain, _, _, _ = stores
    captured, resident = harness
    with brain() as db:
        row = personal(db)
        batch.request(db, row['id'], action(row['revision']))
    def disable_in_other_connection():
        with brain() as db:
            save_section(db, 'foresight', {'enabled': False, 'live_transcription_enabled': False})
    resident.callback = disable_in_other_connection
    batch._run(captured[0])
    with brain() as db:
        assert batch.status(db, row['id'])['state'] == 'interrupted'
        assert not db.scalar(select(LiveTranscriptSegment.id))
        assert db.scalar(select(MeetingAudioChunk.speech_status).where(MeetingAudioChunk.session_id == row['id'])) == 'retained'
    assert resident.closed and cpu._batch_owner is None


def test_general_off_closes_running_mock_and_reactivation_accepts_new_explicit_batch(stores, harness, monkeypatch,
                                                                                  fusion_controls_without_other_workers):
    brain, _, _, _ = stores
    captured, resident = harness
    route = fusion_controls_without_other_workers
    entered = threading.Event()
    def transcribe(prepared, **kwargs):
        entered.set()
        assert kwargs['cancel'].wait(3)
        raise InterruptedError()
    monkeypatch.setattr(resident, 'transcribe', transcribe)
    with brain() as db:
        row = personal(db)
        body = action(row['revision'])
        admitted = batch.request(db, row['id'], body)
    active = captured[0]
    active.thread = threading.Thread(target=batch._run, args=(active,))
    active.thread.start()
    assert entered.wait(3)
    with brain() as db:
        route.configure(route.Controls(enabled=False, live_transcription_enabled=False), db)
    active.thread.join(3)
    assert not active.thread.is_alive() and active.finished.is_set() and resident.closed
    assert cpu._batch_owner is None and not batch._shutdown.is_set()
    replacement = FakeResident()
    monkeypatch.setattr(batch, '_new_resident', lambda root: replacement)
    with brain() as db:
        assert batch.status(db, row['id'])['state'] == 'interrupted'
        assert batch.request(db, row['id'], body) == admitted
        route.configure(route.Controls(enabled=True, live_transcription_enabled=False), db)
        current = sessions.get_session(db, row['id'])
        result = batch.request(db, row['id'], action(current.revision))
        assert result['batch']['state'] == 'admitted' and len(captured) == 2
    batch._run(captured[1])
    with brain() as db:
        assert batch.status(db, row['id'])['state'] == 'completed'
    assert replacement.closed and len(replacement.calls) == 1


def test_general_off_still_signals_and_closes_if_stop_marker_write_fails(stores, harness, monkeypatch,
                                                                     fusion_controls_without_other_workers):
    brain, _, _, _ = stores
    captured, resident = harness
    route = fusion_controls_without_other_workers
    entered = threading.Event()
    caller = threading.get_ident()
    stopped = []
    monkeypatch.setattr('app.services.live_speech.stop_worker', lambda: stopped.append('speech'))
    monkeypatch.setattr('app.services.session_proactive.stop_worker', lambda: stopped.append('proactive'))
    def transcribe(prepared, **kwargs):
        entered.set()
        assert kwargs['cancel'].wait(3)
        raise InterruptedError()
    monkeypatch.setattr(resident, 'transcribe', transcribe)
    with brain() as db:
        row = personal(db)
        batch.request(db, row['id'], action(row['revision']))
    active = captured[0]
    active.thread = threading.Thread(target=batch._run, args=(active,))
    active.thread.start()
    assert entered.wait(3)
    original_writer = batch._writer
    def fail_marker_only(db):
        if threading.get_ident() == caller:
            raise RuntimeError('Fictitious stop-marker SQL failure')
        return original_writer(db)
    monkeypatch.setattr(batch, '_writer', fail_marker_only)
    with brain() as db, pytest.raises(RuntimeError):
        route.configure(route.Controls(enabled=False, live_transcription_enabled=False), db)
    active.thread.join(3)
    assert stopped == ['speech', 'proactive']
    assert active.cancel.is_set() and active.finished.is_set() and resident.closed
    assert cpu._batch_owner is None and not batch._shutdown.is_set()
    with brain() as db:
        assert not sessions.feature_enabled(db)
        assert batch.status(db, row['id'])['state'] == 'interrupted'
        assert not db.scalar(select(LiveTranscriptSegment.id))



def test_general_off_still_stops_batch_if_speech_stop_raises(stores, harness, monkeypatch,
                                                           fusion_controls_without_other_workers):
    brain, _, _, _ = stores
    captured, resident = harness
    route = fusion_controls_without_other_workers
    entered = threading.Event()
    stopped = []
    def transcribe(prepared, **kwargs):
        entered.set()
        assert kwargs['cancel'].wait(3)
        raise InterruptedError()
    def fail_speech_stop():
        stopped.append('speech')
        raise RuntimeError('Fictitious speech stop failure')
    monkeypatch.setattr(resident, 'transcribe', transcribe)
    monkeypatch.setattr('app.services.live_speech.stop_worker', fail_speech_stop)
    with brain() as db:
        row = personal(db)
        batch.request(db, row['id'], action(row['revision']))
    active = captured[0]
    active.thread = threading.Thread(target=batch._run, args=(active,))
    active.thread.start()
    assert entered.wait(3)
    with brain() as db, pytest.raises(RuntimeError, match='Fictitious speech stop failure'):
        route.configure(route.Controls(enabled=False, live_transcription_enabled=False), db)
    active.thread.join(3)
    assert stopped == ['speech']
    assert not active.thread.is_alive() and active.cancel.is_set() and active.finished.is_set()
    assert resident.closed and cpu._batch_owner is None and not batch._shutdown.is_set()
    with brain() as db:
        assert not sessions.feature_enabled(db)
        assert batch.status(db, row['id'])['state'] == 'interrupted'
        assert not db.scalar(select(LiveTranscriptSegment.id))
