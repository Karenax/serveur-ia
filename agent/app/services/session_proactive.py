"""Separate opt-ins, one reserved AI action per tick; no human note edits."""
import asyncio
from datetime import timezone
import logging
import os
import re
import threading
import unicodedata
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from sqlalchemy import select, text

from .inference_scheduler import DEFAULT_WAIT_SECONDS

LOG = logging.getLogger(__name__)
_stop = threading.Event()
_wake = threading.Event()
_thread = None
_tick_lock = threading.Lock()
_lifecycle_lock = threading.RLock()
_active_attempt = None
TICK_SECONDS = 8
STABLE_SECONDS = 8
QUEUE_WAIT_SECONDS = DEFAULT_WAIT_SECONDS
GENERATION_TIMEOUT_SECONDS = 600
ADMISSION_RETRY_SECONDS = 15
MAX_ADMISSION_RETRY_SECONDS = 60


def _event(db, sid, kind, *, stamp=None):
    from ..meeting_session_models import MeetingSessionEvent
    query = select(MeetingSessionEvent).where(MeetingSessionEvent.session_id == sid, MeetingSessionEvent.kind == kind)
    if stamp is not None:
        query = query.where(MeetingSessionEvent.data['stamp'].as_string() == stamp)
    return db.scalar(query.order_by(MeetingSessionEvent.id.desc()).limit(1))


def _age(event):
    from .meeting_sessions import now
    return (now() - event.created_at.replace(tzinfo=timezone.utc)).total_seconds()


def question_progress(db, row):
    """Read durable progress without launching, retrying or timing out inference."""
    from ..meeting_session_models import LiveTranscriptSegment, MeetingSessionEvent
    from . import meeting_sessions as sessions
    from .settings_service import get_section

    sessions.get_session(db, row.id)
    enabled = bool(get_section(db, 'foresight').get('proactive_enabled', False))
    result = {'state': 'idle' if enabled else 'disabled', 'elapsed_seconds': 0.0,
              'delayed': False, 'enabled': enabled, 'attempt_id': None}
    attempt = db.scalar(select(MeetingSessionEvent).where(
        MeetingSessionEvent.session_id == row.id,
        MeetingSessionEvent.kind == 'assistant.proactive-attempt',
    ).order_by(MeetingSessionEvent.id.desc()).limit(1))
    if attempt is None:
        return result
    result.update(attempt_id=attempt.id, elapsed_seconds=round(max(0, _age(attempt)), 1))
    if attempt.data.get('progress_version') != 1:
        return {**result, 'state': 'unknown'}
    token = attempt.data.get('question_token', '')
    if not isinstance(token, str):
        return {**result, 'state': 'unknown'}
    segment_id, separator, revision = token.rpartition(':')
    segment = db.get(LiveTranscriptSegment, segment_id) if separator else None
    if segment is None or segment.session_id != row.id or str(segment.revision) != revision:
        return {**result, 'state': 'obsolete'}
    outcome = db.scalar(select(MeetingSessionEvent).where(
        MeetingSessionEvent.session_id == row.id,
        MeetingSessionEvent.id > attempt.id,
        MeetingSessionEvent.kind.in_(['assistant.proactive-completed', 'assistant.proactive-error']),
        MeetingSessionEvent.data['question_token'].as_string() == token,
    ).order_by(MeetingSessionEvent.id.desc()).limit(1))
    if outcome is not None:
        elapsed = (outcome.created_at.replace(tzinfo=timezone.utc)
                   - attempt.created_at.replace(tzinfo=timezone.utc)).total_seconds()
        state = 'failed' if outcome.kind == 'assistant.proactive-error' else (
            'obsolete' if outcome.data.get('obsolete') else 'completed')
        return {**result, 'state': state, 'elapsed_seconds': round(max(0, elapsed), 1)}
    if row.state not in {'recording', 'paused'}:
        return {**result, 'state': 'interrupted'}
    if not enabled:
        return {**result, 'state': 'unknown'}
    return {**result, 'state': 'pending', 'delayed': result['elapsed_seconds'] >= 10}


def _admission_failure(failure, attempt):
    """Only a known pre-generation admission refusal is safe to reschedule."""
    if failure is None or failure.id <= attempt.id:
        return False
    if 'retryable' in failure.data:
        return failure.data['retryable'] is True
    # Recover the old queue-only receipts without changing their audit data.
    # Transport errors, cancellations and uncertain crash outcomes never retry.
    return failure.data.get('error') in {
        'Activité IA de fond occupée ; délai d’attente dépassé',
        "Moteur IA occupé ; délai d'attente dépassé",
        'File IA pleine ; réessayer après les demandes en cours',
    }


def _admission_delay(attempt):
    retries = min(int(attempt.data.get('admission_retries', 0)), 2)
    return min(MAX_ADMISSION_RETRY_SECONDS, ADMISSION_RETRY_SECONDS * 2 ** retries)


def _observe(db, row):
    from . import meeting_sessions as sessions, scoped_assistant as assistant
    # SQLite's writer lock makes observations/reservations atomic across workers.
    db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
    db.refresh(row)
    sessions.get_session(db, row.id, write=True)
    stamp, note, segments = assistant.session_snapshot(db, row)
    if row.state not in {'created', 'recording', 'paused', 'completed'} or row.pending_command_id:
        db.rollback()
        return None
    if not note and not any(segment.text.strip() for segment in segments):
        db.rollback()
        return None
    observed = _event(db, row.id, 'enhancement.auto-observed', stamp=stamp)
    if observed is None:
        sessions.append_event(db, row, 'enhancement.auto-observed', {'stamp': stamp})
        db.commit()
        return None
    if _age(observed) < STABLE_SECONDS or _stop.is_set():
        db.rollback()
        return None
    previous = _event(db, row.id, 'enhancement.auto-attempt', stamp=stamp)
    retries = 0
    if previous:
        failure = _event(db, row.id, 'enhancement.auto-error', stamp=stamp)
        if not _admission_failure(failure, previous) or _age(failure) < _admission_delay(previous):
            db.rollback()
            return None
        retries = int(previous.data.get('admission_retries', 0)) + 1
    identity = f'auto-enhancement:{row.id}:{stamp}' + (f':retry:{previous.id}' if previous else '')
    attempt = str(uuid5(NAMESPACE_URL, identity))
    sessions.append_event(db, row, 'enhancement.auto-attempt', {
        'stamp': stamp, 'attempt_id': attempt, 'admission_retries': retries})
    db.commit()  # Persist before scheduling; only confirmed admission refusals retry.
    return stamp, attempt


def automatic_status(db, row):
    from ..meeting_session_models import MeetingSessionEvent
    from . import meeting_sessions as sessions, scoped_assistant as assistant
    from .settings_service import get_section
    enabled = sessions.feature_enabled(db) and bool(get_section(db, 'foresight').get('auto_enhancement_enabled', False))
    stamp, note, _ = assistant.session_snapshot(db, row)
    value = {'enabled': enabled, 'state': 'disabled', 'detail': 'Enrichissement automatique désactivé.',
             'error': None, 'note_version_id': note.get('version_id') if note else None,
             'stable_seconds': STABLE_SECONDS, 'attempt_id': None}
    if not enabled:
        return value
    if _stop.is_set():
        return {**value, 'state': 'stopped', 'detail': 'Nouvelles analyses suspendues ; une génération déjà engagée peut encore se terminer.'}
    attempt = _event(db, row.id, 'enhancement.auto-attempt', stamp=stamp)
    if attempt is None:
        return {**value, 'state': 'waiting', 'detail': 'Attente de stabilité : au moins huit secondes sur les notes et segments enregistrés.'}
    value['attempt_id'] = attempt.data['attempt_id']
    proposal = db.scalar(select(MeetingSessionEvent).where(MeetingSessionEvent.session_id == row.id,
                        MeetingSessionEvent.kind == 'enhancement.proposed', MeetingSessionEvent.data['session_stamp'].as_string() == stamp)
                        .order_by(MeetingSessionEvent.id.desc()).limit(1))
    if proposal:
        current = assistant.context_current(db, row, proposal.data)
        return {**value, 'state': 'completed' if current else 'obsolete', 'detail': 'Proposition disponible ; acceptation humaine requise.' if current else 'Proposition périmée ; relancer depuis le contexte enregistré actuel.'}
    failure = _event(db, row.id, 'enhancement.auto-error', stamp=stamp)
    if failure and failure.id > attempt.id:
        if _admission_failure(failure, attempt):
            remaining = max(0, round(_admission_delay(attempt) - _age(failure)))
            return {**value, 'state': 'waiting', 'retry_after_seconds': remaining,
                    'detail': 'Moteur IA occupé ; nouvelle tentative automatique dès qu’il est disponible. Vos notes sont conservées.'}
        return {**value, 'state': 'failed', 'error': failure.data['error'],
                'detail': 'La tentative n’est pas répétée automatiquement. « Améliorer les notes » permet de réessayer explicitement.'}
    # A reservation recovered after a crash stays visible instead of retrying.
    if _active_attempt != attempt.data['attempt_id'] and _age(attempt) > GENERATION_TIMEOUT_SECONDS + QUEUE_WAIT_SECONDS + TICK_SECONDS:
        return {**value, 'state': 'failed', 'error': 'Résultat de tentative non confirmé après reprise ; la fin de l’ancienne exécution n’est pas attestée.',
                'detail': 'Réessayer explicitement avec « Améliorer les notes » ; aucun rejeu automatique de cet instantané.'}
    return {**value, 'state': 'running', 'detail': 'Analyse de la dernière version enregistrée ; vos saisies non enregistrées sont exclues.'}


def _overlapping_question_attempt(db, row, question):
    """Collapse audio echo/overlap, without a time window or semantic guessing."""
    from ..meeting_session_models import LiveTranscriptSegment, MeetingSessionEvent

    def key(value):
        # Spaces and case can vary between tracks; punctuation can carry an
        # industrial reference, decimal value or fraction and must remain exact.
        return tuple(re.findall(r'\w+|[^\w\s]', unicodedata.normalize('NFKC', value).casefold()))

    wanted = key(question.text)
    candidates = db.scalars(select(LiveTranscriptSegment).where(
        LiveTranscriptSegment.session_id == row.id, LiveTranscriptSegment.id != question.id,
        LiveTranscriptSegment.start_ms < question.end_ms, LiveTranscriptSegment.end_ms > question.start_ms))
    for previous in candidates:
        if key(previous.text) != wanted:
            continue
        token = f'{previous.id}:{previous.revision}'
        if db.scalar(select(MeetingSessionEvent.id).where(MeetingSessionEvent.session_id == row.id,
            MeetingSessionEvent.kind == 'assistant.proactive-attempt',
            MeetingSessionEvent.data['question_token'].as_string() == token).limit(1)):
            return token
    return None


def _tick():
    global _active_attempt
    from ..db import SessionLocal
    from ..meeting_session_models import MeetingSession, LiveTranscriptSegment, MeetingSessionEvent
    from . import meeting_sessions as sessions, scoped_assistant as assistant, session_enhancements as enhancements
    from .settings_service import get_section
    from .inference_scheduler import wait_policy
    with SessionLocal() as db:
        options = get_section(db, 'foresight')
        if not sessions.feature_enabled(db) or not (options.get('proactive_enabled', False) or options.get('auto_enhancement_enabled', False)):
            return
        rows = []
        for row in db.scalars(select(MeetingSession).where(MeetingSession.state.in_(['created', 'recording', 'paused', 'completed']))
                              .order_by(MeetingSession.updated_at.desc()).limit(20)):
            try:
                sessions.get_session(db, row.id, write=True)
                rows.append(row)
            except Exception:
                continue
        # Consider questions across the whole bounded batch before any enrichment.
        if options.get('proactive_enabled', False):
            for row in rows:
                if row.state not in {'recording', 'paused'}:
                    continue
                segments = list(db.scalars(select(LiveTranscriptSegment).where(LiveTranscriptSegment.session_id == row.id)
                                           .order_by(LiveTranscriptSegment.start_ms.desc()).limit(12)))
                for question in (s for s in segments if '?' in s.text and len(s.text.strip()) >= 5):
                    db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
                    db.refresh(row)
                    try:
                        sessions.get_session(db, row.id, write=True)
                    except HTTPException:
                        db.rollback()
                        break
                    if row.state not in {'recording', 'paused'} or row.pending_command_id:
                        db.rollback()
                        break
                    db.refresh(question)
                    if '?' not in question.text or len(question.text.strip()) < 5:
                        db.rollback()
                        continue
                    token = f'{question.id}:{question.revision}'
                    if _stop.is_set() or db.scalar(select(MeetingSessionEvent.id).where(MeetingSessionEvent.session_id == row.id,
                        MeetingSessionEvent.kind.in_(['assistant.proactive-attempt', 'assistant.proactive-duplicate']),
                        MeetingSessionEvent.data['question_token'].as_string() == token).limit(1)):
                        db.rollback()
                        continue
                    duplicate = _overlapping_question_attempt(db, row, question)
                    if duplicate:
                        sessions.append_event(db, row, 'assistant.proactive-duplicate',
                            {'question_token': token, 'duplicate_of': duplicate})
                        db.commit()
                        continue
                    sessions.append_event(db, row, 'assistant.proactive-attempt',
                        {'question_token': token, 'query': question.text, 'progress_version': 1})
                    db.commit()
                    try:
                        with wait_policy(timeout=QUEUE_WAIT_SECONDS, cancel=_stop):
                            result = asyncio.run(assistant.answer(db, row, query=question.text, scope='project' if row.brain_project_id else 'session', live=True, proactive=True))
                        _record_outcome(db, row, 'assistant.proactive-completed', {
                            'question_token': token, 'answer_id': (result or {}).get('id'),
                            'obsolete': bool((result or {}).get('stale') or (result or {}).get('status') == 'obsolete'),
                        })
                    except Exception as exc:
                        db.rollback()
                        _record_outcome(db, row, 'assistant.proactive-error', {'question_token': token, 'error': str(exc)[:1000]})
                        LOG.warning('Proactive question failed: %s', exc)
                    return
        if options.get('auto_enhancement_enabled', False):
            for row in rows:
                try:
                    reserved = _observe(db, row)
                except HTTPException:
                    db.rollback()
                    continue
                if reserved is None:
                    continue
                stamp, attempt = reserved
                _active_attempt = attempt
                try:
                    try:
                        with wait_policy(timeout=QUEUE_WAIT_SECONDS, cancel=_stop):
                            result = asyncio.run(enhancements.propose(db, row, automatic=True, expected_stamp=stamp))
                        _record_outcome(db, row, 'enhancement.auto-finished', {'stamp': stamp, 'attempt_id': attempt, 'proposal_id': result['id'], 'status': result['status']})
                    except Exception as exc:
                        db.rollback()
                        from .inference_scheduler import InferenceBusy
                        from .llm_activity import Deferred
                        retryable = isinstance(exc, (InferenceBusy, Deferred)) and not _stop.is_set()
                        _record_outcome(db, row, 'enhancement.auto-error', {
                            'stamp': stamp, 'attempt_id': attempt, 'error': str(exc)[:1000],
                            'retryable': retryable})
                        LOG.warning('Automatic enhancement failed: %s', exc)
                finally:
                    _active_attempt = None
                return


def _record_outcome(db, row, kind, data):
    from . import meeting_sessions as sessions
    # A project reassignment can revoke this worker's rights during generation.
    # Do not write even its error on the now-inaccessible session.
    db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
    db.refresh(row)
    try:
        sessions.get_session(db, row.id, write=True)
    except HTTPException:
        db.rollback()
        return
    sessions.append_event(db, row, kind, data)
    db.commit()


def tick():
    if _stop.is_set() or not _tick_lock.acquire(blocking=False):
        return
    try:
        _tick()
    finally:
        _tick_lock.release()


def wake_worker():
    """Coalesce committed transcript changes without starting another worker."""
    _wake.set()


def start_worker():
    global _thread
    if os.environ.get('AGENT_TESTING') == '1':
        return
    def loop():
        global _thread
        while True:
            _wake.wait(TICK_SECONDS)
            # Clear before tick: an update during inference must remain pending.
            _wake.clear()
            with _lifecycle_lock:
                # start_worker can rearm a stopped, still-running generation.
                # Exit and clearing the handle share its lock to avoid a lost
                # restart or two simultaneous worker loops.
                if _stop.is_set():
                    _thread = None
                    return
            try:
                tick()
            except Exception:
                LOG.exception('Proactive tick failed')
    with _lifecycle_lock:
        _stop.clear()
        if _thread and _thread.is_alive():
            return
        _thread = threading.Thread(target=loop, name='session-proactive', daemon=True)
        _thread.start()


def stop_worker():
    with _lifecycle_lock:
        _stop.set()
        _wake.set()


def status():
    return {'worker_running': bool(_thread and _thread.is_alive()), 'stop_requested': _stop.is_set(),
        'tick_seconds': TICK_SECONDS, 'wake_on_transcript_commit': True,
        'max_sessions_per_tick': 20, 'max_recent_segments': 12,
        'max_questions_per_tick': 1, 'queue_wait_seconds': QUEUE_WAIT_SECONDS,
        'max_ai_actions_per_tick': 1, 'enhancement_stable_seconds': STABLE_SECONDS,
        'generation_timeout_seconds': GENERATION_TIMEOUT_SECONDS,
        'generation_timeout_scope': 'single transport timeout; not a global wall-clock deadline',
        'cancel_waiting_on_stop': True, 'preempt_running_generation': False}
