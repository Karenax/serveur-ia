"""Pure clocks/locks/events: no subprocess, model, microphone or database."""
from contextlib import contextmanager
from io import StringIO
import json
from pathlib import Path
from types import SimpleNamespace
import threading
from unittest.mock import Mock

import pytest

from app.services import live_speech as live
from app.services.audio_capture import PreparedAudio


class Clock:
    value = 0.0

    def advance(self, seconds):
        self.value += seconds

    def monotonic(self):
        return self.value


class WaitingLock:
    def __init__(self, clock, wait=0, cancel=None):
        self.clock, self.wait, self.cancel = clock, wait, cancel
        self.released = 0

    def acquire(self, timeout):
        used = min(timeout, self.wait)
        self.clock.advance(used)
        self.wait -= used
        if self.cancel is not None:
            self.cancel.set()
            return False
        return self.wait <= 0

    def release(self):
        self.released += 1


def fixture(monkeypatch, *, lock_wait=0):
    clock = Clock()
    monkeypatch.setattr(live, 'time', clock)
    resident = live.ResidentWhisper.__new__(live.ResidentWhisper)
    resident._request_lock = WaitingLock(clock, lock_wait)
    resident._close_lock = threading.RLock()
    resident.process = None
    resident._job = None
    resident.loaded = False
    resident._loaded_profile_key = None
    resident.models = Path('MODEL-FORBIDDEN')
    resident.device_override = None
    resident.close = Mock()
    prepared = PreparedAudio(Path('AUDIO-FICTIVE'), 0, 0, 5000, False)
    return clock, resident, prepared


def test_lock_lease_load_and_response_share_one_budget(monkeypatch):
    clock, resident, prepared = fixture(monkeypatch, lock_wait=2)
    lease_timeouts, load_timeouts = [], []

    @contextmanager
    def lease(_engine, **kwargs):
        lease_timeouts.append(kwargs['timeout'])
        clock.advance(3)
        yield

    def start(**kwargs):
        load_timeouts.append((kwargs['timeout'], kwargs['deadline']))
        clock.advance(2)
        resident.process = SimpleNamespace(stdin=StringIO())

    class Reply:
        def get(self, timeout):
            assert timeout <= .2
            clock.advance(1)
            request = json.loads(resident.process.stdin.getvalue())
            return {'kind': 'result', 'request_id': request['request_id']}

    monkeypatch.setattr(live, 'lease', lease)
    resident.start = start
    resident._events = Reply()
    assert resident.transcribe(prepared, timeout=10)['kind'] == 'result'
    assert lease_timeouts == pytest.approx([8])
    assert load_timeouts[0] == pytest.approx((5, 10))
    assert clock.value == pytest.approx(8)
    assert resident._request_lock.released == 1
    resident.close.assert_not_called()


def test_lease_refusal_does_not_close_an_engine_owned_elsewhere(monkeypatch):
    _clock, resident, prepared = fixture(monkeypatch)

    @contextmanager
    def lease(*_args, **_kwargs):
        raise RuntimeError('Reservation refused')
        yield

    monkeypatch.setattr(live, 'lease', lease)
    resident.start = Mock()
    with pytest.raises(RuntimeError, match='Reservation refused'):
        resident.transcribe(prepared, timeout=10)
    resident.start.assert_not_called()
    resident.close.assert_not_called()
    assert resident._request_lock.released == 1


def test_late_load_cannot_send_or_complete_inference(monkeypatch):
    clock, resident, prepared = fixture(monkeypatch)

    @contextmanager
    def lease(*_args, **_kwargs):
        clock.advance(8)
        yield

    def start(**kwargs):
        assert kwargs['timeout'] == pytest.approx(2)
        clock.advance(3)
        resident.process = SimpleNamespace(stdin=StringIO())

    monkeypatch.setattr(live, 'lease', lease)
    resident.start = start
    with pytest.raises(TimeoutError):
        resident.transcribe(prepared, timeout=10)
    assert resident.process.stdin.getvalue() == ''
    resident.close.assert_called_once()
    assert resident._request_lock.released == 1


def test_late_reply_is_rejected_even_if_it_contains_the_matching_id(monkeypatch):
    clock, resident, prepared = fixture(monkeypatch)

    @contextmanager
    def lease(*_args, **_kwargs):
        yield

    def start(**_kwargs):
        resident.process = SimpleNamespace(stdin=StringIO())

    class Reply:
        def get(self, timeout):
            clock.advance(11)
            request = json.loads(resident.process.stdin.getvalue())
            return {'kind': 'result', 'request_id': request['request_id']}

    monkeypatch.setattr(live, 'lease', lease)
    resident.start = start
    resident._events = Reply()
    with pytest.raises(TimeoutError):
        resident.transcribe(prepared, timeout=10)
    resident.close.assert_called_once()


def test_cancel_while_waiting_for_request_lock_does_not_close_other_work(monkeypatch):
    clock, resident, prepared = fixture(monkeypatch)
    cancel = threading.Event()
    resident._request_lock = WaitingLock(clock, 5, cancel)
    with pytest.raises(InterruptedError):
        resident.transcribe(prepared, timeout=10, cancel=cancel)
    assert clock.value <= .2
    resident.close.assert_not_called()
    assert resident._request_lock.released == 0


def test_queue_wait_observes_cancel_without_waiting_for_the_whole_deadline(monkeypatch):
    clock, resident, _prepared = fixture(monkeypatch)
    cancel = threading.Event()
    calls = []

    class Empty:
        def get(self, timeout):
            calls.append(timeout)
            clock.advance(timeout)
            cancel.set()
            raise live.queue.Empty

    resident._events = Empty()
    with pytest.raises(InterruptedError):
        resident._next_event(1000, cancel)
    assert calls == [.2]


def test_start_does_not_spawn_after_old_process_close_spent_remaining_budget(monkeypatch):
    clock, resident, _prepared = fixture(monkeypatch)
    monkeypatch.setattr(live, 'speech_profile_key', lambda _models: 'fictive-profile')
    spawn = Mock(side_effect=AssertionError('No subprocess allowed'))
    monkeypatch.setattr(live.subprocess, 'Popen', spawn)
    resident.close = Mock(side_effect=lambda: clock.advance(2))
    with pytest.raises(TimeoutError):
        resident.start(timeout=1)
    spawn.assert_not_called()


@pytest.mark.parametrize('stop', ['deadline', 'cancel'])
def test_loaded_start_rechecks_after_profile_lookup_before_announcing_ready(monkeypatch, stop):
    clock, resident, _prepared = fixture(monkeypatch)
    cancel = threading.Event()
    resident.process = SimpleNamespace(poll=lambda: None)
    resident.loaded = True
    resident._loaded_profile_key = 'fictive-profile'

    def profile(_models):
        if stop == 'deadline':
            clock.advance(2)
        else:
            cancel.set()
        return 'fictive-profile'

    monkeypatch.setattr(live, 'speech_profile_key', profile)
    with pytest.raises(TimeoutError if stop == 'deadline' else InterruptedError):
        resident.start(timeout=1, cancel=cancel)
    resident.close.assert_not_called()  # Refusal did not preempt another lease.
