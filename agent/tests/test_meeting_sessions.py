"""Studio durability, retry receipts and Notes concurrency on isolated stores."""
import hashlib
import io
from uuid import uuid4
import wave

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.db_support import configure_sqlite
from app.meeting_session_models import MeetingAudioChunk, MeetingSession, StagedSessionNoteVersion
from app.meeting_session_schemas import Command, SessionAssign, SessionCreate, SessionNoteSave
from app.models import Project as BrainProject, Source, SourceArtifact
from app.routers.meeting_sessions import router
from app.services import meeting_sessions as studio
from backend.app.db import Base as ERPBase
from backend.app.models import BrainLink, Project
from backend.app.note_evidence_models import NoteEvidenceOutbox
from backend.app.project_note_models import NoteVersion
from backend.app.project_note_schemas import NoteContent, NoteCreate, NoteSave
from backend.app.services import project_notes as notes
from backend.app.services.project_note_schema import install_note_schema
from backend.app.services.project_operator import Operator, operator_context


def key():
    return str(uuid4())


def content(value='Décision vérifiée'):
    return NoteContent.model_validate({'blocks': [{'type': 'paragraph', 'runs': [{'text': value}]}]})


def wav(samples=160, sample=7):
    output = io.BytesIO()
    with wave.open(output, 'wb') as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(16000)
        writer.writeframes(bytes([sample, 0]) * samples)
    return output.getvalue()


@pytest.fixture
def stores(tmp_path, monkeypatch):
    engines = [create_engine('sqlite:///' + (tmp_path / name).as_posix(), connect_args={'check_same_thread': False})
               for name in ['brain.db', 'erp.db']]
    for engine in engines:
        configure_sqlite(engine)
    Base.metadata.create_all(engines[0], tables=[t for t in Base.metadata.sorted_tables if not t.name.startswith('foresight_')])
    ERPBase.metadata.create_all(engines[1], tables=[t for t in ERPBase.metadata.sorted_tables if not t.name.startswith('foresight_')])
    install_note_schema(engines[1], backup=lambda: None)
    brain, erp = [sessionmaker(bind=engine) for engine in engines]
    from app.config import settings
    from backend.app.routers import meeting_audio
    monkeypatch.setenv('AGENT_MEETING_SESSIONS_ENABLED', '1')
    monkeypatch.setattr(settings, 'storage_dir', str(tmp_path / 'storage'))
    monkeypatch.setattr('backend.app.db.SessionLocal', erp)
    monkeypatch.setattr('app.db.SessionLocal', brain)
    monkeypatch.setattr(meeting_audio, 'ERP', erp)
    monkeypatch.setattr(meeting_audio, 'BrainSession', brain)
    raw_dir = tmp_path / 'raw'
    raw_dir.mkdir()
    monkeypatch.setattr(meeting_audio, 'RAW_DIR', raw_dir)
    with brain() as db:
        bp = BrainProject(code='STUDIO', name='Studio')
        db.add(bp)
        db.commit()
        bid = bp.id
    with erp() as db:
        ep = Project(code='STUDIO', title='Studio')
        db.add(ep)
        db.flush()
        db.add(BrainLink(project_id=ep.id, brain_project_id=bid))
        db.commit()
        pid = ep.id
    yield brain, erp, pid, bid
    for engine in engines:
        engine.dispose()


def create(db, **kwargs):
    return studio.create_session(db, SessionCreate(command_id=key(), title='Réunion', **kwargs))


def command(db, sid, kind, revision, **kwargs):
    cls = SessionAssign if kind == 'assign-project' else SessionNoteSave if kind == 'notes' else Command
    return studio.execute_command(db, sid, kind, cls(command_id=key(), expected_revision=revision, **kwargs))


def chunk(db, sid, sequence=0, *, raw=None, track='mic', command_id=None, start_ms=0, duration_ms=10):
    raw = wav() if raw is None else raw
    return studio.store_chunk(db, sid, track, sequence, raw=raw, filename='capture.wav', mime_type='audio/wav',
        command_id=command_id or key(), sha256=hashlib.sha256(raw).hexdigest(), start_ms=start_ms, duration_ms=duration_ms)


def test_feature_settings_and_emergency_stop(stores, monkeypatch):
    from app.services.settings_service import save_section
    brain, _, _, _ = stores
    with brain() as db:
        assert studio.feature_enabled(db)
        save_section(db, 'foresight', {'enabled': False})
        assert not studio.feature_enabled(db)
        save_section(db, 'foresight', {'enabled': True})
        monkeypatch.setenv('AGENT_MEETING_SESSIONS_ENABLED', '0')
        assert not studio.feature_enabled(db)
        with pytest.raises(HTTPException) as caught:
            create(db)
        assert caught.value.status_code == 409


def test_create_replay_and_revision(stores):
    brain, _, _, _ = stores
    with brain() as db:
        body = SessionCreate(command_id=key(), title=' Première réunion ')
        row = studio.create_session(db, body)
        assert studio.create_session(db, body) == row
        assert row['title'] == 'Première réunion' and row['state'] == 'created'
        resumed = command(db, row['id'], 'resume', 1)
        assert resumed['revision'] == 2 and resumed['state'] == 'recording'
        with pytest.raises(HTTPException) as caught:
            command(db, row['id'], 'pause', 1)
        assert caught.value.status_code == 409
        assert db.scalar(select(func.count()).select_from(MeetingSession)) == 1


def test_staging_versions_assign_once_and_concurrent_documents_edit(stores):
    brain, erp, pid, _ = stores
    with brain() as db:
        row = create(db, kind='note')
        staged = command(db, row['id'], 'notes', 1, title='Décision', content=content())
        assert staged['staged_note']['revision'] == 1 and staged['note_id'] is None
        assign = SessionAssign(command_id=key(), expected_revision=2, project_id=pid)
        bound = studio.execute_command(db, row['id'], 'assign-project', assign)
        assert bound['note']['content'] == content().model_dump(mode='json')
        assert studio.execute_command(db, row['id'], 'assign-project', assign) == bound
        assert db.scalar(select(func.count()).select_from(StagedSessionNoteVersion)) == 1
    with erp() as db:
        current = notes.read_note(db, pid, bound['note_id'])
        notes.save_note(db, pid, bound['note_id'], NoteSave(command_id=key(), expected_revision=1,
            title='Depuis Documents', content=content('Modifié ailleurs')))
        db.commit()
        assert db.scalar(select(func.count()).select_from(NoteEvidenceOutbox)) == 2
    with brain() as db:
        with pytest.raises(HTTPException) as caught:
            command(db, row['id'], 'notes', 3, title='Saisie conservée', content=content('Ancien écran'),
                expected_note_revision=current['revision'], expected_note_version_id=current['version_id'])
        assert caught.value.status_code == 409
        detail = studio.serialize_session(db, studio.get_session(db, row['id']))
        assert detail['note']['title'] == 'Depuis Documents' and detail['pending_command'] is None
        assert detail['note_revision'] == 2
    with erp() as db:
        assert db.scalar(select(func.count()).select_from(NoteVersion)) == 2


def test_lost_brain_response_after_erp_note_commit_replays_without_duplicate(stores, monkeypatch):
    brain, erp, pid, _ = stores
    with brain() as db:
        row = create(db, project_id=pid, kind='note')
        body = SessionNoteSave(command_id=key(), expected_revision=1, title='Une seule fois', content=content())
        finish = studio._finish
        monkeypatch.setattr(studio, '_finish', lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('lost response')))
        with pytest.raises(RuntimeError):
            studio.execute_command(db, row['id'], 'notes', body)
        db.rollback()
        monkeypatch.setattr(studio, '_finish', finish)
        result = studio.execute_command(db, row['id'], 'notes', body)
        assert result['note_revision'] == 1
    with erp() as db:
        assert db.scalar(select(func.count()).select_from(NoteVersion)) == 1


def test_chunk_ack_replays_hash_and_sequences_then_finalizes_staging(stores):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        cid = key()
        ack = chunk(db, row['id'], command_id=cid)
        assert ack['session_id'] == row['id'] and ack['accepted_chunk']['seq'] == 0
        assert chunk(db, row['id'], command_id=cid) == ack
        assert chunk(db, row['id'])['replayed']
        with pytest.raises(HTTPException) as caught:
            chunk(db, row['id'], raw=wav(sample=8))
        assert caught.value.status_code == 409
        chunk(db, row['id'], 1, raw=wav(sample=9), start_ms=10)
        assert db.scalar(select(func.count()).select_from(MeetingAudioChunk)) == 2
        assert db.get(MeetingSession, row['id']).revision == 1
        combined, _, _ = studio.consolidated_audio(db, studio.get_session(db, row['id']))
        with wave.open(io.BytesIO(combined), 'rb') as source:
            assert source.getnframes() == 320
        final = command(db, row['id'], 'finalize', 1)
        assert final['state'] == 'completed' and final['recording_id'] is None
        assert final['transcript_provisional']


def test_missing_sequence_rejected_without_trapping_capture(stores):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        chunk(db, row['id'], 1, start_ms=10)
        with pytest.raises(HTTPException) as caught:
            command(db, row['id'], 'finalize', 1)
        assert caught.value.status_code == 409
        db.refresh(db.get(MeetingSession, row['id']))
        assert db.get(MeetingSession, row['id']).pending_command_id is None
        chunk(db, row['id'], 0)
        assert command(db, row['id'], 'finalize', 1)['state'] == 'completed'


def test_audio_tampering_paths_and_capture_quota(stores, monkeypatch, tmp_path):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        monkeypatch.setattr(studio, 'MAX_CAPTURE_BYTES', len(wav()))
        chunk(db, row['id'])
        with pytest.raises(HTTPException) as caught:
            chunk(db, row['id'], 1, start_ms=10)
        assert caught.value.status_code == 413
        saved = db.scalar(select(MeetingAudioChunk))
        path = studio.chunk_path(saved)
        path.write_bytes(b'damaged')
        with pytest.raises(HTTPException) as caught:
            studio.consolidated_audio(db, studio.get_session(db, row['id']))
        assert caught.value.status_code == 409
        saved.storage_path = str(tmp_path / 'outside.wav')
        with pytest.raises(HTTPException) as caught:
            studio.chunk_path(saved)
        assert caught.value.status_code == 409


def test_completed_staging_assign_recording_and_retry(stores):
    brain, _, pid, _ = stores
    with brain() as db:
        row = create(db)
        chunk(db, row['id'])
        finalized = command(db, row['id'], 'finalize', 1)
        body = SessionAssign(command_id=key(), expected_revision=finalized['revision'], project_id=pid)
        bound = studio.execute_command(db, row['id'], 'assign-project', body)
        assert bound['recording_id']
        assert studio.execute_command(db, row['id'], 'assign-project', body)['recording_id'] == bound['recording_id']


def test_private_staging_scopes_readers_and_restart(stores):
    brain, _, pid, _ = stores
    with brain() as db:
        row = create(db)
        command(db, row['id'], 'resume', 1)
        with operator_context(Operator('other', 'owner')):
            with pytest.raises(HTTPException) as caught:
                studio.get_session(db, row['id'])
            assert caught.value.status_code == 404
        with operator_context(Operator('local', 'editor', frozenset([pid]))):
            assert studio.list_sessions(db)['total'] == 0
            with pytest.raises(HTTPException):
                create(db)
        with operator_context(Operator('local', 'reader')):
            with pytest.raises(HTTPException) as caught:
                studio.get_session(db, row['id'], write=True)
            assert caught.value.status_code == 403
        studio.recover_interrupted(db)
        assert studio.get_session(db, row['id']).state == 'interrupted'


def test_http_upload_and_sse_reconnect_cursor(stores):
    brain, _, _, _ = stores
    app = FastAPI()
    app.include_router(router)
    def dependency():
        with brain() as db:
            yield db
    app.dependency_overrides[get_db] = dependency
    client = TestClient(app)
    row = client.post('/api/v1/meeting-sessions', json={'command_id': key(), 'title': 'HTTP'}).json()
    data = wav()
    response = client.put(f"/api/v1/meeting-sessions/{row['id']}/chunks/mic/0",
        data={'command_id': key(), 'sha256': hashlib.sha256(data).hexdigest(), 'start_ms': '0', 'duration_ms': '10'},
        files={'file': ('capture.wav', data, 'audio/wav')})
    assert response.status_code == 200 and response.json()['accepted_chunk']['size_bytes'] == len(data)
    detail = client.get(f"/api/v1/meeting-sessions/{row['id']}").json()
    events = client.get(f"/api/v1/meeting-sessions/{row['id']}/events", headers={'last-event-id': str(detail['event_cursor'])})
    assert events.status_code == 200 and 'chunk.received' not in events.text
    assert client.get(f"/api/v1/meeting-sessions/{row['id']}/events", headers={'last-event-id': 'bad'}).status_code == 422


def test_additive_schema_backup_first_invalid_schema_and_retry(tmp_path):
    from app.services.meeting_session_schema import install_session_schema
    from backend.app.services.note_evidence_outbox import install_outbox_schema
    engine = create_engine('sqlite:///' + (tmp_path / 'schema.db').as_posix())
    with engine.begin() as db:
        db.exec_driver_sql('CREATE TABLE legacy (id INTEGER, cell TEXT)')
        db.exec_driver_sql("INSERT INTO legacy VALUES (1,'preserved')")
    calls = []
    def backup():
        assert 'meeting_sessions' not in inspect(engine).get_table_names()
        calls.append(True)
    install_session_schema(engine, backup=backup)
    assert calls == [True]
    assert not install_session_schema(engine, backup=lambda: pytest.fail('no repeat backup'))
    assert install_outbox_schema(engine, backup=lambda: calls.append(True))
    assert not install_outbox_schema(engine, backup=lambda: pytest.fail('no repeat backup'))
    with engine.connect() as db:
        assert db.exec_driver_sql('SELECT cell FROM legacy').scalar() == 'preserved'
    engine.dispose()
    broken = create_engine('sqlite:///' + (tmp_path / 'broken.db').as_posix())
    with broken.begin() as db:
        db.exec_driver_sql('CREATE TABLE meeting_sessions (id TEXT PRIMARY KEY)')
    with pytest.raises(ValueError, match='incompatible'):
        install_session_schema(broken, backup=lambda: pytest.fail('validate first'))
    assert inspect(broken).get_table_names() == ['meeting_sessions']
    broken.dispose()


def test_note_outbox_is_in_same_transaction_and_rollback_neutral(stores):
    _, erp, pid, _ = stores
    with erp() as db:
        result = notes.create_note(db, pid, NoteCreate(command_id=key(), title='Rollback', content=content()))
        assert db.scalar(select(NoteEvidenceOutbox).where(NoteEvidenceOutbox.note_id == result['note']['id'])) is not None
        db.rollback()
    with erp() as db:
        assert db.scalar(select(func.count()).select_from(NoteVersion)) == 0
        assert db.scalar(select(func.count()).select_from(NoteEvidenceOutbox)) == 0


def test_notes_latest_version_projection_and_source_identity(stores):
    from app.meeting_session_models import NoteEvidenceBinding, NoteEvidenceReceipt
    from app.services.note_evidence_bridge import current_source_version, process_pending
    brain, erp, pid, _ = stores
    with erp() as db:
        first = notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note', content=content('V1')))
        db.commit()
    assert process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        source = db.scalar(select(Source))
        source_id, old_metadata = source.id, dict(source.source_metadata)
        source.source_metadata = {**source.source_metadata, 'labels': ['Devis', 'BE']}
        db.commit()
    with erp() as db:
        second = notes.save_note(db, pid, first['note']['id'], NoteSave(command_id=key(), expected_revision=1,
            title='Note', content=content('V2')))
        third = notes.save_note(db, pid, first['note']['id'], NoteSave(command_id=key(), expected_revision=2,
            title='Note', content=content('V3')))
        db.commit()
    assert not current_source_version(old_metadata, erp_factory=erp)['eligible']
    result = process_pending(erp_factory=erp, brain_factory=brain)
    assert result['obsolete'] == 1 and result['received'] == 1
    with brain() as db:
        source = db.get(Source, source_id)
        binding = db.scalar(select(NoteEvidenceBinding))
        assert binding.revision == 3 and source.source_metadata['note_version_id'] == third['note']['version_id']
        assert source.source_metadata['labels'] == ['Devis', 'BE']
        assert source.source_metadata['evidence_state'] == 'assessed' and not source.source_metadata['truth_eligible']
        assert current_source_version(source.source_metadata, erp_factory=erp)['eligible']
        artifacts = list(db.scalars(select(SourceArtifact).where(SourceArtifact.source_id == source_id)))
        assert len(artifacts) == 2
        assert sum(not a.content_json['superseded'] for a in artifacts) == 1
        assert 'V3' in next(a.content_text for a in artifacts if not a.content_json['superseded'])
        assert all('V2' not in a.content_text for a in artifacts)
        assert db.scalar(select(func.count()).select_from(NoteEvidenceReceipt)) == 3
    assert second['note']['revision'] == 2
    assert process_pending(erp_factory=erp, brain_factory=brain) == {'received': 0, 'obsolete': 0, 'waiting_project': 0, 'failed': 0}


def test_bridge_crash_after_brain_commit_then_ack_reuses_receipt(stores):
    from app.meeting_session_models import NoteEvidenceReceipt
    from app.services.note_evidence_bridge import process_pending
    brain, erp, pid, _ = stores
    with erp() as db:
        notes.create_note(db, pid, NoteCreate(command_id=key(), title='Interruption', content=content()))
        db.commit()
    def crash(packet):
        raise RuntimeError('simulate lost acknowledgement')
    assert process_pending(erp_factory=erp, brain_factory=brain, after_brain_commit=crash)['failed'] == 1
    with erp() as db:
        event = db.scalar(select(NoteEvidenceOutbox))
        assert event.status == 'failed' and event.attempts == 1
        event.retry_at = None
        db.commit()
    assert process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 1
        assert db.scalar(select(func.count()).select_from(SourceArtifact)) == 1
        assert db.scalar(select(func.count()).select_from(NoteEvidenceReceipt)) == 1


def test_identical_note_text_in_two_projects_stays_separate(stores):
    from app.services.note_evidence_bridge import process_pending
    brain, erp, pid, bid = stores
    with erp() as db:
        other = Project(code='OTHER', title='Autre')
        db.add(other)
        db.flush()
        db.add(BrainLink(project_id=other.id, brain_project_id=bid))
        for project_id in [pid, other.id]:
            notes.create_note(db, project_id, NoteCreate(command_id=key(), title='Identique', content=content()))
        db.commit()
    assert process_pending(erp_factory=erp, brain_factory=brain)['received'] == 2
    with brain() as db:
        sources = list(db.scalars(select(Source)))
        assert len(sources) == 2 and len({s.sha256 for s in sources}) == 2
        assert len({s.source_metadata['erp_project_id'] for s in sources}) == 2


def test_historical_backfill_is_resumable_and_preserves_versions(stores, monkeypatch):
    from backend.app.services import note_evidence_outbox as outbox
    _, erp, pid, _ = stores
    enqueue = outbox.enqueue_note_version
    monkeypatch.setattr(outbox, 'enqueue_note_version', lambda *args: None)
    with erp() as db:
        for value in ['A', 'B', 'C']:
            notes.create_note(db, pid, NoteCreate(command_id=key(), title=value, content=content(value)))
        db.commit()
        before = [(v.id, v.sha256, v.snapshot) for v in db.scalars(select(NoteVersion).order_by(NoteVersion.id))]
    monkeypatch.setattr(outbox, 'enqueue_note_version', enqueue)
    cursor = ''
    with erp() as db:
        while True:
            result = outbox.backfill(db, limit=2, after_id=cursor)
            cursor = result['after_id']
            db.commit()
            if not result['has_more']:
                break
        outbox.backfill(db)
        db.commit()
        assert db.scalar(select(func.count()).select_from(NoteEvidenceOutbox)) == 3
        after = [(v.id, v.sha256, v.snapshot) for v in db.scalars(select(NoteVersion).order_by(NoteVersion.id))]
        assert before == after


def test_current_note_helper_fails_closed_on_unavailable_canonical_store(stores):
    from app.services.note_evidence_bridge import current_source_version
    assert current_source_version({'origin_kind': 'document'})['eligible']
    def unavailable():
        raise OSError('offline canonical store')
    status = current_source_version({'origin_kind': 'erp_note'}, erp_factory=unavailable)
    assert not status['eligible'] and status['reason'] == 'canonical_unavailable'


def publication(db, pid):
    from app.meeting_notes_publication_schemas import PublishNotes
    row = create(db, project_id=pid, kind='note')
    saved = command(db, row['id'], 'notes', 1, title='Notes relues', content=content('Vérifier le devis demain.'))
    body = PublishNotes(command_id=key(), expected_revision=2, expected_note_revision=1,
        expected_note_version_id=saved['note_version_id'], summary={
            'overview': 'Le devis doit être vérifié.',
            'actions': [{'text': 'Vérifier le devis', 'block_index': 0, 'quote': 'Vérifier le devis', 'owner': 'BE', 'due_date': '2026-10-12'}]})
    return row, saved, body


def test_notes_only_publication_creates_report_grounded_truth_and_no_task_or_audio(stores):
    from app.models import MeetingRecording, KnowledgeItem, ProvenanceLink
    from app.services.meeting_notes_publication import publish_notes
    from backend.app.models import Meeting, MeetingAction, Task
    brain, erp, pid, _ = stores
    with brain() as db:
        row, saved, body = publication(db, pid)
        result = publish_notes(db, row['id'], body)
        replay = publish_notes(db, row['id'], body)
        assert replay['replayed'] and replay['meeting_id'] == result['meeting_id']
        assert result['session']['published_meeting_id'] == result['meeting_id']
        assert result['published_note_version_id'] == saved['note_version_id']
        assert db.scalar(select(func.count()).select_from(MeetingRecording)) == 0
        assert db.scalar(select(func.count()).select_from(KnowledgeItem)) == 2
        provenance = list(db.scalars(select(ProvenanceLink)))
        assert len(provenance) == 2 and all(p.locator['note_version_id'] == saved['note_version_id'] for p in provenance)
        assert any(p.locator['block_index'] == 0 and p.locator['quote'] == 'Vérifier le devis' for p in provenance)
    with erp() as db:
        assert db.scalar(select(func.count()).select_from(Meeting)) == 1
        action = db.scalar(select(MeetingAction))
        assert action.owner == 'BE' and action.task_id is None
        assert db.scalar(select(func.count()).select_from(Task)) == 0


def test_notes_publication_crash_replays_frozen_version_after_documents_edit(stores):
    from app.models import KnowledgeItem
    from app.services.meeting_notes_publication import publish_notes
    from backend.app.models import Meeting
    brain, erp, pid, _ = stores
    with brain() as db:
        row, saved, body = publication(db, pid)
        with pytest.raises(RuntimeError):
            publish_notes(db, row['id'], body, after_erp_commit=lambda: (_ for _ in ()).throw(RuntimeError('lost response')))
        with erp() as canonical:
            notes.save_note(canonical, pid, saved['note_id'], NoteSave(command_id=key(), expected_revision=1,
                title='Nouvelle note', content=content('Nouvelle décision après publication.')))
            canonical.commit()
        result = publish_notes(db, row['id'], body)
        assert result['published_note_version_id'] == saved['note_version_id']
        assert db.scalar(select(func.count()).select_from(KnowledgeItem)) == 2
        assert result['session']['note_revision'] == 2
        with pytest.raises(HTTPException) as caught:
            publish_notes(db, row['id'], body.model_copy(update={'command_id': key(), 'expected_revision': result['session']['revision']}))
        assert caught.value.status_code == 409
    with erp() as db:
        assert db.scalar(select(func.count()).select_from(Meeting)) == 1


def test_publication_rejects_fabricated_quote_and_stale_canonical_version(stores):
    from app.services.meeting_notes_publication import publish_notes
    brain, erp, pid, _ = stores
    with brain() as db:
        row, saved, body = publication(db, pid)
        payload = body.model_dump(mode='json')
        payload['summary']['actions'][0]['quote'] = 'Phrase absente de la note'
        with pytest.raises(HTTPException) as caught:
            publish_notes(db, row['id'], body.model_validate(payload))
        assert caught.value.status_code == 422
        assert studio.get_session(db, row['id']).pending_command_id is None
        with erp() as canonical:
            notes.save_note(canonical, pid, saved['note_id'], NoteSave(command_id=key(), expected_revision=1,
                title='Autre version', content=content()))
            canonical.commit()
        with pytest.raises(HTTPException) as caught:
            publish_notes(db, row['id'], body)
        assert caught.value.status_code == 409
        assert studio.get_session(db, row['id']).pending_command_id is None


def test_live_segment_correction_is_atomic_scoped_replayed_and_keeps_times(stores, monkeypatch):
    from app.meeting_session_models import LiveTranscriptSegment
    from app.meeting_session_schemas import SessionSegmentEdit
    brain, _, _, _ = stores
    from app.services import session_proactive
    committed_wakes = []

    def observe_committed_correction():
        with brain() as reader:
            committed_wakes.append(reader.get(LiveTranscriptSegment, segment.id).text)

    monkeypatch.setattr(session_proactive, 'wake_worker', observe_committed_correction)
    with brain() as db:
        row = create(db)
        segment = LiveTranscriptSegment(id='live-' + key(), session_id=row['id'], track='mic',
            start_ms=1000, end_ms=2000, text='Transcription provisoire', speaker='UNKNOWN')
        db.add(segment)
        db.commit()
        body = SessionSegmentEdit(command_id=key(), expected_session_revision=1, expected_segment_revision=1,
            text='Correction humaine', speaker='Intervenant validé')
        result = studio.edit_segment(db, row['id'], segment.id, body)
        assert studio.edit_segment(db, row['id'], segment.id, body) == result
        assert committed_wakes == ['Correction humaine']
        saved = db.get(LiveTranscriptSegment, segment.id)
        assert (saved.start_ms, saved.end_ms, saved.track) == (1000, 2000, 'mic')
        assert saved.revision == 2 and saved.text == 'Correction humaine' and not saved.finalized
        with pytest.raises(HTTPException) as caught:
            studio.edit_segment(db, row['id'], segment.id, body.model_copy(update={'command_id': key(), 'expected_session_revision': 2}))
        assert caught.value.status_code == 409
        assert studio.get_session(db, row['id']).pending_command_id is None
        other = create(db)
        with pytest.raises(HTTPException) as caught:
            studio.edit_segment(db, other['id'], segment.id, body)
        assert caught.value.status_code == 404
        assert committed_wakes == ['Correction humaine']


def test_capture_native_owner_is_private_and_excludes_browser(stores, monkeypatch):
    from app.services import native_audio
    brain, _, _, _ = stores
    private = object()
    # An interrupted/stopped owner still excludes browser uploads until drain.
    monkeypatch.setattr(native_audio, 'owns_session', lambda sid: False)
    monkeypatch.setattr(native_audio, 'has_registered_capture', lambda sid: True)
    monkeypatch.setattr(native_audio, 'accepts_owner', lambda sid, token: token is private)
    with brain() as db:
        state = create(db)
        with pytest.raises(HTTPException) as caught:
            chunk(db, state['id'])
        assert caught.value.status_code == 409
        data = wav()
        args = {'raw': data, 'filename': 'fictif.wav', 'mime_type': 'audio/wav', 'command_id': key(),
            'sha256': hashlib.sha256(data).hexdigest(), 'start_ms': 0, 'duration_ms': 10}
        with pytest.raises(HTTPException) as caught:
            studio.store_chunk(db, state['id'], 'mic', 0, **args, internal_capture_owner={'json': True})
        assert caught.value.status_code == 403
        receipt = studio._begin(db, studio.get_session(db, state['id']), 'native.stop',
            {'command_id': key(), 'expected_revision': 1})
        assert receipt.status == 'prepared'
        accepted = studio.store_chunk(db, state['id'], 'mic', 0, **args, internal_capture_owner=private)
        assert accepted['acknowledged']


def test_disabled_feature_keeps_existing_capture_corrections_and_export(stores, monkeypatch):
    from app.meeting_session_models import LiveTranscriptSegment
    from app.meeting_session_schemas import SessionSegmentEdit
    from app.services.session_export import export
    brain, _, pid, _ = stores
    with brain() as db:
        row = create(db, project_id=pid)
        resumed = command(db, row['id'], 'resume', 1)
        unused = create(db)
        monkeypatch.setenv('AGENT_MEETING_SESSIONS_ENABLED', '0')
        with pytest.raises(HTTPException) as caught:
            create(db)
        assert caught.value.status_code == 409
        with pytest.raises(HTTPException) as caught:
            chunk(db, unused['id'])
        assert caught.value.status_code == 409
        chunk(db, row['id'])  # Previously started browser buffer still drains.
        paused = command(db, row['id'], 'pause', resumed['revision'])
        with pytest.raises(HTTPException) as caught:
            command(db, row['id'], 'resume', paused['revision'])
        assert caught.value.status_code == 409
        segment = LiveTranscriptSegment(id='live-' + key(), session_id=row['id'], track='mic',
            start_ms=0, end_ms=10, text='Ancien texte', speaker='UNKNOWN')
        db.add(segment)
        db.commit()
        corrected = studio.edit_segment(db, row['id'], segment.id, SessionSegmentEdit(command_id=key(),
            expected_session_revision=paused['revision'], expected_segment_revision=1,
            text='Correction humaine conservée', speaker='BE'))
        saved = command(db, row['id'], 'notes', corrected['revision'], title='Note conservée', content=content())
        ended = command(db, row['id'], 'finalize', saved['revision'])
        assert ended['state'] == 'completed' and ended['recording_id']
        assert export(db, row['id']).is_file()


def test_browser_resume_excludes_reserved_native_owner_other_or_same_session(stores, monkeypatch):
    from types import SimpleNamespace
    from app.services import native_audio
    brain, _, _, _ = stores
    with brain() as db:
        browser = create(db)
        other = create(db)
        captures = {other['id']: SimpleNamespace(state='created')}
        monkeypatch.setattr(native_audio, '_captures', captures)
        with pytest.raises(HTTPException) as caught:
            command(db, browser['id'], 'resume', 1)
        assert caught.value.status_code == 409
        assert studio.get_session(db, browser['id']).pending_command_id is None
        captures.clear()
        captures[browser['id']] = SimpleNamespace(state='paused')
        with pytest.raises(HTTPException) as caught:
            command(db, browser['id'], 'resume', 1)
        assert caught.value.status_code == 409


def test_completed_speech_processing_does_not_claim_final_transcript(stores):
    from app.meeting_session_models import LiveTranscriptSegment
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        chunk(db, row['id'])
        fragment = db.scalar(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == row['id']))
        fragment.speech_status = 'completed'
        db.add(LiveTranscriptSegment(id='live-' + key(), session_id=row['id'], chunk_id=fragment.id,
            track='mic', start_ms=0, end_ms=10, text='Texte provisoire', speaker='UNKNOWN', finalized=False))
        db.commit()
        detail = studio.serialize_session(db, studio.get_session(db, row['id']))
        assert detail['transcript_processing_complete'] and detail['transcript_provisional']

@pytest.mark.parametrize('state,expected,saved,missing', [
    ('completed', ['mic', 'system'], ['mic'], ['system']),
    ('completed', ['mic', 'system'], ['system'], ['mic']),
    ('completed', ['mic', 'system'], ['mic', 'system'], []),
    ('completed', ['mic'], ['mic'], []),
    ('completed', [], [], []),
    ('interrupted', ['mic', 'system'], [], ['mic', 'system']),
    ('recording', ['mic', 'system'], ['mic'], []),
])
def test_missing_started_track_is_visible_without_inventing_audio(stores, state, expected, saved, missing):
    brain, _, _, _ = stores
    with brain() as db:
        row = create(db)
        stored = studio.get_session(db, row['id'])
        stored.state = state
        studio.append_event(db, stored, 'native.start', {'tracks': expected})
        for track in saved:
            db.add(MeetingAudioChunk(session_id=stored.id, track=track, sequence=0,
                filename='fixture.ogg', mime_type='audio/ogg', storage_path='unused-fixture.ogg',
                sha256='0' * 64, size_bytes=100, start_ms=0, duration_ms=1000))
        db.commit()
        result = studio.serialize_session(db, stored)
        warnings = [text for text in result['issues'] if 'aucun fragment audio conservé' in text]
        assert len(warnings) == len(missing)
        for track in missing:
            assert any(('Microphone' if track == 'mic' else 'Son du PC') in text for text in warnings)
        assert {item['name'] for item in result['tracks']} == set(saved)
        assert db.scalar(select(func.count()).select_from(MeetingAudioChunk)) == len(saved)
