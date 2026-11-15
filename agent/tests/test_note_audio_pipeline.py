"""A personal note can capture audio and supply its transcript without a project."""
import asyncio

from sqlalchemy import select

from app.meeting_session_models import LiveTranscriptSegment, MeetingAudioChunk
from app.services import live_speech as live, meeting_sessions as sessions
from app.services import scoped_assistant as assistant
from app.services.settings_service import save_section
from tests.test_meeting_sessions import stores as stores_fixture, create, command, content, chunk
from tests.test_session_assistant import enable

stores = stores_fixture


def test_personal_note_audio_is_transcribed_and_survives_finalization(stores, monkeypatch, tmp_path):
    from app.config import settings
    brain, _, _, _ = stores
    captured = []

    class SpeechFixture:
        def transcribe(self, prepared, **kwargs):
            captured.append((prepared.path.exists(), kwargs['track']))
            return {'segments': [{'start_ms': 0, 'end_ms': 10, 'speaker': 'mic',
                                  'text': 'Marie prépare le devis jeudi.'}],
                    'duration_ms': 10, 'compute_s': .01}

    monkeypatch.setattr(live, '_resident', SpeechFixture())
    monkeypatch.setattr(live, '_stop_generation', 0)
    live._stop.clear()
    try:
        with brain() as db:
            enable(db)
            save_section(db, 'foresight', {'live_transcription_enabled': True})
            sid = create(db, kind='note')['id']
            # Keep Windows' private test capture paths below the legacy limit.
            monkeypatch.setattr(settings, 'storage_dir', str(tmp_path.parent / ('s-' + sid[:8])))
            saved = command(db, sid, 'notes', 1, title='Ma note', content=content('Réserve : chiffrage provisoire.'))
            command(db, sid, 'resume', saved['revision'])
            chunk(db, sid)
            cid = db.scalar(select(MeetingAudioChunk.id).where(MeetingAudioChunk.session_id == sid))
        live._process_chunk(cid)
        assert captured == [(True, 'mic')]
        with brain() as db:
            row = sessions.get_session(db, sid)
            assert db.get(MeetingAudioChunk, cid).speech_status == 'completed'
            assert db.scalar(select(LiveTranscriptSegment.text).where(
                LiveTranscriptSegment.session_id == sid)) == 'Marie prépare le devis jeudi.'
            _, messages, metadata = asyncio.run(assistant.prepare(
                db, row, query='Qui prépare le devis ?', scope='session'))
            assert 'Marie prépare le devis jeudi.' in messages[-1]['content']
            assert 'Réserve : chiffrage provisoire.' in messages[-1]['content']
            assert any(c['locator'].get('segment_id') for c in metadata['citations'])
            completed = command(db, sid, 'finalize', row.revision)
            assert completed['state'] == 'completed' and completed['kind'] == 'note'
            assert completed['project_id'] is None and completed['recording_id'] is None
            assert completed['staged_note']['plain_text'] == 'Réserve : chiffrage provisoire.'
            assert completed['transcript_processing_complete'] is True
            assert completed['segments'][0]['text'] == 'Marie prépare le devis jeudi.'
            assert sessions.consolidated_audio(db, row)[0]
    finally:
        live._stop.clear()
