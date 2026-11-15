"""Durable memory retries, manual or automatic, with bounded failure backoff."""
import asyncio
import logging
import os
import threading
from datetime import datetime, timedelta, timezone

from ..db import SessionLocal
from ..models import MemoryProjection

_lock = threading.Lock()
_thread = None
_auto_thread = None
_stop = threading.Event()
AUTO_BATCH = 20
MIN_RETRY_SECONDS = 60
MAX_RETRY_SECONDS = 3600
_state = {'running': False, 'total': 0, 'processed': 0, 'indexed': 0, 'failed': 0, 'error': None}


def snapshot(db):
    with _lock:
        state = dict(_state)
    state['remaining_failed'] = db.query(MemoryProjection).filter_by(status='failed').count()
    state['automatic'] = bool(_auto_thread and _auto_thread.is_alive())
    return state


def reconcile(db):
    from ..workspace_models import MailEnrichmentJob
    for job in db.query(MailEnrichmentJob).filter_by(status='failed', stage='memory'):
        if not job.projection_ids:
            continue
        rows = db.query(MemoryProjection).filter(MemoryProjection.id.in_(job.projection_ids)).all()
        if len(rows) == len(set(job.projection_ids)) and all(row.status == 'indexed' for row in rows):
            job.status, job.stage, job.error = 'completed', 'completed', None
            job.updated_at = datetime.now(timezone.utc)
    db.commit()


def _run(ids):
    from .memory_factory import get_memory_adapter
    from .projections import process
    try:
        for pid in ids:
            if _stop.is_set():
                break
            with SessionLocal() as db:
                row = db.get(MemoryProjection, pid)
                # Never touch an already indexed, obsolete, or manually changed entry.
                counts = asyncio.run(process(db, get_memory_adapter(SessionLocal), projection_ids=[pid], limit=1)) if row and row.status in {'failed', 'pending'} else {}
                if counts.get('failed') and row and row.status in {'failed', 'pending'}:
                    row.projected_at = datetime.now(timezone.utc)
                    db.commit()
                reconcile(db)
            with _lock:
                _state['processed'] += 1
                _state['indexed'] += counts.get('indexed', 0)
                _state['failed'] += counts.get('failed', 0)
    except Exception as exc:
        logging.getLogger(__name__).exception('Reprise mémoire interrompue')
        with _lock:
            _state['error'] = f'{type(exc).__name__} : reprise interrompue, éléments conservés'
    finally:
        with _lock:
            _state['running'] = False


def start(db, automatic=False):
    global _thread
    from .memory_factory import resolve_engine
    if resolve_engine(SessionLocal) != 'eg2':
        from fastapi import HTTPException
        raise HTTPException(409, 'Activer la mémoire EG2 avant la reprise')
    with _lock:
        if not _state['running']:
            query = db.query(MemoryProjection)
            if automatic:
                cutoff = datetime.now(timezone.utc) - timedelta(seconds=MIN_RETRY_SECONDS)
                query = query.filter(MemoryProjection.status.in_(['failed', 'pending']),
                                     MemoryProjection.projected_at <= cutoff)
            else:
                query = query.filter_by(status='failed')
            query = query.order_by(MemoryProjection.projected_at, MemoryProjection.id)
            if automatic:
                query = query.limit(AUTO_BATCH)
            ids = [row.id for row in query.all()]
            _state.update(running=bool(ids), total=len(ids), processed=0, indexed=0, failed=0, error=None)
            _stop.clear()
            if ids:
                _thread = threading.Thread(target=_run, args=(ids,), daemon=True, name='memory-recovery')
                _thread.start()
    return snapshot(db)


def retry_delay(previous, state):
    if state.get('error') or state.get('failed'):
        return min(MAX_RETRY_SECONDS, max(MIN_RETRY_SECONDS, previous * 2))
    return 10


def _automatic_pass():
    from .memory_factory import resolve_engine
    from .projections import active_mail_indexing
    if resolve_engine(SessionLocal) != 'eg2' or active_mail_indexing():
        return None
    with SessionLocal() as db:
        return start(db, automatic=True)


def start_automatic():
    global _auto_thread
    if os.environ.get('AGENT_TESTING') == '1' or (_auto_thread and _auto_thread.is_alive()):
        return
    _stop.clear()

    def supervise():
        delay = 10
        while not _stop.is_set():
            try:
                state = _automatic_pass()
                if state and state['running']:
                    while not _stop.wait(1):
                        with _lock:
                            if not _state['running']:
                                state = dict(_state)
                                break
                    delay = retry_delay(delay, state)
                else:
                    delay = 10
            except Exception:
                logging.getLogger(__name__).exception('Reprise mémoire automatique différée')
                delay = retry_delay(delay, {'error': True})
            _stop.wait(delay)

    _auto_thread = threading.Thread(target=supervise, daemon=True, name='memory-auto-recovery')
    _auto_thread.start()


def stop():
    _stop.set()
    if _auto_thread and _auto_thread is not threading.current_thread():
        _auto_thread.join(timeout=5)
    if _thread and _thread is not threading.current_thread():
        _thread.join(timeout=5)
