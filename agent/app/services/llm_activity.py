"""Reserve idle Agent LLM time; foreground callers take priority between batches."""
from contextlib import contextmanager
import threading
import time

_condition = threading.Condition()
_active = 0
_waiting = 0
_automated_active = 0
_automated_waiting = 0
_background = None
_last_activity = time.monotonic()


class Deferred(RuntimeError):
    """A foreground caller arrived between background requests."""

    def __init__(self, message, *, retry_after_seconds=0):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def owns_idle_slot():
    return _background == threading.get_ident()


def acquire(*, timeout=None, cancel=None, count_as_interaction=True):
    global _active, _waiting, _automated_active, _automated_waiting
    deadline = time.monotonic() + timeout if timeout is not None else None
    with _condition:
        if cancel is not None and cancel.is_set():
            raise Deferred('Demande IA annulée avant son démarrage')
        if _background == threading.get_ident():
            if _waiting > _automated_waiting:
                raise Deferred("Foreground request waiting")
            return False
        _waiting += 1
        if not count_as_interaction:
            _automated_waiting += 1
        try:
            while _background is not None:
                if cancel is not None and cancel.is_set():
                    raise Deferred('Demande IA annulée avant son démarrage')
                remaining = deadline - time.monotonic() if deadline is not None else None
                if remaining is not None and remaining <= 0:
                    raise Deferred('Activité IA de fond occupée ; délai d’attente dépassé')
                _condition.wait(min(remaining, .1) if remaining is not None else .1 if cancel is not None else None)
            _active += 1
            if not count_as_interaction:
                _automated_active += 1
        finally:
            _waiting -= 1
            if not count_as_interaction:
                _automated_waiting -= 1
    return True


def release(acquired, *, count_as_interaction=True):
    global _active, _automated_active, _last_activity
    if acquired:
        with _condition:
            _active -= 1
            if count_as_interaction:
                _last_activity = time.monotonic()
            else:
                _automated_active -= 1
            _condition.notify_all()


@contextmanager
def foreground(*, timeout=None, cancel=None, count_as_interaction=True):
    acquired = acquire(timeout=timeout, cancel=cancel, count_as_interaction=count_as_interaction)
    try:
        yield
    finally:
        release(acquired, count_as_interaction=count_as_interaction)


@contextmanager
def idle(min_idle_seconds=30):
    global _background, _last_activity
    with _condition:
        # The engine lease still serializes calls. Reserve the next turn even
        # when a scan is already running or queued, so continuous scans cannot
        # prevent an analysis from entering the engine queue.
        available = (_active == _automated_active and _waiting == _automated_waiting
                     and _background is None and time.monotonic() - _last_activity >= min_idle_seconds)
        if available:
            _background = threading.get_ident()
    try:
        yield available
    finally:
        if available:
            with _condition:
                _background = None
                _last_activity = time.monotonic()
                _condition.notify_all()


def status():
    with _condition:
        return {"active_calls": _active, "waiting_calls": _waiting,
                "background_active": _background is not None,
                "idle_seconds": round(time.monotonic() - _last_activity, 1),
                "scope": "Agent process; external applications are not observed"}
