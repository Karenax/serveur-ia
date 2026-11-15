"""Durable browser ownership, acquired before media permission or streams.

Events are additive. No timeout, process restart, generic state transition or
publication releases an owner. Only its explicit release command does so.
The frontend must close every acquired stream before sending that command.
"""
from contextlib import nullcontext

from fastapi import HTTPException
from sqlalchemy import select, text

from app.meeting_session_models import MeetingSession, MeetingSessionCommand, MeetingSessionEvent
from backend.app.services.project_operator import current_operator

OWNER = 'browser.capture.owner'
RELEASED = 'browser.capture.released'
FROZEN_ON_COPY = 'browser.capture.frozen-on-copy'


def active_owners(db):
    latest = {}
    for event in db.scalars(select(MeetingSessionEvent).where(
            MeetingSessionEvent.kind.in_([OWNER, RELEASED, FROZEN_ON_COPY])).order_by(MeetingSessionEvent.id)):
        latest[event.session_id] = event
    return {sid: event for sid, event in latest.items() if event.kind == OWNER}


def session_snapshot(db, row):
    event = active_owners(db).get(row.id)
    if event is None:
        return None
    operator = current_operator()
    controlled = event.data.get('operator_id') == operator.id and operator.role != 'reader'
    return {'session_id': row.id, 'owner_id': event.data['owner_id'] if controlled else None,
            'can_control': controlled, 'state': row.state if row.state in {'recording', 'paused'} else 'reserved'}


def _same_owner(event, owner_id):
    return (event is not None and event.data.get('owner_id') == owner_id
            and event.data.get('operator_id') == current_operator().id)


def legacy_paused_owner(db, sid, *, browser_only=False):
    """A declared old capture owns streams even before its first audio ACK."""
    row = db.get(MeetingSession, sid)
    if row is None or row.state != 'paused':
        return False
    kinds = ['session.resume'] if browser_only else ['session.resume', 'native.capture.owner']
    intent = db.scalar(select(MeetingSessionEvent).where(
        MeetingSessionEvent.session_id == sid, MeetingSessionEvent.kind.in_(kinds))
        .order_by(MeetingSessionEvent.id.desc()).limit(1))
    if intent is None:
        return False  # A paused draft without capture history does not own media.
    closed = db.scalar(select(MeetingSessionEvent.id).where(MeetingSessionEvent.session_id == sid,
        MeetingSessionEvent.id > intent.id, MeetingSessionEvent.kind.in_(
            ['session.finalize', 'session.cancel', RELEASED, FROZEN_ON_COPY])).limit(1))
    if closed:
        return False
    stops = db.scalars(select(MeetingSessionCommand).where(MeetingSessionCommand.session_id == sid,
        MeetingSessionCommand.kind == 'native.stop', MeetingSessionCommand.created_at >= intent.created_at))
    return not any(command.body.get('_native_drain_confirmed') is True for command in stops)


def legacy_active_session(db, sid):
    """Only captures declared active or paused with unclosed intent block."""
    for row in db.scalars(select(MeetingSession).where(MeetingSession.id != sid,
            MeetingSession.state.in_(['recording', 'paused']))):
        if row.state == 'recording':
            return row.id
        if legacy_paused_owner(db, row.id):
            return row.id
    return None


def require_available(db, sid):
    from . import native_audio
    if active_owners(db):
        raise HTTPException(409, 'Une capture navigateur reste à arrêter ou à libérer.')
    if native_audio.has_capture_owner():
        raise HTTPException(409, 'Une capture Windows reste à arrêter ou à conserver.')
    if legacy_paused_owner(db, sid, browser_only=True):
        raise HTTPException(409, 'Cette capture navigateur héritée reste en pause ; fermer ses pistes et conserver la séance.')
    if legacy_active_session(db, sid):
        raise HTTPException(409, 'Une autre capture est active ou en pause ; terminer sa conservation.')


def authorize_control(db, row, kind, value):
    """Called with fresh SQL writer + admission before any capture transition."""
    from . import native_audio
    owners = active_owners(db)
    owner = owners.get(row.id)
    token = value.get('browser_capture_owner_id')
    if native_audio.has_registered_capture(row.id):
        raise HTTPException(409, 'La capture Windows possède cette séance ; utiliser ses commandes Windows.')
    if owner:
        if kind in {'finalize', 'cancel'}:
            raise HTTPException(409, 'Fermer les pistes navigateur et libérer leur réservation avant de conserver la séance.')
        if not _same_owner(owner, token):
            raise HTTPException(409, 'Le propriétaire navigateur doit confirmer cette commande.')
    elif token is not None:
        raise HTTPException(409, 'Cette réservation navigateur n’est plus active ; aucune nouvelle ouverture.')
    if kind == 'resume':
        if native_audio.has_capture_owner():
            raise HTTPException(409, 'Une capture Windows possède déjà les pistes audio ; arrêter cette capture avant de démarrer le navigateur.')
        if any(identity != row.id for identity in owners) or legacy_active_session(db, row.id):
            raise HTTPException(409, 'Une autre capture possède déjà les pistes audio.')


def perform(db, sid, operation, body):
    from .audio_cpu_coordinator import AudioCpuBusy
    try:
        return _perform(db, sid, operation, body)
    except AudioCpuBusy as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


def durable_reserve_refusal(db, sid, body, failure):
    """An explicit refused attempt cannot become an opening after conditions change.

Only authorized 409 preconditions are retained. Collisions with another exact
command and completed historical receipts stay immutable and reveal no nonce
acknowledgment. No session state/revision/pending field or owner is changed.
"""
    from . import meeting_sessions as sessions
    value = body.model_dump(mode='json')
    kind = 'browser.reserve'
    with sessions._lock:
        try:
            db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
            db.expire_all()
            sessions.get_session(db, sid, write=True)  # Fresh rights, even after a race.
            digest = sessions._digest(kind, value)
            existing = db.get(MeetingSessionCommand, value['command_id'])
            if existing:
                exact = (existing.session_id == sid and existing.operator_id == current_operator().id
                    and existing.kind == kind and existing.digest == digest)
                if not exact or existing.status != 'rejected':
                    db.rollback()
                    return None
                reason = existing.error or 'Réservation navigateur refusée.'
                db.rollback()
            else:
                reason = str(failure.detail)[:500]
                db.add(MeetingSessionCommand(id=value['command_id'], session_id=sid, kind=kind,
                    operator_id=current_operator().id, digest=digest, body=value,
                    status='rejected', error=reason))
                db.commit()
            return HTTPException(409, {'message': reason, 'rejected_command_id': value['command_id']})
        except Exception:
            db.rollback()
            raise


def _perform(db, sid, operation, body):
    from . import meeting_sessions as sessions
    from .audio_cpu_coordinator import capture_start
    value = body.model_dump(mode='json')
    if operation not in {'reserve', 'release'}:
        raise HTTPException(422, 'Opération de capture navigateur inconnue.')
    kind = 'browser.' + operation
    def refuse_busy(error):
        failure = HTTPException(409, str(error))
        raise durable_reserve_refusal(db, sid, body, failure) or failure
    admission = capture_start(db, sid, on_refused=refuse_busy) if operation == 'reserve' else nullcontext()
    # The admission lock is shared with native start; SQLite serializes even
    # independent Sessions and protects the gap before helper registration.
    with admission, sessions._lock:
        savepoint = None
        try:
            db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
            db.expire_all()
            # A rejected mutation rolls back to this savepoint, retaining the
            # outer SQLite writer lock until the refused receipt is committed.
            savepoint = db.begin_nested()
            row = sessions.get_session(db, sid, write=True)
            previous = db.get(MeetingSessionCommand, value['command_id'])
            digest = sessions._digest(kind, value)
            if previous:
                if (previous.session_id != sid or previous.operator_id != current_operator().id
                        or previous.kind != kind or previous.digest != digest):
                    raise HTTPException(409, 'Clé de commande réutilisée avec un autre contenu.')
                if previous.status != 'completed':
                    raise HTTPException(409, 'Réservation non confirmée ; relire la séance.')
                # A historical reserve receipt is never authority to reopen.
                if operation == 'reserve' and not _same_owner(active_owners(db).get(sid), value['owner_id']):
                    raise HTTPException(409, 'Cette réservation navigateur est terminée ; aucune nouvelle ouverture.')
                result = previous.result
                db.rollback()
                return result
            if row.pending_command_id:
                raise HTTPException(409, 'Une commande conservée doit être reprise avant de modifier la séance.')
            if row.revision != value['expected_revision']:
                raise HTTPException(409, 'La séance a changé ; conserver la saisie et recharger.')
            if operation == 'reserve':
                sessions.require_enabled(db)
                if row.state not in {'created', 'paused', 'interrupted'} or row.recording_id:
                    raise HTTPException(409, 'Cette séance ne peut pas réserver une nouvelle capture navigateur.')
                used = db.scalar(select(MeetingSessionEvent.id).where(MeetingSessionEvent.kind == OWNER,
                        MeetingSessionEvent.data['owner_id'].as_string() == value['owner_id']).limit(1))
                rejected = db.scalar(select(MeetingSessionCommand.id).where(
                    MeetingSessionCommand.kind == 'browser.reserve', MeetingSessionCommand.status == 'rejected',
                    MeetingSessionCommand.body['owner_id'].as_string() == value['owner_id']).limit(1))
                if used or rejected:
                    raise HTTPException(409, 'Ce propriétaire navigateur a déjà été utilisé ; aucune réouverture.')
                require_available(db, sid)
                event_kind = OWNER
            else:
                if not _same_owner(active_owners(db).get(sid), value['owner_id']):
                    raise HTTPException(409, 'La libération ne correspond pas au propriétaire navigateur actuel.')
                event_kind = RELEASED
                # Streams are closed by the caller, before this explicit command.
                # Keep chunks/human edits, and stop claiming ongoing recording.
                if row.state in {'recording', 'paused'}:
                    row.state = 'interrupted'
            command = MeetingSessionCommand(id=value['command_id'], session_id=sid, kind=kind,
                operator_id=current_operator().id, digest=digest, body=value)
            db.add(command)
            return sessions._finish(db, row, command, event_kind,
                {'owner_id': value['owner_id'], 'operator_id': current_operator().id})
        except HTTPException as exc:
            if operation == 'reserve' and exc.status_code == 409:
                if savepoint is not None and savepoint.is_active:
                    savepoint.rollback()  # Does not release the outer writer.
                failure = durable_reserve_refusal(db, sid, body, exc)
                if failure is not None:
                    raise failure from exc
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
