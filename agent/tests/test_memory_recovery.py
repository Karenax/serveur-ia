import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import MemoryProjection, Project
from app.services import memory_recovery as recovery


def test_retry_requires_real_memory():
    response = TestClient(app).post('/v1/settings/memory/recovery')
    assert response.status_code == 409


def test_recovery_skips_already_indexed_and_attempts_failures_once(monkeypatch):
    from app.services import projections, memory_factory
    with SessionLocal() as db:
        project = Project(code='RETRY-' + uuid.uuid4().hex, name='Retry')
        db.add(project)
        db.flush()
        failed = MemoryProjection(project_id=project.id, purpose='evidence', content_hash='test', status='failed')
        indexed = MemoryProjection(project_id=project.id, purpose='evidence', content_hash='test', status='indexed')
        db.add_all([failed, indexed])
        db.commit()
        ids = [failed.id, indexed.id]
    calls = []

    async def process(db, mem, **kwargs):
        calls.extend(kwargs['projection_ids'])
        db.get(MemoryProjection, kwargs['projection_ids'][0]).status = 'indexed'
        db.commit()
        return {'indexed': 1, 'failed': 0}

    monkeypatch.setattr(projections, 'process', process)
    monkeypatch.setattr(memory_factory, 'get_memory_adapter', lambda factory: object())
    monkeypatch.setattr(recovery, 'reconcile', lambda db: None)
    monkeypatch.setattr(recovery, '_state', dict(running=True, total=2, processed=0, indexed=0, failed=0, error=None))
    recovery._stop.clear()
    recovery._run(ids)
    assert calls == [ids[0]]
    assert recovery._state['processed'] == 2
    assert recovery._state['indexed'] == 1
    assert not recovery._state['running']


def test_automatic_recovery_is_bounded_and_respects_persisted_cooldown(monkeypatch):
    from app.services import memory_factory
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        project = Project(code='AUTO-' + uuid.uuid4().hex, name='Auto')
        db.add(project)
        db.flush()
        rows = [MemoryProjection(project_id=project.id, purpose='evidence', content_hash='',
                                 status='failed', projected_at=now-timedelta(hours=1)) for _ in range(25)]
        recent = MemoryProjection(project_id=project.id, purpose='evidence', content_hash='', status='failed', projected_at=now)
        indexed = MemoryProjection(project_id=project.id, purpose='evidence', content_hash='', status='indexed', projected_at=now-timedelta(hours=1))
        db.add_all(rows + [recent, indexed])
        db.commit()
        recent_id, indexed_id = recent.id, indexed.id
    monkeypatch.setattr(memory_factory, 'resolve_engine', lambda factory: 'eg2')
    monkeypatch.setattr(recovery, '_state', dict(running=False))
    calls = []

    class Thread:
        def __init__(self, **kwargs):
            calls.extend(kwargs['args'][0])

        def start(self):
            pass

    monkeypatch.setattr(recovery.threading, 'Thread', Thread)
    monkeypatch.setattr(recovery, '_thread', None)
    with SessionLocal() as db:
        recovery.start(db, automatic=True)
    assert len(calls) == recovery.AUTO_BATCH
    assert recent_id not in calls and indexed_id not in calls


def test_auto_backoff_increases_caps_and_resets_after_success():
    assert recovery.retry_delay(10, {'failed': 1}) == 60
    assert recovery.retry_delay(60, {'failed': 1}) == 120
    assert recovery.retry_delay(3000, {'error': True}) == 3600
    assert recovery.retry_delay(3600, {'indexed': 20, 'failed': 0}) == 10


@pytest.mark.skipif(os.name != 'nt', reason='Windows Job Object')
def test_windows_children_exit_after_abrupt_parent_stop(tmp_path):
    record = tmp_path / 'child.json'
    script = ("from app.services.child_process import protect_children; "
              "import subprocess,sys,json,time; protect_children(); "
              "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']); "
              f"open({str(record)!r},'w').write(json.dumps(child.pid)); time.sleep(60)")
    parent = subprocess.Popen([sys.executable, '-c', script])
    try:
        until = time.monotonic() + 10
        while not record.exists() and time.monotonic() < until:
            time.sleep(.05)
        assert record.exists(), 'Parent failed to create child'
        child_id = json.loads(record.read_text())
        import ctypes
        from ctypes import wintypes as w
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        kernel.OpenProcess.restype = w.HANDLE
        kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        kernel.CloseHandle.argtypes = [w.HANDLE]
        child = kernel.OpenProcess(0x100000, False, child_id)
        assert child
        parent.kill()
        parent.wait(timeout=5)
        try:
            assert kernel.WaitForSingleObject(child, 5000) == 0
        finally:
            kernel.CloseHandle(child)
    finally:
        if parent.poll() is None:
            parent.kill()
        parent.wait(timeout=5)
