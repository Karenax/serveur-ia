"""Bounded SQL admission, independent of durable audio and model execution.

Mutations require SQLite's writer reservation and never commit on behalf of
the caller. Terminal retained/failed audio has no automatic consumer.
"""
from app.operational_limits import BACKLOG_CHUNKS, BACKLOG_AUDIO_MS
from collections import defaultdict
from pathlib import Path
import wave

from sqlalchemy import case, func, or_, select, text

from app.db_support import utc_iso
from app.meeting_session_models import MeetingAudioChunk, MeetingSession, MeetingSessionEvent, now


POLICY = 'direct-admission-v1'
MAX_CHUNKS = BACKLOG_CHUNKS
MAX_BUDGET_MS = BACKLOG_AUDIO_MS
MIN_COST_MS = 5_000
MAX_DIRECT_MS = 10_000
RETRY_LIMIT = 32
UNKNOWN_COST_MS = MAX_BUDGET_MS + 1
MESSAGES = {
    'direct_disabled': 'Audio conservé ; transcription directe désactivée.',
    'import_manual': 'Audio importé conservé ; demander explicitement son traitement.',
    'duration_unknown': 'Durée inconnue ; audio conservé pour un traitement complet explicite.',
    'chunk_too_long': 'Fragment long ; audio conservé pour un traitement complet explicite.',
    'invalid_pcm': 'WAV ou durée PCM incohérents ; original conservé pour vérification.',
    'audio_unavailable': 'Audio conservé mais indisponible pour le direct ; vérifier sa récupération.',
    'capacity': 'Budget du direct atteint ; enregistrement conservé, reprise explicite nécessaire.',
    'suspended': 'Admission directe suspendue ; enregistrement conservé, reprise explicite nécessaire.',
    'cancelled': 'Séance annulée ; audio conservé sans nouvelle transcription.',
}


def eligible_direct(chunk):
    duration = chunk.duration_ms
    return (isinstance(duration, int) and not isinstance(duration, bool)
            and 0 < duration <= MAX_DIRECT_MS and chunk.track in {'mic', 'system'})


def budget_ms(chunk):
    # Unknown/long historical jobs cannot buy new slots with a guessed five
    # seconds. Their actual running reservation is retained until completion.
    return max(MIN_COST_MS, chunk.duration_ms) if eligible_direct(chunk) else UNKNOWN_COST_MS


def _writer(db):
    # Acquire before refreshing settings/statuses so concurrent upload/retry
    # connections cannot each reserve the last available slot.
    db.execute(text('UPDATE meeting_session_chunks SET speech_status=speech_status WHERE 0'))
    db.expire_all()


def _enabled(db):
    from .meeting_sessions import live_transcription_enabled
    return live_transcription_enabled(db)


def _event(db, row, kind, data):
    from .meeting_sessions import append_event
    return append_event(db, row, kind, {'policy': POLICY, 'at_utc': utc_iso(now()), **data})


def _transition(db, sid):
    return db.scalar(select(MeetingSessionEvent).where(MeetingSessionEvent.session_id == sid,
        MeetingSessionEvent.kind.in_(['transcript.admission.suspended', 'transcript.admission.resumed']))
        .order_by(MeetingSessionEvent.id.desc()).limit(1))


def _suspend(db, row, reason):
    previous = _transition(db, row.id)
    if previous is None or previous.kind != 'transcript.admission.suspended':
        _event(db, row, 'transcript.admission.suspended', {'reason': reason})


def _usage(db):
    cost = case((or_(MeetingAudioChunk.duration_ms <= 0, MeetingAudioChunk.duration_ms > MAX_DIRECT_MS), UNKNOWN_COST_MS),
                (MeetingAudioChunk.duration_ms < MIN_COST_MS, MIN_COST_MS),
                else_=MeetingAudioChunk.duration_ms)
    count, duration = db.execute(select(func.count(MeetingAudioChunk.id), func.coalesce(func.sum(cost), 0))
        .where(MeetingAudioChunk.speech_status.in_(['pending', 'running']))).one()
    # Declared-short running WAVs from an old installation may still contain
    # longer or unreadable PCM. Keep the job, block new admission conservatively.
    for running in db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.speech_status == 'running')):
        if eligible_direct(running) and _reason(running):
            duration += UNKNOWN_COST_MS - budget_ms(running)
    return int(count), int(duration)


def _reason(chunk):
    if not eligible_direct(chunk):
        return 'duration_unknown' if not chunk.duration_ms else 'chunk_too_long'
    if chunk.mime_type not in {'audio/wav', 'audio/ogg', 'audio/opus'}:
        return None
    # Frames are metadata, not a decoder/model invocation. Never read outside
    # the configured capture storage, including historical malformed rows.
    from app.config import settings
    path = Path(chunk.storage_path).resolve()
    if not path.is_relative_to(Path(settings.storage_dir).resolve()) or not path.is_file():
        return 'audio_unavailable'
    try:
        if chunk.mime_type != 'audio/wav':
            with path.open('rb') as source:
                payload = source.read(128 * 1024 + 1)
            # Browser Ogg may have headerless continuation fragments; their
            # existing assembly path remains authoritative. Native fragments
            # are independent Opus containers and have verifiable duration.
            if payload.startswith(b'OggS') and b'OpusHead' in payload[:100]:
                from scripts.audio_codec import opus_duration_ms
                if len(payload) > 128 * 1024:
                    return 'invalid_pcm'
                actual = opus_duration_ms(payload)
                if actual <= 0 or actual > MAX_DIRECT_MS or abs(actual - chunk.duration_ms) > 2:
                    return 'invalid_pcm'
            return None
        with wave.open(str(path), 'rb') as audio:
            if (audio.getcomptype() != 'NONE' or audio.getnchannels() not in {1, 2}
                    or not 8000 <= audio.getframerate() <= 96000 or audio.getsampwidth() not in {1, 2, 3, 4}):
                return 'invalid_pcm'
            actual = round(audio.getnframes() * 1000 / audio.getframerate())
        if actual <= 0 or actual > MAX_DIRECT_MS or abs(actual - chunk.duration_ms) > 2:
            return 'invalid_pcm'
    except (OSError, EOFError, ValueError, wave.Error):
        return 'invalid_pcm'
    return None


def _retain(chunk, reason):
    chunk.speech_status = 'retained'
    chunk.speech_error = MESSAGES[reason]


def _reconcile_locked(db, *, recover_running=False):
    if not _enabled(db):
        count, duration = _usage(db)
        return {'policy': POLICY, 'enabled': False, 'reconciled': False, 'changed_chunks': 0,
                'admitted_chunk_ids': [], 'retained_chunks': 0, 'recovered_running_chunks': 0,
                'bounded': count <= MAX_CHUNKS and duration <= MAX_BUDGET_MS}
    # Actual in-flight work keeps its reservation. Only a caller that has
    # proved no direct CPU owner exists may request orphan running recovery.
    statuses = ['pending', 'running'] if recover_running else ['pending']
    candidates = list(db.execute(select(MeetingAudioChunk, MeetingSession)
        .join(MeetingSession, MeetingAudioChunk.session_id == MeetingSession.id)
        .where(MeetingAudioChunk.speech_status.in_(statuses))
        .order_by(case((MeetingSession.state == 'recording', 0), else_=1),
                  MeetingAudioChunk.created_at, MeetingAudioChunk.sequence, MeetingAudioChunk.id)))
    if recover_running:
        used_count = used_ms = 0
    else:
        running = list(db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.speech_status == 'running')))
        used_count = len(running)
        used_ms = sum(UNKNOWN_COST_MS if _reason(chunk) else budget_ms(chunk) for chunk in running)
    grouped = defaultdict(lambda: {'admitted_chunk_ids': [], 'retained_chunks': 0,
                                  'recovered_running_chunks': 0, 'reasons': defaultdict(int)})
    changed = retained = recovered = 0
    admitted = []
    for chunk, row in candidates:
        group = grouped[row.id]
        reason = 'cancelled' if row.state == 'cancelled' else _reason(chunk)
        if reason is None and (used_count >= MAX_CHUNKS or used_ms + budget_ms(chunk) > MAX_BUDGET_MS):
            reason = 'capacity'
        if reason:
            _retain(chunk, reason)
            group['retained_chunks'] += 1
            group['reasons'][reason] += 1
            retained += 1
            changed += 1
            if reason == 'capacity':
                _suspend(db, row, reason)
        else:
            if chunk.speech_status == 'running':
                chunk.speech_status, chunk.speech_error = 'pending', None
                group['recovered_running_chunks'] += 1
                recovered += 1
                changed += 1
            used_count += 1
            used_ms += budget_ms(chunk)
            group['admitted_chunk_ids'].append(chunk.id)
            admitted.append(chunk.id)
    for sid, data in grouped.items():
        previous = db.scalar(select(MeetingSessionEvent.id).where(MeetingSessionEvent.session_id == sid,
            MeetingSessionEvent.kind == 'transcript.admission.reconciled').limit(1))
        if data['retained_chunks'] or data['recovered_running_chunks'] or previous is None:
            _event(db, db.get(MeetingSession, sid), 'transcript.admission.reconciled',
                   {**data, 'reasons': dict(data['reasons']), 'recover_running': recover_running})
    db.flush()
    return {'policy': POLICY, 'enabled': True, 'reconciled': True, 'changed_chunks': changed,
            'admitted_chunk_ids': admitted, 'retained_chunks': retained, 'recovered_running_chunks': recovered,
            'bounded': used_count <= MAX_CHUNKS and used_ms <= MAX_BUDGET_MS}


def reconcile_queue(db, *, recover_running=False):
    _writer(db)
    return _reconcile_locked(db, recover_running=recover_running)


def admit_new_chunk(db, row, chunk):
    """Decide before adding the chunk ORM object; durable file already exists."""
    _writer(db)
    reason = None
    if not _enabled(db):
        reason = 'direct_disabled'
    elif row.state == 'cancelled':
        reason = 'cancelled'
    elif row.kind == 'import':
        reason = 'import_manual'
    else:
        _reconcile_locked(db)
        reason = _reason(chunk)
        transition = _transition(db, row.id)
        if reason is None and transition and transition.kind == 'transcript.admission.suspended':
            reason = 'suspended'
        if reason is None:
            count, duration = _usage(db)
            if count >= MAX_CHUNKS or duration + budget_ms(chunk) > MAX_BUDGET_MS:
                reason = 'capacity'
                _suspend(db, row, reason)
    if reason:
        _retain(chunk, reason)
    else:
        chunk.speech_status, chunk.speech_error = 'pending', None
    transition = _transition(db, row.id)
    return {'policy': POLICY, 'status': chunk.speech_status, 'reason': reason,
            'admitted_at_utc': utc_iso(now()) if reason is None else None,
            'suspended': bool(transition and transition.kind == 'transcript.admission.suspended')}


def admit_retry(db, row, limit=None):
    if limit is None:
        limit = RETRY_LIMIT
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= RETRY_LIMIT:
        raise ValueError(f'Lot de reprise STT entre 1 et {RETRY_LIMIT} fragments requis')
    _writer(db)
    from .meeting_sessions import require_live_transcription
    require_live_transcription(db)
    _reconcile_locked(db)
    count, duration = _usage(db)
    selected = []
    for chunk in db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == row.id,
            MeetingAudioChunk.speech_status.in_(['failed', 'retained']))
            .order_by(MeetingAudioChunk.created_at, MeetingAudioChunk.sequence, MeetingAudioChunk.id)):
        reason = _reason(chunk)
        if reason:
            continue
        if len(selected) >= limit:
            break
        if count >= MAX_CHUNKS or duration + budget_ms(chunk) > MAX_BUDGET_MS:
            continue
        chunk.speech_status, chunk.speech_error = 'pending', None
        count += 1
        duration += budget_ms(chunk)
        selected.append(chunk.id)
    db.flush()
    transition = _transition(db, row.id)
    resumed = False
    free = count < MAX_CHUNKS and duration + MIN_COST_MS <= MAX_BUDGET_MS
    if free and transition and transition.kind == 'transcript.admission.suspended':
        _event(db, row, 'transcript.admission.resumed', {'reason': 'explicit_retry'})
        resumed = True
    remaining = batch_only = 0
    for chunk in db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == row.id,
                               MeetingAudioChunk.speech_status.in_(['failed', 'retained']))):
        if _reason(chunk):
            batch_only += 1
        else:
            remaining += 1
    return {'retried_chunks': len(selected), 'chunk_ids': selected,
            'remaining_recoverable_chunks': remaining, 'retained_batch_only_chunks': batch_only,
            'admission_resumed': resumed, 'admission_blocked_reason': None if free else 'capacity'}


def session_snapshot(db, row):
    """Only this authorized session's numbers; never expose global IDs/usage."""
    chunks = list(db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == row.id)))
    retained = [chunk for chunk in chunks if chunk.speech_status == 'retained']
    transition = _transition(db, row.id)
    suspended = bool(transition and transition.kind == 'transcript.admission.suspended')
    return {'policy': POLICY, 'suspended': suspended,
            'reason': transition.data.get('reason') if suspended else None,
            'admitted_chunks': sum(chunk.speech_status in {'pending', 'running'} for chunk in chunks),
            'retained_chunks': len(retained),
            'recoverable_direct_chunks': sum(chunk.speech_status in {'failed', 'retained'} and
                _reason(chunk) is None for chunk in chunks),
            'retained_batch_only_chunks': sum(not eligible_direct(chunk) or
                chunk.speech_error in {MESSAGES['invalid_pcm'], MESSAGES['audio_unavailable']} for chunk in retained),
            'last_transition_at_utc': transition.data.get('at_utc') if transition else None}
