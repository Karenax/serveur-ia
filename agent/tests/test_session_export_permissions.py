"""Scoped recovery ZIPs preserve originals without leaking historic answers."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from uuid import uuid4
import zipfile

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from app.meeting_session_models import MeetingAudioChunk, MeetingSession, MeetingSessionEvent, LiveTranscriptSegment
from app.models import Project as BrainProject, Source, SourceArtifact
from app.services import meeting_sessions as studio, session_export as staged, scoped_assistant as assistant
from app.services.session_calendar import attach_context
from backend.app.models import BrainLink, Project
from backend.app.services.project_operator import Operator, operator_context
from tests.test_meeting_sessions import stores as stores_fixture, create, command, content

stores = stores_fixture



@pytest.fixture(autouse=True)
def no_engines(monkeypatch):
    from app.services import native_audio, ai_client, live_speech
    import subprocess
    import socket

    def forbidden(*args, **kwargs):
        pytest.fail('No process, network, hardware or inference belongs to this ZIP test')
    monkeypatch.setattr(native_audio, 'status', lambda sid=None: {'session': None})
    monkeypatch.setattr(native_audio, 'inventory', forbidden)
    monkeypatch.setattr(native_audio, 'start_capture', forbidden)
    monkeypatch.setattr(ai_client, 'chat_text', forbidden)
    monkeypatch.setattr(live_speech, 'start_worker', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)


def seed(stores):
    brain, erp, pid, bid = stores
    with brain() as db, erp() as target:
        other_brain = BrainProject(code='PRIVATE-B', name='Private B')
        db.add(other_brain)
        db.commit()
        other = Project(code='PRIVATE-B', title='Private B')
        target.add(other)
        target.flush()
        target.add(BrainLink(project_id=other.id, brain_project_id=other_brain.id))
        target.commit()
        sid = create(db, project_id=pid, kind='note')['id']
        sources = []
        for project_id, label in ((bid, 'allowed'), (other_brain.id, 'private')):
            source = Source(project_id=project_id, source_type='document', status='resolved',
                original_uri='fixture:' + label, sha256=hashlib.sha256(label.encode()).hexdigest())
            db.add(source)
            db.flush()
            sources.append(source.id)
        db.commit()
        return {'brain': brain, 'erp': erp, 'pid': pid, 'bid': bid, 'sid': sid,
                'private_pid': other.id, 'private_bid': other_brain.id, 'sources': sources}


def payload(state, private=False, **changes):
    project = state['private_bid'] if private else state['bid']
    value = {'id': str(uuid4()), 'scope': 'global', 'query': 'PRIVATE QUERY' if private else 'Question A',
        'answer': 'PRIVATE ANSWER' if private else 'Answer A',
        'conversation': {'scope': 'global', 'source_ids': [], 'erp_project_id': state['pid'], 'brain_project_id': state['bid']},
        'citations': [{'reference': 'C1', 'excerpt': 'PRIVATE EXCERPT' if private else 'Excerpt A',
                      'source_id': state['sources'][int(private)], 'source_project_id': project, 'locator': {}}],
        'status': 'answered'}
    value.update(changes)
    return value


def suggestion(state, private=False, **changes):
    value = payload(state, private=private)
    value.pop('query')
    text = value.pop('answer')
    value.update(text=text, content=content(text).model_dump(mode='json'), status='pending')
    value.update(changes)
    return value


def event(db, sid, kind, data):
    result = studio.append_event(db, studio.get_session(db, sid), kind, data)
    db.commit()
    return result.id


def read_zip(path):
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read('session.json'))


def reader(state, role='reader'):
    return operator_context(Operator('reader-A', role, frozenset([state['pid']])))


def opaque_chunk(db, sid):
    # Deliberately NOT WAV/audio: opaque bytes only, never decoded or submitted
    # to a worker. They exercise identity/hash/copy preservation in the ZIP.
    raw = b'FICTIONAL OPAQUE EXPORT BYTES; NOT AUDIO'
    file = studio._root() / sid / 'mic' / 'fixture.bin'
    file.parent.mkdir(parents=True)
    file.write_bytes(raw)
    chunk = MeetingAudioChunk(session_id=sid, track='mic', sequence=0, filename='fixture.bin',
        mime_type='application/octet-stream', storage_path=str(file), sha256=hashlib.sha256(raw).hexdigest(),
        size_bytes=len(raw), start_ms=0, duration_ms=0, speech_status='completed')
    db.add(chunk)
    db.commit()
    return raw



@pytest.mark.parametrize('kind', ['assistant.answer', 'assistant.live-answer', 'enhancement.proposed'])
@pytest.mark.parametrize('role', ['reader', 'editor', 'owner'])
def test_scoped_zip_keeps_allowed_and_redacts_private_payload_exactly(stores, kind, role):
    state = seed(stores)
    with state['brain']() as db:
        build = suggestion if kind == 'enhancement.proposed' else payload
        allowed, private = build(state), build(state, private=True)
        a, b = event(db, state['sid'], kind, allowed), event(db, state['sid'], kind, private)
        before = [(e.id, deepcopy(e.data)) for e in db.scalars(select(MeetingSessionEvent))]
        with reader(state, role):
            bundle = read_zip(staged.export(db, state['sid']))
        exported = {item['id']: item for item in bundle['events']}
        assert exported[a]['data'] == allowed and exported[a]['redacted'] is False
        assert exported[b]['data'] == {} and exported[b]['redacted'] is True
        assert set(exported[b]) == {'id', 'kind', 'revision', 'created_at', 'data', 'redacted', 'redaction_reason'}
        assert 'PRIVATE' not in json.dumps(bundle)
        assert [(e.id, e.data) for e in db.scalars(select(MeetingSessionEvent))] == before


def test_unrestricted_owner_keeps_entire_historical_envelopes_exactly(stores):
    state = seed(stores)
    with state['brain']() as db:
        for kind, value in [('assistant.answer', payload(state, private=True)),
                            ('legacy.unknown', {'query': 'raw legacy', 'error': 'retain exact'}),
                            ('assistant.live-answer', {'citations': 'old malformed', 'answer': 'raw'})]:
            event(db, state['sid'], kind, value)
        expected = {'format': 'agent-meeting-session-review', 'version': 1,
            'session': deepcopy(studio.serialize_session(db, studio.get_session(db, state['sid']))),
            'restore_policy': 'Review bundle. Restore the coordinated global backup into a new copy for identity-preserving recovery; never replay these commands.',
            'events': [{'kind': value.kind, 'data': deepcopy(value.data), 'revision': value.revision,
                        'created_at': value.created_at.isoformat()}
                       for value in db.scalars(select(MeetingSessionEvent).where(MeetingSessionEvent.session_id == state['sid']))],
            'staged_note_versions': [], 'note_versions': [], 'files': {}}
        new = read_zip(staged.export(db, state['sid']))
        assert new == expected
        assert all('id' not in item and 'redacted' not in item for item in new['events'])


@pytest.mark.parametrize('mutation', [
    {'conversation': None}, {'conversation': {}}, {'conversation': []},
    {'citations': None}, {'citations': ['private excerpt']},
    {'citations': [{'reference': 'C1', 'excerpt': 'x', 'locator': 'private'}]},
    {'citations': [{'reference': 'C1', 'excerpt': 'x', 'locator': {'erp_project_id': []}}]},
    {'citations': [{'reference': 'C1', 'excerpt': 'x', 'source_id': []}]},
    {'scope': ['global'], 'conversation': {'scope': ['global'], 'source_ids': [], 'erp_project_id': None, 'brain_project_id': None}},
])
def test_malformed_answer_is_metadata_only_without_exception(stores, mutation):
    state = seed(stores)
    with state['brain']() as db:
        eid = event(db, state['sid'], 'assistant.answer', payload(state, **mutation))
        with reader(state):
            exported = read_zip(staged.export(db, state['sid']))['events']
        item = next(item for item in exported if item['id'] == eid)
        assert item['data'] == {} and item['redacted'] is True


def test_unknown_kind_cannot_leak_text_even_with_visible_answer_shape(stores):
    state = seed(stores)
    with state['brain']() as db:
        eid = event(db, state['sid'], 'custom.future', {**payload(state), 'error': 'PRIVATE DIAGNOSTIC'})
        with reader(state):
            bundle = read_zip(staged.export(db, state['sid']))
        assert next(item for item in bundle['events'] if item['id'] == eid)['data'] == {}
        assert 'PRIVATE DIAGNOSTIC' not in json.dumps(bundle)


def test_human_selected_calendar_preserves_snapshot_and_event(stores):
    state = seed(stores)
    raw = b'BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:fixture-human\r\nSUMMARY:Context A\r\nDTSTART;TZID=Europe/Paris:20261012T140000\r\nDTEND;TZID=Europe/Paris:20261012T150000\r\nDESCRIPTION:Human uploaded fictional ICS\r\nLOCATION:Fixture\r\nATTENDEE;CN=QA:mailto:qa@example.invalid\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n'
    with state['brain']() as db:
        attach_context(db, state['sid'], raw, 'fixture-human', str(uuid4()), 1)
        expected = deepcopy(studio.serialize_session(db, studio.get_session(db, state['sid']))['calendar_context'])
        assert expected['origin'] == 'human_selected_ics'
        with reader(state):
            bundle = read_zip(staged.export(db, state['sid']))
        assert bundle['session']['calendar_context'] == expected
        item = next(item for item in bundle['events'] if item['kind'] == 'calendar.context')
        assert item['data'] == expected and item['redacted'] is False


@pytest.mark.parametrize('changes', [
    {'origin': 'other'}, {'context_only': 1}, {'sha256': 'bad'},
    {'attendees': [{'value': 'x', 'parameters': 'bad'}]}, {'unknown': 'untrusted field'},
])
def test_unrecognized_calendar_event_is_redacted_but_session_snapshot_exact(stores, changes):
    state = seed(stores)
    with state['brain']() as db:
        calendar = {'uid': 'fixture', 'attendees': [], 'origin': 'human_selected_ics',
                    'sha256': 'a' * 64, 'context_only': True, **changes}
        eid = event(db, state['sid'], 'calendar.context', calendar)
        with reader(state):
            bundle = read_zip(staged.export(db, state['sid']))
        # Session calendar is session-owned human context; no hypothetical
        # interproject leak is claimed for direct malformed DB insertion.
        assert bundle['session']['calendar_context'] == calendar
        assert next(item for item in bundle['events'] if item['id'] == eid)['data'] == {}


def test_authorized_notes_versions_segments_and_opaque_bytes_survive(stores):
    state = seed(stores)
    with state['brain']() as db:
        saved = command(db, state['sid'], 'notes', 1, title='Fictitious note', content=content('Reserved 50 euros.'))
        command(db, state['sid'], 'notes', saved['revision'], title='Fictitious note', content=content('Reserved 70 euros.'),
            expected_note_revision=saved['note_revision'], expected_note_version_id=saved['note_version_id'])
        raw = opaque_chunk(db, state['sid'])
        db.add(LiveTranscriptSegment(id='fictional-segment', session_id=state['sid'], track='mic', start_ms=0,
            end_ms=0, text='Fictional corrected text', speaker='QA', finalized=False))
        db.commit()
        with reader(state):
            path = staged.export(db, state['sid'])
        bundle = read_zip(path)
        assert bundle['session']['note']['plain_text'] == 'Reserved 70 euros.'
        assert [item['revision'] for item in bundle['note_versions']] == [1, 2]
        assert '50 euros' in json.dumps(bundle['note_versions'][0])
        assert bundle['session']['segments'][0]['text'] == 'Fictional corrected text'
        with zipfile.ZipFile(path) as archive:
            assert archive.read('audio/mic/000000.bin') == raw
            assert archive.read('notes.txt').decode() == 'Reserved 70 euros.'
        assert bundle['files']['audio/mic/000000.bin']['sha256'] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize('stage', ['before_json', 'after_close'])
def test_source_move_from_other_sql_session_denies_delivery_and_keeps_private_candidate(stores, monkeypatch, stage):
    state = seed(stores)
    with state['brain']() as db:
        eid = event(db, state['sid'], 'assistant.answer', payload(state))
        opaque_chunk(db, state['sid'])
        moved = False
        def move():
            nonlocal moved
            if moved:
                return
            moved = True
            with state['brain']() as other:
                other.get(Source, state['sources'][0]).project_id = state['private_bid']
                other.commit()
        if stage == 'before_json':
            base = zipfile.ZipFile.open
            def opening(archive, name, mode='r', *args, **kwargs):
                handle = base(archive, name, mode, *args, **kwargs)
                if isinstance(name, str) and name.startswith('audio/') and mode == 'w':
                    move()
                return handle
            monkeypatch.setattr(zipfile.ZipFile, 'open', opening)
        else:
            # A destructor/second close of an older ZIP must not trigger the
            # current export's authorization boundary. Reproduce that callback
            # deterministically while the new session DTO allocates its data.
            stale_path = studio._root().parent / 'closed-before-current-export.zip'
            stale_path.parent.mkdir(parents=True, exist_ok=True)
            stale = zipfile.ZipFile(stale_path, 'w')
            stale.writestr('old.txt', b'FICTIONAL OLD CLOSED ARCHIVE')
            stale.close()
            serialize = studio.serialize_session
            def serialize_with_old_close(*args, **kwargs):
                stale.close()
                return serialize(*args, **kwargs)
            monkeypatch.setattr(studio, 'serialize_session', serialize_with_old_close)
            base = zipfile.ZipFile.close
            candidate_folder = (studio._root().parent / 'session-exports').resolve()
            closed_candidates = []
            def closing(archive):
                candidate = archive.filename
                was_open = archive.fp is not None
                base(archive)
                if (was_open and archive.mode == 'w' and candidate
                        and Path(candidate).resolve().parent == candidate_folder
                        and Path(candidate).name.startswith(state['sid'] + '-')
                        and Path(candidate).suffix == '.zip'):
                    closed_candidates.append(str(candidate))
                    move()
            monkeypatch.setattr(zipfile.ZipFile, 'close', closing)
        with reader(state), pytest.raises(HTTPException) as caught:
            staged.export(db, state['sid'])
        assert caught.value.status_code == 404 and moved
        if stage == 'after_close':
            assert len(closed_candidates) == 1
        candidates = list((studio._root().parent / 'session-exports').glob('*.zip'))
        assert len(candidates) == 1 and candidates[0].exists()
        assert db.get(MeetingSessionEvent, eid).data['answer'] == 'Answer A'
        with zipfile.ZipFile(candidates[0]) as archive:
            assert archive.read('audio/mic/000000.bin').startswith(b'FICTIONAL')
            assert ('session.json' in archive.namelist()) is (stage == 'after_close')


def test_original_project_reference_stays_denied_after_source_moves_into_allowed_scope(stores):
    state = seed(stores)
    with state['brain']() as db:
        eid = event(db, state['sid'], 'assistant.answer', payload(state, private=True))
        db.get(Source, state['sources'][1]).project_id = state['bid']
        db.commit()
        with reader(state):
            bundle = read_zip(staged.export(db, state['sid']))
        assert next(item for item in bundle['events'] if item['id'] == eid)['data'] == {}


def test_unquoted_selected_source_cannot_evade_scope(stores):
    state = seed(stores)
    with state['brain']() as db:
        value = payload(state, citations=[], scope='sources', conversation={
            'scope': 'sources', 'source_ids': [state['sources'][1]], 'erp_project_id': state['pid'], 'brain_project_id': state['bid']})
        eid = event(db, state['sid'], 'assistant.answer', value)
        with reader(state):
            bundle = read_zip(staged.export(db, state['sid']))
        assert next(item for item in bundle['events'] if item['id'] == eid)['data'] == {}


def test_session_moves_after_archive_close_refuses_return(stores, monkeypatch):
    state = seed(stores)
    with state['brain']() as db:
        opaque_chunk(db, state['sid'])
        base = zipfile.ZipFile.close
        moved = False
        def close(archive):
            nonlocal moved
            candidate = archive.filename
            base(archive)
            if not moved and candidate and str(candidate).endswith('.zip'):
                moved = True
                with state['brain']() as other:
                    other.get(MeetingSession, state['sid']).project_id = state['private_pid']
                    other.commit()
        monkeypatch.setattr(zipfile.ZipFile, 'close', close)
        with reader(state), pytest.raises(HTTPException) as caught:
            staged.export(db, state['sid'])
        assert caught.value.status_code == 404 and moved
        assert len(list((studio._root().parent / 'session-exports').glob('*.zip'))) == 1


def test_pending_caller_writes_are_refused_without_discard(stores):
    state = seed(stores)
    with state['brain']() as db:
        row = studio.get_session(db, state['sid'])
        row.title = 'Unsaved human draft'
        with pytest.raises(HTTPException) as caught:
            staged.export(db, state['sid'])
        assert caught.value.status_code == 409 and row.title == 'Unsaved human draft' and row in db.dirty


def published_citation(db, state, private):
    """Actual Notes publication producer, entirely fictional isolated stores."""
    from app.meeting_notes_publication_schemas import PublishNotes
    from app.services.meeting_notes_publication import publish_notes, _id
    project_id = state['private_pid'] if private else state['pid']
    sid = create(db, project_id=project_id, kind='note')['id']
    text = 'PRIVATE published content B' if private else 'Published content A'
    saved = command(db, sid, 'notes', 1, title='Fictional published note', content=content(text))
    completed = command(db, sid, 'finalize', saved['revision'])
    publish_notes(db, sid, PublishNotes(command_id=str(uuid4()), expected_revision=completed['revision'],
        expected_note_revision=saved['note_revision'], expected_note_version_id=saved['note_version_id'],
        summary={'overview': text}))
    source = db.get(Source, _id(sid, 'source'))
    artifact = db.get(SourceArtifact, _id(sid, 'artifact'))
    assert source.source_metadata['origin_kind'] == 'published_erp_note'
    citation = assistant._citation(db, {'source_id': source.id, 'excerpt': artifact.content_text,
                                       'locator': deepcopy(artifact.content_json)}, 1)
    citation['source_project_id'] = source.project_id
    assert citation['locator']['session_id'] == sid != state['sid']
    return citation


@pytest.mark.parametrize('private', [False, True])
def test_real_published_note_other_session_uses_authorized_source_origin_and_current_project(stores, private):
    state = seed(stores)
    with state['brain']() as db:
        value = payload(state, citations=[published_citation(db, state, private)])
        eid = event(db, state['sid'], 'assistant.answer', value)
        with reader(state):
            bundle = read_zip(staged.export(db, state['sid']))
        actual = next(item for item in bundle['events'] if item['id'] == eid)
        assert actual['data'] == ({} if private else value)
        assert actual['redacted'] is private


def test_other_session_locator_without_source_or_knowledge_is_redacted(stores):
    state = seed(stores)
    with state['brain']() as db:
        foreign_sid = create(db, project_id=state['private_pid'], kind='note')['id']
        value = payload(state, citations=[{'reference': 'C1', 'excerpt': 'PRIVATE other session',
            'locator': {'session_id': foreign_sid, 'erp_project_id': state['private_pid']}}])
        eid = event(db, state['sid'], 'assistant.answer', value)
        with reader(state):
            bundle = read_zip(staged.export(db, state['sid']))
        assert next(item for item in bundle['events'] if item['id'] == eid)['data'] == {}


@pytest.mark.parametrize('kind', ['assistant.answer', 'assistant.live-answer'])
@pytest.mark.parametrize('invalid', [{'answer': None}, {'query': []}])
def test_partial_or_malformed_answer_body_is_redacted(stores, kind, invalid):
    state = seed(stores)
    with state['brain']() as db:
        eid = event(db, state['sid'], kind, payload(state, **invalid))
        with reader(state):
            bundle = read_zip(staged.export(db, state['sid']))
        assert next(item for item in bundle['events'] if item['id'] == eid)['data'] == {}


@pytest.mark.parametrize('invalid', [{'text': None}, {'content': None}, {'content': {'blocks': [{'type': 'unknown'}]}}])
def test_invalid_enhancement_body_is_redacted_without_exception(stores, invalid):
    state = seed(stores)
    with state['brain']() as db:
        eid = event(db, state['sid'], 'enhancement.proposed', suggestion(state, **invalid))
        with reader(state):
            bundle = read_zip(staged.export(db, state['sid']))
        assert next(item for item in bundle['events'] if item['id'] == eid)['data'] == {}


@pytest.mark.parametrize('kind', ['assistant.answer', 'enhancement.proposed'])
def test_explicit_no_evidence_answer_and_empty_additions_remain_available(stores, kind):
    state = seed(stores)
    with state['brain']() as db:
        value = payload(state, citations=[]) if kind == 'assistant.answer' else suggestion(state, citations=[], text='', content={'version': 1, 'blocks': []})
        eid = event(db, state['sid'], kind, value)
        with reader(state):
            bundle = read_zip(staged.export(db, state['sid']))
        assert next(item for item in bundle['events'] if item['id'] == eid)['data'] == value


def test_unanchored_excerpt_cannot_leak_as_structured_citation(stores):
    state = seed(stores)
    with state['brain']() as db:
        eid = event(db, state['sid'], 'assistant.answer', payload(state, citations=[{
            'reference': 'C1', 'excerpt': 'PRIVATE unknown origin', 'locator': {}}]))
        with reader(state):
            bundle = read_zip(staged.export(db, state['sid']))
        assert next(item for item in bundle['events'] if item['id'] == eid)['data'] == {}


def test_real_working_note_calendar_and_transcript_citations_remain_visible_after_new_versions(stores):
    state = seed(stores)
    from app.services.settings_service import save_section
    raw = b'BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:working-qa\nSUMMARY:Reserve calendar\nEND:VEVENT\nEND:VCALENDAR\n'
    with state['brain']() as db:
        saved = command(db, state['sid'], 'notes', 1, title='Working note', content=content('Reserve 50 euros.'))
        attach_context(db, state['sid'], raw, 'working-qa', str(uuid4()), saved['revision'])
        db.add(LiveTranscriptSegment(id='working-segment', session_id=state['sid'], track='mic',
            start_ms=0, end_ms=0, speaker='QA', text='Reserve transcript', finalized=False))
        db.commit()
        # Preparation builds citations only; transport/model callbacks are
        # forbidden by the fixture and no generation function is called.
        save_section(db, 'ai', {'enabled': True, 'provider': 'openai_compatible',
                     'base_url': 'http://127.0.0.1:1', 'model': 'qa-forbidden'})
        preparation = assistant.prepare(db, studio.get_session(db, state['sid']), query='Reserve', scope='session')
        try:
            # This working-only branch performs synchronous local reads and
            # has no await. Drive it directly, so Windows' event-loop socketpair
            # cannot bypass the fixture's deliberately strict network guard.
            preparation.send(None)
        except StopIteration as result:
            _, _, metadata = result.value
        else:
            pytest.fail('Working-only preparation unexpectedly requested async I/O')
        finally:
            preparation.close()
        assert len(metadata['citations']) == 3
        assert all(item['locator']['session_id'] == state['sid'] for item in metadata['citations'])
        value = {'id': str(uuid4()), 'query': 'Reserve', 'answer': 'Fictional QA answer', **metadata}
        eid = event(db, state['sid'], 'assistant.answer', value)
        next_note = command(db, state['sid'], 'notes', studio.get_session(db, state['sid']).revision,
            title='Working note', content=content('Reserve 70 euros.'), expected_note_revision=saved['note_revision'],
            expected_note_version_id=saved['note_version_id'])
        from app.meeting_session_schemas import SessionSegmentEdit
        studio.edit_segment(db, state['sid'], 'working-segment', SessionSegmentEdit(command_id=str(uuid4()),
            expected_session_revision=next_note['revision'], expected_segment_revision=1,
            text='Reserve transcript corrected', speaker='QA'))
        attach_context(db, state['sid'], raw.replace(b'working-qa', b'working-next'), 'working-next', str(uuid4()),
            studio.get_session(db, state['sid']).revision)
        with reader(state):
            history = assistant.stored_answers(db, studio.get_session(db, state['sid']), 'assistant.answer')['items']
            assert history[0]['stale'] is True and history[0]['status'] == 'obsolete'
            bundle = read_zip(staged.export(db, state['sid']))
        assert bundle['session']['note_revision'] == 2
        assert bundle['session']['segments'][0]['revision'] == 2
        assert bundle['session']['calendar_context']['uid'] == 'working-next'
        assert next(item for item in bundle['events'] if item['id'] == eid)['data'] == value


@pytest.mark.parametrize('kind', ['note_wrong_parent', 'note_denied_project', 'segment', 'staged', 'calendar', 'missing_segment'])
def test_working_reference_foreign_or_missing_identity_is_redacted(stores, kind):
    state = seed(stores)
    raw = b'BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:foreign-working\nSUMMARY:PRIVATE Calendar\nEND:VEVENT\nEND:VCALENDAR\n'
    with state['brain']() as db:
        foreign = create(db, project_id=state['private_pid'], kind='note')['id']
        foreign_note = command(db, foreign, 'notes', 1, title='Private foreign note', content=content('PRIVATE Note'))
        locator = {'session_id': state['sid']}
        if kind.startswith('note'):
            locator.update(note_id=foreign_note['note_id'], note_version_id=foreign_note['note_version_id'],
                erp_project_id=state['pid'] if kind == 'note_wrong_parent' else state['private_pid'])
        elif kind in {'segment', 'missing_segment'}:
            db.add(LiveTranscriptSegment(id='foreign-working-segment', session_id=foreign, track='mic',
                start_ms=0, end_ms=0, speaker='QA', text='PRIVATE Transcript', finalized=False))
            db.commit()
            locator['segment_id'] = 'foreign-working-segment' if kind == 'segment' else 'does-not-exist'
        elif kind == 'staged':
            another = create(db, kind='note')['id']
            version = command(db, another, 'notes', 1, title='Private staging', content=content('PRIVATE Staged'))['staged_note']['version_id']
            locator.update(note_version_id=version, staged_note_version_id=version)
        else:
            attach_context(db, foreign, raw, 'foreign-working', str(uuid4()), foreign_note['revision'])
            locator.update(calendar_uid='foreign-working', calendar_sha256=hashlib.sha256(raw).hexdigest())
        value = payload(state, citations=[{'reference': 'C1', 'excerpt': 'PRIVATE working excerpt', 'locator': locator}])
        eid = event(db, state['sid'], 'assistant.answer', value)
        with reader(state):
            bundle = read_zip(staged.export(db, state['sid']))
        assert next(item for item in bundle['events'] if item['id'] == eid)['data'] == {}


def test_historical_staged_note_version_survives_project_assignment_and_new_note_head(stores):
    state = seed(stores)
    with state['brain']() as db:
        sid = create(db, kind='note')['id']
        first = command(db, sid, 'notes', 1, title='Staged original', content=content('Reserve 50 euros.'))
        second = command(db, sid, 'notes', first['revision'], title='Staged current', content=content('Reserve 70 euros.'))
        assigned = command(db, sid, 'assign-project', second['revision'], project_id=state['pid'])
        assert assigned['note']['plain_text'] == 'Reserve 70 euros.'
        version = first['staged_note']['version_id']
        value = payload(state, scope='session', conversation={'scope': 'session', 'source_ids': [],
            'erp_project_id': state['pid'], 'brain_project_id': state['bid']}, citations=[{
            'reference': 'C1', 'excerpt': 'Reserve 50 euros.', 'locator': {'session_id': sid,
                'note_id': None, 'note_version_id': version, 'staged_note_version_id': version, 'erp_project_id': None}}])
        eid = event(db, sid, 'assistant.answer', value)
        with reader(state):
            bundle = read_zip(staged.export(db, sid))
        assert next(item for item in bundle['events'] if item['id'] == eid)['data'] == value


def test_bare_session_locator_without_evidence_identity_is_redacted(stores):
    state = seed(stores)
    with state['brain']() as db:
        eid = event(db, state['sid'], 'assistant.answer', payload(state, citations=[{
            'reference': 'C1', 'excerpt': 'Unverifiable excerpt', 'locator': {'session_id': state['sid']}}]))
        with reader(state):
            bundle = read_zip(staged.export(db, state['sid']))
        assert next(item for item in bundle['events'] if item['id'] == eid)['data'] == {}


@pytest.mark.parametrize('declared_sid', [True, False])
def test_working_erp_note_from_another_session_same_project_requires_source_or_knowledge(stores, declared_sid):
    state = seed(stores)
    with state['brain']() as db:
        command(db, state['sid'], 'notes', 1, title='Current session note', content=content('Current note A'))
        other_sid = create(db, project_id=state['pid'], kind='note')['id']
        other = command(db, other_sid, 'notes', 1, title='Other session same project', content=content('Other note A'))
        locator = {'erp_project_id': state['pid'], 'note_id': other['note_id'], 'note_version_id': other['note_version_id']}
        if declared_sid:
            locator['session_id'] = state['sid']
        value = payload(state, citations=[{'reference': 'C1', 'excerpt': 'Other note A', 'locator': locator}])
        eid = event(db, state['sid'], 'assistant.answer', value)
        with reader(state):
            bundle = read_zip(staged.export(db, state['sid']))
        assert bundle['session']['note_id'] != other['note_id']
        assert bundle['session']['note']['plain_text'] == 'Current note A'
        assert next(item for item in bundle['events'] if item['id'] == eid)['data'] == {}


