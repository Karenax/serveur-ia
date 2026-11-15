"""Self-contained review/recovery bundle, without replaying business commands."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import zipfile

from fastapi import HTTPException
from sqlalchemy import select

from ..meeting_session_models import MeetingAudioChunk, MeetingSessionEvent, StagedSessionNoteVersion
from . import meeting_sessions as sessions


def _operator_identity():
    from backend.app.services.project_operator import current_operator
    operator = current_operator()
    return operator.id, operator.role, operator.project_ids


def _bindings(row):
    return tuple(getattr(row, key) for key in ('project_id', 'brain_project_id', 'note_id', 'recording_id', 'operator_id'))


def _fresh_session(db, sid, operator, bindings=None):
    # This is a read-only export: never discard pending caller writes while
    # ending the previous SQLite read snapshot for a fresh authorization check.
    if db.new or db.dirty or db.deleted:
        raise HTTPException(409, 'Enregistrer les modifications avant l’export')
    db.rollback()
    db.expire_all()
    if _operator_identity() != operator:
        raise HTTPException(409, 'Les droits de l’opérateur ont changé pendant l’export')
    row = sessions.get_session(db, sid)
    if bindings is not None and _bindings(row) != bindings:
        raise HTTPException(409, 'Le rattachement de la séance a changé pendant l’export')
    return row


def _identifier(value, *, nullable=False):
    return value is None and nullable or isinstance(value, str) and bool(value) and len(value) <= 80


def _structured_answer(data, sid, kind):
    """Validate policy-bearing fields before invoking the shared visibility rule."""
    if not isinstance(data, dict) or not _identifier(data.get('id')):
        return False
    if kind in {'assistant.answer', 'assistant.live-answer'}:
        if not all(isinstance(data.get(key), str) for key in ('query', 'answer')):
            return False
    elif kind == 'enhancement.proposed':
        if not isinstance(data.get('text'), str) or not isinstance(data.get('content'), dict):
            return False
        from backend.app.project_note_schemas import NoteContent
        from pydantic import ValidationError
        try:
            NoteContent.model_validate(data['content'])
        except ValidationError:
            return False
    conversation = data.get('conversation')
    if not isinstance(conversation, dict) or set(conversation) != {'scope', 'source_ids', 'erp_project_id', 'brain_project_id'}:
        return False
    scope = conversation['scope']
    if not isinstance(scope, str) or scope not in {'session', 'project', 'sources', 'global'} or data.get('scope') != scope:
        return False
    if not all(_identifier(conversation[key], nullable=True) for key in ('erp_project_id', 'brain_project_id')):
        return False
    source_ids = conversation['source_ids']
    if not isinstance(source_ids, list) or not all(_identifier(value) for value in source_ids):
        return False
    if (scope != 'sources' and source_ids) or (scope == 'sources' and not source_ids):
        return False
    citations = data.get('citations')
    if not isinstance(citations, list):
        return False
    for citation in citations:
        if not isinstance(citation, dict) or not isinstance(citation.get('reference'), str) or not citation['reference']:
            return False
        if not isinstance(citation.get('excerpt'), str):
            return False
        for key in ('source_id', 'knowledge_id', 'source_project_id', 'knowledge_project_id'):
            if key in citation and not _identifier(citation[key], nullable=True):
                return False
        locator = citation.get('locator')
        if locator is not None and not isinstance(locator, dict):
            return False
        if locator:
            for key in ('erp_project_id', 'session_id'):
                if key in locator and not _identifier(locator[key], nullable=True):
                    return False
            # Published Source/Knowledge citations carry their originating
            # session locator. Their origin/current project guards below are
            # authoritative even when that historical session is archived.
            if (locator.get('session_id') and locator['session_id'] != sid
                    and not citation.get('source_id') and not citation.get('knowledge_id')):
                return False
        if not citation.get('source_id') and not citation.get('knowledge_id'):
            if not locator or not (locator.get('session_id') == sid or locator.get('erp_project_id')):
                return False
    return True


def _calendar_context(data):
    """Only the closed shape emitted by the human-selected ICS parser is shared."""
    if not isinstance(data, dict) or data.get('origin') != 'human_selected_ics' or data.get('context_only') is not True:
        return False
    allowed = {'uid', 'summary', 'description', 'location', 'dtstart', 'dtend',
               'dtstart_parameters', 'dtend_parameters', 'attendees', 'origin', 'sha256', 'context_only'}
    if set(data) - allowed or not isinstance(data.get('uid'), str) or not data['uid']:
        return False
    digest = data.get('sha256')
    if not isinstance(digest, str) or len(digest) != 64 or any(char not in '0123456789abcdef' for char in digest):
        return False
    for key in ('uid', 'summary', 'description', 'location', 'dtstart', 'dtend'):
        if key in data and (not isinstance(data[key], str) or len(data[key]) > 12000):
            return False
    for key in ('dtstart_parameters', 'dtend_parameters'):
        if key in data and (not isinstance(data[key], list) or not all(isinstance(value, str) for value in data[key])):
            return False
    attendees = data.get('attendees')
    if not isinstance(attendees, list) or len(attendees) > 100:
        return False
    return all(isinstance(attendee, dict) and set(attendee) == {'value', 'parameters'}
               and isinstance(attendee['value'], str) and isinstance(attendee['parameters'], list)
               and all(isinstance(value, str) for value in attendee['parameters']) for attendee in attendees)


def _working_citation_visible(db, sid, citation):
    """Resolve working identities, without confusing old versions with denial."""
    locator = citation.get('locator') or {}
    anchored = False
    if any(locator.get(key) is not None for key in ('note_id', 'note_version_id', 'staged_note_version_id')):
        version_id = locator.get('note_version_id')
        staged_id = locator.get('staged_note_version_id')
        if locator.get('note_id'):
            project_id, note_id = locator.get('erp_project_id'), locator['note_id']
            if not all(_identifier(value) for value in (project_id, note_id, version_id)) or staged_id is not None:
                return False
            row = sessions.get_session(db, sid)
            if (locator.get('session_id'), project_id, note_id) != (sid, row.project_id, row.note_id):
                return False
            from backend.app.db import SessionLocal
            from backend.app.services.project_notes import read_version
            # read_version authorizes the exact parent/version; it does not
            # require that the cited version equal the editable head.
            with SessionLocal() as erp:
                read_version(erp, project_id, note_id, version_id)
        else:
            identity = staged_id or version_id
            if not _identifier(identity) or version_id is not None and version_id != identity:
                return False
            version = db.get(StagedSessionNoteVersion, identity)
            if version is None or version.session_id != sid:
                return False
        anchored = True
    if locator.get('segment_id') is not None:
        from ..meeting_session_models import LiveTranscriptSegment
        if not _identifier(locator['segment_id']):
            return False
        segment = db.get(LiveTranscriptSegment, locator['segment_id'])
        if segment is None or segment.session_id != sid:
            return False
        # A correction can advance revision/text; the original card remains
        # legitimate historical evidence belonging to this authorized session.
        anchored = True
    if locator.get('calendar_uid') is not None:
        uid, digest = locator['calendar_uid'], locator.get('calendar_sha256')
        if not isinstance(uid, str) or not uid or not isinstance(digest, str):
            return False
        found = any(_calendar_context(event.data) and event.data['uid'] == uid and event.data['sha256'] == digest
            for event in db.scalars(select(MeetingSessionEvent).where(MeetingSessionEvent.session_id == sid,
                MeetingSessionEvent.kind == 'calendar.context')))
        if not found:
            return False
        anchored = True
    return anchored


def _event_visible(db, sid, kind, data):
    if kind == 'calendar.context':
        return _calendar_context(data)
    if kind not in {'assistant.answer', 'assistant.live-answer', 'enhancement.proposed'} or not _structured_answer(data, sid, kind):
        return False
    from ..models import Source
    from .project_access import require_brain
    from .scoped_assistant import answer_visible
    try:
        for source_id in data['conversation']['source_ids']:
            source = db.get(Source, source_id)
            if source is None:
                return False
            require_brain(source.project_id)
        for citation in data['citations']:
            if not citation.get('source_id') and not citation.get('knowledge_id'):
                if not _working_citation_visible(db, sid, citation):
                    return False
        return answer_visible(db, data)
    except HTTPException:
        return False


def _export_events(db, sid, restricted):
    exported, retained = [], {}
    for event in db.scalars(select(MeetingSessionEvent).where(MeetingSessionEvent.session_id == sid)):
        envelope = {'kind': event.kind, 'data': deepcopy(event.data), 'revision': event.revision,
                    'created_at': event.created_at.isoformat()}
        if restricted:
            visible = _event_visible(db, sid, event.kind, event.data)
            envelope.update(id=event.id, redacted=not visible)
            if visible:
                retained[event.id] = deepcopy(event.data)
            else:
                envelope['data'] = {}
                envelope['redaction_reason'] = 'Payload omitted for the current project scope'
        exported.append(envelope)
    return exported, retained


def _revalidate(db, sid, operator, bindings, retained):
    _fresh_session(db, sid, operator, bindings)
    for event_id, original in retained.items():
        event = db.get(MeetingSessionEvent, event_id)
        if event is None or event.session_id != sid or event.data != original:
            raise HTTPException(409, 'Un événement a changé pendant l’export')
        if not _event_visible(db, sid, event.kind, original):
            raise HTTPException(404, 'Un événement est désormais hors du périmètre autorisé')


def export(db, sid):
    operator = _operator_identity()
    row = _fresh_session(db, sid, operator)
    bindings = _bindings(row)
    events, retained = _export_events(db, sid, operator[2] is not None)
    snapshot = deepcopy(sessions.serialize_session(db, row))
    metadata = {'format': 'agent-meeting-session-review', 'version': 1, 'session': snapshot,
                'restore_policy': 'Review bundle. Restore the coordinated global backup into a new copy for identity-preserving recovery; never replay these commands.',
                'events': events,
                'staged_note_versions': [{key: getattr(v, key) for key in ('id', 'revision', 'title', 'content', 'plain_text', 'sha256')}
                    for v in db.scalars(select(StagedSessionNoteVersion).where(StagedSessionNoteVersion.session_id == sid))],
                'note_versions': [], 'files': {}}
    chunks = list(db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == sid)
                            .order_by(MeetingAudioChunk.track, MeetingAudioChunk.sequence)))
    folder = sessions._root().parent / 'session-exports'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{sid}-{uuid4()}.zip'
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for chunk in chunks:
            source = sessions.chunk_path(chunk)
            name = f'audio/{chunk.track}/{chunk.sequence:06d}{Path(chunk.filename).suffix.lower()}'
            digest = hashlib.sha256()
            size = 0
            with source.open('rb') as origin, archive.open(name, 'w', force_zip64=True) as destination:
                while block := origin.read(1024 * 1024):
                    digest.update(block)
                    size += len(block)
                    destination.write(block)
            if (digest.hexdigest(), size) != (chunk.sha256, chunk.size_bytes):
                raise HTTPException(409, 'Fragment modifié pendant l’export ; conserver et rétablir son original')
            metadata['files'][name] = {'sha256': chunk.sha256, 'size_bytes': size, 'chunk_id': chunk.id}
        if row.note_id:
            from backend.app.db import SessionLocal
            from backend.app.project_note_models import NoteVersion
            from backend.app.services.project_note_files import listing, download
            with SessionLocal() as erp:
                for version in erp.scalars(select(NoteVersion).where(NoteVersion.note_id == row.note_id, NoteVersion.project_id == row.project_id).order_by(NoteVersion.revision)):
                    metadata['note_versions'].append({'id': version.id, 'revision': version.revision,
                        'sha256': version.sha256, 'snapshot': json.loads(version.snapshot)})
                for attachment in listing(erp, row.project_id, row.note_id)['items']:
                    data, info = download(erp, row.project_id, row.note_id, attachment['id'])
                    name = 'attachments/' + info['id']
                    archive.writestr(name, data)
                    metadata['files'][name] = info
        _revalidate(db, sid, operator, bindings, retained)
        archive.writestr('session.json', json.dumps(metadata, ensure_ascii=False, indent=2))
        note = snapshot.get('note') or snapshot.get('staged_note')
        if note:
            archive.writestr('notes.txt', note.get('plain_text', ''))
    # A ZIP that loses authorization remains private on disk for diagnosis;
    # no bytes/path are returned to the request after this final fresh check.
    _revalidate(db, sid, operator, bindings, retained)
    return path
