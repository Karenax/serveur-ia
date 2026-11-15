"""A reviewed complete recording supersedes the provisional live ASR context."""
import asyncio
import hashlib
import json

from fastapi import HTTPException
import pytest
from sqlalchemy import select

from app.meeting_session_models import LiveTranscriptSegment, MeetingSessionEvent
from app.models import MeetingRecording, Project as BrainProject, Source, SourceArtifact
from app.services import meeting_audio, scoped_assistant as assistant, meeting_sessions as sessions
from backend.app.models import BrainLink
from backend.app.services.project_operator import Operator, operator_context
from tests.test_session_assistant import stores as stores_fixture, enable
from tests.test_meeting_sessions import command, content, create, key

stores = stores_fixture


def seed(db, pid, bid, *, full=True):
    enable(db)
    parent = create(db, project_id=pid)
    command(db, parent['id'], 'notes', parent['revision'], title='Note fictive',
            content=content('Le dossier reste à relire.'))
    row = sessions.get_session(db, parent['id'])
    source = Source(project_id=bid, source_type='meeting', status='resolved', author='fictitious-test',
                    original_uri='fictif://recording.wav', sha256=hashlib.sha256(key().encode()).hexdigest(),
                    source_metadata={'filename': 'fictitious.wav', 'subject': 'Réunion fictive'})
    db.add(source)
    db.flush()
    recording = MeetingRecording(project_id=bid, erp_project_id=pid, source_id=source.id,
        title='Réunion fictive', filename='fictitious.wav', duration_seconds=10,
        revision=1, reviewed_revision=0, job_status='completed', stage='transcribed',
        segments=[{'id': 'seg-1', 'start': 0., 'end': 2., 'speaker': 'SPEAKER_01', 'text': 'Puissance : 2250 W.'}] if full else [],
        speaker_names={})
    db.add(recording)
    db.flush()
    row.recording_id, row.state = recording.id, 'completed'
    db.add(LiveTranscriptSegment(id=key(), session_id=row.id, track='mic', start_ms=0, end_ms=2000,
                                speaker='MIC', text='Puissance : 2250 W.', revision=1, finalized=False))
    db.commit()
    return row, recording


def review(db, recording, value, *, validate=True):
    segments = [meeting_audio.TranscriptSegment.model_validate({
        'id': 'seg-1', 'start': 0, 'end': 2, 'speaker': 'SPEAKER_01', 'text': f'Puissance : {value} W.'})]
    meeting_audio.save_review(db, recording, segments, {}, recording.revision, validate)


def prepare(db, row):
    return asyncio.run(assistant.prepare(db, row, query='Quelle puissance ?', scope='session'))


def test_reviewed_complete_transcript_replaces_old_live_in_assistant_context(stores):
    brain, _, pid, bid = stores
    with brain() as db:
        row, recording = seed(db, pid, bid)
        review(db, recording, 1250)
        _, messages, metadata = prepare(db, row)
        assert '1250 W' in messages[-1]['content']
        assert '2250 W' not in messages[-1]['content']
        citation = next(item for item in metadata['citations'] if '1250 W' in item['excerpt'])
        assert citation['source_id'] == recording.source_id
        assert citation['locator']['recording_id'] == recording.id
        assert citation['locator']['revision'] == recording.revision
        artifact = db.get(SourceArtifact, citation['locator']['artifact_id'])
        assert artifact.content_json['revision'] == recording.revision
        snapshot = db.scalar(select(SourceArtifact).where(SourceArtifact.source_id == recording.source_id,
                                                         SourceArtifact.kind == 'transcription_snapshot'))
        assert snapshot.content_json['superseded'] is True and snapshot.content_json['reviewed'] is False
        assert '2250 W' in snapshot.content_text
        assert assistant.context_current(db, row, metadata)
        assert db.scalar(select(LiveTranscriptSegment).where(LiveTranscriptSegment.session_id == row.id)).text == 'Puissance : 2250 W.'


def test_review_invalidates_old_session_answer_without_changing_session_revision(stores):
    brain, _, pid, bid = stores
    with brain() as db:
        row, recording = seed(db, pid, bid, full=False)
        _, _, metadata = prepare(db, row)
        before = row.revision
        recording.segments = [{'id': 'seg-1', 'start': 0., 'end': 2., 'speaker': 'SPEAKER_01', 'text': 'Puissance : 2250 W.'}]
        db.commit()
        review(db, recording, 1250)
        assert row.revision == before
        assert not assistant.context_current(db, row, metadata)


def test_saved_edit_immediately_retires_old_evidence_until_revalidated(stores):
    brain, _, pid, bid = stores
    with brain() as db:
        row, recording = seed(db, pid, bid)
        review(db, recording, 1250)
        artifact = db.scalar(select(SourceArtifact).where(SourceArtifact.source_id == recording.source_id,
                                                          SourceArtifact.kind == 'transcription'))
        review(db, recording, 1500, validate=False)
        db.refresh(artifact)
        assert artifact.content_json['superseded'] is True
        assert '1250 W' in artifact.content_text
        _, messages, metadata = prepare(db, row)
        assert '1250 W' not in messages[-1]['content'] and '2250 W' not in messages[-1]['content']
        assert any('relecture' in warning.lower() for warning in metadata['warnings'])
        review(db, recording, 1500)
        _, current, _ = prepare(db, row)
        assert '1500 W' in current[-1]['content'] and '1250 W' not in current[-1]['content']
        assert len(list(db.scalars(select(SourceArtifact).where(SourceArtifact.source_id == recording.source_id,
                                                               SourceArtifact.kind == 'transcription')))) == 2


def test_complete_unreviewed_transcript_cannot_silently_fall_back_to_old_live(stores):
    brain, _, pid, bid = stores
    with brain() as db:
        row, _ = seed(db, pid, bid)
        _, messages, metadata = prepare(db, row)
        assert '2250 W' not in messages[-1]['content']
        assert any('relecture' in warning.lower() for warning in metadata['warnings'])


def test_foreign_recording_binding_is_refused_before_generation(stores):
    brain, _, pid, bid = stores
    with brain() as db:
        row, recording = seed(db, pid, bid)
        review(db, recording, 1250)
        recording.erp_project_id = 'another-fictitious-project'
        db.commit()
        with pytest.raises(HTTPException):
            prepare(db, row)


def test_empty_full_recording_keeps_the_existing_live_working_path(stores):
    brain, _, pid, bid = stores
    with brain() as db:
        row, _ = seed(db, pid, bid, full=False)
        _, messages, metadata = prepare(db, row)
        assert '2250 W' in messages[-1]['content']
        assert next(item for item in metadata['citations'] if '2250 W' in item['excerpt'])['level'] == 'working'


def test_notes_only_snapshot_format_is_unchanged(stores):
    brain, _, pid, _ = stores
    with brain() as db:
        enable(db)
        row = sessions.get_session(db, create(db, project_id=pid, kind='note')['id'])
        stamp, note, segments = assistant.session_snapshot(db, row)
        original_payload = {'revision': row.revision, 'note_version_id': note.get('version_id') if note else None,
                            'note_content': note.get('content') if note else None, 'calendar': None,
                            'segments': [(s.id, s.revision, s.text, s.start_ms, s.end_ms) for s in segments]}
        assert stamp == hashlib.sha256(json.dumps(original_payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def test_recording_edit_on_another_connection_invalidates_cached_context(stores):
    brain, _, pid, bid = stores
    with brain() as db:
        db.expire_on_commit = False
        row, recording = seed(db, pid, bid)
        review(db, recording, 1250)
        _, _, metadata = prepare(db, row)
        before = recording.revision
        db.commit()
        with brain() as other:
            review(other, other.get(MeetingRecording, recording.id), 1500)
        assert recording.revision == before  # This connection still has its old ORM object.
        assert not assistant.context_current(db, row, metadata)
        _, messages, _ = prepare(db, row)
        assert '1500 W' in messages[-1]['content'] and '1250 W' not in messages[-1]['content']


def test_review_wakes_session_feed_without_overwriting_live_or_note_revision(stores):
    brain, _, pid, bid = stores
    with brain() as db:
        row, recording = seed(db, pid, bid)
        before = row.revision
        review(db, recording, 1250)
        event = db.scalar(select(MeetingSessionEvent).where(MeetingSessionEvent.session_id == row.id,
            MeetingSessionEvent.kind == 'transcript.updated').order_by(MeetingSessionEvent.id.desc()))
        assert event.data == {'recording_id': recording.id, 'recording_revision': recording.revision,
                              'reviewed_revision': recording.revision, 'mode': 'complete-recording-review'}
        assert row.revision == before


def test_inconsistent_review_artifact_is_refused_instead_of_reusing_old_live(stores):
    brain, _, pid, bid = stores
    with brain() as db:
        row, recording = seed(db, pid, bid)
        review(db, recording, 1250)
        artifact = db.scalar(select(SourceArtifact).where(SourceArtifact.source_id == recording.source_id,
                                                          SourceArtifact.kind == 'transcription'))
        artifact.content_text = 'Fictitious corrupted snapshot'
        db.commit()
        with pytest.raises(HTTPException, match='preuve de relecture'):
            prepare(db, row)


def test_current_brain_access_is_checked_before_exposing_reviewed_text(stores):
    brain, erp, pid, bid = stores
    with brain() as db:
        row, recording = seed(db, pid, bid)
        review(db, recording, 1250)
        other_brain = BrainProject(code='RELINKED', name='Autre liaison fictive')
        db.add(other_brain)
        db.commit()
        with erp() as target:
            target.query(BrainLink).filter_by(project_id=pid).one().brain_project_id = other_brain.id
            target.commit()
        # ERP access is still allowed, but this recording's old Brain corpus is not.
        with operator_context(Operator('local', 'editor', frozenset([pid]))):
            with pytest.raises(HTTPException) as failure:
                prepare(db, row)
            assert failure.value.status_code == 404
