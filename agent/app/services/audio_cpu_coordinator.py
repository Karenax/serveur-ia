"""Immediate CPU admission between existing batch audio and live capture.

The lock protects short admissions only. A batch owns a token while running;
capture requests fail immediately instead of waiting behind a four-hour job.
"""
from contextlib import contextmanager
import threading

from sqlalchemy import inspect, select

_guard = threading.RLock()
_batch_owner = None
_direct_jobs = 0


class AudioCpuBusy(ValueError):
    """The existing original/queued job is preserved for an explicit retry."""


def _running_batch(db, *, include_queued=False):
    from ..models import MeetingRecording
    from .session_batch_transcription import has_reserved_job
    states = ('queued', 'running') if include_queued else ('running',)
    return bool(db.scalar(select(MeetingRecording.id).where(MeetingRecording.job_kind == 'transcription',
        MeetingRecording.job_status.in_(states)).limit(1))) or has_reserved_job(db)


def _capture_declared(db):
    from .native_audio import has_capture_owner
    if has_capture_owner():
        return True
    if not inspect(db.get_bind()).has_table('meeting_sessions'):
        return False
    from .browser_capture import active_owners
    if active_owners(db):
        return True
    from ..meeting_session_models import MeetingSession
    return bool(db.scalar(select(MeetingSession.id).where(
        MeetingSession.state.in_(['recording', 'paused', 'finalizing'])).limit(1)))


def ensure_batch_available(db):
    """Request-time check; the worker repeats it atomically before claiming."""
    with _guard:
        if _batch_owner is not None or _direct_jobs or _capture_declared(db):
            raise AudioCpuBusy('Capture ou transcription directe en cours ; audio conservé, relancer le traitement complet après son arrêt')


@contextmanager
def capture_start(db, sid, *, on_refused=None):
    """Hold admission only through the caller's recording-state commit."""
    with _guard:
        if _batch_owner is not None or _running_batch(db):
            error = AudioCpuBusy('Transcription complète en cours ; démarrage audio indisponible jusqu’à sa fin ou son annulation')
            if on_refused is not None:
                on_refused(error)  # Still audio_guard -> session writer; never after admission unlock.
            raise error
        yield


@contextmanager
def batch_slot(db, recording_id, *, require_empty_queue=False):
    global _batch_owner
    token = object()
    with _guard:
        ensure_batch_available(db)
        # The legacy worker may claim its existing queue; a new session batch
        # must not create a second hidden queue ahead of those old admissions.
        if _running_batch(db, include_queued=require_empty_queue):
            raise AudioCpuBusy('Une autre transcription complète utilise déjà le moteur audio')
        _batch_owner = (recording_id, token)
    try:
        yield
    finally:
        with _guard:
            if _batch_owner == (recording_id, token):
                _batch_owner = None


@contextmanager
def direct_speech():
    global _direct_jobs
    with _guard:
        if _batch_owner is not None:
            raise AudioCpuBusy('Transcription complète en cours ; fragment direct conservé en attente')
        _direct_jobs += 1
    try:
        yield
    finally:
        with _guard:
            _direct_jobs -= 1


def status():
    with _guard:
        return {'batch_active': _batch_owner is not None, 'direct_speech_jobs': _direct_jobs,
            'admission_wait_seconds': 0, 'preemption': False,
            'policy': 'Live capture and legacy batch transcription cannot start together',
            'scope': 'Agent process, with canonical recording-state checks'}
