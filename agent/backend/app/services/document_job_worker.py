"""Opt-in leased worker. Never installs a schema or publishes to a share."""
import logging
import os
from pathlib import Path
import threading

from fastapi import HTTPException
from sqlalchemy import select

from ..project_document_job_models import DocumentJob
from . import document_jobs as jobs
from .document_worker_lease import WorkerLease
from .project_operator import configured_operator, operator_context

logger=logging.getLogger(__name__)


class DocumentCoordinator:
    def __init__(self, factory, *, storage_root, operator=None):
        self.factory=factory
        self.storage_root=Path(storage_root)
        self.operator=operator
        self._lock=threading.RLock()
        self._stop=threading.Event()
        self._wake=threading.Event()
        self._thread=None
        self._lease=None
        self._state='stopped'
        self._enabled=False
        self._error=''

    def status(self):
        with self._lock:
            alive=bool(self._thread and self._thread.is_alive())
            return {'state':self._state,'enabled':self._enabled,'running':alive,
                'can_submit':alive and self._state=='running' and not self._stop.is_set(),
                'error':self._error}

    def _scope(self, query):
        if self.operator.project_ids is not None:
            query=query.where(DocumentJob.project_id.in_(self.operator.project_ids))
        return query

    def _recover(self):
        # Holding an actual OS lock is the proof of exclusive worker ownership;
        # a PID file, heartbeat or stale timestamp is never sufficient.
        after=''
        while True:
            with self.factory() as db:
                rows=list(db.execute(self._scope(select(DocumentJob.id,DocumentJob.project_id,DocumentJob.revision)
                    .where(DocumentJob.status=='running',DocumentJob.execution_blocked.is_(False),DocumentJob.id>after)).order_by(DocumentJob.id).limit(100)))
            if not rows:
                break
            for row in rows:
                after=row.id
                with self.factory() as db:
                    current=db.get(DocumentJob,row.id)
                    if current.status!='running':
                        continue
                    jobs.recover_interrupted(db,row.project_id,row.id,current.revision)
                    db.commit()

    def start(self, *, enabled=None):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return self.status()
            self._enabled=os.environ.get('AGENT_DOCUMENT_JOBS_ENABLED')=='1' if enabled is None else enabled
            self._error=''
            if not self._enabled:
                self._state='disabled'
                return self.status()
            self.operator=self.operator or configured_operator()
            if self.operator.role=='reader':
                self._state='read_only'
                return self.status()
            with self.factory() as db:
                if not jobs._ready(db):
                    self._state='not_installed'
                    return self.status()
                bind=db.get_bind()
                if bind.dialect.name!='sqlite' or not bind.url.database or bind.url.database==':memory:':
                    raise ValueError('Worker documentaire : base SQLite locale persistante requise')
                lease=WorkerLease(bind.url.database)
            if not lease.acquire():
                self._state='lease_busy'
                return self.status()
            self._lease=lease
            try:
                with operator_context(self.operator):
                    self._recover()
                self._stop.clear()
                self._wake.clear()
                self._state='running'
                self._thread=threading.Thread(target=self._loop,name='document-worker',daemon=True)
                self._thread.start()
            except Exception:
                lease.close()
                self._lease=None
                self._state='failed'
                raise
            return self.status()

    def wake(self):
        self._wake.set()

    def stop(self, *, timeout=5):
        with self._lock:
            self._stop.set()
            self._wake.set()
            thread=self._thread
            if thread and thread.is_alive():
                self._state='stopping'
        if thread and thread is not threading.current_thread():
            thread.join(timeout=timeout)
        # A timeout is not completion: the live thread retains its OS lease.
        return not thread or not thread.is_alive()

    def _next(self):
        with self.factory() as db:
            row=db.execute(self._scope(select(DocumentJob.id,DocumentJob.project_id).where(
                DocumentJob.status.in_({'queued','running'}),DocumentJob.cancel_requested.is_(False),
                DocumentJob.execution_blocked.is_(False),
                DocumentJob.active_attempt_id.is_(None))).order_by(DocumentJob.created_at,DocumentJob.id).limit(1)).first()
            return (row.project_id,row.id) if row else None

    def _loop(self):
        failed=False
        try:
            with operator_context(self.operator):
                while not self._stop.is_set():
                    item=self._next()
                    if item:
                        try:
                            jobs.run_one(self.factory,*item,storage_root=self.storage_root)
                        except HTTPException as exc:
                            if exc.status_code!=409 or str(exc.detail) not in {
                                'Lot modifié : relire avant de réessayer','Lot arrêté ou déjà pris en charge'}:
                                raise
                        continue
                    self._wake.wait(1)
                    self._wake.clear()
        except Exception:
            failed=True
            logger.exception('Document worker stopped; pending attempts and candidate files retained')
        finally:
            with self._lock:
                if self._lease:
                    self._lease.close()
                    self._lease=None
                self._state='failed' if failed else 'stopped'
                if failed:
                    self._error='Le worker documentaire s’est arrêté après une erreur. Consulter le journal serveur.'


_coordinator=None


def get_coordinator():
    global _coordinator
    if _coordinator is None:
        from ..db import APP_DIR, SessionLocal
        _coordinator=DocumentCoordinator(SessionLocal,storage_root=APP_DIR/'document-artifacts')
    return _coordinator


def start_worker():
    if os.environ.get('AGENT_TESTING')=='1':
        return {'state':'testing','can_submit':False}
    return get_coordinator().start()


def stop_worker():
    return True if _coordinator is None else _coordinator.stop()
