"""Proactive waits are cancellable before inference; legacy defaults persist."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time
from uuid import uuid4

import pytest

from app.services import ai_client, inference_scheduler as scheduler, llm_activity


def test_proactive_queue_deadline_removes_waiter_and_restores_policy():
    resource = 'proactive-deadline-' + uuid4().hex
    def wait():
        with scheduler.wait_policy(timeout=.05), scheduler.lease(resource):
            pytest.fail('occupied engine admitted')
    with scheduler.lease(resource), ThreadPoolExecutor(max_workers=1) as executor:
        with pytest.raises(scheduler.InferenceBusy, match='délai'):
            executor.submit(wait).result(timeout=2)
        assert scheduler.status()['waiting'] == 0
    assert scheduler.waiting_policy() == (None, None)


def test_stop_cancels_waiting_generation_without_preempting_owner():
    from app.services.session_proactive import QUEUE_WAIT_SECONDS
    resource, stopped = 'proactive-cancel-' + uuid4().hex, Event()
    entered = Event()
    def wait():
        entered.set()
        with scheduler.wait_policy(timeout=QUEUE_WAIT_SECONDS, cancel=stopped), scheduler.lease(resource):
            pytest.fail('cancelled engine admitted')
    with scheduler.lease(resource), ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(wait)
        assert entered.wait(1)
        deadline = time.monotonic() + 1
        while not scheduler.status()['waiting'] and time.monotonic() < deadline:
            stopped.wait(.01)
        stopped.set()
        with pytest.raises(scheduler.InferenceBusy, match='annulée'):
            future.result(timeout=1)
        assert scheduler.status()['active'] >= 1 and scheduler.status()['waiting'] == 0


def test_automatic_wait_survives_the_old_two_second_cutoff():
    from app.services.session_proactive import QUEUE_WAIT_SECONDS
    resource = 'automatic-normal-contention-' + uuid4().hex
    started = Event()

    def automatic():
        started.set()
        with scheduler.priority_scope('enhancement'), scheduler.wait_policy(timeout=QUEUE_WAIT_SECONDS):
            with scheduler.lease(resource):
                return 'admitted after the ongoing request'

    with ThreadPoolExecutor(max_workers=1) as executor:
        with scheduler.lease(resource):
            future = executor.submit(automatic)
            assert started.wait(1)
            Event().wait(2.1)
            assert not future.done(), 'Automatic work abandoned a healthy busy engine after two seconds'
        assert future.result(timeout=1) == 'admitted after the ongoing request'


def test_proactive_foreground_idle_wait_is_also_bounded_and_cancellable(monkeypatch):
    monkeypatch.setattr(llm_activity, '_background', -1)
    monkeypatch.setattr(ai_client.urllib.request, 'urlopen', lambda *args, **kwargs: pytest.fail('network must not start'))
    before = llm_activity.status()
    with scheduler.wait_policy(timeout=.05):
        with pytest.raises(llm_activity.Deferred, match='délai'):
            ai_client._post_json('http://127.0.0.1:1234/v1/chat/completions', {})
    stopped = Event()
    stopped.set()
    with scheduler.wait_policy(timeout=2, cancel=stopped):
        with pytest.raises(llm_activity.Deferred, match='annulée'):
            ai_client._post_json('http://127.0.0.1:1234/v1/chat/completions', {})
    assert llm_activity.status()['active_calls'] == before['active_calls']
    assert llm_activity.status()['waiting_calls'] == before['waiting_calls']


def test_background_chat_default_still_returns_none_but_proactive_exposes_busy(monkeypatch):
    cfg = {'enabled': True, 'provider': 'openai_compatible', 'base_url': 'http://127.0.0.1:1234',
        'model': 'fixture', 'fallback_enabled': False}
    monkeypatch.setattr(ai_client, '_chat_content', lambda *args, **kwargs: (_ for _ in ()).throw(scheduler.InferenceBusy('fixture busy')))
    assert ai_client.chat_text(cfg, []) is None
    with pytest.raises(scheduler.InferenceBusy, match='fixture'):
        ai_client.chat_text(cfg, [], timeout=45, raise_errors=True)
