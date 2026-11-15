"""Committed speech wakes the ordinary singleton worker, without extra inference."""
from threading import Event, get_ident

import pytest

from app.services import session_proactive as worker


@pytest.fixture
def isolated_worker(monkeypatch):
    assert worker._thread is None or not worker._thread.is_alive()
    monkeypatch.delenv('AGENT_TESTING', raising=False)
    monkeypatch.setattr(worker, '_thread', None)
    monkeypatch.setattr(worker, '_stop', Event())
    monkeypatch.setattr(worker, '_wake', Event())
    # A wake must work without waiting for this deliberately distant fallback.
    monkeypatch.setattr(worker, 'TICK_SECONDS', 60)
    yield
    thread = worker._thread
    worker.stop_worker()
    if thread:
        thread.join(timeout=3)
        assert not thread.is_alive()


def test_committed_update_wakes_immediately_and_stop_wakes_idle_loop(isolated_worker, monkeypatch):
    entered = Event()
    monkeypatch.setattr(worker, 'tick', entered.set)
    worker.start_worker()
    thread = worker._thread
    worker.wake_worker()
    assert entered.wait(3), 'Must not wait for the 60-second fallback'
    worker.stop_worker()
    thread.join(timeout=3)
    assert not thread.is_alive()
    assert not worker.status()['worker_running']


def test_changes_during_inference_are_coalesced_without_losing_next_tick(isolated_worker, monkeypatch):
    entered, release, continued = Event(), Event(), Event()
    thread_ids = []

    def tick():
        thread_ids.append(get_ident())
        if len(thread_ids) == 1:
            entered.set()
            assert release.wait(3)
        else:
            continued.set()

    monkeypatch.setattr(worker, 'tick', tick)
    worker.start_worker()
    thread = worker._thread
    try:
        worker.wake_worker()
        assert entered.wait(3)
        for _ in range(20):
            worker.wake_worker()
        assert worker._thread is thread
        release.set()
        assert continued.wait(3)
        worker.stop_worker()
        thread.join(timeout=3)
        assert thread_ids == [thread.ident, thread.ident]
    finally:
        release.set()
