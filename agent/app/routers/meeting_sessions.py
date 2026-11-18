"""Project-aware studio API; registration and activation remain explicit."""
import asyncio
import json
import re
import time
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from app.db import get_db
from app.db_support import utc_iso
from app.meeting_session_models import MeetingAudioChunk, MeetingSessionCommand, MeetingSessionEvent, LiveTranscriptSegment, StagedSessionNoteVersion
from app.meeting_session_schemas import (Command, SessionCreate, SessionAssign, SessionNoteSave,
    SessionSegmentEdit, BrowserCaptureReservation, CaptureControl)
from app.services import meeting_sessions as service
from backend.app.services.project_operator import current_operator, operator_context

router = APIRouter(prefix='/api/v1/meeting-sessions', tags=['meeting-sessions'])

EVENT_BATCH_LIMIT = 200
EVENT_FOLLOW_SECONDS = 30.0
EVENT_POLL_SECONDS = 0.2
EVENT_HEARTBEAT_SECONDS = 10.0


def _event_batch(db, sid, after):
    service.get_session(db, sid)
    rows = list(db.scalars(select(MeetingSessionEvent).where(MeetingSessionEvent.session_id == sid,
        MeetingSessionEvent.id > after).order_by(MeetingSessionEvent.id).limit(EVENT_BATCH_LIMIT)))
    # This feed only wakes canonical reads, which enforce their own current source
    # rights. Old answers/proposals can refer to projects no longer authorised.
    # Keep no business payload in the feed, including unknown future event types.
    wanted = {row.data.get('chunk_id') for row in rows
              if row.kind == 'transcript.updated' and isinstance(row.data.get('chunk_id'), str)}
    chunks = set(db.scalars(select(MeetingAudioChunk.id).where(
        MeetingAudioChunk.session_id == sid, MeetingAudioChunk.id.in_(wanted)))) if wanted else set()
    return [{'id': row.id, 'kind': row.kind,
             'data': {'chunk_id': row.data['chunk_id']} if row.kind == 'transcript.updated'
                     and isinstance(row.data.get('chunk_id'), str)
                     and row.data.get('chunk_id') in chunks else {},
             'revision': row.revision, 'created_at': utc_iso(row.created_at)} for row in rows]


def _scoped_event_batch(factory, operator, sid, after):
    with operator_context(operator), factory() as db:
        return _event_batch(db, sid, after)


def _event_frame(row):
    return f'id: {row["id"]}\nevent: {row["kind"]}\ndata: ' + json.dumps(
        {key: row[key] for key in ('kind', 'data', 'revision', 'created_at')}, ensure_ascii=False) + '\n\n'


async def _follow_events(request, factory, operator, sid, after):
    deadline = time.monotonic() + EVENT_FOLLOW_SECONDS
    heartbeat = time.monotonic() + EVENT_HEARTBEAT_SECONDS
    yield 'retry: 500\n\n'
    while time.monotonic() < deadline:
        if await request.is_disconnected():
            return
        try:
            rows = await run_in_threadpool(_scoped_event_batch, factory, operator, sid, after)
        except HTTPException as exc:
            # A previously authorised session can move outside this operator's scope.
            # Send no session payload after access has disappeared.
            yield 'event: stream.denied\ndata: ' + json.dumps({'status': exc.status_code}) + '\n\n'
            return
        for row in rows:
            if time.monotonic() >= deadline or await request.is_disconnected():
                return
            after = row['id']
            yield _event_frame(row)
        if len(rows) == EVENT_BATCH_LIMIT:
            continue
        current = time.monotonic()
        if current >= heartbeat:
            yield ': heartbeat\n\n'
            heartbeat = current + EVENT_HEARTBEAT_SECONDS
        remaining = deadline - time.monotonic()
        if remaining > 0:
            # Every ORM session and its read transaction have closed before waiting.
            await asyncio.sleep(min(EVENT_POLL_SECONDS, remaining))


@router.get('/capabilities')
def capabilities(db: Session = Depends(get_db)):
    return service.capabilities(db)


@router.get('')
def listing(project_id: str | None = None, q: str = Query('', max_length=255), offset: int = Query(0, ge=0, le=100000),
            limit: int = Query(30, ge=1, le=100), db: Session = Depends(get_db)):
    return service.list_sessions(db, project_id=project_id, q=q, offset=offset, limit=limit)


@router.post('', status_code=201)
def create(body: SessionCreate, db: Session = Depends(get_db)):
    return service.create_session(db, body)


@router.get('/{sid}')
def detail(sid: str, db: Session = Depends(get_db)):
    return service.serialize_session(db, service.get_session(db, sid))


@router.put('/{sid}/chunks/{track}/{sequence}')
async def chunk(sid: str, track: str, sequence: int, file: UploadFile = File(...),
                command_id: str = Form(...), sha256: str = Form(...), start_ms: int = Form(..., ge=0),
                duration_ms: int = Form(..., ge=0), db: Session = Depends(get_db)):
    raw = await file.read(service.MAX_BYTES + 1)
    return await run_in_threadpool(service.store_chunk, db, sid, track, sequence, raw=raw, filename=file.filename or '',
        mime_type=file.content_type, command_id=command_id, sha256=sha256, start_ms=start_ms, duration_ms=duration_ms)


@router.put('/{sid}/notes')
def notes(sid: str, body: SessionNoteSave, db: Session = Depends(get_db)):
    return service.execute_command(db, sid, 'notes', body)


@router.get('/{sid}/note-versions/{version_id}')
def note_version(sid: str, version_id: str, db: Session = Depends(get_db)):
    service.get_session(db, sid)
    version = db.scalar(select(StagedSessionNoteVersion).where(
        StagedSessionNoteVersion.id == version_id, StagedSessionNoteVersion.session_id == sid))
    if version is None:
        raise HTTPException(404, 'Version de note introuvable dans cette séance')
    return {**{key: getattr(version, key) for key in (
        'id', 'session_id', 'revision', 'title', 'content', 'plain_text', 'sha256')},
        'created_at': utc_iso(version.created_at)}


@router.post('/{sid}/assign-project')
def assign(sid: str, body: SessionAssign, db: Session = Depends(get_db)):
    return service.execute_command(db, sid, 'assign-project', body)


@router.post('/{sid}/resume')
def resume(sid: str, body: CaptureControl, db: Session = Depends(get_db)):
    return service.execute_command(db, sid, 'resume', body)


@router.post('/{sid}/pause')
def pause(sid: str, body: CaptureControl, db: Session = Depends(get_db)):
    return service.execute_command(db, sid, 'pause', body)


@router.post('/{sid}/browser-capture/reserve')
def reserve_browser(sid: str, body: BrowserCaptureReservation, db: Session = Depends(get_db)):
    from app.services.browser_capture import perform
    return perform(db, sid, 'reserve', body)


@router.post('/{sid}/browser-capture/release')
def release_browser(sid: str, body: BrowserCaptureReservation, db: Session = Depends(get_db)):
    from app.services.browser_capture import perform
    return perform(db, sid, 'release', body)


@router.post('/{sid}/finalize')
def finalize(sid: str, body: Command, db: Session = Depends(get_db)):
    return service.execute_command(db, sid, 'finalize', body)


@router.post('/{sid}/cancel')
def cancel(sid: str, body: Command, db: Session = Depends(get_db)):
    return service.execute_command(db, sid, 'cancel', body)


@router.get('/{sid}/commands/{command_id}')
def command(sid: str, command_id: str, db: Session = Depends(get_db)):
    service.get_session(db, sid)
    row = db.get(MeetingSessionCommand, command_id)
    if row is None or row.session_id != sid:
        raise HTTPException(404, 'Commande introuvable dans cette séance')
    if row.operator_id != current_operator().id:
        # A 403 keeps old clients from treating another operator's command as
        # absent and discarding their local recovery payload.
        raise HTTPException(403, 'Reçu réservé à son opérateur')
    return {'id': row.id, 'kind': row.kind, 'status': row.status, 'error': row.error, 'result': row.result}


@router.get('/{sid}/audio')
def audio(sid: str, request: Request, track: str = 'mic', db: Session = Depends(get_db)):
    row = service.get_session(db, sid)
    raw, mime, filename = service.consolidated_audio(db, row, track)
    headers = {'Cache-Control': 'private, no-store', 'Accept-Ranges': 'bytes',
        'Content-Disposition': "inline; filename*=UTF-8''" + quote(filename)}
    # Authorization and original-byte integrity are checked before any partial
    # response or size disclosure. No validator is advertised for If-Range.
    selected = None if request.headers.get('if-range') else _audio_byte_range(request.headers.get('range'), len(raw))
    if selected is None:
        return Response(raw, media_type=mime, headers=headers)
    start, end = selected
    headers['Content-Range'] = f'bytes {start}-{end}/{len(raw)}'
    return Response(raw[start:end+1], status_code=206, media_type=mime, headers=headers)


def _audio_byte_range(value, size):
    """Single byte ranges; unsupported/malformed/multipart ranges use full GET."""
    if not value or not size:
        return None
    match = re.fullmatch(r'bytes=\s*([0-9]*)-([0-9]*)\s*', value.strip(), flags=re.IGNORECASE)
    if not match or not any(match.groups()):
        return None
    def bounded(digits):
        # Compare huge decimal numerals as strings before conversion. Their
        # only relevant upper bound is this representation's actual byte size.
        digits = digits.lstrip('0') or '0'
        return size if len(digits)>len(str(size)) else min(size, int(digits))
    first, last = match.groups()
    if first:
        start, end = bounded(first), bounded(last) if last else size-1
        if end < start < size:
            return None
    else:
        suffix = bounded(last)
        start, end = size-suffix, size-1
    if start >= size:
        raise HTTPException(416, 'Plage audio hors du fichier conservé', headers={
            'Content-Range': f'bytes */{size}', 'Accept-Ranges':'bytes', 'Cache-Control':'private, no-store'})
    return start, min(end, size-1)


@router.get('/{sid}/segments')
def segments(sid: str, db: Session = Depends(get_db)):
    service.get_session(db, sid)
    return [{key: getattr(row, key) for key in ('id', 'track', 'start_ms', 'end_ms', 'speaker', 'text', 'revision', 'finalized')}
            for row in db.scalars(select(LiveTranscriptSegment).where(LiveTranscriptSegment.session_id == sid)
                .order_by(LiveTranscriptSegment.start_ms, LiveTranscriptSegment.id))]


@router.put('/{sid}/segments/{segment_id}')
def edit_segment(sid: str, segment_id: str, body: SessionSegmentEdit, db: Session = Depends(get_db)):
    return service.edit_segment(db, sid, segment_id, body)


@router.post('/{sid}/transcription/retry')
def retry_transcription(sid: str, body: Command, db: Session = Depends(get_db)):
    return service.retry_transcription(db, sid, body)


@router.get('/{sid}/transcription/batch')
def batch_status(sid: str, db: Session = Depends(get_db)):
    from app.services.session_batch_transcription import status
    return status(db, sid)


@router.post('/{sid}/transcription/batch', status_code=202)
def batch_transcription(sid: str, body: Command, db: Session = Depends(get_db)):
    from app.services.session_batch_transcription import request
    return request(db, sid, body)


@router.post('/{sid}/transcription/batch/cancel')
def cancel_batch_transcription(sid: str, body: Command, db: Session = Depends(get_db)):
    from app.services.session_batch_transcription import cancel
    return cancel(db, sid, body)


@router.get('/{sid}/events')
def events(sid: str, request: Request, after: int = Query(0, ge=0),
           follow: bool = False, db: Session = Depends(get_db)):
    service.get_session(db, sid)
    previous = request.headers.get('last-event-id', '')
    if previous:
        if not previous.isdecimal():
            raise HTTPException(422, 'Curseur événement invalide')
        after = max(after, int(previous))
    if follow:
        # Retain the authoritative binding, including an isolated test override,
        # while closing this dependency's transaction before the response starts.
        factory = sessionmaker(bind=db.get_bind().engine, expire_on_commit=False)
        operator = current_operator()
        db.close()
        return StreamingResponse(_follow_events(request, factory, operator, sid, after),
            media_type='text/event-stream', headers={'Cache-Control': 'no-cache, no-transform'})
    # Existing collectors retain their finite replay contract.
    rows = _event_batch(db, sid, after)
    db.close()
    async def stream():
        for row in rows:
            yield _event_frame(row)
        if not rows:
            await asyncio.sleep(0.05)
            yield ': ready\n\n'
    return StreamingResponse(stream(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache, no-transform'})
