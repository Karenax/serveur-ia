"""Durable local capture commands, staging, Notes bindings and recovery receipts."""
from app.operational_limits import AUDIO_IMPORT_BYTES, CAPTURE_BYTES, CAPTURE_DURATION_MS
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import threading
import wave
from contextlib import nullcontext
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import HTTPException
from sqlalchemy import func, inspect, select, text

from app.db_support import utc_iso
from app.meeting_session_models import (MeetingSession, MeetingAudioChunk, MeetingSessionCommand,
    MeetingSessionEvent, LiveTranscriptSegment, StagedSessionNoteVersion, now)
from backend.app.project_note_schemas import NoteContent, NoteCreate, NoteSave, content_text
from backend.app.services.project_operator import current_operator, require_project_access


MAX_BYTES = AUDIO_IMPORT_BYTES
MAX_CAPTURE_BYTES = CAPTURE_BYTES
MAX_DURATION_MS = CAPTURE_DURATION_MS
TRACKS = {'mic', 'system'}
_lock = threading.RLock()


def feature_enabled(db=None):
    switch = os.environ.get('AGENT_MEETING_SESSIONS_ENABLED')
    if switch is not None and switch.lower() in {'0', 'false', 'off'}:
        return False
    if db is None:
        from app.db import SessionLocal
        try:
            with SessionLocal() as session:
                return feature_enabled(session)
        except Exception:
            return False
    from .settings_service import get_section
    configured = get_section(db, 'foresight')
    return bool(configured['enabled']) if 'enabled' in configured else switch in {'1', 'true', 'on'}


def require_enabled(db):
    if not feature_enabled(db):
        raise HTTPException(409, 'Les nouvelles séances sont désactivées dans les réglages.')


def live_transcription_enabled(db=None, *, operator_id=None):
    """Direct transcription needs its own explicit opt-in, including legacy data."""
    if db is None:
        from app.db import SessionLocal
        try:
            with SessionLocal() as session:
                return live_transcription_enabled(session, operator_id=operator_id)
        except Exception:
            return False
    from . import meeting_preferences
    key = 'live_transcription_enabled'
    return feature_enabled(db) and (meeting_preferences.preferences(db, operator_id)[key]
        if operator_id is not None else meeting_preferences.any_enabled(db, key))


def require_live_transcription(db, *, operator_id=None):
    require_enabled(db)
    if not live_transcription_enabled(db, operator_id=operator_id):
        raise HTTPException(409, 'La transcription directe est désactivée ; les fragments audio restent conservés.')


def capabilities(db):
    from .meeting_audio import runtime_status
    status = runtime_status()
    live = {'ready': False, 'detail': 'Transcription directe non qualifiée.'}
    try:
        from . import live_speech
        live = live_speech.runtime_status()
    except ImportError:
        pass
    from .settings_service import get_section
    ai_enabled = bool(get_section(db, 'ai').get('enabled'))
    live_operational = bool(live.get('ready'))
    live_qualified = live_operational and bool(live.get('qualified_live_latency')) and bool(live.get('industrial_quality_qualified'))
    from .session_batch_transcription import available as session_batch_available
    saved_direct_gpu = ('PB_SPEECH_DEVICE' not in os.environ
        and get_section(db, 'foresight').get('live_speech_device') == 'cuda')
    session_batch_ready = session_batch_available() if saved_direct_gpu else bool(live.get('installed'))
    live_detail = ('Direct disponible en essai, qualité/latence industrielles non qualifiées ; relecture nécessaire'
        if live_operational and not live_qualified else live.get('detail') or status.get('detail', ''))
    from .audio_cpu_coordinator import status as audio_cpu_status
    from .session_proactive import status as proactive_status
    return {'enabled': feature_enabled(db), 'installed': _ready(db),
        'capture': {'durable': True, 'max_upload_mb': MAX_BYTES // 1024**2, 'max_capture_mb': MAX_CAPTURE_BYTES // 1024**2, 'max_duration_minutes': MAX_DURATION_MS // 60000,
                    'tracks': ['mic', 'system'], 'browser_permission_required': True,
                    'native_format': 'audio/ogg;codecs=opus', 'audio_bits_per_second': 32000},
        'transcription': {'batch_ready': status['ready'], 'session_batch_ready': session_batch_ready, 'live_ready': live_qualified,
                          'enabled': live_transcription_enabled(db, operator_id=current_operator().id),
                          **({'installed': live['installed']} if isinstance(live.get('installed'), bool) else {}),
                          'live_operational': live_operational, 'qualified_live_latency': bool(live.get('qualified_live_latency')),
                          'industrial_quality_qualified': bool(live.get('industrial_quality_qualified')), 'detail': live_detail},
        'notes': {'staging': True, 'erp_projection': True},
        'native_capture': native_capture_status(db),
        'audio_arbitration': audio_cpu_status(), 'proactive_limits': proactive_status(),
        'assistant': {'enabled': ai_enabled, 'ready': ai_enabled, 'operational_probe': False,
                      'scopes': ['session', 'project', 'sources', 'global']}}


def _root():
    from app.config import settings
    return (Path(settings.storage_dir) / 'meeting-sessions').resolve()


def chunk_path(chunk):
    path = Path(chunk.storage_path).resolve()
    if not path.is_relative_to(_root()):
        raise HTTPException(409, 'Chemin audio hors du stockage de capture')
    return path


def _ready(db):
    return inspect(db.connection()).has_table('meeting_sessions')


def get_session(db, sid, *, write=False):
    if not _ready(db):
        raise HTTPException(404, 'Séances non installées')
    row = db.get(MeetingSession, sid)
    if row is None:
        raise HTTPException(404, 'Séance introuvable')
    operator = current_operator()
    if row.project_id:
        require_project_access(row.project_id, write=write)
    elif operator.id != row.operator_id or operator.project_ids is not None:
        raise HTTPException(404, 'Séance introuvable')
    elif write and operator.role == 'reader':
        raise HTTPException(403, 'Opérateur en lecture seule')
    return row


def native_capture_status(db, sid=None, *, probe_devices=True):
    """One authorized DTO for workspace, capabilities and a selected session.

    Private registry snapshots are taken before SQL and contain no device probe.
    Unexpected SQL failures propagate instead of masquerading as empty capture.
    """
    import os
    from . import native_audio as native
    if sid is not None:
        get_session(db, sid)
    snapshots = native.registered_snapshots()
    managed = bool(os.environ.get('AGENT_KIARA_KEY'))
    value = native.status(sid) if probe_devices and not managed else native.owner_status()
    if managed:
        value['installed'] = False
    owners, recovery = [], []

    def authorized(identity):
        try:
            row = get_session(db, identity)
        except HTTPException as exc:
            if exc.status_code in {403, 404}:
                return None, False
            raise
        try:
            get_session(db, identity, write=True)
            control = True
        except HTTPException as exc:
            if exc.status_code not in {403, 404}:
                raise
            control = False
        return row, control

    for item in snapshots:
        if sid is not None and item['session_id'] != sid:
            continue
        row, control = authorized(item['session_id'])
        if row is not None:
            owners.append({**item, 'can_control': control})
    if _ready(db):
        candidates = select(MeetingSession).where(MeetingSession.state.in_(
            ['recording', 'paused', 'interrupted', 'finalizing']),
            select(MeetingSessionEvent.id).where(MeetingSessionEvent.session_id == MeetingSession.id,
                MeetingSessionEvent.kind == 'native.capture.owner').exists())
        if sid is not None:
            candidates = candidates.where(MeetingSession.id == sid)
        registered = {item['session_id'] for item in owners}
        for row in db.scalars(candidates):
            authorized_row, control = authorized(row.id)
            if authorized_row is None:
                continue
            if row.id in registered and row.state in {'recording', 'paused'}:
                continue
            latest_owner = db.scalar(select(MeetingSessionEvent).where(
                MeetingSessionEvent.session_id == row.id,
                MeetingSessionEvent.kind == 'native.capture.owner')
                .order_by(MeetingSessionEvent.id.desc()).limit(1))
            stop = db.scalar(select(MeetingSessionCommand).where(
                MeetingSessionCommand.session_id == row.id, MeetingSessionCommand.kind == 'native.stop',
                MeetingSessionCommand.created_at >= latest_owner.created_at)
                .order_by(MeetingSessionCommand.created_at.desc()).limit(1))
            stopped_bad = db.scalar(select(MeetingSessionEvent.id).where(
                MeetingSessionEvent.session_id == row.id,
                MeetingSessionEvent.kind == 'native.stop.unconfirmed',
                MeetingSessionEvent.id > latest_owner.id).limit(1))
            pending = db.get(MeetingSessionCommand, row.pending_command_id) if row.pending_command_id else None
            reason = 'stop-unconfirmed' if stopped_bad else 'conservation-pending' if pending and (
                pending.kind in {'native.stop', 'session.finalize'}) or stop and (
                stop.body.get('_native_drain_confirmed') is True) else 'interrupted'
            notice = {'session_id': row.id, 'event_cursor': db.scalar(select(func.max(MeetingSessionEvent.id))
                .where(MeetingSessionEvent.session_id == row.id)) or 0,
                'reason': reason, 'can_control': control}
            replay = pending if pending and pending.kind == 'native.stop' else stop
            if replay and replay.status in {'prepared', 'completed'} and (replay.result or {}).get('state') != 'completed':
                notice['pending_stop'] = {key: replay.body[key] for key in ('command_id', 'expected_revision')}
            recovery.append(notice)
    selected = next((item for item in owners if item['session_id'] == sid), None) if sid else None
    # Detailed sticky errors remain scoped to the explicitly authorized session.
    if selected and probe_devices and value.get('session'):
        selected = {**selected, 'error': value['session'].get('error')}
    return {**{key: item for key, item in value.items() if key not in {'active', 'session', 'owners', 'recovery'}},
            'owners': owners, 'recovery': recovery, 'session': selected,
            'active': [{'session_id': item['session_id'], 'state': item['state'], 'tracks': item['tracks'],
                        'can_control': item['can_control']}
                       for item in owners if item['process_alive'] is True]}


def append_event(db, row, kind, data):
    event = MeetingSessionEvent(session_id=row.id, kind=kind, data=data,
                                revision=row.revision)
    db.add(event)
    db.flush()
    return event


def session_note(db, row, *, erp_factory=None):
    if row.note_id and row.project_id:
        if erp_factory is None:
            from backend.app.db import SessionLocal
            erp_factory = SessionLocal
        from backend.app.services.project_notes import read_note
        with erp_factory() as erp:
            return read_note(erp, row.project_id, row.note_id)
    return dict(row.staged_note) if row.staged_note else None


def serialize_session(db, row, *, include_content=True, erp_factory=None):
    chunks = list(db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == row.id)
                            .order_by(MeetingAudioChunk.track, MeetingAudioChunk.sequence)))
    tracks = []
    for track in sorted({chunk.track for chunk in chunks}):
        items = [chunk for chunk in chunks if chunk.track == track]
        tracks.append({'name': track, 'mime_type': items[0].mime_type, 'filename': items[0].filename,
            'chunks': len(items), 'total_bytes': sum(chunk.size_bytes for chunk in items),
            'duration_seconds': max((chunk.start_ms + chunk.duration_ms for chunk in items), default=0) / 1000,
            'complete': [chunk.sequence for chunk in items] == list(range(len(items)))})
    pending = db.get(MeetingSessionCommand, row.pending_command_id) if row.pending_command_id else None
    publication = db.scalar(select(MeetingSessionCommand).where(MeetingSessionCommand.session_id == row.id,
        MeetingSessionCommand.kind == 'publish-notes', MeetingSessionCommand.status != 'rejected')
        .order_by(MeetingSessionCommand.created_at.desc()).limit(1))
    calendar = db.scalar(select(MeetingSessionEvent).where(MeetingSessionEvent.session_id == row.id,
        MeetingSessionEvent.kind == 'calendar.context').order_by(MeetingSessionEvent.id.desc()).limit(1))
    unconfirmed_stop = db.scalar(select(MeetingSessionEvent.id).where(MeetingSessionEvent.session_id == row.id,
        MeetingSessionEvent.kind.in_(['native.stop.unconfirmed', 'native.capture.interrupted'])).limit(1))
    issues = [] if row.project_id else ['Rattacher à un projet pour publier.']
    if unconfirmed_stop:
        issues.append('Cette séance a connu un arrêt Windows non confirmé. Vérifiez l’audio conservé ; le journal natif reste récupérable.')
    if db.scalar(select(MeetingSessionEvent.id).where(MeetingSessionEvent.session_id == row.id,
            MeetingSessionEvent.kind == 'native.start.unconfirmed').limit(1)):
        issues.append('Cette séance a connu un démarrage Windows non confirmé. Les fragments acquittés et journaux restent conservés.')
    if row.state in {'completed', 'interrupted'}:
        requested_tracks = set()
        for event in db.scalars(select(MeetingSessionEvent).where(
                MeetingSessionEvent.session_id == row.id,
                MeetingSessionEvent.kind == 'native.start')):
            requested_tracks.update(track for track in (event.data or {}).get('tracks', [])
                                    if track in TRACKS)
        missing_tracks = requested_tracks - {chunk.track for chunk in chunks}
        for track in sorted(missing_tracks):
            name = 'Microphone' if track == 'mic' else 'Son du PC'
            issues.append(f'{name} : aucun fragment audio conservé pour cette piste pourtant démarrée. '
                          'La cause reste à vérifier ; l’enregistrement ne couvre pas cette piste.')
    data = {key: getattr(row, key) for key in ('id', 'title', 'kind', 'date', 'project_id', 'brain_project_id',
        'operator_id', 'state', 'revision', 'recording_id', 'note_id')}
    data.update(created_at=utc_iso(row.created_at), updated_at=utc_iso(row.updated_at), tracks=tracks,
        total_bytes=sum(chunk.size_bytes for chunk in chunks),
        duration_seconds=max((chunk.start_ms + chunk.duration_ms for chunk in chunks), default=0) / 1000,
        issues=issues,
        live_transcription_enabled=live_transcription_enabled(db, operator_id=row.operator_id),
        transcript_provisional=(any(chunk.speech_status != 'completed' for chunk in chunks) or bool(db.scalar(
            select(LiveTranscriptSegment.id).where(LiveTranscriptSegment.session_id == row.id,
                LiveTranscriptSegment.finalized.is_(False)).limit(1)))),
        transcript_processing_complete=bool(chunks) and all(chunk.speech_status == 'completed' for chunk in chunks),
        published_meeting_id=(publication.result or {}).get('meeting_id') if publication and publication.status == 'completed' else None,
        published_note_version_id=(publication.body.get('_snapshot') or {}).get('note_version_id') if publication else None,
        calendar_context=calendar.data if calendar else None,
        pending_command={'id': pending.id, 'kind': pending.kind, 'status': pending.status, 'error': pending.error} if pending else None,
        event_cursor=db.scalar(select(func.max(MeetingSessionEvent.id)).where(MeetingSessionEvent.session_id == row.id)) or 0)
    owned = native_capture_status(db, row.id, probe_devices=False)
    data['native_capture'] = owned['session']
    data['native_recovery'] = owned['recovery']
    from .browser_capture import session_snapshot as browser_snapshot
    data['browser_capture'] = browser_snapshot(db, row)
    from .speech_admission import session_snapshot as admission_snapshot
    data['transcription_admission'] = admission_snapshot(db, row)
    from .session_batch_transcription import session_status as batch_status
    data['transcription_batch'] = batch_status(db, row)
    if include_content:
        note = session_note(db, row, erp_factory=erp_factory)
        data.update(note=note if row.note_id else None, staged_note=note if not row.note_id else None,
            note_revision=note.get('revision') if note and row.note_id else None,
            note_version_id=note.get('version_id') if note and row.note_id else None,
            chunks=[{**{key: getattr(chunk, key) for key in ('id', 'track', 'sequence', 'sha256', 'size_bytes',
                'start_ms', 'duration_ms', 'speech_status', 'speech_error')}, 'created_at': utc_iso(chunk.created_at)} for chunk in chunks],
            segments=[{key: getattr(segment, key) for key in ('id', 'track', 'start_ms', 'end_ms', 'speaker', 'text', 'revision', 'finalized')}
                for segment in db.scalars(select(LiveTranscriptSegment).where(LiveTranscriptSegment.session_id == row.id)
                    .order_by(LiveTranscriptSegment.start_ms, LiveTranscriptSegment.id))])
    return data


def list_sessions(db, *, project_id=None, q='', offset=0, limit=30):
    if not _ready(db):
        return {'items': [], 'total': 0, 'offset': offset, 'limit': limit, 'available': False}
    operator = current_operator()
    query = select(MeetingSession)
    if project_id:
        require_project_access(project_id)
        query = query.where(MeetingSession.project_id == project_id)
    if q.strip():
        needle = q.strip()[:255]
        query = query.where(MeetingSession.title.icontains(needle, autoescape=True)
            | MeetingSession.date.contains(needle, autoescape=True))
    if operator.project_ids is not None:
        query = query.where(MeetingSession.project_id.in_(operator.project_ids))
    else:
        query = query.where((MeetingSession.project_id.is_not(None)) | (MeetingSession.operator_id == operator.id))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(MeetingSession.updated_at.desc(), MeetingSession.id).offset(offset).limit(limit))
    return {'items': [serialize_session(db, row, include_content=False) for row in rows],
            'total': total, 'offset': offset, 'limit': limit, 'available': True}


def _digest(kind, body):
    return hashlib.sha256(json.dumps([kind, body], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def _link(project_id, *, erp_factory=None):
    require_project_access(project_id, write=True)
    if erp_factory is None:
        from backend.app.db import SessionLocal
        erp_factory = SessionLocal
    from backend.app.models import Project, BrainLink
    with erp_factory() as erp:
        if erp.get(Project, project_id) is None:
            raise HTTPException(404, 'Projet introuvable')
        link = erp.get(BrainLink, project_id)
        if not link:
            raise HTTPException(409, 'Relier le projet au cœur de connaissance avant attribution.')
        return link.brain_project_id


def _begin(db, row, kind, body, *, server_data=None):
    # Explicit SQLite writer lock; no migration or seeding in API commands.
    db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
    db.refresh(row)
    cid = body['command_id']
    previous = db.get(MeetingSessionCommand, cid)
    digest = _digest(kind, body)
    if previous:
        if (previous.session_id != row.id or previous.operator_id != current_operator().id
                or previous.kind != kind or previous.digest != digest):
            raise HTTPException(409, 'Clé de commande réutilisée avec un autre contenu.')
        if previous.status == 'rejected':
            raise HTTPException(409, previous.error or 'Commande rejetée ; relire la séance.')
        return previous
    if row.pending_command_id:
        raise HTTPException(409, 'Une commande conservée doit être reprise avant de modifier la séance.')
    if row.revision != body['expected_revision']:
        raise HTTPException(409, 'La séance a changé ; conserver la saisie et recharger.')
    command = MeetingSessionCommand(id=cid, session_id=row.id, kind=kind,
        operator_id=current_operator().id, digest=digest, body={**body, **(server_data or {})})
    db.add(command)
    row.pending_command_id = cid
    db.commit()  # Freeze any cross-store effect before touching ERP/files.
    return command


def _finish(db, row, command, kind, data=None, *, envelope=None):
    row.revision += 1
    row.updated_at = now()
    row.pending_command_id = None
    command.status, command.error = 'completed', None
    append_event(db, row, kind, data or {})
    result = serialize_session(db, row)
    if envelope is not None:
        result = {'session': result, **envelope}
    command.result = result
    db.commit()
    if kind == 'transcript.corrected':
        from . import session_proactive
        session_proactive.wake_worker()
    return result


def retry_transcription(db, sid, body):
    """Explicit receipt-based recovery; never reload a model or change audio/text."""
    from app.meeting_session_schemas import Command
    value = Command.model_validate(body if isinstance(body, dict) else body.model_dump(mode='json')).model_dump(mode='json')
    row = get_session(db, sid, write=True)
    with _lock:
        db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
        db.expire_all()
        row = get_session(db, sid, write=True)
        previous = db.get(MeetingSessionCommand, value['command_id'])
        if previous is not None:
            command = _begin(db, row, 'retry-transcription', value)
            if command.status == 'completed':
                return command.result  # Recovery of a validated receipt is not new inference.
        require_live_transcription(db, operator_id=row.operator_id)
        if row.state == 'cancelled':
            raise HTTPException(409, 'Une séance annulée ne peut pas reprendre sa transcription.')
        command = _begin(db, row, 'retry-transcription', value)
        if command.status == 'completed':
            return command.result
        try:
            # _begin preserves the receipt first; recheck fresh authority while
            # taking the writer lock for the actual status change and result.
            db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
            db.expire_all()
            row = get_session(db, sid, write=True)
            command = db.get(MeetingSessionCommand, value['command_id'])
            require_live_transcription(db, operator_id=row.operator_id)
            if row.state == 'cancelled':
                raise HTTPException(409, 'Une séance annulée ne peut pas reprendre sa transcription.')
            from .speech_admission import admit_retry
            admission = admit_retry(db, row)
            result = _finish(db, row, command, 'transcript.retry_requested',
                {**admission, 'requested_at_utc': utc_iso(now())}, envelope=admission)
        except HTTPException as exc:
            db.rollback()
            db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
            db.expire_all()
            try:
                row = get_session(db, sid, write=True)
            except HTTPException:
                db.rollback()
                raise  # Lost authority leaves the prepared receipt recoverable.
            command = db.get(MeetingSessionCommand, value['command_id'])
            command.status, command.error = 'rejected', str(exc.detail)[:500]
            row.pending_command_id = None
            db.commit()
            raise
    from .live_speech import wake_worker
    if result['retried_chunks']:
        wake_worker()  # Only after the durable commit; no model startup here.
    return result


def create_session(db, body):
    require_enabled(db)
    operator = current_operator()
    if operator.role == 'reader':
        raise HTTPException(403, 'Opérateur en lecture seule')
    value = body.model_dump(mode='json')
    if not value['title'].strip():
        raise HTTPException(422, 'Titre requis')
    if operator.project_ids is not None and not value['project_id']:
        raise HTTPException(403, 'Choisir un projet autorisé pour la séance.')
    bid = _link(value['project_id']) if value['project_id'] else None
    if bid:
        from app.models import Project
        if db.get(Project, bid) is None:
            raise HTTPException(409, 'Projet Brain introuvable')
    with _lock:
        db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
        previous = db.get(MeetingSessionCommand, value['command_id'])
        if previous:
            if previous.kind != 'create' or previous.digest != _digest('create', value) or previous.operator_id != operator.id:
                raise HTTPException(409, 'Clé de création déjà utilisée.')
            get_session(db, previous.session_id)
            return previous.result
        row = MeetingSession(title=value['title'].strip(), kind=value['kind'], date=value['date'],
            project_id=value['project_id'], brain_project_id=bid, operator_id=operator.id)
        db.add(row)
        db.flush()
        append_event(db, row, 'session.created', {})
        result = serialize_session(db, row)
        db.add(MeetingSessionCommand(id=value['command_id'], session_id=row.id, kind='create',
            operator_id=operator.id, digest=_digest('create', value), body=value, status='completed', result=result))
        db.commit()
        return result


def _write_file(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != hashlib.sha256(raw).hexdigest():
            raise HTTPException(409, 'Fragment audio conservé différent ; aucune copie écrasée.')
        return
    if shutil.disk_usage(path.parent).free < len(raw) + 128 * 1024 * 1024:
        raise HTTPException(507, 'Espace disque insuffisant ; le fragment reste conservé dans le navigateur.')
    # Exclusive staging and fsync precede the metadata commit/acknowledgement.
    temporary = path.with_suffix(path.suffix + '.pending')
    with temporary.open('wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def store_chunk(db, sid, track, sequence, *, raw, filename, mime_type, command_id, sha256, start_ms, duration_ms,
                internal_capture_owner=None):
    row = get_session(db, sid, write=True)
    from . import native_audio
    native_owner = internal_capture_owner is not None and native_audio.accepts_owner(sid, internal_capture_owner)
    if internal_capture_owner is not None and not native_owner:
        raise HTTPException(403, 'Propriétaire de capture interne invalide')
    if native_audio.has_registered_capture(sid) and not native_owner:
        raise HTTPException(409, 'La capture native possède cette séance audio')
    if (not feature_enabled(db) and not native_owner and row.state == 'created'
            and not db.scalar(select(MeetingAudioChunk.id).where(MeetingAudioChunk.session_id == sid).limit(1))):
        require_enabled(db)
    if track not in TRACKS or sequence < 0 or start_ms < 0 or duration_ms < 0:
        raise HTTPException(422, 'Piste, séquence ou durée invalide.')
    if not raw or len(raw) > MAX_BYTES:
        raise HTTPException(413 if raw else 400, 'Audio vide ou supérieur à 256 Mio.')
    digest = hashlib.sha256(raw).hexdigest()
    if sha256 != digest:
        raise HTTPException(422, 'Empreinte du fragment incorrecte.')
    try:
        if str(UUID(command_id)) != command_id:
            raise ValueError()
    except (ValueError, TypeError):
        raise HTTPException(422, 'UUID de commande requis') from None
    from backend.app.routers.meeting_audio import EXTENSIONS, MIMES
    filename = Path(filename.replace('\\', '/')).name
    suffix = Path(filename).suffix.lower()
    if suffix not in EXTENSIONS or len(filename) > 255:
        raise HTTPException(422, 'Format audio non pris en charge.')
    body = {'command_id': command_id, 'track': track, 'sequence': sequence, 'sha256': digest,
            'filename': filename, 'start_ms': start_ms, 'duration_ms': duration_ms}
    with _lock:
        db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
        db.refresh(row)
        previous_command = db.get(MeetingSessionCommand, command_id)
        if previous_command:
            if (previous_command.session_id != sid or previous_command.operator_id != current_operator().id
                    or previous_command.digest != _digest('chunk', body)):
                raise HTTPException(409, 'Clé de fragment réutilisée avec un autre contenu.')
            return previous_command.result
        previous = db.scalar(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == sid,
            MeetingAudioChunk.track == track, MeetingAudioChunk.sequence == sequence))
        if previous:
            if (previous.sha256, previous.start_ms, previous.duration_ms) != (digest, start_ms, duration_ms):
                raise HTTPException(409, 'Séquence audio déjà reçue avec un autre contenu.')
            result = {'acknowledged': True, 'sequence': sequence, 'sha256': digest, 'revision': row.revision, 'replayed': True}
        else:
            pending = db.get(MeetingSessionCommand, row.pending_command_id) if row.pending_command_id else None
            native_drain = native_owner and pending is not None and pending.kind in {'native.start', 'native.pause', 'native.resume', 'native.stop'}
            # A recoverable secondary command must not stop native persistence
            # if its SQL completion failed after preparation.
            secondary_pending = pending is not None and pending.kind in {'retry-transcription', 'transcription-batch'}
            if (row.pending_command_id and not native_drain and not secondary_pending) or row.state not in {'created', 'recording', 'paused', 'interrupted'}:
                raise HTTPException(409, 'Cette séance ne reçoit plus de fragments.')
            total = db.scalar(select(func.coalesce(func.sum(MeetingAudioChunk.size_bytes), 0)).where(MeetingAudioChunk.session_id == sid))
            quota = MAX_BYTES if row.kind == 'import' else MAX_CAPTURE_BYTES
            if total + len(raw) > quota or start_ms + duration_ms > MAX_DURATION_MS:
                raise HTTPException(413, 'Limite de séance audio de 512 Mio ou 12 heures dépassée.')
            initial = db.scalar(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == sid,
                MeetingAudioChunk.track == track).order_by(MeetingAudioChunk.sequence).limit(1))
            if initial and initial.mime_type != MIMES[suffix]:
                raise HTTPException(409, 'Le format de la piste a changé ; créer une autre séance.')
            destination = _root() / sid / track / f'{sequence:08d}-{digest}{suffix}'
            _write_file(destination, raw)
            stored = MeetingAudioChunk(session_id=sid, track=track, sequence=sequence, filename=filename,
                mime_type=MIMES[suffix], storage_path=str(destination), sha256=digest, size_bytes=len(raw),
                start_ms=start_ms, duration_ms=duration_ms)
            from .speech_admission import admit_new_chunk
            admission = admit_new_chunk(db, row, stored)
            db.add(stored)
            append_event(db, row, 'chunk.received', {'track': track, 'sequence': sequence, 'sha256': digest,
                                                  'speech_admission': admission})
            result = {'acknowledged': True, 'sequence': sequence, 'sha256': digest, 'revision': row.revision,
                      'replayed': False, 'speech_admission': admission}
        result.update(session_id=sid, accepted_chunk={'track': track, 'seq': sequence,
            'sha256': digest, 'size_bytes': len(raw)})
        db.add(MeetingSessionCommand(id=command_id, session_id=sid, kind='chunk', operator_id=current_operator().id,
            digest=_digest('chunk', body), body=body, status='completed', result=result))
        db.commit()
        from .live_speech import wake_worker
        if result.get('speech_admission', {}).get('status') == 'pending':
            wake_worker()
        return result


def consolidated_audio(db, row, track='mic'):
    if track not in TRACKS:
        raise HTTPException(422, 'Choisir la piste mic ou system ; mélange non qualifié.')
    chunks = list(db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == row.id,
        MeetingAudioChunk.track == track).order_by(MeetingAudioChunk.sequence)))
    if not chunks:
        raise HTTPException(404, 'Aucun audio sur cette piste.')
    if [chunk.sequence for chunk in chunks] != list(range(len(chunks))):
        raise HTTPException(409, 'Fragments manquants : compléter la capture avant consolidation.')
    data = []
    for chunk in chunks:
        raw = chunk_path(chunk).read_bytes()
        if len(raw) != chunk.size_bytes or hashlib.sha256(raw).hexdigest() != chunk.sha256:
            raise HTTPException(409, 'Fragment audio altéré ; original conservé pour récupération.')
        data.append(raw)
    if len(data) > 1 and chunks[0].mime_type == 'audio/wav':
        output = io.BytesIO()
        try:
            with wave.open(io.BytesIO(data[0]), 'rb') as initial:
                parameters = initial.getparams()
            with wave.open(output, 'wb') as target:
                target.setparams(parameters)
                for raw in data:
                    with wave.open(io.BytesIO(raw), 'rb') as source:
                        if source.getparams()[:3] != parameters[:3]:
                            raise ValueError('PCM format changed')
                        target.writeframes(source.readframes(source.getnframes()))
            return output.getvalue(), chunks[0].mime_type, chunks[0].filename
        except (wave.Error, ValueError, EOFError):
            raise HTTPException(409, 'Fragments WAV incompatibles ; originaux conservés.') from None
    if len(chunks) > 1 and chunks[0].mime_type in {'audio/ogg', 'audio/opus'}:
        from .live_speech import consolidate_session_audio
        mixed = consolidate_session_audio(chunks, chunk_path)
        return mixed.read_bytes(), 'audio/ogg', row.id + '-' + track + '.ogg'
    return b''.join(data), chunks[0].mime_type, chunks[0].filename


def _bind_recording(db, row):
    if row.recording_id or not row.project_id:
        return
    chunks = list(db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == row.id)
        .order_by(MeetingAudioChunk.track, MeetingAudioChunk.sequence)))
    if not chunks:
        return
    tracks = {chunk.track for chunk in chunks}
    timeline_gap = chunks[0].start_ms != 0 or any(
        following.start_ms != previous.start_ms + previous.duration_ms
        for previous, following in zip(chunks, chunks[1:]) if previous.track == following.track)
    if len(tracks) > 1 or timeline_gap or (len(chunks) > 1 and chunks[0].mime_type != 'audio/wav'):
        from .live_speech import consolidate_session_audio
        try:
            path = consolidate_session_audio(chunks, chunk_path)
            raw, mime, filename = path.read_bytes(), 'audio/ogg', row.id + '-mixed.ogg'
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
    else:
        raw, mime, filename = consolidated_audio(db, row, chunks[0].track)
    from backend.app.routers.meeting_audio import import_audio
    # import_audio is already idempotent by immutable audio hash and project.
    db.commit()
    result = import_audio(row.project_id, row.title, row.date, 0, filename, mime, raw)
    row.recording_id = result['id']


def _bind_note(db, row, command, content, title, *, expected_note_revision=None, expected_note_version_id=None):
    from backend.app.db import SessionLocal as ERP
    from backend.app.services import project_notes as notes
    if not row.project_id:
        return None
    # The command was committed in Brain before ERP is entered. Its deterministic
    # nonce safely discovers a note created just before a lost Brain response.
    nonce = str(uuid5(NAMESPACE_URL, 'agent:session-note:' + command.id))
    with ERP() as erp:
        if row.note_id:
            if expected_note_revision is None:
                raise HTTPException(422, 'Révision de la note attendue requise.')
            current = notes.read_note(erp, row.project_id, row.note_id)
            # Replayed NoteSave itself checks the saved command before stale
            # revision handling, so do not pre-reject an already executed nonce.
            from backend.app.project_note_models import NoteVersion
            replay = erp.scalar(select(NoteVersion).where(NoteVersion.project_id == row.project_id, NoteVersion.command_id == nonce))
            if not replay and expected_note_version_id and current['version_id'] != expected_note_version_id:
                raise HTTPException(409, 'La note a changé dans Documents ; conserver la saisie.')
            result = notes.save_note(erp, row.project_id, row.note_id, NoteSave(command_id=nonce,
                expected_revision=expected_note_revision, title=title, content=content, attachment_ids=current['attachment_ids']))
        else:
            result = notes.create_note(erp, row.project_id, NoteCreate(command_id=nonce, title=title, content=content))
        erp.commit()
        row.note_id = result['note']['id']
        return result['note']


def execute_command(db, sid, kind, body):
    row = get_session(db, sid, write=True)
    value = body.model_dump(mode='json')
    if value.get('browser_capture_owner_id') is None:
        value.pop('browser_capture_owner_id', None)  # Legacy receipt digests remain exact.
    previous = db.get(MeetingSessionCommand, value['command_id'])
    if kind == 'resume' and not (previous and previous.status == 'completed'):
        require_enabled(db)
        from . import native_audio
        if native_audio.has_capture_owner():
            raise HTTPException(409, 'Une capture Windows possède déjà les pistes audio ; arrêter cette capture avant de démarrer le navigateur.')
    # Preflight failures leave no pending command to trap the user.
    if kind == 'assign-project':
        bid = _link(value['project_id'])
        from app.models import Project
        if db.get(Project, bid) is None:
            raise HTTPException(409, 'Projet Brain introuvable')
        if row.project_id and row.project_id != value['project_id']:
            raise HTTPException(409, 'Le projet attribué ne peut pas être remplacé implicitement.')
    if kind == 'notes' and row.note_id and value.get('expected_note_revision') is None:
        raise HTTPException(422, 'Révision de note attendue requise.')
    from .audio_cpu_coordinator import AudioCpuBusy, capture_start
    admission = capture_start(db, sid) if kind == 'resume' and not (previous and previous.status == 'completed') else nullcontext()
    try:
        with admission:
            return _execute_command(db, sid, kind, value, row, bid if kind == 'assign-project' else None)
    except AudioCpuBusy as exc:
        raise HTTPException(409, str(exc)) from exc


def _execute_command(db, sid, kind, value, row, bid):
    with _lock:
        if kind in {'resume', 'pause', 'finalize', 'cancel'}:
            db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
            db.expire_all()
            row = get_session(db, sid, write=True)
            previous = db.get(MeetingSessionCommand, value['command_id'])
            if value.get('browser_capture_owner_id') or not (previous and previous.status == 'completed'):
                from .browser_capture import authorize_control
                authorize_control(db, row, kind, value)
        if kind == 'finalize':
            existing = db.get(MeetingSessionCommand, value['command_id'])
            from .native_audio import has_registered_capture
            if not (existing and existing.status == 'completed') and has_registered_capture(sid):
                raise HTTPException(409, 'Arrêter et vérifier la capture Windows avant de conserver ses fragments.')
        command = _begin(db, row, kind, value)
        if command.status == 'completed':
            return command.result
        try:
            if kind == 'resume':
                if row.state not in {'created', 'paused', 'interrupted'}:
                    raise HTTPException(409, 'Cette séance ne peut pas reprendre.')
                row.state = 'recording'
            elif kind == 'pause':
                if row.state != 'recording':
                    raise HTTPException(409, 'Aucune capture active à mettre en pause.')
                row.state = 'paused'
            elif kind == 'cancel':
                if row.state == 'completed':
                    raise HTTPException(409, 'La séance est déjà terminée.')
                row.state = 'cancelled'
            elif kind == 'finalize':
                if row.state == 'cancelled':
                    raise HTTPException(409, 'La capture annulée reste conservée.')
                for track in {chunk.track for chunk in db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == sid))}:
                    consolidated_audio(db, row, track)
                row.state = 'finalizing'
                db.commit()
                _bind_recording(db, row)
                row.state = 'completed'
            elif kind == 'assign-project':
                row.project_id, row.brain_project_id = value['project_id'], bid
                db.commit()
                if row.staged_note and not row.note_id:
                    _bind_note(db, row, command, NoteContent.model_validate(row.staged_note['content']), row.staged_note['title'])
                if row.state == 'completed':
                    _bind_recording(db, row)
            elif kind == 'notes':
                content = NoteContent.model_validate(value['content'])
                title = value['title'].strip()
                if not title:
                    raise HTTPException(422, 'Titre requis')
                if row.project_id:
                    _bind_note(db, row, command, content, title,
                        expected_note_revision=value.get('expected_note_revision'), expected_note_version_id=value.get('expected_note_version_id'))
                else:
                    if any(block.type == 'image' for block in content.blocks):
                        raise HTTPException(422, 'Associer la séance au projet avant de joindre une image.')
                    revision = (row.staged_note or {}).get('revision', 0) + 1
                    plain = content_text(content)
                    encoded = json.dumps(content.model_dump(mode='json'), sort_keys=True, ensure_ascii=False)
                    version = StagedSessionNoteVersion(session_id=sid, revision=revision, title=title,
                        content=content.model_dump(mode='json'), plain_text=plain,
                        sha256=hashlib.sha256(encoded.encode()).hexdigest(), operator_id=current_operator().id)
                    db.add(version)
                    db.flush()
                    row.staged_note = {'title': title, 'content': version.content, 'plain_text': plain,
                                       'revision': revision, 'version_id': version.id}
            else:
                raise HTTPException(422, 'Commande inconnue.')
            return _finish(db, row, command, 'session.' + kind, {'note_id': row.note_id, 'recording_id': row.recording_id})
        except HTTPException as exc:
            db.rollback()
            row = db.get(MeetingSession, sid)
            command = db.get(MeetingSessionCommand, value['command_id'])
            if command:
                command.error = str(exc.detail)[:500]
                # A precondition error cannot have an ERP side effect. Let a
                # fresh revision/command recover the user's preserved draft.
                if kind in {'notes', 'pause', 'resume', 'cancel'} or (kind == 'finalize' and row.state != 'finalizing'):
                    row.pending_command_id = None
                    command.status = 'rejected'
                db.commit()
            raise


def recover_interrupted(db):
    """Startup-only state repair; never restarts the microphone or STT implicitly."""
    from .native_audio import registered_snapshots
    registered = {item['session_id'] for item in registered_snapshots()}
    with _lock:
        db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
        native_paused = select(MeetingSessionEvent.id).where(
            MeetingSessionEvent.session_id == MeetingSession.id,
            MeetingSessionEvent.kind == 'native.capture.owner').exists()
        for row in db.scalars(select(MeetingSession).where(
                (MeetingSession.state == 'recording') | ((MeetingSession.state == 'paused') & native_paused))):
            if row.id in registered:
                continue
            owner = db.scalar(select(MeetingSessionEvent).where(MeetingSessionEvent.session_id == row.id,
                MeetingSessionEvent.kind == 'native.capture.owner')
                .order_by(MeetingSessionEvent.id.desc()).limit(1))
            if row.state == 'paused' and owner:
                stop = db.scalar(select(MeetingSessionCommand).where(MeetingSessionCommand.session_id == row.id,
                    MeetingSessionCommand.kind == 'native.stop', MeetingSessionCommand.created_at >= owner.created_at)
                    .order_by(MeetingSessionCommand.created_at.desc()).limit(1))
                if stop and stop.body.get('_native_drain_confirmed') is True:
                    continue  # A confirmed drain needs SQL conservation, not a new interruption.
            row.state, row.updated_at = 'interrupted', now()
            row.revision += 1
            append_event(db, row, 'native.capture.interrupted' if owner else 'capture.interrupted',
                         {'owner_event_id': owner.id} if owner else {})
        db.commit()


def edit_segment(db, sid, segment_id, body):
    row = get_session(db, sid, write=True)
    segment = db.get(LiveTranscriptSegment, segment_id)
    if segment is None or segment.session_id != sid:
        raise HTTPException(404, 'Segment introuvable dans cette séance')
    value = body.model_dump(mode='json')
    value.update(expected_revision=value['expected_session_revision'], segment_id=segment_id)
    with _lock:
        command = _begin(db, row, 'edit-segment', value)
        if command.status == 'completed':
            return command.result
        try:
            db.refresh(segment)
            if segment.revision != value['expected_segment_revision']:
                raise HTTPException(409, 'Le segment a changé ; conserver la correction et recharger.')
            if not value['text'].strip() or not value['speaker'].strip():
                raise HTTPException(422, 'Texte et intervenant requis')
            segment.text, segment.speaker = value['text'].strip(), value['speaker'].strip()
            segment.revision += 1
            return _finish(db, row, command, 'transcript.corrected',
                {'segment_id': segment_id, 'segment_revision': segment.revision, 'provisional': True})
        except HTTPException as exc:
            db.rollback()
            command = db.get(MeetingSessionCommand, value['command_id'])
            row = db.get(MeetingSession, sid)
            command.status, command.error = 'rejected', str(exc.detail)[:500]
            row.pending_command_id = None
            db.commit()
            raise
