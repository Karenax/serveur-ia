"""Owner/recovery visibility with private stores and fake processes only."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
from pathlib import Path
from types import SimpleNamespace
from threading import Event

from fastapi import HTTPException
import pytest
from sqlalchemy import select

from app.meeting_session_models import MeetingSession, MeetingSessionCommand, MeetingSessionEvent, MeetingAudioChunk
from app.meeting_session_schemas import Command
from app.routers import native_capture as routes
from app.services import meeting_sessions as sessions, native_audio as native
from backend.app.services.project_operator import Operator, operator_context
from tests.test_meeting_sessions import stores as stores_fixture, create, key, wav

stores = stores_fixture


@pytest.fixture(autouse=True)
def no_hardware(monkeypatch):
    monkeypatch.setattr(native, '_captures', {})
    monkeypatch.setattr(native, '_qualification', None)
    def forbidden(*args, **kwargs):
        raise AssertionError('This NEXT suite never opens devices or a real child')
    monkeypatch.setattr(native, 'inventory', forbidden)
    monkeypatch.setattr(native.subprocess, 'Popen', forbidden)
    def metadata(sid=None):
        selected = native._captures.get(sid)
        return {'installed': True, 'ready': True, 'devices': [], 'active': [
            {'session_id': identity, 'state': owner.state, 'tracks': owner.tracks}
            for identity, owner in native._captures.items()],
            'session': {'session_id': sid, 'state': selected.state, 'error': selected.error}
                if selected else None}
    monkeypatch.setattr(native, 'status', metadata)


def owned(db, row, tmp_path, *, state='recording', exit_code=None):
    record = db.get(MeetingSession, row['id'])
    record.state = 'paused' if state == 'paused' else 'recording'
    event = sessions.append_event(db, record, 'native.capture.owner', {'tracks': ['mic']})
    db.commit()
    owner = native.NativeCapture(row['id'], tmp_path, ['mic'], {}, {'mic': 0}, 0)
    owner.owner_event_id = event.id
    owner.state = state
    owner.process = SimpleNamespace(poll=lambda: exit_code, wait=lambda timeout: exit_code,
        stdin=io.StringIO(), stdout=io.StringIO())
    native._captures[row['id']] = owner
    return owner


@pytest.mark.parametrize('state,exit_code,expected', [
    ('created', None, 'starting'), ('paused', None, 'paused'),
    ('interrupted', 1, 'interrupted'), ('stopped', 0, 'stopped'),
])
def test_all_registered_owners_visible_without_inventory(stores, tmp_path, state, exit_code, expected):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        owner = owned(db, row, tmp_path, state=state, exit_code=exit_code)
        if state == 'interrupted':
            owner.error = 'Do not disclose a raw private path globally'
        result = routes.status(db)
        assert result['owners'][0]['session_id'] == row['id']
        assert result['owners'][0]['state'] == expected
        assert result['owners'][0]['stop_confirmation_required'] is True
        assert result['owners'][0]['can_control'] is True
        assert bool(result['active']) is (exit_code is None)
        assert 'Do not disclose' not in str(result)
        assert native.has_capture_owner()


def test_snapshot_releases_registry_before_waiting_for_event_lock(stores, tmp_path):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        owner = owned(db, row, tmp_path)
    attempted = Event()
    real = owner._event_lock
    class Observe:
        def __enter__(self):
            attempted.set()
            return real.__enter__()
        def __exit__(self, *args):
            return real.__exit__(*args)
    owner._event_lock = Observe()
    with ThreadPoolExecutor(max_workers=1) as executor:
        with real:
            future = executor.submit(native.registered_snapshots)
            assert attempted.wait(1)
            with native._lock:
                native._captures.pop(row['id'])
        assert future.result(timeout=1) == []


def test_poll_failure_is_unknown_not_an_empty_success(stores, tmp_path):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        owner = owned(db, row, tmp_path)
        def failed():
            raise OSError('Fake unavailable handle')
        owner.process.poll = failed
        result = routes.status(db)
        assert result['active'] == []
        assert result['owners'][0]['process_alive'] is None
        assert result['owners'][0]['problem_code'] == 'status-unknown'


def test_paused_reader_interruption_is_durable_once_and_keeps_audio(stores, tmp_path):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        owner = owned(db, row, tmp_path, state='paused', exit_code=1)
        artifact = owner.directory / 'retained.wav'
        artifact.write_bytes(b'Already retained immutable audio')
        owner._interrupt('Fake audio permission lost')
        owner._record_interruption()
        owner._record_interruption()
        db.expire_all()
        assert db.get(MeetingSession, row['id']).state == 'interrupted'
        events = list(db.scalars(select(MeetingSessionEvent).where(
            MeetingSessionEvent.session_id == row['id'], MeetingSessionEvent.kind == 'native.capture.interrupted')))
        assert len(events) == 1 and events[0].data['owner_event_id'] == owner.owner_event_id
        assert artifact.read_bytes() == b'Already retained immutable audio'
        assert routes.status(db)['recovery'][0]['reason'] == 'interrupted'
        assert sessions.serialize_session(db, db.get(MeetingSession, row['id']))['issues']


def test_old_reader_cannot_interrupt_a_new_generation(stores, tmp_path):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        owner = owned(db, row, tmp_path)
        sessions.append_event(db, db.get(MeetingSession, row['id']), 'native.capture.owner', {'tracks': ['mic']})
        db.commit()
        owner._interrupt('Late old-reader failure')
        owner._record_interruption()
        db.expire_all()
        assert db.get(MeetingSession, row['id']).state == 'recording'
        assert not list(db.scalars(select(MeetingSessionEvent).where(
            MeetingSessionEvent.kind == 'native.capture.interrupted')))


def test_persistence_failure_remains_an_unconfirmed_runtime_warning(stores, tmp_path, monkeypatch):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        owner = owned(db, row, tmp_path, state='paused', exit_code=1)
        owner._interrupt('Fake device ended')
        def fail():
            raise OSError('Fake store closed')
        monkeypatch.setattr('app.db.SessionLocal', fail)
        owner._record_interruption()
        result = routes.status(db)
        assert result['owners'][0]['problem_code'] == 'interruption-unpersisted'
        assert db.get(MeetingSession, row['id']).state == 'paused'


def test_restart_recovers_native_pause_but_preserves_browser_pause(stores, tmp_path):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        owned(db, row, tmp_path, state='paused', exit_code=1)
        browser = create(db)
        db.get(MeetingSession, browser['id']).state = 'paused'
        db.commit()
        native._captures.clear()  # Simulated backend restart; no real process exists.
        sessions.recover_interrupted(db)
        assert db.get(MeetingSession, row['id']).state == 'interrupted'
        assert db.get(MeetingSession, browser['id']).state == 'paused'
        result = routes.status(db)
        assert result['owners'] == [] and result['active'] == []
        assert [item['session_id'] for item in result['recovery']] == [row['id']]
        revision = db.get(MeetingSession, row['id']).revision
        sessions.recover_interrupted(db)
        assert db.get(MeetingSession, row['id']).revision == revision


@pytest.mark.parametrize('entry', ['workspace', 'capabilities', 'session', 'serialize'])
def test_every_outward_status_scopes_projects_and_private_sessions(stores, tmp_path, monkeypatch, entry):
    brain, _, pid, _ = stores
    monkeypatch.setattr('app.services.meeting_audio.runtime_status', lambda: {'ready': False, 'detail': 'fake'})
    monkeypatch.setattr('app.services.live_speech.runtime_status', lambda: {'ready': False, 'detail': 'fake'})
    with brain() as db:
        with operator_context(Operator('alice', 'owner')):
            visible = create(db, project_id=pid)
            hidden_private = create(db)
            owned(db, hidden_private, tmp_path / 'private', state='interrupted', exit_code=1)
            owned(db, visible, tmp_path / 'project', state='stopped', exit_code=0)
        with operator_context(Operator('reader', 'reader', frozenset([pid]))):
            if entry == 'workspace':
                value = routes.status(db)
            elif entry == 'capabilities':
                value = sessions.capabilities(db)['native_capture']
            elif entry == 'session':
                value = routes.session_status(visible['id'], db)
            else:
                value = sessions.serialize_session(db, sessions.get_session(db, visible['id']))
            assert hidden_private['id'] not in str(value)
            assert visible['id'] in str(value)
            for item in value.get('owners', []):
                assert item['can_control'] is False
            with pytest.raises(HTTPException) as denied:
                routes.perform(db, visible['id'], 'stop', Command(command_id=key(), expected_revision=1))
            assert denied.value.status_code == 403
        with operator_context(Operator('bob', 'owner')):
            result = routes.status(db)
            assert hidden_private['id'] not in str(result)
            with pytest.raises(HTTPException) as denied:
                routes.session_status(hidden_private['id'], db)
            assert denied.value.status_code == 404
        with operator_context(Operator('scoped', 'owner', frozenset())):
            assert routes.status(db)['owners'] == []
            assert routes.status(db)['recovery'] == []


def test_unexpected_authorization_failure_is_not_silently_filtered(stores, tmp_path, monkeypatch):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        owned(db, row, tmp_path)
        def unavailable(*args, **kwargs):
            raise RuntimeError('Fake SQL unavailable')
        monkeypatch.setattr(sessions, 'get_session', unavailable)
        with pytest.raises(RuntimeError, match='SQL unavailable'):
            routes.status(db)


@pytest.mark.parametrize('exit_code', [0, 1])
def test_general_stopped_owner_requires_eof_and_clean_exit(stores, tmp_path, exit_code):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        owner = owned(db, row, tmp_path, state='stopped', exit_code=exit_code)
        owner._reader_done.set()
        raw = wav()
        sessions.store_chunk(db, row['id'], 'mic', 0, raw=raw, filename='native.wav', mime_type='audio/wav',
            command_id=key(), sha256=hashlib.sha256(raw).hexdigest(), start_ms=0, duration_ms=10,
            internal_capture_owner=owner)
        db.get(MeetingSession, row['id']).state = 'paused'
        db.commit()
        body = Command(command_id=key(), expected_revision=db.get(MeetingSession, row['id']).revision)
        if exit_code:
            with pytest.raises(HTTPException) as rejected:
                routes.perform(db, row['id'], 'stop', body)
            assert rejected.value.status_code == 409
            assert routes.status(db)['recovery'][0]['reason'] == 'stop-unconfirmed'
        else:
            result = routes.perform(db, row['id'], 'stop', body)
            assert result['state'] == 'completed'
            assert routes.status(db)['recovery'] == []
        assert not native.has_registered_capture(row['id'])


def test_new_start_cannot_replace_a_stopped_registered_owner(stores, tmp_path):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        owned(db, row, tmp_path, state='stopped', exit_code=0)
        db.get(MeetingSession, row['id']).state = 'interrupted'
        db.commit()
        with pytest.raises(HTTPException, match='Vérifier') as denied:
            routes.perform(db, row['id'], 'start', routes.Start(command_id=key(), expected_revision=1, tracks=['mic']))
        assert denied.value.status_code == 409
        assert db.get(MeetingSession, row['id']).pending_command_id is None


@pytest.mark.parametrize('completed', [False, True])
def test_drain_confirmed_receipt_survives_restart_for_explicit_conservation(stores, tmp_path, completed):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        owned(db, row, tmp_path, state='paused', exit_code=0)
        record = db.get(MeetingSession, row['id'])
        body = {'command_id': key(), 'expected_revision': 1}
        receipt = sessions._begin(db, record, 'native.stop', body,
            server_data={'_native_drain_confirmed': True})
        if completed:
            receipt.status, receipt.result, record.pending_command_id = 'completed', {'state': 'paused'}, None
        db.commit()
        native._captures.clear()
        sessions.recover_interrupted(db)
        assert record.state == 'paused'
        notice = routes.status(db)['recovery'][0]
        assert notice['reason'] == 'conservation-pending'
        assert notice['pending_stop'] == body


def test_pinned_script_resources_are_private_not_canonical():
    from scripts import native_audio_capture, native_capture_qualification, transcribe_live, transcribe_meeting
    root = Path(__file__).resolve().parents[1]
    for module in (native_audio_capture, native_capture_qualification, transcribe_live, transcribe_meeting):
        assert Path(module.__file__).resolve().is_relative_to(root / 'scripts')


@pytest.mark.parametrize('state,exit_code', [('interrupted', 1), ('stopped', 0), ('recording', 1)])
def test_prepared_start_with_ended_owner_is_rejected_exactly_and_preserves_human_data(stores, tmp_path, state, exit_code):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        owner = owned(db, row, tmp_path, state=state, exit_code=exit_code)
        if state == 'interrupted':
            owner.error = 'Fake startup interrupted'
        raw = wav()
        audio_key = key()
        audio_receipt = sessions.store_chunk(db, row['id'], 'mic', 0, raw=raw, filename='native.wav', mime_type='audio/wav',
            command_id=audio_key, sha256=hashlib.sha256(raw).hexdigest(), start_ms=0, duration_ms=10,
            internal_capture_owner=owner)
        record = db.get(MeetingSession, row['id'])
        human = {'title': 'Texte humain', 'content': {'blocks': []}, 'plain_text': 'Never overwrite this draft'}
        record.staged_note = human
        db.commit()
        body = routes.Start(command_id=key(), expected_revision=record.revision, tracks=['mic'])
        receipt = sessions._begin(db, record, 'native.start', body.model_dump(mode='json'))
        original_body, original_digest = dict(receipt.body), receipt.digest
        with pytest.raises(HTTPException) as rejected:
            routes.perform(db, row['id'], 'start', body)
        assert rejected.value.status_code == 409
        assert rejected.value.detail['rejected_command_id'] == body.command_id
        db.expire_all()
        assert receipt.status == 'rejected' and receipt.body == original_body and receipt.digest == original_digest
        assert record.pending_command_id is None and record.state == 'interrupted'
        assert record.staged_note == human and native._captures[row['id']] is owner
        assert db.get(MeetingSessionCommand, audio_key).result == audio_receipt
        audio_file = db.scalar(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == row['id']))
        assert Path(audio_file.storage_path).read_bytes() == raw
        assert owner.process is not None  # Rejecting a start never closes a device.
        with pytest.raises(HTTPException) as replay:
            routes.perform(db, row['id'], 'start', body)
        assert replay.value.status_code == 409
        assert replay.value.detail['rejected_command_id'] == body.command_id
        if state == 'stopped':
            owner._reader_done.set()
            result = routes.perform(db, row['id'], 'stop', Command(command_id=key(), expected_revision=record.revision))
            assert result['state'] == 'completed'
        assert record.staged_note == human


def test_prepared_start_with_starting_owner_stays_pending_without_false_ack(stores, tmp_path):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        owner = owned(db, row, tmp_path, state='created', exit_code=None)
        record = db.get(MeetingSession, row['id'])
        body = routes.Start(command_id=key(), expected_revision=record.revision, tracks=['mic'])
        receipt = sessions._begin(db, record, 'native.start', body.model_dump(mode='json'))
        with pytest.raises(HTTPException) as incomplete:
            routes.perform(db, row['id'], 'start', body)
        assert incomplete.value.status_code == 409
        assert receipt.status == 'prepared' and record.pending_command_id == body.command_id
        assert owner.state == 'created' and owner.process.poll() is None


def test_prepared_recording_start_finishes_without_reopening_hardware(stores, tmp_path):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        owner = owned(db, row, tmp_path, state='recording', exit_code=None)
        record = db.get(MeetingSession, row['id'])
        body = routes.Start(command_id=key(), expected_revision=record.revision, tracks=['mic'])
        receipt = sessions._begin(db, record, 'native.start', body.model_dump(mode='json'))
        result = routes.perform(db, row['id'], 'start', body)
        assert result['state'] == 'recording' and receipt.status == 'completed'
        assert native._captures[row['id']] is owner
        assert routes.perform(db, row['id'], 'start', body) == result


def test_prepared_start_after_restart_rejects_without_opening_audio_when_disabled(stores, tmp_path, monkeypatch):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        owned(db, row, tmp_path, state='interrupted', exit_code=1)
        record = db.get(MeetingSession, row['id'])
        body = routes.Start(command_id=key(), expected_revision=record.revision, tracks=['mic'])
        receipt = sessions._begin(db, record, 'native.start', body.model_dump(mode='json'))
        sessions.append_event(db, record, 'native.capture.owner', {'tracks': ['mic'], 'start_command_id': body.command_id})
        db.commit()
        native._captures.clear()
        monkeypatch.setenv('AGENT_MEETING_SESSIONS_ENABLED', '0')
        with pytest.raises(HTTPException) as failed:
            routes.perform(db, row['id'], 'start', body)
        assert failed.value.detail['rejected_command_id'] == body.command_id
        assert receipt.status == 'rejected' and record.state == 'interrupted'
        assert record.pending_command_id is None


def test_rejected_start_keeps_a_different_pending_command_and_human_note(stores, tmp_path):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        owner = owned(db, row, tmp_path, state='interrupted', exit_code=1)
        owner.error = 'Fake startup ended'
        record = db.get(MeetingSession, row['id'])
        body = routes.Start(command_id=key(), expected_revision=record.revision, tracks=['mic'])
        receipt = sessions._begin(db, record, 'native.start', body.model_dump(mode='json'))
        other = MeetingSessionCommand(id=key(), session_id=record.id, operator_id=sessions.current_operator().id,
            kind='session.notes', digest='stable-human-command', body={'human_text': 'Keep this text'})
        db.add(other)
        record.pending_command_id = other.id
        record.staged_note = {'title': 'Human draft', 'plain_text': 'Keep this text'}
        db.commit()
        with pytest.raises(HTTPException) as failed:
            routes.perform(db, row['id'], 'start', body)
        assert failed.value.detail['rejected_command_id'] == body.command_id
        assert receipt.status == 'rejected' and record.pending_command_id == other.id
        assert other.status == 'prepared' and other.body['human_text'] == 'Keep this text'
        assert record.staged_note['plain_text'] == 'Keep this text'


@pytest.mark.parametrize('disabled', [False, True])
def test_preopening_start_retry_requires_fresh_cpu_and_feature_admission(stores, monkeypatch, disabled):
    from app.services import audio_cpu_coordinator as cpu
    brain, _, _, _ = stores
    calls = []
    monkeypatch.setattr(cpu, '_batch_owner', None)
    monkeypatch.setattr(cpu, '_direct_jobs', 0)
    monkeypatch.setattr(native, 'start_capture', lambda *args, **kwargs: calls.append('open'))
    with brain() as db:
        row = create(db)
        record = db.get(MeetingSession, row['id'])
        body = routes.Start(command_id=key(), expected_revision=record.revision, tracks=['mic'])
        receipt = sessions._begin(db, record, 'native.start', body.model_dump(mode='json'))
        record.state = 'interrupted'
        receipt.error = 'Simulated failure before ownership'
        db.commit()
        original = (dict(receipt.body), receipt.digest, record.revision)
        if disabled:
            monkeypatch.setenv('AGENT_MEETING_SESSIONS_ENABLED', '0')
            with pytest.raises(HTTPException) as denied:
                routes.perform(db, row['id'], 'start', body)
        else:
            with cpu.batch_slot(db, 'explicit-fake-batch'):
                with pytest.raises(HTTPException) as denied:
                    routes.perform(db, row['id'], 'start', body)
        assert denied.value.status_code == 409 and calls == []
        db.expire_all()
        assert receipt.status == 'prepared' and record.state == 'interrupted'
        assert record.pending_command_id == body.command_id
        assert (receipt.body, receipt.digest, record.revision) == original
        monkeypatch.setenv('AGENT_MEETING_SESSIONS_ENABLED', '1')
        assert routes.perform(db, row['id'], 'start', body)['state'] == 'recording'
        assert calls == ['open'] and receipt.status == 'completed'


@pytest.mark.parametrize('commit_fails', [False, True])
def test_owner_commit_releases_registry_before_sql_and_opens_only_after_commit(stores, monkeypatch, commit_fails):
    brain, _, _, _ = stores
    opened, closed = [], []
    monkeypatch.setattr(native.NativeCapture, 'start', lambda self: opened.append(self.owner_event_id))
    monkeypatch.setattr(native.NativeCapture, 'close', lambda self: closed.append(self))
    with brain() as db:
        row = create(db)
        record = db.get(MeetingSession, row['id'])
        record.state = 'recording'
        db.commit()
        # An unrelated existing artifact must survive an ownership-write failure.
        from app.config import settings
        artifact = Path(settings.storage_dir) / 'preserved-test.raw'
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_bytes(b'Preserved bytes')
        original_commit = db.commit
        def commit():
            assert row['id'] in native._captures  # Reservation precedes SQL.
            assert not native._lock._is_owned()  # SQL never holds the registry.
            # A concurrent status reader must complete before this SQL commit.
            with ThreadPoolExecutor(max_workers=1) as executor:
                assert executor.submit(native.registered_snapshots).result(timeout=1)[0]['session_id'] == row['id']
            assert not opened
            if commit_fails:
                raise OSError('Simulated owner commit failure')
            original_commit()
        monkeypatch.setattr(db, 'commit', commit)
        if commit_fails:
            with pytest.raises(OSError, match='owner commit'):
                native.start_capture(db, row['id'], tracks=['mic'])
            assert not native.has_registered_capture(row['id']) and not opened and len(closed) == 1
            db.rollback()
            assert not list(db.scalars(select(MeetingSessionEvent).where(MeetingSessionEvent.kind == 'native.capture.owner')))
        else:
            native.start_capture(db, row['id'], tracks=['mic'])
            assert len(opened) == 1 and opened[0] is not None and not closed
        assert artifact.read_bytes() == b'Preserved bytes'
