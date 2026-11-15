"""Interactive Windows capture uses the same chunks and command receipts."""
from typing import Literal
from contextlib import nullcontext
from threading import Lock, RLock
from uuid import NAMESPACE_URL, uuid5
from weakref import WeakValueDictionary

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..db import get_db
from ..meeting_session_models import MeetingSessionCommand, MeetingSession, MeetingSessionEvent
from ..meeting_session_schemas import Command
from ..services import native_audio as native, meeting_sessions as sessions
from ..services.audio_cpu_coordinator import AudioCpuBusy, capture_start

router = APIRouter(tags=['native-capture'])
_command_guard = Lock()
_command_locks = WeakValueDictionary()


class Start(Command):
    tracks: list[Literal['mic', 'system']] = Field(min_length=1, max_length=2)
    devices: dict[Literal['mic', 'system'], int] = Field(default_factory=dict)


@router.get('/api/v1/workspace/native-capture')
def status(db: Session = Depends(get_db)):
    return sessions.native_capture_status(db, probe_devices=False)


@router.get('/api/v1/meeting-sessions/{sid}/native-capture/status')
def session_status(sid: str, db: Session = Depends(get_db)):
    return sessions.native_capture_status(db, sid)


def finalize_stop(db, sid, command_id):
    final_id = str(uuid5(NAMESPACE_URL, f'native-finalize:{sid}:{command_id}'))
    previous = db.get(MeetingSessionCommand, final_id)
    row = sessions.get_session(db, sid, write=True)
    revision = previous.body['expected_revision'] if previous else row.revision
    result = sessions.execute_command(db, sid, 'finalize', Command(command_id=final_id, expected_revision=revision))
    parent = db.get(MeetingSessionCommand, command_id)
    parent.result = result
    db.commit()
    return result


def perform(db, sid, operation, body):
    # An identical retry may arrive while the first call drains hardware. This
    # lock is independent from the session writer lock used by chunk readers.
    with _command_guard:
        command_lock = _command_locks.get(body.command_id)
        if command_lock is None:
            command_lock = RLock()
            _command_locks[body.command_id] = command_lock
    with command_lock:
        db.expire_all()
        try:
            return _perform(db, sid, operation, body)
        except AudioCpuBusy as exc:
            raise HTTPException(409, str(exc)) from exc


def _start_needs_open(db, sid, previous):
    """A prepared verification is recovery; only a pre-owner retry opens audio."""
    if previous is None:
        return True
    if previous.status != 'prepared' or native.has_registered_capture(sid):
        return False
    owners = db.scalars(select(MeetingSessionEvent).where(
        MeetingSessionEvent.session_id == sid, MeetingSessionEvent.kind == 'native.capture.owner'))
    return not any((event.data or {}).get('start_command_id') == previous.id or (
        'start_command_id' not in (event.data or {}) and event.created_at >= previous.created_at)
        for event in owners)


def _perform(db, sid, operation, body):
    row = sessions.get_session(db, sid, write=True)
    value = body.model_dump(mode='json')
    previous = db.get(MeetingSessionCommand, value['command_id'])
    opening = operation == 'start' and _start_needs_open(db, sid, previous)
    resuming = operation == 'resume' and not (previous and previous.status == 'completed')
    if opening or resuming:
        sessions.require_enabled(db)
    if operation == 'start' and (len(set(body.tracks)) != len(body.tracks) or any(v < 0 for v in body.devices.values())):
        raise HTTPException(422, 'Pistes uniques et identifiants de périphérique positifs requis')
    kind = 'native.' + operation
    admission = capture_start(db, sid) if opening or resuming else nullcontext()
    with admission, sessions._lock:
        db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
        db.expire_all()
        row = sessions.get_session(db, sid, write=True)
        existing = db.get(MeetingSessionCommand, value['command_id'])
        if not (existing and existing.status == 'completed'):
            from ..services.browser_capture import active_owners, legacy_active_session, legacy_paused_owner
            browser_owners = active_owners(db)
            if sid in browser_owners or ((opening or resuming) and
                    (browser_owners or legacy_active_session(db, sid) or
                     operation == 'start' and legacy_paused_owner(db, sid, browser_only=True))):
                raise HTTPException(409, 'Une capture navigateur est réservée, active ou en pause ; fermer ses pistes avant Windows.')
        if existing is None:
            allowed = {'created', 'paused', 'interrupted'} if operation == 'start' else {'paused'} if operation == 'resume' else {'recording'} if operation == 'pause' else {'recording', 'paused', 'interrupted', 'finalizing'}
            if row.state not in allowed:
                raise HTTPException(409, 'État de séance incompatible avec cette capture Windows')
            if operation == 'start':
                if native.has_capture_owner():
                    raise HTTPException(409, 'Vérifier l’arrêt Windows avant un nouveau démarrage')
                # One interactive audio source for the local operator, including
                # browser captures already declared recording on the server.
                if db.scalar(select(MeetingSession.id).where(MeetingSession.id != sid, MeetingSession.state == 'recording').limit(1)):
                    raise HTTPException(409, 'Une autre capture est déjà déclarée active ; terminer cette capture avant de démarrer Windows')
                if not native.status().get('ready'):
                    raise HTTPException(409, 'Capture Windows indisponible dans la session interactive')
        try:
            command = sessions._begin(db, row, kind, value, server_data={'previous_state': row.state,
                **({'_native_drain_confirmed': False} if operation == 'stop' else {})})
        except HTTPException as exc:
            if operation == 'start' and previous and previous.status == 'rejected' and (
                    previous.session_id == sid and previous.operator_id == sessions.current_operator().id
                    and previous.kind == kind and previous.digest == sessions._digest(kind, value)):
                raise HTTPException(409, {'message': previous.error or str(exc.detail),
                                         'rejected_command_id': previous.id}) from exc
            raise
        if command.status == 'completed':
            if operation == 'stop' and command.result.get('state') != 'completed':
                return finalize_stop(db, sid, body.command_id)
            return command.result
        # Recheck durable ownership under the writer transaction. Never turn a
        # recovery-only attempt into hardware opening without CPU admission.
        needs_open = operation == 'start' and _start_needs_open(db, sid, existing)
        if needs_open and not opening:
            raise HTTPException(409, 'Le propriétaire Windows a changé ; relire la séance avant de vérifier le démarrage.')
        if needs_open or resuming:
            sessions.require_enabled(db)
            row.state = 'recording'
        # _begin also acquires a SQLite writer transaction on a prepared retry.
        # Release it before the native reader persists its final fragments.
        db.commit()
    # Do not hold the session lock while draining: the reader thread writes its
    # final chunks through store_chunk, which needs that same lock.
    try:
        if operation == 'start':
            if native.has_registered_capture(sid):
                owner = next((item for item in native.registered_snapshots() if item['session_id'] == sid), None)
                if owner and not owner.get('problem_code') and (
                        owner['state'] == 'starting' and owner['process_alive'] is True
                        or owner['process_alive'] is None):
                    raise HTTPException(409, 'Ouverture Windows non confirmée ; le démarrage conservé reste à vérifier.')
                if not owner or owner['state'] != 'recording' or owner['process_alive'] is not True or owner.get('problem_code'):
                    raise native.NativeStartNotConfirmed('Démarrage Windows interrompu ; vérifier l’arrêt, fragments conservés.')
            elif existing is not None:
                if not needs_open or not _start_needs_open(db, sid, existing):
                    raise native.NativeStartNotConfirmed('Démarrage Windows non confirmé après interruption ; fragments conservés.')
                # A pre-opening failure with no ownership retains the existing
                # explicit retry behavior. No background replay opens hardware.
                native.start_capture(db, sid, tracks=body.tracks, devices=body.devices)
            else:
                if not needs_open:
                    raise native.NativeStartNotConfirmed('Démarrage Windows non confirmé ; aucune nouvelle ouverture.')
                native.start_capture(db, sid, tracks=body.tracks, devices=body.devices)
        elif operation == 'pause':
            native.pause_capture(sid)
        elif operation == 'resume':
            native.resume_capture(sid)
        elif operation == 'stop':
            if native.has_registered_capture(sid):
                # An automatic helper stop can precede EOF/cleanup. Retain the
                # registered owner until its reader/exit barrier is checked.
                native.stop_capture(sid)
            elif command.body.get('_native_drain_confirmed') is not True:
                raise native.NativeStopNotConfirmed('Arrêt Windows non confirmé ; conserver séparément les fragments acquittés.')
            with sessions._lock:
                db.expire_all()
                command = db.get(MeetingSessionCommand, value['command_id'])
                command.body = {**command.body, '_native_drain_confirmed': True}
                db.commit()  # A later SQL/finalization retry must not infer a drain.
        with sessions._lock:
            db.expire_all()
            row = sessions.get_session(db, sid, write=True)
            command = db.get(MeetingSessionCommand, value['command_id'])
            if command.status == 'completed':
                return command.result
            if operation == 'start':
                row.state = 'recording'
            elif operation == 'pause':
                row.state = 'paused'
            elif operation == 'stop':
                # Record drain receipt before the existing, separately durable
                # finalization. A retry uses its deterministic child command.
                row.state = 'paused'
            result = sessions._finish(db, row, command, kind, {'tracks': getattr(body, 'tracks', [])})
        if operation == 'stop':
            result = finalize_stop(db, sid, body.command_id)
        return result
    except (native.NativeStopNotConfirmed, native.NativeStartNotConfirmed) as exc:
        db.rollback()
        with sessions._lock:
            db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
            db.expire_all()
            row = sessions.get_session(db, sid, write=True)
            command = db.get(MeetingSessionCommand, body.command_id)
            command.status, command.error = 'rejected', str(exc)[:500]
            if row.pending_command_id == command.id:
                row.pending_command_id = None
            row.state = 'interrupted'
            row.revision += 1
            row.updated_at = sessions.now()
            start_failure = isinstance(exc, native.NativeStartNotConfirmed)
            sessions.append_event(db, row, 'native.start.unconfirmed' if start_failure else 'native.stop.unconfirmed',
                                  {'error': command.error, **({'rejected_command_id': command.id} if start_failure else {})})
            db.commit()
        if start_failure:
            raise HTTPException(409, {'message': str(exc), 'rejected_command_id': body.command_id}) from exc
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        db.rollback()
        command = db.get(MeetingSessionCommand, body.command_id)
        if command:
            command.error = str(exc)[:500]
            if operation in {'start', 'resume'} and not native.owns_session(sid):
                row = db.get(MeetingSession, sid)
                row.state = 'interrupted'
            db.commit()
        raise


@router.post('/api/v1/meeting-sessions/{sid}/native-capture/start')
def start(sid: str, body: Start, db: Session = Depends(get_db)):
    return perform(db, sid, 'start', body)


@router.post('/api/v1/meeting-sessions/{sid}/native-capture/pause')
def pause(sid: str, body: Command, db: Session = Depends(get_db)):
    return perform(db, sid, 'pause', body)


@router.post('/api/v1/meeting-sessions/{sid}/native-capture/resume')
def resume(sid: str, body: Command, db: Session = Depends(get_db)):
    return perform(db, sid, 'resume', body)


@router.post('/api/v1/meeting-sessions/{sid}/native-capture/stop')
def stop(sid: str, body: Command, db: Session = Depends(get_db)):
    return perform(db, sid, 'stop', body)
