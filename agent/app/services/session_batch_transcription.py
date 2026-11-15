"""Explicit, single-slot transcription of retained session audio, without a project.

The admission receipt and immutable audio snapshot live in existing commands.
No queue, model, device or schema is installed at import/startup. A request owns
the CPU token before its first write and until its own resident really closes.
"""
from copy import deepcopy
from contextlib import nullcontext
from dataclasses import dataclass, field, replace
from pathlib import Path
import hashlib
import threading
import time

from fastapi import HTTPException
from sqlalchemy import inspect, select, text

from ..meeting_session_models import LiveTranscriptSegment, MeetingAudioChunk, MeetingSession, MeetingSessionCommand
from ..meeting_session_schemas import Command
from backend.app.services.project_operator import configured_operator, current_operator, operator_context
from . import audio_capture
from . import grouped_batch
from scripts.grouped_pcm_core import GroupRefused

KIND = 'transcription-batch'
ACTIVE = frozenset({'admitted', 'running', 'cancelling'})
BATCH_CHUNK_STATES = frozenset({'batch_pending', 'batch_running'})
MAX_JOB_SECONDS = 72 * 60 * 60
_lock = threading.RLock()
_shutdown = threading.Event()
_active = None


@dataclass
class ActiveBatch:
    command_id: str
    session_id: str
    factory: object
    reservation: object
    cancel: threading.Event = field(default_factory=threading.Event)
    deadline_exceeded: threading.Event = field(default_factory=threading.Event)
    finished: threading.Event = field(default_factory=threading.Event)
    thread: object = None
    resident: object = None
    processes: list = field(default_factory=list)
    interrupted: bool = False


def available():
    from .live_speech import runtime_paths
    from .meeting_audio import runtime_status
    return runtime_status(models_dir=runtime_paths()[1]).get('ready') is True


def _factory(db):
    from sqlalchemy.orm import sessionmaker
    return sessionmaker(bind=db.get_bind().engine, expire_on_commit=False)


def _packet(command):
    value = (command.body or {}).get('_batch')
    return value if isinstance(value, dict) else {}


def _latest(db, sid):
    return db.scalar(select(MeetingSessionCommand).where(
        MeetingSessionCommand.session_id == sid, MeetingSessionCommand.kind == KIND)
        .order_by(MeetingSessionCommand.created_at.desc(), MeetingSessionCommand.id.desc()).limit(1))


def _describe(command):
    packet = _packet(command) if command else {}
    return {'command_id': command.id if command else None, 'state': packet.get('state', 'idle'),
            'selected_chunks': len(packet.get('chunks', [])),
            'completed_chunks': len(packet.get('completed_ids', [])), 'error': packet.get('error')}


def session_status(db, row):
    """Caller has authorized this exact session; never describe another job."""
    return _describe(_latest(db, row.id))


def status(db, sid):
    from .meeting_sessions import get_session
    return session_status(db, get_session(db, sid))


def has_reserved_job(db):
    """Durable CPU guard, including an admission interrupted before spawning."""
    if not inspect(db.get_bind()).has_table('meeting_session_commands'):
        return False
    return bool(db.scalar(select(MeetingSessionCommand.id).where(
        MeetingSessionCommand.kind == KIND,
        MeetingSessionCommand.body['_batch']['state'].as_string().in_(tuple(ACTIVE))).limit(1)))


def _bindings(row):
    return {key: getattr(row, key) for key in ('project_id', 'brain_project_id', 'operator_id', 'recording_id')}


def _actor(operator):
    return {'id': operator.id, 'role': operator.role,
            'project_ids': sorted(operator.project_ids) if operator.project_ids is not None else None,
            'person_id': operator.person_id}


def _chunk_snapshot(chunk):
    return {key: getattr(chunk, key) for key in ('id', 'session_id', 'track', 'sequence', 'storage_path',
        'sha256', 'size_bytes', 'filename', 'mime_type', 'start_ms', 'duration_ms', 'speech_status', 'speech_error')}


def _human_snapshot(db, sid):
    return {segment.id: {'revision': segment.revision,
        'sha256': hashlib.sha256(segment.text.encode()).hexdigest()}
        for segment in db.scalars(select(LiveTranscriptSegment).where(LiveTranscriptSegment.session_id == sid))}


def _validate_authority(db, command, packet):
    from .meeting_sessions import feature_enabled, get_session
    if not feature_enabled(db):
        raise InterruptedError('L’espace de séance est désactivé ; audio et texte conservés')
    if _actor(configured_operator()) != packet['actor']:
        raise InterruptedError('Les droits ont changé ; audio et texte conservés')
    with operator_context(configured_operator()):
        row = get_session(db, command.session_id, write=True)
    if row.state != 'completed' or _bindings(row) != packet['bindings']:
        raise InterruptedError('Le rattachement ou l’état de la séance a changé')
    from ..config import settings
    if str(Path(settings.storage_dir).resolve()) != packet['storage_root']:
        raise InterruptedError('Le stockage de la séance a changé')
    return row


def _validate_snapshot(db, packet):
    """Validate originals and every decode dependency, not just the last chunk."""
    root = Path(packet['storage_root'])
    for snapshot in packet['audio_snapshot']:
        chunk = db.get(MeetingAudioChunk, snapshot['id'])
        if chunk is None or any(getattr(chunk, key) != snapshot[key] for key in (
                'session_id', 'track', 'sequence', 'storage_path', 'sha256', 'size_bytes',
                'filename', 'mime_type', 'start_ms')):
            raise InterruptedError('Un original de la séance a changé')
        if chunk.id not in packet.get('completed_ids', []) and chunk.duration_ms != snapshot['duration_ms']:
            raise InterruptedError('La durée déclarée d’un original a changé')
        audio_capture.stored_path(snapshot, root)
    for identity, snapshot in packet['human_segments'].items():
        segment = db.get(LiveTranscriptSegment, identity)
        if segment is None or (segment.revision, hashlib.sha256(segment.text.encode()).hexdigest()) != (
                snapshot['revision'], snapshot['sha256']):
            raise InterruptedError('Une correction de transcription a changé ; résultat non appliqué')


def _save_packet(command, packet):
    command.body = {**(command.body or {}), '_batch': deepcopy(packet)}


def _writer(db):
    db.execute(text('UPDATE meeting_session_chunks SET speech_status=speech_status WHERE 0'))
    db.expire_all()


def request(db, sid, body):
    from . import meeting_sessions as sessions
    from .audio_cpu_coordinator import AudioCpuBusy, batch_slot
    from ..config import settings
    global _active
    value = Command.model_validate(body if isinstance(body, dict) else body.model_dump(mode='json')).model_dump(mode='json')
    with _lock:
        row = sessions.get_session(db, sid, write=True)
        previous = db.get(MeetingSessionCommand, value['command_id'])
        if previous:
            previous = sessions._begin(db, row, KIND, value)
            if previous.status == 'completed':
                return previous.result  # An old receipt cannot start another model.
            if not (_active and _active.command_id == previous.id):
                recover_orphans(db, sid=sid)
            raise HTTPException(409, 'Admission interrompue : conserver ce reçu et créer une nouvelle commande')
        sessions.require_enabled(db)  # Old receipts above remain replayable while disabled.
        if _shutdown.is_set():
            raise HTTPException(409, 'Serveur en cours d’arrêt ; audio conservé')
        if row.state != 'completed':
            raise HTTPException(409, 'Arrêter et conserver la séance avant le traitement complet')
        if not available():
            raise HTTPException(409, 'Runtime de transcription locale non installé')
        if _active is not None:
            raise HTTPException(409, 'Une transcription complète utilise déjà le moteur audio')
        # Close the read snapshot before CPU admission -> writer lock.
        db.rollback()
        reservation = batch_slot(db, value['command_id'], require_empty_queue=True)
        try:
            reservation.__enter__()
        except AudioCpuBusy as exc:
            raise HTTPException(409, str(exc)) from exc
        active = None
        try:
            _writer(db)
            row = sessions.get_session(db, sid, write=True)
            sessions.require_enabled(db)
            if row.state != 'completed':
                raise HTTPException(409, 'La séance a changé avant l’admission')
            chunks = list(db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == sid)
                .order_by(MeetingAudioChunk.track, MeetingAudioChunk.sequence)))
            selected = [chunk for chunk in chunks if chunk.speech_status in {'pending', 'retained', 'failed'}]
            if not selected:
                raise HTTPException(409, 'Aucun fragment conservé, en attente ou en échec à traiter')
            if sum(chunk.size_bytes for chunk in chunks) > audio_capture.MAX_SESSION_BYTES:
                raise HTTPException(409, 'Volume audio hors de la limite de séance ; originaux conservés')
            if any(chunk.start_ms + chunk.duration_ms > audio_capture.MAX_SESSION_MS for chunk in chunks):
                raise HTTPException(409, 'Audio supérieur à deux heures ; originaux conservés')
            storage = Path(settings.storage_dir).resolve()
            for chunk in chunks:
                try:
                    audio_capture.stored_path(chunk, storage)
                except (OSError, ValueError):
                    raise HTTPException(409, 'Un original audio est absent ou modifié ; vérifier sa récupération') from None
            packet = {'state': 'admitted', 'chunks': [_chunk_snapshot(chunk) for chunk in selected],
                      'audio_snapshot': [_chunk_snapshot(chunk) for chunk in chunks],
                      'human_segments': _human_snapshot(db, sid), 'bindings': _bindings(row),
                      'actor': _actor(current_operator()), 'storage_root': str(storage),
                      'admitted_at': sessions.utc_iso(sessions.now()), 'completed_ids': [], 'error': None}
            packet['grouping_plan'] = grouped_batch.admit_plan(db, packet)
            command = sessions._begin(db, row, KIND, value, server_data={'_batch': packet})
            _writer(db)
            row = sessions.get_session(db, sid, write=True)
            command = db.get(MeetingSessionCommand, value['command_id'])
            sessions.require_enabled(db)  # _begin committed; re-read after writer refresh.
            try:
                grouped_batch.require_active_plan(db, packet)
            except InterruptedError:
                raise HTTPException(409, 'La consolidation groupée a été désactivée avant admission') from None
            if _bindings(row) != packet['bindings'] or row.state != 'completed':
                raise HTTPException(409, 'Le rattachement de la séance a changé avant l’admission')
            try:
                _validate_snapshot(db, packet)
            except (OSError, ValueError, InterruptedError):
                raise HTTPException(409, 'Un original ou une correction a changé avant l’admission') from None
            for snapshot in packet['chunks']:
                chunk = db.get(MeetingAudioChunk, snapshot['id'])
                if chunk.speech_status != snapshot['speech_status']:
                    raise HTTPException(409, 'Le traitement audio a changé avant l’admission')
                chunk.speech_status, chunk.speech_error = 'batch_pending', None
            result = sessions._finish(db, row, command, 'transcript.batch.admitted',
                {'command_id': command.id, 'selected_chunks': len(selected), 'admitted_at': packet['admitted_at']},
                envelope={'batch': _describe(command)})
            active = ActiveBatch(command.id, sid, _factory(db), reservation)
            _active = active
            try:
                _launch(active)
            except Exception:
                _terminal(active, 'interrupted', 'Le traitement n’a pas démarré ; audio conservé')
                raise HTTPException(503, 'Le traitement n’a pas démarré ; reçu et audio conservés') from None
            return result
        except Exception:
            db.rollback()
            if active is None:
                # The request knows it never spawned a process. Settle its own
                # prepared admission rather than leaving audio/notes trapped.
                try:
                    recover_orphans(db, sid=sid)
                except Exception:
                    db.rollback()  # Durable guard still blocks an uncertain job.
                reservation.__exit__(None, None, None)
            elif not active.thread or not active.thread.is_alive():
                _release(active)
            raise


def _launch(active):
    active.thread = threading.Thread(target=_run, args=(active,), name='session-batch-transcription', daemon=True)
    active.thread.start()


def _new_resident(root):
    from .live_speech import ResidentWhisper
    from scripts.speech_runtime import device
    # The UI choice is direct-only. Preserve the explicit service-wide override.
    return ResidentWhisper(Path(root), device_override=device())


def _track_resident(active):
    """Keep child handles even when Resident.close detaches before waiting."""
    resident = active.resident
    original = resident.close
    def close():
        # start() creates its child under this same RLock. Snapshotting before
        # acquiring it can miss a child created just before close detaches it.
        with (getattr(resident, '_close_lock', None) or nullcontext()):
            process = getattr(resident, 'process', None)
            if process is not None:
                with _lock:
                    if not any(known is process for known in active.processes):
                        active.processes.append(process)
            return original()
    resident.close = close


def _all_closed(active):
    try:
        return all(process.poll() is not None for process in active.processes)
    except Exception:
        return False


def _deadline(active):
    # A single wall-clock bound covers lease waiting, model loading and result
    # waiting. The shared resident's individual timeouts are not additive proof.
    if active.finished.is_set():
        return
    active.deadline_exceeded.set()
    active.cancel.set()
    resident = active.resident
    if resident is not None:
        try:
            resident.close()
        except Exception:
            pass  # Only the worker may confirm closure and release the CPU.


def _release(active):
    global _active
    active.reservation.__exit__(None, None, None)
    with _lock:
        if _active is active:
            _active = None
    active.finished.set()


def _terminal(active, state, error=None):
    from .meeting_sessions import append_event, now
    with active.factory() as db:
        _writer(db)
        command = db.get(MeetingSessionCommand, active.command_id)
        if not command:
            db.rollback()
            return
        packet = deepcopy(_packet(command))
        if packet.get('state') not in ACTIVE:
            db.rollback()
            return
        row = db.get(MeetingSession, active.session_id)
        if not row:
            db.rollback()
            return
        for snapshot in packet.get('chunks', []):
            chunk = db.get(MeetingAudioChunk, snapshot['id'])
            if chunk and chunk.speech_status in BATCH_CHUNK_STATES:
                chunk.speech_status = ('failed' if state == 'failed' and chunk.speech_status == 'batch_running'
                                       else 'failed' if snapshot['speech_status'] == 'failed' else 'retained')
                chunk.speech_error = error if chunk.speech_status == 'failed' else snapshot['speech_error']
        packet.update(state=state, error=error, finished_at=now().isoformat())
        _save_packet(command, packet)
        row.revision += 1
        row.updated_at = now()
        append_event(db, row, 'transcript.batch.' + state,
            {'command_id': command.id, 'completed_chunks': len(packet.get('completed_ids', [])), 'error': error})
        db.commit()


def _run(active):
    from .meeting_sessions import append_event
    started = time.monotonic()
    terminal, error = 'completed', None
    watchdog = threading.Timer(MAX_JOB_SECONDS, _deadline, args=(active,))
    watchdog.daemon = True
    watchdog.start()
    try:
        if active.cancel.is_set() or _shutdown.is_set():
            raise InterruptedError()
        with active.factory() as db:
            _writer(db)
            command = db.get(MeetingSessionCommand, active.command_id)
            packet = deepcopy(_packet(command))
            if packet.get('state') not in {'admitted', 'running'}:
                raise InterruptedError()
            _validate_authority(db, command, packet)
            grouped_batch.require_active_plan(db, packet)
            _validate_snapshot(db, packet)
            db.rollback()
        if active.cancel.is_set() or _shutdown.is_set():
            raise InterruptedError()
        work_units = grouped_batch.units(packet)
        active.resident = grouped_batch.resident(packet) or _new_resident(packet['storage_root'])
        _track_resident(active)
        for unit in work_units:
            if active.cancel.is_set() or _shutdown.is_set():
                raise InterruptedError()
            grouped_batch.confirm_final_profile(packet)
            if unit['kind'] == 'group':
                grouped_batch.process_group(__import__(__name__, fromlist=['']), active, unit, started)
                continue
            snapshot = next(item for item in packet['chunks'] if item['id'] == unit['chunk_id'])
            if active.cancel.is_set() or _shutdown.is_set():
                raise InterruptedError()
            with active.factory() as db:
                _writer(db)
                command = db.get(MeetingSessionCommand, active.command_id)
                packet = deepcopy(_packet(command))
                row = _validate_authority(db, command, packet)
                grouped_batch.require_active_plan(db, packet)
                _validate_snapshot(db, packet)
                if packet['state'] not in {'admitted', 'running'}:
                    raise InterruptedError()
                chunk = db.get(MeetingAudioChunk, snapshot['id'])
                if chunk.speech_status != 'batch_pending':
                    raise InterruptedError('Le fragment n’est plus réservé à ce traitement')
                chunk.speech_status = 'batch_running'
                packet.update(state='running', running_chunk_id=chunk.id)
                _save_packet(command, packet)
                append_event(db, row, 'transcript.batch.running', {'command_id': command.id, 'chunk_id': chunk.id})
                db.commit()
            prepared = audio_capture.prepare_chunk(snapshot, packet['audio_snapshot'],
                storage_root=Path(packet['storage_root']),
                derived_root=Path(packet['storage_root']) / 'meeting-sessions' / 'batch-derived')
            if not prepared.assembled:
                # A complete standalone import is not a direct fragment window.
                # Preserve its original declaration in the receipt, and decode
                # all bytes even when old metadata understated its duration.
                prepared = replace(prepared, clip_end_ms=None)
            remaining = MAX_JOB_SECONDS - (time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError()
            result = active.resident.transcribe(prepared, track=snapshot['track'],
                keep_from_ms=snapshot['start_ms'], timeout=remaining, cancel=active.cancel)
            if active.cancel.is_set() or _shutdown.is_set():
                raise InterruptedError()
            grouped_batch.confirm_final_profile(packet)
            with active.factory() as db:
                _writer(db)
                command = db.get(MeetingSessionCommand, active.command_id)
                packet = deepcopy(_packet(command))
                row = _validate_authority(db, command, packet)
                grouped_batch.require_active_plan(db, packet)
                _validate_snapshot(db, packet)
                chunk = db.get(MeetingAudioChunk, snapshot['id'])
                if packet['state'] != 'running' or chunk.speech_status != 'batch_running':
                    raise InterruptedError()
                if active.cancel.is_set() or _shutdown.is_set():
                    raise InterruptedError()
                duration = result.get('duration_ms')
                if not isinstance(duration, int) or isinstance(duration, bool) or not 0 < duration <= audio_capture.MAX_SESSION_MS:
                    raise ValueError('Durée de transcription hors limites')
                audio_end = prepared.offset_ms + duration
                if audio_end > audio_capture.MAX_SESSION_MS:
                    raise ValueError('Horodatage de transcription hors limites')
                if not isinstance(result.get('segments'), list) or len(result['segments']) > 20000:
                    raise ValueError('Résultat de transcription invalide')
                for ordinal, item in enumerate(result['segments']):
                    identity = 'live-' + hashlib.sha256(f'{chunk.id}:{ordinal}'.encode()).hexdigest()
                    if db.get(LiveTranscriptSegment, identity):
                        continue  # Canonical human corrections are never replaced.
                    if not (isinstance(item.get('text'), str) and item['text'].strip() and len(item['text']) <= 10000
                            and isinstance(item.get('start_ms'), int) and isinstance(item.get('end_ms'), int)
                            and chunk.start_ms <= item['start_ms'] <= item['end_ms'] <= audio_end):
                        raise ValueError('Segment de transcription hors limites')
                    db.add(LiveTranscriptSegment(id=identity, session_id=row.id, chunk_id=chunk.id,
                        track=chunk.track, start_ms=item['start_ms'], end_ms=item['end_ms'],
                        speaker=item.get('speaker') or 'UNKNOWN', text=item['text'], revision=1, finalized=False))
                if not prepared.assembled or not chunk.duration_ms:
                    chunk.duration_ms = audio_end - chunk.start_ms
                chunk.speech_status, chunk.speech_error = 'completed', None
                packet['completed_ids'].append(chunk.id)
                packet.pop('running_chunk_id', None)
                _save_packet(command, packet)
                append_event(db, row, 'transcript.updated', {'chunk_id': chunk.id,
                    'segments': len(result['segments']), 'provisional': True, 'mode': 'explicit-batch'})
                if active.cancel.is_set() or _shutdown.is_set():
                    raise InterruptedError()
                db.commit()
        grouped_batch.confirm_final_profile(packet)
    except InterruptedError:
        if active.deadline_exceeded.is_set():
            terminal, error = 'failed', 'Durée limite du traitement atteinte ; audio et corrections conservés'
        else:
            terminal = 'interrupted' if active.interrupted or _shutdown.is_set() or not active.cancel.is_set() else 'cancelled'
            error = 'Traitement interrompu ; audio et corrections conservés' if terminal == 'interrupted' else None
    except GroupRefused as exc:
        terminal, error = 'failed', f'Groupe non appliqué ({str(exc)[:120]}) ; audio et corrections conservés'
    except Exception:
        terminal, error = 'failed', 'La transcription complète a échoué ; audio et corrections conservés'
    finally:
        watchdog.cancel()
        # Never make CPU/capture admission available before process termination.
        try:
            if active.resident is not None:
                active.resident.close()
            if not _all_closed(active):
                return  # Reserved token remains; no fake success/termination.
            _terminal(active, terminal, error)
        except Exception:
            return  # An uncertain close/commit remains reserved for diagnosis.
        _release(active)


def cancel(db, sid, body):
    from . import meeting_sessions as sessions
    value = Command.model_validate(body if isinstance(body, dict) else body.model_dump(mode='json')).model_dump(mode='json')
    row = sessions.get_session(db, sid, write=True)
    with _lock:
        pending = db.get(MeetingSessionCommand, row.pending_command_id) if row.pending_command_id else None
        if pending and pending.kind == KIND and not (_active and _active.command_id == pending.id):
            _writer(db)
            row = sessions.get_session(db, sid, write=True)
            if row.revision != value['expected_revision']:
                raise HTTPException(409, 'La séance a changé ; recharger avant l’annulation')
            row.pending_command_id = None
            db.commit()  # Known secondary orphan; its durable CPU guard remains.
        command = sessions._begin(db, row, 'cancel-transcription-batch', value)
        if command.status == 'completed':
            return command.result
        _writer(db)
        row = sessions.get_session(db, sid, write=True)
        command = db.get(MeetingSessionCommand, value['command_id'])
        job = _latest(db, sid)
        if job and _packet(job).get('state') in ACTIVE:
            packet = deepcopy(_packet(job))
            packet['state'] = 'cancelling'
            _save_packet(job, packet)
        result = sessions._finish(db, row, command, 'transcript.batch.cancel_requested',
            {'command_id': job.id if job else None}, envelope={'batch': _describe(job)})
        active = _active if _active and _active.session_id == sid else None
        if active:
            active.cancel.set()
    if active:
        _stop_active(active)
    elif job and _packet(job).get('state') in ACTIVE:
        # No process handle exists in this installation; explicit cancellation
        # may settle the durable orphan, without loading or re-admitting it.
        recover_orphans(db, sid=sid, terminal='cancelled')
    return result


def _stop_active(active):
    resident = active.resident
    if resident is not None:
        try:
            resident.close()
        except Exception:
            pass  # Keep reservation until the worker verifies closure itself.
    if active.thread is not None and active.thread.is_alive():
        active.finished.wait(5)
    if not active.finished.is_set() and active.thread is not None and not active.thread.is_alive():
        # A previously failed SQL settlement is retried only after the known
        # worker has ended and its process is demonstrably no longer running.
        if _all_closed(active):
            try:
                _terminal(active, 'interrupted' if active.interrupted else 'cancelled')
                _release(active)
            except Exception:
                pass


def cancel_current(*, reason='workspace_disabled'):
    """Cooperative workspace stop; unlike lifespan stop, never seals shutdown.

    Called only by the owner-controlled general-disable route. Its durable
    metadata is session-local; existing admission/cancel receipts stay intact.
    """
    from .meeting_sessions import append_event, now
    with _lock:
        active = _active
        if active is not None:
            active.interrupted = True
            active.cancel.set()  # Signal first, even if the marker write fails.
    if active is None:
        return
    try:
        with active.factory() as db:
            _writer(db)
            command = db.get(MeetingSessionCommand, active.command_id)
            row = db.get(MeetingSession, active.session_id)
            packet = deepcopy(_packet(command)) if command else {}
            if command and row and packet.get('state') in ACTIVE:
                packet.update(state='cancelling', stop_reason=reason,
                              stop_requested_at=now().isoformat())
                _save_packet(command, packet)
                append_event(db, row, 'transcript.batch.interruption_requested',
                             {'command_id': command.id, 'reason': reason})
                db.commit()
            else:
                db.rollback()  # A completed job is not rewritten as cancelled.
    finally:
        # No SQL/global/CPU lock is held during model/process closure. Do not
        # clear the reservation here: _stop_active requires terminal handles.
        _stop_active(active)


def stop_all():
    _shutdown.set()
    with _lock:
        active = _active
        if active:
            active.interrupted = True
            active.cancel.set()
    if active:
        _stop_active(active)


def recover_orphans(db, *, sid=None, terminal='interrupted', startup=False):
    """Startup/explicit orphan settlement, with no model or implicit resume."""
    from .meeting_sessions import append_event, now
    with _lock:
        if not inspect(db.get_bind()).has_table('meeting_session_commands'):
            if startup:
                _shutdown.clear()
            return 0
        _writer(db)
        count = 0
        commands = select(MeetingSessionCommand).where(MeetingSessionCommand.kind == KIND)
        if sid:
            commands = commands.where(MeetingSessionCommand.session_id == sid)
        for command in db.scalars(commands):
            packet = deepcopy(_packet(command))
            if packet.get('state') not in ACTIVE:
                continue
            if _active and _active.command_id == command.id:
                continue  # Own reservation/handle is still authoritative.
            row = db.get(MeetingSession, command.session_id)
            if not row:
                continue
            for snapshot in packet.get('chunks', []):
                chunk = db.get(MeetingAudioChunk, snapshot['id'])
                if chunk and chunk.speech_status in BATCH_CHUNK_STATES:
                    chunk.speech_status = 'failed' if snapshot['speech_status'] == 'failed' else 'retained'
                    chunk.speech_error = snapshot['speech_error']
            error = 'Traitement ancien interrompu ; nouvelle commande explicite nécessaire' if terminal == 'interrupted' else None
            packet.update(state=terminal, error=error, finished_at=now().isoformat())
            _save_packet(command, packet)
            if command.status == 'prepared':
                command.status, command.error = 'rejected', error or 'Traitement annulé avant admission'
            if row.pending_command_id == command.id:
                row.pending_command_id = None
            row.revision += 1
            row.updated_at = now()
            append_event(db, row, 'transcript.batch.' + terminal, {'command_id': command.id, 'reason': 'orphan-settlement'})
            count += 1
        db.commit()
        if startup and _active is None:
            _shutdown.clear()
        return count
